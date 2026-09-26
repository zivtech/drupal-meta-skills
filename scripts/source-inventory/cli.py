#!/usr/bin/env python3
"""drupal-source-inventory CLI.

    python3 cli.py analyze --profile path/to/project.profile.yaml

See profile.example.yaml for the profile shape. Read-only against the
source: every DB call in db.py is a SELECT/SHOW, and this tool never
writes to config or the source database.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import assemble  # noqa: E402
import explorer_export  # noqa: E402
from db import DbError  # noqa: E402
from site_profile import ProfileError, load_profile  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="drupal-source-inventory")
    sub = parser.add_subparsers(dest="command", required=True)

    analyze_p = sub.add_parser("analyze", help="Run the full inventory and write source-structure.json")
    analyze_p.add_argument("--profile", required=True, help="Path to a profile YAML (see profile.example.yaml)")
    analyze_p.add_argument(
        "--samples", action="store_true",
        help="Enable sample values in field output. OFF by default. Even when on, every "
             "sample is regex-scrubbed for emails/phones/SSNs before it is written.",
    )
    analyze_p.add_argument("--no-db", action="store_true", help="Config-only dry run: skip every DB-backed extractor.")
    analyze_p.add_argument("--output-dir", default=None, help="Override the profile's output.dir")
    analyze_p.add_argument(
        "--render-explorer", action="store_true",
        help="Also write explorer-ready data files under <output-dir>/explorer/. "
             "Documented follow-up: does not port the explorer HTML/JS viewer itself.",
    )
    return parser


def _report_library_bundles(items: list[dict]) -> None:
    """paragraph_bundle is "" only for an item whose wrapped paragraph could
    not be found; say so on stderr rather than leaving it to be noticed."""
    missing = [str(i["id"]) for i in items if not i.get("paragraph_bundle")]
    if missing:
        print(f"WARNING: {len(missing)}/{len(items)} library item(s) have no wrapped paragraph bundle "
              f"(paragraph_bundle is empty): {', '.join(missing[:10])}", file=sys.stderr)
    elif items:
        print(f"Library items: {len(items)}/{len(items)} wrapped paragraph bundles resolved")


def run_analyze(args: argparse.Namespace) -> int:
    try:
        prof = load_profile(args.profile)
    except ProfileError as exc:
        print(f"Profile error: {exc}", file=sys.stderr)
        return 2

    db = None if args.no_db else prof.db
    try:
        result = assemble.analyze(prof, db=db, samples_enabled=args.samples)
    except DbError as exc:
        print(f"Database error: {exc}", file=sys.stderr)
        print("Re-run with --no-db for a config-only dry run.", file=sys.stderr)
        return 1

    issues = assemble.validate_against_schema(result)
    if issues:
        print("source-structure.json FAILED schema validation:", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1

    output_dir = args.output_dir or prof.output_dir
    out_path = assemble.write_source_structure(result, output_dir)
    print(f"Wrote {out_path}")
    total = result["counts"]["total"]
    print(f"Components: {total}")
    for kind, n in sorted(result["counts"].items()):
        if kind != "total":
            print(f"  {kind}: {n}")
    dq = result.get("data_quality", {}).get("parent_chain")
    if dq:
        print(
            f"Data quality: {dq['stale_denormalized_parent_rows']}/{dq['total_child_rows']} "
            f"({dq['stale_pct']}%) denormalized parent rows disagreed with live reference tables"
        )
    unresolved = result.get("data_quality", {}).get("unresolved_tables")
    if unresolved:
        print(f"WARNING: {len(unresolved)} field table(s) not found in the live schema; "
              "their rows are missing from the purpose shown:", file=sys.stderr)
        for u in unresolved:
            print(f"  {u['entity_type']}.{u['field_name']} ({u['purpose']})", file=sys.stderr)
    elif unresolved is not None:
        print("Field tables: all resolved against the live schema")
    _report_library_bundles(result.get("library_items", []))

    if args.render_explorer:
        explorer_dir = explorer_export.write_explorer_data(result, output_dir)
        print(f"Wrote explorer-ready data files to {explorer_dir}/ (data only; no HTML viewer)")

    return 0


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "analyze":
        return run_analyze(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
