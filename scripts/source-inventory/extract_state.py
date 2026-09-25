"""State API keys — KEYS ONLY, never values.

This is a structural PII rule, not just a documented convention: the SQL
this module issues never selects the `value` column of `key_value`. Only
`name` and `LENGTH(value)` (a size in bytes, not the content) are read.
"""
from __future__ import annotations

from db import fetch_rows
from site_profile import DbConfig


def fetch_state_keys(db: DbConfig, collection: str = "state") -> list[dict]:
    rows = fetch_rows(
        db,
        f"SELECT name, LENGTH(value) AS size_bytes FROM key_value WHERE collection={collection!r};",
    )
    out = []
    for r in rows:
        size = r.get("size_bytes")
        out.append({
            "key": r["name"],
            "collection": collection,
            "size_bytes": int(size) if size not in (None, "", "NULL") else None,
            "changed": None,  # core State API does not track a per-key changed timestamp
        })
    return out


def build_state_components(db: DbConfig | None, collection: str = "state") -> tuple[list[dict], list[dict]]:
    if db is None:
        return [], []
    state_keys = fetch_state_keys(db, collection)
    components = [{"id": k["key"], "kind": "state_setting", "label": k["key"]} for k in state_keys]
    return components, state_keys
