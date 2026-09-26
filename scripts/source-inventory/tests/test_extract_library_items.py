import pytest

import extract_library_items
import field_tables
from db import DbError
from extract_library_items import build_library_item_components, compute_library_item_hosts, find_wrapping_fields
from site_profile import DbConfig


def test_find_wrapping_fields_detects_target_paragraphs_library_item():
    all_entity_fields = {
        "paragraph": {
            "from_library": {
                "field_reusable_paragraph": {"field_type": "entity_reference", "target_entity_type": "paragraphs_library_item"},
            },
            "hero_banner": {
                "field_light_theme": {"field_type": "boolean", "target_entity_type": None},
            },
        },
        "node": {}, "block_content": {},
    }
    assert find_wrapping_fields(all_entity_fields) == [("paragraph", "field_reusable_paragraph")]


def test_library_item_with_three_hosts():
    # Negative control: a library item with 3 hosts.
    wrapping_rows = [
        {"wrapping_id": 20, "library_item_id": "shared_closure_notice"},
        {"wrapping_id": 21, "library_item_id": "shared_closure_notice"},
        {"wrapping_id": 22, "library_item_id": "shared_closure_notice"},
    ]
    edges = {
        "20": [{"host_kind": "node_bundle", "host_id": "100", "field_name": "field_content"}],
        "21": [{"host_kind": "node_bundle", "host_id": "200", "field_name": "field_sidebar"}],
        "22": [{"host_kind": "node_bundle", "host_id": "200", "field_name": "field_content"}],
    }
    result = compute_library_item_hosts(wrapping_rows, edges)
    assert result["shared_closure_notice"]["host_count"] == 3
    host_ids = {(h["host_kind"], h["host_id"], h["field_name"]) for h in result["shared_closure_notice"]["hosts"]}
    assert host_ids == {
        ("node_bundle", "100", "field_content"),
        ("node_bundle", "200", "field_sidebar"),
        ("node_bundle", "200", "field_content"),
    }


def test_library_item_host_unresolved_wrapping_paragraph_is_excluded():
    wrapping_rows = [{"wrapping_id": 30, "library_item_id": "orphaned_reuse"}]
    edges = {}  # no live edge at all -> resolve_roots returns no roots, errors={'orphaned'}
    result = compute_library_item_hosts(wrapping_rows, edges)
    assert "orphaned_reuse" not in result


LONG_WRAPPING_FIELD = "field_reusable_section_from_shared_library"  # paragraph__ + this > 48 chars
HASHED_WRAPPING_TABLE = "paragraph__0123456789"


def _library_fake(schema_tables, rows_by_table, base_rows=None, paragraph_types=None):
    """base_rows=None: the library item's base column is absent from the
    schema; otherwise the rows its `paragraphs__target_id` query returns."""
    paragraph_types = paragraph_types if paragraph_types is not None else [{"id": "900", "type": "notice_banner"}]

    def fetch_rows(_db, sql):
        if "information_schema.COLUMNS" in sql and "TABLE_NAME = 'paragraphs_library_item_field_data'" in sql:
            if base_rows is None:
                return []
            return [{"column_name": "paragraphs__target_id" if "paragraphs__target_id" in sql else "default_langcode"}]
        if "information_schema.COLUMNS" in sql and "paragraphs\\_library\\_item" in sql:
            return []  # no dedicated paragraphs_library_item__* field table
        if "information_schema.COLUMNS" in sql:
            return [{"table_name": t, "column_name": c} for t, cols in schema_tables.items() for c in cols]
        if "paragraphs__target_id AS paragraph_id" in sql:
            return base_rows or []
        if "paragraphs_library_item_field_data" in sql:
            return [{"id": "7", "label": "Shared closing-times notice"}]
        if "FROM paragraphs_item_field_data" in sql:
            return paragraph_types
        for table, rows in rows_by_table.items():
            if f"`{table}`" in sql:
                return rows
        raise DbError("query failed (exit 1): ERROR 1146 (42S02): Table doesn't exist")
    return fetch_rows


def _fields():
    return {
        "paragraph": {"from_shared": {LONG_WRAPPING_FIELD: {
            "field_type": "entity_reference", "target_entity_type": "paragraphs_library_item"}}},
        "node": {}, "block_content": {},
    }


def test_library_wrapping_field_with_hashed_table_is_read(monkeypatch):
    assert len(f"paragraph__{LONG_WRAPPING_FIELD}") > 48
    fake = _library_fake(
        {HASHED_WRAPPING_TABLE: ["entity_id", "deleted", f"{LONG_WRAPPING_FIELD}_target_id"]},
        {HASHED_WRAPPING_TABLE: [{"wrapping_id": "40", "library_item_id": "7"}]},
        base_rows=[{"item_id": "7", "paragraph_id": "900"}],
    )
    for mod in (extract_library_items, field_tables):
        monkeypatch.setattr(mod, "fetch_rows", fake)
    edges = {"40": [{"host_kind": "node_bundle", "host_id": "100", "field_name": "field_content"}]}

    components, details, unresolved = build_library_item_components(
        DbConfig(docker_container="fixture-src-db", database="fixture"), _fields(), edges,
    )

    assert unresolved == []
    assert components == [{"id": "7", "kind": "paragraphs_library_item", "label": "Shared closing-times notice"}]
    assert details[0]["host_count"] == 1


def test_library_wrapping_table_missing_is_reported_unresolved(monkeypatch):
    fake = _library_fake({}, {}, base_rows=[{"item_id": "7", "paragraph_id": "900"}])
    for mod in (extract_library_items, field_tables):
        monkeypatch.setattr(mod, "fetch_rows", fake)

    _components, details, unresolved = build_library_item_components(
        DbConfig(docker_container="fixture-src-db", database="fixture"), _fields(), edges={},
    )

    assert [u.to_dict() for u in unresolved] == [{
        "entity_type": "paragraph", "field_name": LONG_WRAPPING_FIELD,
        "expected_table": f"paragraph__{LONG_WRAPPING_FIELD}", "purpose": "library_items",
    }]
    assert details[0]["host_count"] == 0


def test_library_fetch_db_error_propagates(monkeypatch):
    def boom(_db, _sql):
        raise DbError("query timed out after 30s: docker exec fixture-src-db...")
    for mod in (extract_library_items, field_tables):
        monkeypatch.setattr(mod, "fetch_rows", boom)
    with pytest.raises(DbError, match="timed out"):
        build_library_item_components(
            DbConfig(docker_container="fixture-src-db", database="fixture"), _fields(), edges={},
        )


# ---------------------------------------------------------------------------
# Wrapped paragraph bundle. The stock Paragraphs Library item keeps its
# paragraph in the base field `paragraphs` (paragraphs__target_id on
# paragraphs_library_item_field_data), not in a dedicated field table; the
# earlier lookup only searched dedicated tables and so returned "" for every
# item on a real site.
# ---------------------------------------------------------------------------

def _patch(monkeypatch, fake):
    for mod in (extract_library_items, field_tables):
        monkeypatch.setattr(mod, "fetch_rows", fake)


def _no_wrapping_fields():
    return {"paragraph": {}, "node": {}, "block_content": {}}


def test_wrapped_bundle_is_read_from_the_base_field(monkeypatch):
    _patch(monkeypatch, _library_fake({}, {}, base_rows=[{"item_id": "7", "paragraph_id": "900"}]))

    _components, details, unresolved = build_library_item_components(
        DbConfig(docker_container="fixture-src-db", database="fixture"), _no_wrapping_fields(), edges={},
    )

    assert unresolved == []
    assert details[0]["paragraph_bundle"] == "notice_banner"


def test_wrapped_bundle_first_row_wins_per_item(monkeypatch):
    # Rows arrive ordered (default translation first); a later translation
    # pointing somewhere else must not overwrite the first answer.
    base_rows = [{"item_id": "7", "paragraph_id": "900"}, {"item_id": "7", "paragraph_id": "901"}]
    types = [{"id": "900", "type": "notice_banner"}, {"id": "901", "type": "photo_showcase"}]
    _patch(monkeypatch, _library_fake({}, {}, base_rows=base_rows, paragraph_types=types))

    bundles, unresolved = extract_library_items.fetch_wrapped_paragraph_bundle(
        DbConfig(docker_container="fixture-src-db", database="fixture"),
    )

    assert (bundles, unresolved) == ({"7": "notice_banner"}, [])


def test_wrapped_bundle_query_orders_by_default_translation(monkeypatch):
    seen = []
    fake = _library_fake({}, {}, base_rows=[{"item_id": "7", "paragraph_id": "900"}])
    _patch(monkeypatch, lambda db, sql: seen.append(sql) or fake(db, sql))

    extract_library_items.fetch_wrapped_paragraph_bundle(DbConfig(docker_container="fixture-src-db", database="fixture"))

    base_query = next(q for q in seen if "paragraphs__target_id AS paragraph_id" in q)
    assert "ORDER BY id, default_langcode DESC" in base_query


def test_wrapped_bundle_dangling_reference_is_left_empty_not_unresolved(monkeypatch):
    # The item points at a paragraph row that no longer exists: that is a
    # source-data problem for this one item, not a missing table.
    _patch(monkeypatch, _library_fake({}, {}, base_rows=[{"item_id": "7", "paragraph_id": "404"}]))

    _components, details, unresolved = build_library_item_components(
        DbConfig(docker_container="fixture-src-db", database="fixture"), _no_wrapping_fields(), edges={},
    )

    assert unresolved == []
    assert details[0]["paragraph_bundle"] == ""


def _dedicated_fake(tables):
    """No base column; `tables` maps dedicated table -> (target column, rows)."""
    def fetch_rows(_db, sql):
        if "TABLE_NAME = 'paragraphs_library_item_field_data'" in sql:
            return []
        if "information_schema.COLUMNS" in sql and "paragraphs\\_library\\_item\\_\\_" in sql:
            # Returned in reverse order on purpose: the reader must sort.
            return [{"table_name": t, "column_name": col} for t, (col, _rows) in sorted(tables.items(), reverse=True)]
        if "FROM paragraphs_item_field_data" in sql:
            return [{"id": "900", "type": "notice_banner"}, {"id": "901", "type": "photo_showcase"},
                    {"id": "903", "type": "gallery_item"}]
        for table, (_col, rows) in tables.items():
            if f"`{table}`" in sql:
                assert "ORDER BY entity_id, delta" in sql
                return rows
        raise AssertionError(f"unexpected query: {sql}")
    return fetch_rows


def test_wrapped_bundle_falls_back_to_dedicated_tables_deterministically(monkeypatch):
    tables = {
        "paragraphs_library_item__field_body_para": ("field_body_para_target_id",
                                                      [{"item_id": "7", "paragraph_id": "900"},
                                                       {"item_id": "8", "paragraph_id": "903"}]),
        "paragraphs_library_item__field_extra_para": ("field_extra_para_target_id",
                                                       [{"item_id": "7", "paragraph_id": "901"}]),
    }
    _patch(monkeypatch, _dedicated_fake(tables))

    bundles, unresolved = extract_library_items.fetch_wrapped_paragraph_bundle(
        DbConfig(docker_container="fixture-src-db", database="fixture"),
    )

    # Sorted (table, column): field_body_para is read before field_extra_para,
    # so item 7 keeps 900 regardless of the order information_schema returned.
    assert (bundles, unresolved) == ({"7": "notice_banner", "8": "gallery_item"}, [])


def test_wrapped_bundle_location_missing_is_reported_unresolved(monkeypatch):
    _patch(monkeypatch, _dedicated_fake({}))

    bundles, unresolved = extract_library_items.fetch_wrapped_paragraph_bundle(
        DbConfig(docker_container="fixture-src-db", database="fixture"),
    )

    assert bundles == {}
    assert [u.to_dict() for u in unresolved] == [{
        "entity_type": "paragraphs_library_item", "field_name": "paragraphs",
        "expected_table": "paragraphs_library_item_field_data", "purpose": "library_items",
    }]


def test_wrapped_bundle_location_missing_without_items_is_not_a_gap(monkeypatch):
    _patch(monkeypatch, _dedicated_fake({}))
    assert extract_library_items.fetch_wrapped_paragraph_bundle(
        DbConfig(docker_container="fixture-src-db", database="fixture"), has_items=False,
    ) == ({}, [])
