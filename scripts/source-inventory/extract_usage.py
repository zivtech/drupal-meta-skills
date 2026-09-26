"""Usage / parent-chain resolution for paragraph-shaped (revisionable child)
components.

Generalizes the pilot run's own DB-usage script with one load-bearing
correction, verified against a live source (see
contracts/source-structure/README.md "Data quality: parent-chain
resolution"): a denormalized parent pointer
(`parent_id`/`parent_type`/`parent_field_name` on the child entity) is
**not** trustworthy for resolving current hosts — it is not reliably
cleared when an entity is detached from its host across revisions. This
module resolves hosts from the live `entity_reference_revisions`
reference-field tables (`target_id`) instead, and reports how often the
denormalized pointer disagreed as `data_quality.parent_chain`.

Every function here that does the actual resolution is pure (takes
already-fetched rows, returns computed structures) so it can be unit
tested against small fixtures/sqlite without a live DB. `fetch_*` functions
are the only ones that talk to `db.py`.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from db import fetch_rows
from extract_bundles import KIND_FOR_ENTITY_TYPE
from field_tables import FieldTableIndex, UnresolvedTable, resolve_fields
from site_profile import DbConfig, DomainsConfig

MAX_HOPS = 30


@dataclass(frozen=True)
class RootHost:
    root_kind: str
    root_id: str
    field_name: str


@dataclass
class RootsResolution:
    roots: list[RootHost]
    # Non-fatal per-branch outcomes hit while walking, e.g. a branch that
    # dead-ended in a cycle while a SIBLING branch (a paragraph shared by
    # multiple live parents) still resolved cleanly. Empty `roots` with a
    # non-empty `errors` means every branch dead-ended.
    errors: set[str]  # subset of {'orphaned', 'cycle', 'max_hops'}


# ---------------------------------------------------------------------------
# Pure computation (unit-testable without a DB)
# ---------------------------------------------------------------------------

def build_reference_edges(rows_by_field_table: dict[tuple[str, str], list[dict]]) -> dict[str, list[dict]]:
    """rows_by_field_table: {(host_entity_type, field_name): [{entity_id, target_id}, ...]}
    drawn from the CURRENT (non-`_revision`) reference field table only.

    Returns paragraph_id -> [{host_kind, host_id, field_name}]. Normally
    length 1 per paragraph id (one live parent); length 0 means no live
    reference table row points at it (orphaned, regardless of what any
    denormalized parent pointer claims); length >1 is an anomaly (the same
    paragraph id referenced by more than one currently-live host).
    """
    edges: dict[str, list[dict]] = defaultdict(list)
    for (host_entity_type, field_name), rows in rows_by_field_table.items():
        host_kind = KIND_FOR_ENTITY_TYPE.get(host_entity_type, host_entity_type)
        for row in rows:
            pid = str(row["target_id"])
            edges[pid].append({
                "host_kind": host_kind,
                "host_id": str(row["entity_id"]),
                "field_name": field_name,
            })
    return edges


def resolve_roots(pid: str, edges: dict[str, list[dict]], max_hops: int = MAX_HOPS) -> RootsResolution:
    """Walk EVERY live reference edge from a paragraph id to its root
    host(s), rather than assuming exactly one live parent.

    A paragraph referenced by more than one currently-live host (verified
    against a live source: node cloning produces exactly this shape) is not
    an error -- it is a paragraph legitimately shared by multiple hosts, and
    each branch is walked to its own root independently. Cycle detection is
    per-branch (the `chain` of paragraph ids already visited on THIS walk),
    not global, so one branch hitting a cycle does not suppress a sibling
    branch that resolves cleanly.
    """
    roots: list[RootHost] = []
    errors: set[str] = set()
    # Stack items: (current_paragraph_id, chain-of-ids-visited-on-this-branch, hops)
    stack: list[tuple[str, tuple[str, ...], int]] = [(str(pid), (str(pid),), 0)]
    visited_branches: set[tuple[str, tuple[str, ...]]] = set()

    while stack:
        cur, chain, hops = stack.pop()
        parents = edges.get(cur, [])
        if not parents:
            errors.add("orphaned")
            continue
        if hops > max_hops:
            errors.add("max_hops")
            continue
        for parent in parents:
            if parent["host_kind"] != "paragraph_type":
                roots.append(RootHost(parent["host_kind"], parent["host_id"], parent["field_name"]))
                continue
            if parent["host_id"] in chain:
                errors.add("cycle")
                continue
            branch_key = (parent["host_id"], chain)
            if branch_key in visited_branches:
                continue
            visited_branches.add(branch_key)
            stack.append((parent["host_id"], chain + (parent["host_id"],), hops + 1))

    return RootsResolution(roots=roots, errors=errors)


def compute_usage(
    paragraph_rows: list[dict],
    edges: dict[str, list[dict]],
    node_status_by_id: dict[str, str],
    node_bundle_by_id: dict[str, str],
    node_domains_by_id: dict[str, set[str]],
) -> dict[str, dict]:
    """paragraph_rows: [{id, type, parent_id, parent_type}] (parent_id/type
    are the DENORMALIZED pointer, used only for the stale-comparison, never
    for resolving usage). Returns bundle -> usage dict matching
    source-structure.schema.json's `usage` shape, keyed by bundle.
    """
    per_type: dict[str, dict] = defaultdict(lambda: {
        "total_instances": 0,
        "published_hosts": 0,
        "unpublished_hosts": 0,
        "library_owned_instances": 0,
        "block_hosted_instances": 0,
        "unresolved_instances": 0,
        "shared_by_multiple_hosts": 0,
        "distinct_host_count": 0,
        "domain_owned_hosts": defaultdict(int),
        "host_bundles_seen": defaultdict(int),
        "_distinct_hosts": set(),
    })

    for row in paragraph_rows:
        pid, ptype = str(row["id"]), row["type"]
        agg = per_type[ptype]
        agg["total_instances"] += 1

        resolution = resolve_roots(pid, edges)
        # De-dupe to distinct (root_kind, root_id) pairs: the same host can
        # legitimately appear more than once in `roots` (e.g. two different
        # fields on the same host both reference this paragraph).
        distinct_roots = sorted({(r.root_kind, r.root_id) for r in resolution.roots})

        if not distinct_roots:
            # every branch dead-ended (orphaned/cycle/max_hops) with no live
            # root reached at all -- this is the only case that counts as
            # unresolved now. A paragraph with >1 live parent is no longer
            # lumped in here; see "shared_by_multiple_hosts" below.
            agg["unresolved_instances"] += 1
            continue

        if len(distinct_roots) > 1:
            agg["shared_by_multiple_hosts"] += 1

        for root_kind, root_id in distinct_roots:
            if root_kind == "node_bundle":
                agg["_distinct_hosts"].add(root_id)
                status = node_status_by_id.get(root_id)
                bundle = node_bundle_by_id.get(root_id, "UNKNOWN")
                agg["host_bundles_seen"][bundle] += 1
                if status == "1":
                    agg["published_hosts"] += 1
                else:
                    agg["unpublished_hosts"] += 1
                for domain in node_domains_by_id.get(root_id, set()):
                    agg["domain_owned_hosts"][domain] += 1
            elif root_kind == "paragraphs_library_item":
                agg["library_owned_instances"] += 1
            elif root_kind == "block_content_type":
                # KIND_FOR_ENTITY_TYPE maps the host entity_type
                # 'block_content' to kind 'block_content_type' -- this IS
                # the block_content-hosted branch, not a block bundle
                # definition.
                agg["block_hosted_instances"] += 1
                agg["_distinct_hosts"].add(f"{root_kind}:{root_id}")
            else:
                # any other terminal kind: count as a resolved,
                # published-agnostic host (no status tracked).
                agg["_distinct_hosts"].add(f"{root_kind}:{root_id}")

    out = {}
    for ptype, agg in per_type.items():
        out[ptype] = {
            "total_instances": agg["total_instances"],
            "published_hosts": agg["published_hosts"],
            "unpublished_hosts": agg["unpublished_hosts"],
            "library_owned_instances": agg["library_owned_instances"],
            "block_hosted_instances": agg["block_hosted_instances"],
            "unresolved_instances": agg["unresolved_instances"],
            "shared_by_multiple_hosts": agg["shared_by_multiple_hosts"],
            "distinct_host_count": len(agg["_distinct_hosts"]),
            "domain_owned_hosts": dict(agg["domain_owned_hosts"]),
            "host_bundles_seen": dict(agg["host_bundles_seen"]),
        }
    return out


def compute_stale_parent_metric(paragraph_rows: list[dict], edges: dict[str, list[dict]]) -> dict:
    """Compares each row's denormalized parent_type/parent_id against the
    live-resolved immediate parent (one hop, not the full root walk) and
    counts disagreements. This is the data_quality.parent_chain block.
    """
    total = 0
    stale = 0
    for row in paragraph_rows:
        pid = str(row["id"])
        denorm_type = row.get("parent_type")
        denorm_id = str(row.get("parent_id")) if row.get("parent_id") not in (None, "") else None
        if not denorm_type:
            continue
        total += 1
        live_parents = edges.get(pid, [])
        live_match = any(
            p["host_id"] == denorm_id and _denorm_type_matches(denorm_type, p["host_kind"])
            for p in live_parents
        )
        if not live_match:
            stale += 1

    pct = round(100.0 * stale / total, 1) if total else 0.0
    return {
        "method": "entity_reference_revisions field tables (target_id/target_revision_id), not the denormalized parent_id column",
        "total_child_rows": total,
        "stale_denormalized_parent_rows": stale,
        "stale_pct": pct,
    }


def _denorm_type_matches(denorm_type: str, host_kind: str) -> bool:
    return KIND_FOR_ENTITY_TYPE.get(denorm_type, denorm_type) == host_kind


# ---------------------------------------------------------------------------
# DB fetch (thin, not unit tested directly — mechanism only)
# ---------------------------------------------------------------------------

def fetch_paragraph_rows(db: DbConfig) -> list[dict]:
    rows = fetch_rows(
        db,
        "SELECT id, type, parent_id, parent_type FROM paragraphs_item_field_data;",
    )
    return rows


def fetch_reference_rows(db: DbConfig, table: str, field_name: str) -> list[dict]:
    """`table` is the field's REAL dedicated table, already resolved against
    the live schema by field_tables.resolve_fields() (which handles Drupal's
    hashed names for long fields). DISTINCT collapses duplicate rows (e.g. a
    multi-value delta that still points at the same target); `deleted = 0`
    excludes soft-deleted field instances that can otherwise leave stale rows
    in this table. Any DbError (timeout, auth, SQL) propagates.
    """
    target_col = f"{field_name}_target_id"
    return fetch_rows(
        db,
        f"SELECT DISTINCT entity_id, {target_col} AS target_id FROM `{table}` WHERE deleted = 0;",
    )


LIBRARY_ITEM_HOST = ("paragraphs_library_item", "paragraphs")


def fetch_library_item_reference_rows(db: DbConfig) -> list[dict]:
    """A Paragraphs Library item holds its paragraph in the single-value BASE
    field `paragraphs`, stored as `paragraphs__target_id` on the item's own
    data table, not in a dedicated `{entity_type}__{field}` table, so the
    config-driven field discovery never sees it. Without these edges every
    library-held paragraph (and everything nested in it) is counted
    unresolved and `library_owned_instances` is always 0.

    Returns [] only when the Paragraphs Library schema is absent (module not
    installed); any DbError propagates.
    """
    present = fetch_rows(
        db,
        "SELECT COLUMN_NAME AS column_name FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'paragraphs_library_item_field_data' "
        "AND COLUMN_NAME = 'paragraphs__target_id';",
    )
    if not present:
        return []
    return fetch_rows(
        db,
        "SELECT DISTINCT id AS entity_id, paragraphs__target_id AS target_id "
        "FROM paragraphs_library_item_field_data WHERE paragraphs__target_id IS NOT NULL;",
    )


def fetch_node_status_and_bundle(db: DbConfig) -> tuple[dict[str, str], dict[str, str]]:
    rows = fetch_rows(db, "SELECT nid, status, type FROM node_field_data;")
    status = {r["nid"]: r["status"] for r in rows}
    bundle = {r["nid"]: r["type"] for r in rows}
    return status, bundle


def fetch_node_domains(db: DbConfig, domains: DomainsConfig, table: str | None) -> dict[str, set[str]]:
    """`table` is the ownership field's resolved table (None when the profile
    names no ownership field, or it could not be resolved -- the caller
    records the latter in data_quality.unresolved_tables)."""
    if not domains.ownership_field or table is None:
        return {}
    target_col = f"{domains.ownership_field}_target_id"
    rows = fetch_rows(db, f"SELECT entity_id, {target_col} AS target_id FROM `{table}`;")
    out: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        domain = r["target_id"]
        if domains.enabled and domain not in domains.enabled:
            continue
        out[r["entity_id"]].add(domain)
    return out


def resolve_usage_tables(
    index: FieldTableIndex,
    reference_keys: list[tuple[str, str]],
    domains: DomainsConfig,
    known_fields_by_entity_type: dict[str, frozenset[str]] | None = None,
) -> tuple[dict[tuple[str, str], str], str | None, list[UnresolvedTable]]:
    """Resolves every paragraph-reference field table plus the domain
    ownership field table. Returns (reference_tables, domain_table,
    unresolved)."""
    reference_tables, unresolved = resolve_fields(
        index, reference_keys, "usage", known_fields_by_entity_type, required_suffix="_target_id",
    )
    domain_table = None
    if domains.ownership_field:
        found, missing = resolve_fields(
            index, [("node", domains.ownership_field)], "domains",
            known_fields_by_entity_type, required_suffix="_target_id",
        )
        domain_table = found.get(("node", domains.ownership_field))
        unresolved = unresolved + missing
    return reference_tables, domain_table, unresolved


def extract_usage(
    db: DbConfig,
    domains: DomainsConfig,
    reference_field_map: dict[tuple[str, str], None],
    index: FieldTableIndex,
) -> tuple[dict, dict, list[UnresolvedTable]]:
    """reference_field_map keys are (host_entity_type, field_name) for every
    entity_reference_revisions field targeting paragraph, as produced by
    extract_bundles.build_relationships (derive the key set from hosted_by).
    Returns (usage_by_bundle, data_quality_parent_chain, unresolved_tables).
    """
    reference_tables, domain_table, unresolved = resolve_usage_tables(
        index, sorted(reference_field_map), domains,
    )
    rows_by_field_table = {
        key: fetch_reference_rows(db, table, key[1]) for key, table in reference_tables.items()
    }
    rows_by_field_table[LIBRARY_ITEM_HOST] = fetch_library_item_reference_rows(db)
    edges = build_reference_edges(rows_by_field_table)

    paragraph_rows = fetch_paragraph_rows(db)
    node_status, node_bundle = fetch_node_status_and_bundle(db)
    node_domains = fetch_node_domains(db, domains, domain_table)

    usage = compute_usage(paragraph_rows, edges, node_status, node_bundle, node_domains)
    data_quality = compute_stale_parent_metric(paragraph_rows, edges)
    return usage, data_quality, unresolved
