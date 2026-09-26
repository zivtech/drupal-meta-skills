"""Paragraphs Library items: the specific saved reusable entities (distinct
from paragraph *types* — a paragraphs_library_item is REUSE-shaped by
construction, one definition referenced by many hosts).

A library item's hosts are found by: (1) locating the wrapping paragraph
bundle(s) — any paragraph bundle with a field targeting
`paragraphs_library_item` — (2) for each wrapping paragraph instance,
resolving ITS OWN root host via the same live-reference-edge walk used in
extract_usage.py (a wrapping paragraph is hosted like any other paragraph;
using the denormalized parent pointer here would have the same staleness
problem documented in extract_usage.py).
"""
from __future__ import annotations

from collections import defaultdict

from db import fetch_rows
from extract_usage import resolve_roots
from field_tables import FieldTableIndex, UnresolvedTable, fetch_field_table_index, resolve_fields
from site_profile import DbConfig


def find_wrapping_fields(all_entity_fields: dict[str, dict]) -> list[tuple[str, str]]:
    """Returns [(host_entity_type, field_name)] for every field on any
    bundle-carrying entity type whose target_entity_type is
    'paragraphs_library_item'."""
    out = []
    for entity_type, bundles in all_entity_fields.items():
        for _bundle, fields in bundles.items():
            for fname, entry in fields.items():
                if entry.get("target_entity_type") == "paragraphs_library_item":
                    out.append((entity_type, fname))
    return sorted(set(out))


def fetch_library_item_labels(db: DbConfig) -> dict[str, str]:
    rows = fetch_rows(db, "SELECT id, label FROM paragraphs_library_item_field_data;")
    return {r["id"]: r.get("label") or r["id"] for r in rows}


LIBRARY_ITEM_DATA_TABLE = "paragraphs_library_item_field_data"
LIBRARY_ITEM_BASE_COLUMN = "paragraphs__target_id"


def _has_column(db: DbConfig, table: str, column: str) -> bool:
    return bool(fetch_rows(
        db,
        "SELECT COLUMN_NAME AS column_name FROM information_schema.COLUMNS "
        f"WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{table}' AND COLUMN_NAME = '{column}';",
    ))


def _first_by_item(rows: list[dict]) -> dict[str, str]:
    """rows are already ordered; the first paragraph id seen per item wins."""
    out: dict[str, str] = {}
    for r in rows:
        item_id, paragraph_id = r.get("item_id"), r.get("paragraph_id")
        if item_id is None or paragraph_id is None:
            continue
        out.setdefault(str(item_id), str(paragraph_id))
    return out


def _wrapped_paragraph_ids_from_base_field(db: DbConfig) -> dict[str, str]:
    # One row per translation; the default translation is read first so the
    # choice is deterministic when translations point at different paragraphs.
    order = "id, default_langcode DESC" if _has_column(db, LIBRARY_ITEM_DATA_TABLE, "default_langcode") else "id"
    return _first_by_item(fetch_rows(
        db,
        f"SELECT id AS item_id, {LIBRARY_ITEM_BASE_COLUMN} AS paragraph_id FROM {LIBRARY_ITEM_DATA_TABLE} "
        f"WHERE {LIBRARY_ITEM_BASE_COLUMN} IS NOT NULL ORDER BY {order};",
    ))


def _wrapped_paragraph_ids_from_dedicated_tables(db: DbConfig) -> dict[str, str]:
    """Fallback for a library item whose paragraph reference lives in a
    dedicated `paragraphs_library_item__*` field table (not the stock
    Paragraphs Library layout). Every candidate `*_target_id` column is read,
    in sorted (table, column) order; per item the first candidate that has a
    row wins, and within a table the lowest delta wins."""
    cols = fetch_rows(
        db,
        "SELECT TABLE_NAME AS table_name, COLUMN_NAME AS column_name FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME LIKE 'paragraphs\\_library\\_item\\_\\_%' "
        "AND COLUMN_NAME LIKE '%\\_target\\_id' AND COLUMN_NAME NOT LIKE '%\\_target\\_revision\\_id';",
    )
    candidates = sorted({(c["table_name"], c["column_name"]) for c in cols})
    out: dict[str, str] = {}
    for table, target_col in candidates:
        rows = fetch_rows(
            db,
            f"SELECT entity_id AS item_id, {target_col} AS paragraph_id FROM `{table}` "
            "WHERE deleted = 0 ORDER BY entity_id, delta;",
        )
        for item_id, paragraph_id in _first_by_item(rows).items():
            out.setdefault(item_id, paragraph_id)
    return out


def fetch_wrapped_paragraph_bundle(db: DbConfig, has_items: bool = True) -> tuple[dict[str, str], list[UnresolvedTable]]:
    """Returns (library_item_id -> wrapped paragraph bundle, unresolved).

    The stock Paragraphs Library item holds its paragraph in the base field
    `paragraphs`, stored as `paragraphs__target_id` on the item's own data
    table (the same edge extract_usage.fetch_library_item_reference_rows
    reads), so that column is read first. A dedicated
    `paragraphs_library_item__*` field table is only a fallback.

    When library items exist but neither location is present, the gap is
    returned as an UnresolvedTable (purpose `library_items`) instead of an
    empty map that would read as "every bundle is ''". An item whose wrapped
    paragraph row no longer exists (a dangling reference in the source) is
    simply absent from the map. Any DbError propagates.
    """
    if _has_column(db, LIBRARY_ITEM_DATA_TABLE, LIBRARY_ITEM_BASE_COLUMN):
        paragraph_by_item = _wrapped_paragraph_ids_from_base_field(db)
    else:
        paragraph_by_item = _wrapped_paragraph_ids_from_dedicated_tables(db)
    if not paragraph_by_item:
        if not has_items:
            return {}, []
        return {}, [UnresolvedTable(
            entity_type="paragraphs_library_item", field_name="paragraphs",
            expected_table=LIBRARY_ITEM_DATA_TABLE, purpose="library_items",
        )]
    para_types = fetch_rows(db, "SELECT id, type FROM paragraphs_item_field_data;")
    type_by_pid = {str(r["id"]): r["type"] for r in para_types if r.get("type")}
    return {
        item_id: type_by_pid[pid] for item_id, pid in paragraph_by_item.items() if pid in type_by_pid
    }, []


def fetch_wrapping_rows(db: DbConfig, table: str, field_name: str) -> list[dict]:
    """`table` is the wrapping field's real table, resolved against the live
    schema by field_tables.resolve_fields() (Drupal hashes the name of a
    long field's table). Any DbError propagates."""
    target_col = f"{field_name}_target_id"
    return fetch_rows(
        db,
        f"SELECT entity_id AS wrapping_id, {target_col} AS library_item_id FROM `{table}` WHERE deleted = 0;",
    )


def compute_library_item_hosts(
    wrapping_rows: list[dict],
    edges: dict[str, list[dict]],
) -> dict[str, dict]:
    """Pure. wrapping_rows: [{wrapping_id, library_item_id}]. Returns
    library_item_id -> {host_count, hosts: [{host_kind, host_id, field_name}]}
    (deduplicated by (host_kind, host_id, field_name))."""
    hosts_by_item: dict[str, set[tuple[str, str, str]]] = defaultdict(set)
    for row in wrapping_rows:
        wrapping_id = str(row["wrapping_id"])
        item_id = str(row["library_item_id"])
        resolution = resolve_roots(wrapping_id, edges)
        for root in resolution.roots:
            hosts_by_item[item_id].add((root.root_kind, root.root_id, root.field_name or ""))

    out = {}
    for item_id, hosts in hosts_by_item.items():
        host_list = [{"host_kind": k, "host_id": i, "field_name": f} for k, i, f in sorted(hosts)]
        out[item_id] = {"host_count": len(host_list), "hosts": host_list}
    return out


def build_library_item_components(
    db: DbConfig | None,
    all_entity_fields: dict[str, dict],
    edges: dict[str, list[dict]],
    index: FieldTableIndex | None = None,
) -> tuple[list[dict], list[dict], list[UnresolvedTable]]:
    """Returns (components[kind=paragraphs_library_item], library_items[]
    detail, unresolved wrapping-field tables)."""
    if db is None:
        return [], [], []
    if index is None:
        index = fetch_field_table_index(db, tuple(sorted(all_entity_fields)))

    wrapping_fields = find_wrapping_fields(all_entity_fields)
    known = {et: frozenset(f for fields in bundles.values() for f in fields)
             for et, bundles in all_entity_fields.items()}
    wrapping_tables, unresolved = resolve_fields(
        index, wrapping_fields, "library_items", known, required_suffix="_target_id",
    )
    all_wrapping_rows: list[dict] = []
    for (_entity_type, field_name), table in wrapping_tables.items():
        all_wrapping_rows.extend(fetch_wrapping_rows(db, table, field_name))

    labels = fetch_library_item_labels(db)
    hosts_by_item = compute_library_item_hosts(all_wrapping_rows, edges)
    wrapped_bundle_by_item, bundle_unresolved = fetch_wrapped_paragraph_bundle(db, has_items=bool(labels))
    unresolved = [*unresolved, *bundle_unresolved]

    components = []
    details = []
    for item_id, label in labels.items():
        components.append({"id": item_id, "kind": "paragraphs_library_item", "label": label})
        h = hosts_by_item.get(item_id, {"host_count": 0, "hosts": []})
        details.append({
            "id": item_id,
            "label": label,
            "paragraph_bundle": wrapped_bundle_by_item.get(item_id, ""),
            "host_count": h["host_count"],
            "hosts": h["hosts"],
        })
    return components, details, unresolved
