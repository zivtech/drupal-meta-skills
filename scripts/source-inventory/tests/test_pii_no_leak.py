"""PII regression test: an email/phone regex over every fixture and every
output file must return zero hits.

Covers:
1. Every committed fixture in this repo (contract fixtures + this skill's
   own test fixtures) — the parks-district-shaped, invented data must be clean by
   construction.
2. A source-structure.json assembled end-to-end from the fixtures.
3. A field-profile run with samples ON and synthetic rows that DO contain
   embedded PII, asserting the pipeline's own scrubbing removes it before
   it would ever reach an output file (samples are off by default in the
   CLI; this proves the scrubbing itself works, not just the default).
"""
import json
from pathlib import Path

import pii
from site_profile import PiiConfig

import assemble
from extract_field_profile import compute_field_profile
from test_assemble import build_fixture_profile

REPO_ROOT = Path(__file__).resolve().parents[3]


def all_committed_fixture_texts() -> list[tuple[str, str]]:
    texts = []
    for base in [
        REPO_ROOT / "contracts" / "source-structure" / "fixtures",
        Path(__file__).resolve().parent / "fixtures",
    ]:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix in {".json", ".yml", ".yaml", ".twig", ".theme"}:
                texts.append((str(path), path.read_text(encoding="utf-8", errors="replace")))
    return texts


def test_no_pii_in_any_committed_fixture():
    leaks = {}
    for path, text in all_committed_fixture_texts():
        findings = pii.assert_no_pii(text)
        if findings:
            leaks[path] = findings
    assert leaks == {}, f"PII found in committed fixtures: {leaks}"


def test_no_pii_in_assembled_source_structure(config_dir, theme_dir):
    prof = build_fixture_profile(config_dir, theme_dir)
    result = assemble.analyze(prof, db=None, samples_enabled=False)
    text = json.dumps(result)
    assert pii.assert_no_pii(text) == []


def test_field_profile_scrubs_pii_before_it_would_reach_output():
    rows = [
        {"fname": "field_notes", "entity_id": "1", "delta": 0,
         "val": "Contact staffer@example-parks.org or call (202) 555-0199"},
        {"fname": "field_description", "entity_id": "2", "delta": 0,
         "val": "Open 10am-5pm daily; reach the desk at 555-987-6543 with questions"},
    ]
    profile = compute_field_profile(rows, total_instances=2, pii_config=PiiConfig(), samples_enabled=True)
    serialized = json.dumps(profile)
    findings = pii.assert_no_pii(serialized)
    assert findings == [], f"PII leaked through compute_field_profile: {findings}"
