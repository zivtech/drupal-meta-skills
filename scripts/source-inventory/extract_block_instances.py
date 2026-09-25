"""block_content entities (kind=block_content): the specific editor-authored
block instances, as distinct from block_content_type (the bundle) and
placement (where an instance is shown)."""
from __future__ import annotations

from db import fetch_rows
from site_profile import DbConfig


def fetch_block_content_instances(db: DbConfig) -> list[dict]:
    return fetch_rows(db, "SELECT id, info, type FROM block_content_field_data;")


def build_block_instance_components(db: DbConfig | None) -> list[dict]:
    if db is None:
        return []
    rows = fetch_block_content_instances(db)
    return [
        {"id": r["id"], "kind": "block_content", "label": r.get("info") or r["id"],
         "description": f"bundle: {r.get('type')}" if r.get("type") else None}
        for r in rows
    ]
