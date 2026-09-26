#!/usr/bin/env python3
"""Validate a (source-structure.json, dispositions.json) pair against the
source-structure contract.

Checks performed (see README.md "Gates this contract feeds"):

1. Both files validate against their JSON Schemas in this directory.
2. `contract_version` on both files matches this directory's VERSION file
   (major component must match exactly; this script does not attempt to
   support cross-major reads).
3. `dispositions.json.source_structure_hash` matches the sha256 of the
   paired `source-structure.json` (canonical form: sorted keys, no
   whitespace) — staleness detection.
4. Completeness (Gate G1, the half of it this contract can check without a
   runtime): every `components[].key` (`{kind}:{id}` -- bare `id` is only
   unique within a kind, not globally) in source-structure.json has
   exactly one row in `dispositions.json.types`; every row in `types`
   refers to a real component key. Any undispositioned component is a
   nonzero exit.
5. `counts` in dispositions.json reconciles with the verdict tally actually
   present in `types`.
6. Every disposition row whose verdict is not DROP/DEFER has a non-empty
   `destinations` list (the CONTENT/STRUCTURED/etc. rows must say where
   things go; DROP/DEFER are explicitly exempt because DROP is documented
   as "not migrated" and DEFER as "pending a named downstream decision").

This script is the drupal-meta-skills-side half of Gate G1. It intentionally
does NOT implement Gate G2/G3/G4 (data-blind flattening, non-node export
completeness, non-empty destination at conversion time) — those need a live
runtime/converter and are out of scope for a static two-file check.

Usage:
    python3 validate-dispositions.py <source-structure.json> <dispositions.json>

Exit code 0 on success, 1 on any validation failure (all issues are printed,
not just the first).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

try:
    import jsonschema
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit(
        "jsonschema is required. Install with: pip install jsonschema"
    ) from exc

CONTRACT_DIR = Path(__file__).resolve().parent
NON_DESTINATION_REQUIRED_VERDICTS = {"DROP", "DEFER"}


def canonical_json_bytes(data: Any) -> bytes:
    """Canonical form used for hashing: sorted keys, no extra whitespace."""
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(data)).hexdigest()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def contract_version() -> str:
    return (CONTRACT_DIR / "VERSION").read_text(encoding="utf-8").strip()


def major(version: str) -> str:
    return version.split(".", 1)[0]


def validate_schema(instance: Any, schema_path: Path, label: str) -> list[str]:
    schema = load_json(schema_path)
    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    issues = []
    for err in sorted(validator.iter_errors(instance), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in err.path) or "<root>"
        issues.append(f"{label} schema violation at {loc}: {err.message}")
    return issues


def check_contract_versions(source_structure: dict, dispositions: dict) -> list[str]:
    issues = []
    expected = contract_version()
    for label, doc in (("source-structure.json", source_structure), ("dispositions.json", dispositions)):
        v = doc.get("contract_version")
        if not v:
            issues.append(f"{label}: missing contract_version")
            continue
        if major(v) != major(expected):
            issues.append(
                f"{label}: contract_version {v} has a different major version "
                f"than this contract's VERSION ({expected}); refusing to validate "
                f"across a major version boundary"
            )
    return issues


def check_hash(source_structure: dict, dispositions: dict) -> list[str]:
    expected_hash = sha256_of(source_structure)
    actual_hash = dispositions.get("source_structure_hash")
    if actual_hash != expected_hash:
        return [
            "dispositions.json.source_structure_hash does not match the sha256 "
            f"of the paired source-structure.json (expected {expected_hash}, "
            f"got {actual_hash!r}). The inventory changed since dispositions "
            "were authored/regenerated - re-review before trusting counts."
        ]
    return []


def check_completeness(source_structure: dict, dispositions: dict) -> list[str]:
    # NOTE: bare component `id` is only unique WITHIN a kind (verified
    # against a live source: paragraphs_library_item and block_content are
    # separate tables whose auto-increment ids both start at 1, so the same
    # integer id occurs in both; a placement and a menu can share a machine
    # name). `key` (`{kind}:{id}`) is the actual
    # identity used for completeness/disposition matching.
    issues = []
    component_keys = [c["key"] for c in source_structure.get("components", [])]
    component_key_set = set(component_keys)
    if len(component_keys) != len(component_key_set):
        dupes = sorted({k for k in component_keys if component_keys.count(k) > 1})
        issues.append(f"source-structure.json has duplicate component keys: {dupes}")

    disposition_keys = set(dispositions.get("types", {}).keys())

    undispositioned = sorted(component_key_set - disposition_keys)
    if undispositioned:
        issues.append(
            "package.component_undispositioned: components with no dispositions "
            f"row (Gate G1 FAIL): {undispositioned}"
        )

    orphaned = sorted(disposition_keys - component_key_set)
    if orphaned:
        issues.append(
            "dispositions.json has rows for keys that are not in source-structure.json's "
            f"components[]: {orphaned}"
        )
    return issues


def check_counts_reconcile(dispositions: dict) -> list[str]:
    issues = []
    declared = dispositions.get("counts", {})
    actual: dict[str, int] = {}
    for row in dispositions.get("types", {}).values():
        v = row.get("verdict")
        if v:
            actual[v] = actual.get(v, 0) + 1
    actual["total"] = sum(v for k, v in actual.items() if k != "total")

    for key, expected_count in declared.items():
        actual_count = actual.get(key, 0)
        if actual_count != expected_count:
            issues.append(
                f"dispositions.json.counts['{key}']={expected_count} does not "
                f"reconcile with the actual tally ({actual_count}) over types{{}}"
            )
    for key, actual_count in actual.items():
        if key not in declared and actual_count:
            issues.append(
                f"dispositions.json.counts is missing key '{key}' "
                f"(actual tally: {actual_count})"
            )
    return issues


def check_destinations_present(dispositions: dict) -> list[str]:
    issues = []
    for comp_id, row in dispositions.get("types", {}).items():
        verdict = row.get("verdict")
        if verdict in NON_DESTINATION_REQUIRED_VERDICTS:
            continue
        destinations = row.get("destinations") or []
        if not destinations:
            issues.append(
                f"types['{comp_id}']: verdict={verdict} requires a non-empty "
                "destinations list (only DROP/DEFER are exempt)"
            )
        for cv in row.get("conditional_verdicts", []) or []:
            cv_verdict = cv.get("verdict")
            if cv_verdict in NON_DESTINATION_REQUIRED_VERDICTS:
                continue
            if not (cv.get("destinations") or []):
                issues.append(
                    f"types['{comp_id}'].conditional_verdicts (when={cv.get('when')!r}): "
                    f"verdict={cv_verdict} requires a non-empty destinations list"
                )
    return issues


def validate(source_structure: dict, dispositions: dict) -> list[str]:
    """Run every check; return the full list of issues (empty = valid)."""
    issues: list[str] = []
    issues += validate_schema(
        source_structure, CONTRACT_DIR / "source-structure.schema.json", "source-structure.json"
    )
    issues += validate_schema(
        dispositions, CONTRACT_DIR / "dispositions.schema.json", "dispositions.json"
    )
    # The remaining checks assume basic schema shape; skip them if the schema
    # checks already failed hard enough that key lookups would be meaningless.
    if not issues:
        issues += check_contract_versions(source_structure, dispositions)
        issues += check_hash(source_structure, dispositions)
        issues += check_completeness(source_structure, dispositions)
        issues += check_counts_reconcile(dispositions)
        issues += check_destinations_present(dispositions)
    return issues


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    ss_path, disp_path = Path(argv[1]), Path(argv[2])
    source_structure = load_json(ss_path)
    dispositions = load_json(disp_path)

    issues = validate(source_structure, dispositions)
    if issues:
        print(f"Validation FAILED ({len(issues)} issue(s)):")
        for issue in issues:
            print(f"- {issue}")
        return 1

    total = len(source_structure.get("components", []))
    print(f"Validation passed. Dispositioned: {total}/{total}")
    print(f"Source structure file: {ss_path}")
    print("Data classification: reviewed" if all(
        row.get("role_source") == "reviewed"
        for row in dispositions.get("types", {}).values()
        if "role_source" in row
    ) else "Data classification: heuristic-or-mixed")
    print("Export scope: graph-walk (runtime-enforced, not checked here)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
