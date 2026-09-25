"""Locks in the correction verified against a live Drupal source:
usage/parent-chain resolution must use the live
entity_reference_revisions reference tables, never the denormalized
parent_id/parent_type pointer on paragraphs_item_field_data (which is not
reliably cleared on detach across revisions).

Also locks in that a paragraph referenced by more than one currently-live
host (e.g. node cloning) is a real, non-error shape -- it must resolve to
every distinct host, not be discarded as "unresolved".

Uses a small in-memory SQLite database built to the same column shapes as
the real MySQL tables (paragraphs_item_field_data, node_field_data,
node__field_content, paragraph__field_gallery_items) rather than a live DB,
per the "small SQLite or fixture inputs" testing requirement.
"""
import sqlite3

import pytest

from extract_usage import (
    RootHost,
    build_reference_edges,
    compute_stale_parent_metric,
    compute_usage,
    resolve_roots,
)


@pytest.fixture
def sqlite_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE paragraphs_item_field_data (
            id INTEGER, type TEXT, parent_id TEXT, parent_type TEXT
        );
        CREATE TABLE node_field_data (nid TEXT, status TEXT, type TEXT);
        CREATE TABLE node__field_content (entity_id TEXT, field_content_target_id INTEGER);
        CREATE TABLE paragraph__field_gallery_items (entity_id TEXT, field_gallery_items_target_id INTEGER);
        """
    )
    rows = [
        # pid, type, parent_id, parent_type
        (1, "faq_accordion_row", "100", "node"),       # denormalized: correct
        (2, "faq_accordion_row", "999", "node"),       # denormalized: STALE (live table says host=100)
        (3, "hero_banner", "100", "node"),             # denormalized: correct
        (4, "orphaned_widget", None, None),            # no denormalized parent at all; also unresolved live
        (5, "gallery_item", "10", "paragraph"),        # denormalized: correct (nested in photo_showcase pid 10)
        (10, "photo_showcase", "100", "node"),          # denormalized: correct
    ]
    conn.executemany("INSERT INTO paragraphs_item_field_data VALUES (?, ?, ?, ?)", rows)
    conn.execute("INSERT INTO node_field_data VALUES ('100', '1', 'program_page')")
    # Live reference tables: the ONLY source of truth this module should use.
    conn.executemany(
        "INSERT INTO node__field_content VALUES (?, ?)",
        [("100", 1), ("100", 2), ("100", 3), ("100", 10)],  # note: target_id=2 -> host 100, NOT 999
    )
    conn.execute("INSERT INTO paragraph__field_gallery_items VALUES ('10', 5)")
    conn.commit()
    return conn


def rows_as_dicts(cursor):
    return [dict(r) for r in cursor.fetchall()]


def test_stale_parent_id_is_detected_and_does_not_affect_resolution(sqlite_conn):
    paragraph_rows = rows_as_dicts(sqlite_conn.execute(
        "SELECT id, type, parent_id, parent_type FROM paragraphs_item_field_data"
    ))
    content_rows = rows_as_dicts(sqlite_conn.execute(
        "SELECT entity_id, field_content_target_id AS target_id FROM node__field_content"
    ))
    gallery_rows = rows_as_dicts(sqlite_conn.execute(
        "SELECT entity_id, field_gallery_items_target_id AS target_id FROM paragraph__field_gallery_items"
    ))
    edges = build_reference_edges({
        ("node", "field_content"): content_rows,
        ("paragraph", "field_gallery_items"): gallery_rows,
    })

    # The stale row (pid 2) resolves via the LIVE table to host 100, not the
    # denormalized parent_id of 999.
    resolution = resolve_roots("2", edges)
    assert resolution.errors == set()
    assert resolution.roots == [RootHost("node_bundle", "100", "field_content")]

    dq = compute_stale_parent_metric(paragraph_rows, edges)
    assert dq["total_child_rows"] == 5  # pid 4 has no denormalized parent_type -> excluded
    assert dq["stale_denormalized_parent_rows"] == 1  # only pid 2
    assert dq["stale_pct"] == 20.0
    assert "entity_reference_revisions" in dq["method"]


def test_resolve_roots_walks_nested_paragraph_to_node(sqlite_conn):
    content_rows = rows_as_dicts(sqlite_conn.execute(
        "SELECT entity_id, field_content_target_id AS target_id FROM node__field_content"
    ))
    gallery_rows = rows_as_dicts(sqlite_conn.execute(
        "SELECT entity_id, field_gallery_items_target_id AS target_id FROM paragraph__field_gallery_items"
    ))
    edges = build_reference_edges({
        ("node", "field_content"): content_rows,
        ("paragraph", "field_gallery_items"): gallery_rows,
    })
    resolution = resolve_roots("5", edges)  # gallery_item -> photo_showcase (pid 10) -> node 100
    assert resolution.errors == set()
    assert resolution.roots == [RootHost("node_bundle", "100", "field_content")]


def test_resolve_roots_orphaned_when_no_live_edge(sqlite_conn):
    edges = build_reference_edges({})  # no reference tables at all
    resolution = resolve_roots("4", edges)
    assert resolution.roots == []
    assert resolution.errors == {"orphaned"}


def test_resolve_roots_is_cycle_safe():
    # A malformed/edge-case source where two paragraphs reference each
    # other (a live cycle) must not infinite-loop: it reports 'cycle' for
    # that branch and returns no roots, rather than hanging or crashing.
    edges = {
        "1": [{"host_kind": "paragraph_type", "host_id": "2", "field_name": "field_child"}],
        "2": [{"host_kind": "paragraph_type", "host_id": "1", "field_name": "field_child"}],
    }
    resolution = resolve_roots("1", edges)
    assert resolution.roots == []
    assert "cycle" in resolution.errors


def test_resolve_roots_shared_by_multiple_hosts_is_cycle_safe_per_branch():
    # A paragraph shared by two currently-live parents: one resolves
    # cleanly to a node host, the other loops back into a cycle. The
    # cycling branch must not suppress the branch that resolved cleanly.
    edges = {
        "5": [
            {"host_kind": "node_bundle", "host_id": "100", "field_name": "field_content"},
            {"host_kind": "paragraph_type", "host_id": "9", "field_name": "field_child"},
        ],
        "9": [
            {"host_kind": "paragraph_type", "host_id": "5", "field_name": "field_child"},
        ],
    }
    resolution = resolve_roots("5", edges)
    assert resolution.roots == [RootHost("node_bundle", "100", "field_content")]
    assert "cycle" in resolution.errors


def test_compute_usage_counts_published_host_correctly_despite_stale_denorm(sqlite_conn):
    paragraph_rows = rows_as_dicts(sqlite_conn.execute(
        "SELECT id, type, parent_id, parent_type FROM paragraphs_item_field_data"
    ))
    content_rows = rows_as_dicts(sqlite_conn.execute(
        "SELECT entity_id, field_content_target_id AS target_id FROM node__field_content"
    ))
    gallery_rows = rows_as_dicts(sqlite_conn.execute(
        "SELECT entity_id, field_gallery_items_target_id AS target_id FROM paragraph__field_gallery_items"
    ))
    edges = build_reference_edges({
        ("node", "field_content"): content_rows,
        ("paragraph", "field_gallery_items"): gallery_rows,
    })
    node_status = {"100": "1"}
    node_bundle = {"100": "program_page"}

    usage = compute_usage(paragraph_rows, edges, node_status, node_bundle, node_domains_by_id={})

    faq = usage["faq_accordion_row"]
    assert faq["total_instances"] == 2
    assert faq["published_hosts"] == 2  # both pid1 and pid2 resolve to published node 100
    assert faq["distinct_host_count"] == 1
    assert faq["shared_by_multiple_hosts"] == 0

    orphaned = usage["orphaned_widget"]
    assert orphaned["total_instances"] == 1
    assert orphaned["unresolved_instances"] == 1
    assert orphaned["published_hosts"] == 0

    gallery = usage["gallery_item"]
    assert gallery["published_hosts"] == 1  # resolved through the nested photo_showcase to node 100


def test_compute_usage_shared_paragraph_counts_both_published_hosts():
    # A paragraph referenced by two distinct, currently-live, PUBLISHED
    # node hosts (e.g. node cloning) must be
    # counted once per distinct host, not lumped into unresolved_instances.
    paragraph_rows = [{"id": "6", "type": "shared_widget", "parent_id": "100", "parent_type": "node"}]
    edges = build_reference_edges({
        ("node", "field_content"): [
            {"entity_id": "100", "target_id": "6"},
            {"entity_id": "200", "target_id": "6"},
        ],
    })
    node_status = {"100": "1", "200": "1"}
    node_bundle = {"100": "program_page", "200": "program_page"}

    usage = compute_usage(paragraph_rows, edges, node_status, node_bundle, node_domains_by_id={})

    shared = usage["shared_widget"]
    assert shared["total_instances"] == 1
    assert shared["published_hosts"] == 2
    assert shared["unpublished_hosts"] == 0
    assert shared["unresolved_instances"] == 0
    assert shared["shared_by_multiple_hosts"] == 1
    assert shared["distinct_host_count"] == 2


def test_compute_usage_block_hosted_paragraph_counts_as_block_hosted():
    paragraph_rows = [{"id": "7", "type": "sidebar_widget", "parent_id": None, "parent_type": None}]
    edges = build_reference_edges({
        ("block_content", "field_sidebar"): [{"entity_id": "bc-1", "target_id": "7"}],
    })
    usage = compute_usage(paragraph_rows, edges, node_status_by_id={}, node_bundle_by_id={}, node_domains_by_id={})

    sidebar = usage["sidebar_widget"]
    assert sidebar["block_hosted_instances"] == 1
    assert sidebar["unresolved_instances"] == 0
    assert sidebar["distinct_host_count"] == 1


def test_compute_usage_shared_paragraph_with_published_and_unpublished_host():
    # One instance, two distinct live hosts: one published, one not. It is
    # counted once in each status bucket and once as shared, and the
    # identity documented in the contract README holds:
    # published + unpublished + library + block + unresolved - shared == total
    # (exact here because the shared instance has exactly two hosts).
    paragraph_rows = [{"id": "8", "type": "shared_widget", "parent_id": "100", "parent_type": "node"}]
    edges = build_reference_edges({
        ("node", "field_content"): [
            {"entity_id": "100", "target_id": "8"},
            {"entity_id": "300", "target_id": "8"},
        ],
    })
    usage = compute_usage(
        paragraph_rows, edges,
        node_status_by_id={"100": "1", "300": "0"},
        node_bundle_by_id={"100": "program_page", "300": "program_page"},
        node_domains_by_id={},
    )

    shared = usage["shared_widget"]
    assert shared["published_hosts"] == 1
    assert shared["unpublished_hosts"] == 1
    assert shared["shared_by_multiple_hosts"] == 1
    assert shared["unresolved_instances"] == 0
    assert shared["distinct_host_count"] == 2
    assert shared["host_bundles_seen"] == {"program_page": 2}
    lhs = (shared["published_hosts"] + shared["unpublished_hosts"] + shared["library_owned_instances"]
           + shared["block_hosted_instances"] + shared["unresolved_instances"] - shared["shared_by_multiple_hosts"])
    assert lhs == shared["total_instances"] == 1


def test_contract_fixture_usage_satisfies_the_documented_identity():
    # contracts/source-structure/README.md "Reading the usage counts": with
    # at most two roots per shared instance, the buckets minus the shared
    # count add back up to total_instances.
    import json
    from assemble import CONTRACT_DIR

    doc = json.loads((CONTRACT_DIR / "fixtures" / "valid" / "source-structure.json").read_text())
    checked = 0
    for c in doc["components"]:
        u = c.get("usage")
        if not u:
            continue
        lhs = (u["published_hosts"] + u["unpublished_hosts"] + u.get("library_owned_instances", 0)
               + u.get("block_hosted_instances", 0) + u.get("unresolved_instances", 0)
               - u.get("shared_by_multiple_hosts", 0))
        assert lhs == u["total_instances"], c["id"]
        checked += 1
    assert checked >= 5


def test_library_held_paragraph_counts_as_library_owned_not_unresolved(monkeypatch):
    # The library item's base field is not a dedicated field table; its edges
    # come from fetch_library_item_reference_rows. A paragraph held by a
    # library item, and a paragraph nested inside that one, both resolve to
    # the library item.
    import extract_usage as eu

    def fake(_db, sql):
        if "information_schema.COLUMNS" in sql:
            return [{"column_name": "paragraphs__target_id"}]
        if "FROM paragraphs_library_item_field_data" in sql:
            assert "DISTINCT" in sql  # one row per item even with translations
            return [{"entity_id": "7", "target_id": "50"}]
        raise AssertionError(sql)

    monkeypatch.setattr(eu, "fetch_rows", fake)
    rows = eu.fetch_library_item_reference_rows(db=None)
    edges = build_reference_edges({
        eu.LIBRARY_ITEM_HOST: rows,
        ("paragraph", "field_gallery_items"): [{"entity_id": "50", "target_id": "51"}],
    })
    usage = compute_usage(
        [{"id": "50", "type": "photo_showcase", "parent_id": "7", "parent_type": "paragraphs_library_item"},
         {"id": "51", "type": "gallery_item", "parent_id": "50", "parent_type": "paragraph"}],
        edges, node_status_by_id={}, node_bundle_by_id={}, node_domains_by_id={},
    )
    assert usage["photo_showcase"]["library_owned_instances"] == 1
    assert usage["photo_showcase"]["unresolved_instances"] == 0
    assert usage["gallery_item"]["library_owned_instances"] == 1
    assert edges["50"] == [{"host_kind": "paragraphs_library_item", "host_id": "7", "field_name": "paragraphs"}]


def test_library_reference_rows_empty_only_when_library_schema_absent(monkeypatch):
    import extract_usage as eu
    monkeypatch.setattr(eu, "fetch_rows", lambda _db, sql: [])
    assert eu.fetch_library_item_reference_rows(db=None) == []
