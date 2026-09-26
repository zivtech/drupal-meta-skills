"""Optional --render-explorer output: data files shaped like the pilot
run's own explorer viewer data, for a future explorer viewer to consume.

Documented follow-up: this writes DATA only. It does not port the explorer
HTML/JS viewer itself — that stays a follow-up once the domain-token
generalization work happens.
"""
from __future__ import annotations

import json
from pathlib import Path


def _keyed_by_id(components: list[dict], kind: str) -> dict:
    return {c["id"]: c for c in components if c["kind"] == kind}


def write_explorer_data(source_structure: dict, output_dir: str) -> Path:
    out_dir = Path(output_dir) / "explorer"
    out_dir.mkdir(parents=True, exist_ok=True)

    components = source_structure.get("components", [])
    paragraphs = _keyed_by_id(components, "paragraph_type")
    blocks = {
        "block_content_types": _keyed_by_id(components, "block_content_type"),
        "block_content": _keyed_by_id(components, "block_content"),
        "placements": {p["id"]: p for p in source_structure.get("placements", [])},
        "menus": {m["id"]: m for m in source_structure.get("menus", [])},
    }

    (out_dir / "paragraphs.json").write_text(json.dumps(paragraphs, indent=2) + "\n", encoding="utf-8")
    (out_dir / "blocks.json").write_text(json.dumps(blocks, indent=2) + "\n", encoding="utf-8")
    return out_dir
