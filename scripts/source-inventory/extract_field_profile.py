"""Fill rate, duplication, and (optional, off-by-default) sample values.

Generalizes the pilot run's own field-SQL and field-processing scripts.
Works for any bundle-carrying entity type (node/paragraph/
block_content), not just paragraphs, because Drupal's per-field SQL
storage tables (`<entity_type>__<field_name>`, with a `bundle` column) use
the same shape regardless of entity type.

PII handling differs from the original in one
load-bearing way: every candidate sample
value is regex-scrubbed via pii.scrub_value() BEFORE truncation,
regardless of field name. The original script only checked field name +
skipped the whole field when personal; that leaves a free-text field with
an occasional embedded email unscrubbed. Here, `personal_data_suspected`
(name/content heuristic) still suppresses a field's samples entirely as a
stronger signal, but scrubbing is unconditional for every field that is
shown at all.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict

from db import fetch_rows
import pii
from site_profile import DbConfig, PiiConfig

KEY_COLS = {"bundle", "deleted", "entity_id", "revision_id", "langcode", "delta"}


def build_field_union_sql(
    entity_type: str,
    bundle: str,
    field_columns: dict[str, list[str]],
    tables: dict[str, str] | None = None,
) -> str | None:
    """field_columns: {field_name: [value_column_names]} (already excludes
    KEY_COLS). `tables`: {field_name: real table name}, as resolved by
    field_tables.resolve_fields() (a long field's table name is hashed by
    Drupal); a field missing from `tables` falls back to the naive
    `{entity_type}__{field_name}`. One SELECT per field, UNION ALL'd."""
    parts = []
    for fname, cols in field_columns.items():
        if not cols:
            continue
        table = (tables or {}).get(fname, f"{entity_type}__{fname}")
        concat_expr = "CONCAT_WS('|'," + ",".join(f"`{c}`" for c in cols) + ")"
        parts.append(
            f"SELECT '{fname}' AS fname, entity_id, delta, {concat_expr} AS val "
            f"FROM `{table}` WHERE bundle={bundle!r}"
        )
    if not parts:
        return None
    return " UNION ALL ".join(parts) + ";"


def value_columns(all_columns: list[str]) -> list[str]:
    return [c for c in all_columns if c not in KEY_COLS]


# ---------------------------------------------------------------------------
# Pure computation
# ---------------------------------------------------------------------------

def compute_field_profile(
    field_rows: list[dict],
    total_instances: int,
    pii_config: PiiConfig,
    priority_entity_ids: set[str] | None = None,
    samples_enabled: bool = False,
) -> dict[str, dict]:
    """field_rows: [{fname, entity_id, delta, val}, ...] for one bundle.
    Returns field_name -> {fill_rate_pct, non_empty_instances, sample_values,
    personal_data_suspected}.
    """
    priority_entity_ids = priority_entity_ids or set()
    per_field_rows: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for r in field_rows:
        per_field_rows[r["fname"]].append((r["entity_id"], r.get("val") or ""))

    out: dict[str, dict] = {}
    for fname, rows in per_field_rows.items():
        non_empty = [(eid, v.strip()) for eid, v in rows if v and v.strip()]
        non_empty_ids = {eid for eid, _ in non_empty}
        fill_rate = round(100.0 * len(non_empty_ids) / total_instances, 1) if total_instances else 0.0

        all_vals = [v for _, v in non_empty]
        personal = pii.looks_personal(fname, all_vals)

        samples: list[str] = []
        if samples_enabled and not personal and non_empty:
            priority_first = [(e, v) for e, v in non_empty if e in priority_entity_ids]
            others = [(e, v) for e, v in non_empty if e not in priority_entity_ids]
            seen = set()
            for _eid, v in priority_first + others:
                scrubbed = pii.prepare_sample(v, pii_config.max_sample_len)
                if scrubbed in seen:
                    continue
                seen.add(scrubbed)
                samples.append(scrubbed)
                if len(samples) >= 3:
                    break

        out[fname] = {
            "fill_rate_pct": fill_rate,
            "non_empty_instances": len(non_empty_ids),
            "sample_values": samples,
            "personal_data_suspected": personal,
        }
    return out


def compute_duplication(field_rows: list[dict]) -> dict:
    """field_rows: [{fname, entity_id, delta, val}, ...] for one bundle.
    Hashes each instance's full concatenated field content; instances
    sharing a hash with >=1 other instance are 'duplicate'."""
    per_instance: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for r in field_rows:
        per_instance[r["entity_id"]].append((r["fname"], str(r.get("delta", 0)), r.get("val") or ""))

    instance_hashes = {}
    for entity_id, parts in per_instance.items():
        parts_sorted = sorted(parts, key=lambda p: (p[0], p[1]))
        concat = "||".join(f"{f}:{d}:{v}" for f, d, v in parts_sorted)
        instance_hashes[entity_id] = hashlib.sha256(concat.encode("utf-8", "ignore")).hexdigest()

    hash_counts: dict[str, int] = defaultdict(int)
    for h in instance_hashes.values():
        hash_counts[h] += 1

    dup_instances = sum(c for c in hash_counts.values() if c > 1)
    n_with_content = len(instance_hashes)
    dup_pct = round(100.0 * dup_instances / n_with_content, 1) if n_with_content else 0.0
    top_groups = sorted((c for c in hash_counts.values() if c > 1), reverse=True)[:5]

    return {
        "instances_with_field_content": n_with_content,
        "instances_in_a_duplicate_group": dup_instances,
        "duplication_pct": dup_pct,
        "top_duplicate_group_sizes": top_groups,
    }


# ---------------------------------------------------------------------------
# DB fetch (thin)
# ---------------------------------------------------------------------------

def fetch_bundle_field_rows(
    db: DbConfig,
    entity_type: str,
    bundle: str,
    field_columns: dict[str, list[str]],
    tables: dict[str, str] | None = None,
) -> list[dict]:
    sql = build_field_union_sql(entity_type, bundle, field_columns, tables)
    if not sql:
        return []
    return fetch_rows(db, sql)
