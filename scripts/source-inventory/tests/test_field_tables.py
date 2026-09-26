"""Field-table resolution against the live schema, including Drupal's hashed
names for long fields, and the rule that DB failures propagate instead of
being mistaken for "table not found"."""
import subprocess

import pytest

import extract_library_items
import extract_usage
import field_tables
from db import DbError
from field_tables import build_index, drupal_field_table_name, resolve_fields
from site_profile import DbConfig, DomainsConfig

LONG_FIELD = "field_" + "seasonal_program_schedule_reference"  # 41 chars
STORAGE_UUID = "3f1c2a9e-7b64-4d2e-9a51-0c8e6f4b2d17"
# sha256("3f1c2a9e-7b64-4d2e-9a51-0c8e6f4b2d17")[:10], computed once by hand.
HASHED_TABLE = "paragraph__a5bc89c0ee"


def test_drupal_field_table_name_mirrors_core_rule():
    # Short enough: the plain name.
    assert drupal_field_table_name("node", "field_topic", "unused") == "node__field_topic"
    assert drupal_field_table_name("node", "field_topic", "unused", revision=True) == "node_revision__field_topic"
    # > 48 chars: `{entity_type}__` + first 10 hex of sha256(unique storage id).
    assert len(f"paragraph__{LONG_FIELD}") > 48
    assert drupal_field_table_name("paragraph", LONG_FIELD, STORAGE_UUID) == HASHED_TABLE
    assert drupal_field_table_name("paragraph", LONG_FIELD, STORAGE_UUID, revision=True) == "paragraph_r__a5bc89c0ee"
    # A long DB prefix is cut to 34 chars and the entity type is dropped.
    long_prefix = "p" * 40
    assert drupal_field_table_name("paragraph", LONG_FIELD, STORAGE_UUID, prefix=long_prefix) == "p" * 34 + "__a5bc89c0ee"


def _schema_rows(tables: dict[str, list[str]]) -> list[dict]:
    return [{"table_name": t, "column_name": c} for t, cols in tables.items() for c in cols]


LIVE_SCHEMA = {
    "node__field_content": ["entity_id", "deleted", "field_content_target_id", "field_content_target_revision_id"],
    HASHED_TABLE: ["entity_id", "deleted", "bundle", f"{LONG_FIELD}_target_id", f"{LONG_FIELD}_target_revision_id"],
}


class FakeDb:
    """Answers the information_schema read and SELECTs against known tables
    only; a query against any other table fails like MySQL would."""

    def __init__(self, schema, rows_by_table):
        self.schema = schema
        self.rows_by_table = rows_by_table
        self.queries: list[str] = []

    def fetch_rows(self, _db, sql):
        self.queries.append(sql)
        if "information_schema.COLUMNS" in sql:
            return _schema_rows(self.schema)
        for table, rows in self.rows_by_table.items():
            if f"`{table}`" in sql:
                return rows
        raise DbError("query failed (exit 1): ERROR 1146 (42S02): Table doesn't exist")


def _install(monkeypatch, fake):
    for mod in (field_tables, extract_usage, extract_library_items):
        monkeypatch.setattr(mod, "fetch_rows", fake.fetch_rows)


@pytest.mark.parametrize("uuids", [{("paragraph", LONG_FIELD): STORAGE_UUID}, {}], ids=["core-hash", "column-match"])
def test_long_field_resolves_to_hashed_table_and_rows_are_read(monkeypatch, uuids):
    fake = FakeDb(LIVE_SCHEMA, {HASHED_TABLE: [{"entity_id": "10", "target_id": "5"}]})
    _install(monkeypatch, fake)
    db = DbConfig(docker_container="fixture-src-db", database="fixture")

    index = field_tables.fetch_field_table_index(db, ("node", "paragraph"), uuids)
    tables, domain_table, unresolved = extract_usage.resolve_usage_tables(
        index, [("paragraph", LONG_FIELD)], DomainsConfig(),
    )

    assert unresolved == []
    assert domain_table is None
    assert tables == {("paragraph", LONG_FIELD): HASHED_TABLE}
    rows = extract_usage.fetch_reference_rows(db, tables[("paragraph", LONG_FIELD)], LONG_FIELD)
    assert rows == [{"entity_id": "10", "target_id": "5"}]
    assert any(f"`{HASHED_TABLE}`" in q for q in fake.queries)
    assert not any(f"paragraph__{LONG_FIELD}`" in q for q in fake.queries)


def test_column_match_prefers_the_longest_owning_field():
    # Two hashed tables whose columns both start with "field_image_": the one
    # holding field_image_caption_* belongs to field_image_caption, not to
    # field_image, even though "field_image_" prefixes its columns too.
    index = build_index(_schema_rows({
        "paragraph__1111111111": ["entity_id", "bundle", "field_image_target_id", "field_image_alt"],
        "paragraph__2222222222": ["entity_id", "bundle", "field_image_caption_value", "field_image_caption_format"],
    }))
    known = {"paragraph": frozenset({"field_image", "field_image_caption"})}
    resolved, unresolved = resolve_fields(
        index, [("paragraph", "field_image"), ("paragraph", "field_image_caption")], "field_profile", known,
    )
    assert unresolved == []
    assert resolved[("paragraph", "field_image")] == "paragraph__1111111111"
    assert resolved[("paragraph", "field_image_caption")] == "paragraph__2222222222"


def test_unresolvable_table_is_reported_not_silently_empty():
    index = build_index(_schema_rows(LIVE_SCHEMA))
    tables, _domain_table, unresolved = extract_usage.resolve_usage_tables(
        index, [("node", "field_content"), ("paragraph", "field_missing_everywhere")],
        DomainsConfig(ownership_field="field_domain_access"),
    )
    assert tables == {("node", "field_content"): "node__field_content"}
    assert [u.to_dict() for u in unresolved] == [
        {"entity_type": "paragraph", "field_name": "field_missing_everywhere",
         "expected_table": "paragraph__field_missing_everywhere", "purpose": "usage"},
        {"entity_type": "node", "field_name": "field_domain_access",
         "expected_table": "node__field_domain_access", "purpose": "domains"},
    ]


def _fake_completed(returncode: int, stderr: bytes = b""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=b"", stderr=stderr)


@pytest.mark.parametrize(
    "returncode, stderr, match",
    [
        (124, b"", "timed out"),
        (1, b"ERROR 1045 (28000): Access denied for user 'reader'", "Access denied"),
    ],
    ids=["timeout", "auth"],
)
def test_db_failures_propagate_from_every_fetch(monkeypatch, returncode, stderr, match):
    # Drives the REAL db.fetch_rows/_run path; only the subprocess is faked.
    monkeypatch.setattr("db.subprocess.run", lambda *a, **k: _fake_completed(returncode, stderr))
    db = DbConfig(docker_container="fixture-src-db", database="fixture")

    with pytest.raises(DbError, match=match):
        field_tables.fetch_field_table_index(db, ("paragraph",))
    with pytest.raises(DbError, match=match):
        extract_usage.fetch_reference_rows(db, HASHED_TABLE, LONG_FIELD)
    with pytest.raises(DbError, match=match):
        extract_library_items.fetch_wrapping_rows(db, HASHED_TABLE, LONG_FIELD)
    with pytest.raises(DbError, match=match):
        extract_usage.fetch_node_domains(db, DomainsConfig(ownership_field="field_domain_access"), "node__field_domain_access")
