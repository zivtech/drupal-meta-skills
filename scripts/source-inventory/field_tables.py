"""Resolve Drupal dedicated field-table names against the live schema.

A configurable field's values live in a dedicated table, normally named
`{entity_type}__{field_name}`. Drupal core shortens that name when it would
exceed 48 characters (keeping a 16-character margin for database prefixes):
the field name is replaced by the first 10 hex characters of a sha256 of the
field storage's unique identifier, giving `{entity_type}__{hash10}` (and
`{entity_type}_r__{hash10}` for the revision table). See
`Drupal\\Core\\Entity\\Sql\\DefaultTableMapping::generateFieldTableName()`,
core/lib/Drupal/Core/Entity/Sql/DefaultTableMapping.php:623-650 (Drupal
11.4). For a configurable field the unique identifier is the field storage
config entity's UUID (FieldStorageConfig::getUniqueStorageIdentifier(),
core/modules/field/src/Entity/FieldStorageConfig.php:826-828).

So a naive `{entity_type}__{field_name}` query is simply wrong for long
field names. This module never guesses: it reads the live table/column list
from information_schema once, then maps each field to its table by, in order,

1. the naive name, when that table exists;
2. core's hashed name computed from the storage UUID (when the config export
   provides one), when that table exists;
3. column presence: the hashed-shape table (`{entity_type}__` + 10 hex chars)
   whose value columns are all `{field_name}_*` and are not better explained
   by a longer field name (so `field_image` never claims `field_image_caption`'s
   table), and that carries any column the caller requires (e.g.
   `{field_name}_target_id` for a reference field).

A field none of these resolve is returned as unresolved, never silently
dropped: callers record it in `data_quality.unresolved_tables`.
"""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass, field

from db import fetch_rows
from site_profile import DbConfig

MAX_TABLE_NAME_LENGTH = 48
ENTITY_TYPE_ID_MAX_LENGTH = 32
HASH_LENGTH = 10
KEY_COLUMNS = frozenset({"bundle", "deleted", "entity_id", "revision_id", "langcode", "delta"})


def drupal_field_table_name(
    entity_type_id: str,
    field_name: str,
    unique_storage_identifier: str,
    revision: bool = False,
    prefix: str = "",
) -> str:
    """Python mirror of core's DefaultTableMapping::generateFieldTableName()."""
    entity_type_id = entity_type_id[:ENTITY_TYPE_ID_MAX_LENGTH]
    separator = "_revision__" if revision else "__"
    table_name = f"{prefix}{entity_type_id}{separator}{field_name}"
    if len(table_name) > MAX_TABLE_NAME_LENGTH:
        separator = "_r__" if revision else "__"
        field_hash = hashlib.sha256(unique_storage_identifier.encode("utf-8")).hexdigest()[:HASH_LENGTH]
        table_name = f"{prefix}{entity_type_id}{separator}{field_hash}"
        if len(table_name) > MAX_TABLE_NAME_LENGTH:
            table_name = f"{prefix[:34]}{separator}{field_hash}"
    return table_name


@dataclass(frozen=True)
class UnresolvedTable:
    entity_type: str
    field_name: str
    expected_table: str
    purpose: str

    def to_dict(self) -> dict:
        return {
            "entity_type": self.entity_type,
            "field_name": self.field_name,
            "expected_table": self.expected_table,
            "purpose": self.purpose,
        }


@dataclass(frozen=True)
class FieldTableIndex:
    """Immutable snapshot of `table -> columns` for dedicated field tables."""
    columns_by_table: dict[str, frozenset[str]]
    storage_uuids: dict[tuple[str, str], str] = field(default_factory=dict)

    def columns(self, table: str) -> frozenset[str]:
        return self.columns_by_table.get(table, frozenset())

    def table_for(
        self,
        entity_type: str,
        field_name: str,
        known_fields: frozenset[str] = frozenset(),
        required_column: str | None = None,
    ) -> str | None:
        def acceptable(table: str) -> bool:
            if table not in self.columns_by_table:
                return False
            return required_column is None or required_column in self.columns_by_table[table]

        naive = f"{entity_type}__{field_name}"
        if acceptable(naive):
            return naive

        uuid = self.storage_uuids.get((entity_type, field_name))
        if uuid:
            predicted = drupal_field_table_name(entity_type, field_name, uuid)
            if acceptable(predicted):
                return predicted

        hashed_shape = re.compile(rf"^{re.escape(entity_type)}__[0-9a-f]{{{HASH_LENGTH}}}$")
        candidates = [
            t for t in sorted(self.columns_by_table)
            if hashed_shape.match(t) and acceptable(t)
            and _owning_field(self.columns_by_table[t], known_fields | {field_name}) == field_name
        ]
        return candidates[0] if len(candidates) == 1 else None


def _owning_field(columns: frozenset[str], field_names: frozenset[str] | set[str]) -> str | None:
    """The longest field name that prefixes every value column of a table."""
    value_cols = [c for c in columns if c not in KEY_COLUMNS]
    if not value_cols:
        return None
    owners = [f for f in field_names if all(c.startswith(f"{f}_") for c in value_cols)]
    return max(owners, key=len) if owners else None


def build_index(rows: list[dict], storage_uuids: dict[tuple[str, str], str] | None = None) -> FieldTableIndex:
    cols: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        cols[r["table_name"]].add(r["column_name"])
    return FieldTableIndex(
        columns_by_table={t: frozenset(c) for t, c in cols.items()},
        storage_uuids=dict(storage_uuids or {}),
    )


def _like_prefix(entity_type: str) -> str:
    escaped = entity_type.replace("_", "\\_")
    return f"{escaped}\\_\\_%"


def fetch_field_table_index(
    db: DbConfig,
    entity_types: tuple[str, ...],
    storage_uuids: dict[tuple[str, str], str] | None = None,
) -> FieldTableIndex:
    """One information_schema read for every `{entity_type}__*` table.

    Any DbError (missing client, timeout, auth, SQL) propagates: without the
    live table list nothing downstream can be trusted.
    """
    if not entity_types:
        return build_index([], storage_uuids)
    likes = " OR ".join(f"TABLE_NAME LIKE '{_like_prefix(et)}'" for et in entity_types)
    rows = fetch_rows(
        db,
        "SELECT TABLE_NAME AS table_name, COLUMN_NAME AS column_name "
        "FROM information_schema.COLUMNS "
        f"WHERE TABLE_SCHEMA = DATABASE() AND ({likes});",
    )
    return build_index(rows, storage_uuids)


def resolve_fields(
    index: FieldTableIndex,
    keys: list[tuple[str, str]],
    purpose: str,
    known_fields_by_entity_type: dict[str, frozenset[str]] | None = None,
    required_suffix: str | None = None,
) -> tuple[dict[tuple[str, str], str], list[UnresolvedTable]]:
    """Map (entity_type, field_name) -> table. Returns (resolved, unresolved)."""
    known = known_fields_by_entity_type or {}
    resolved: dict[tuple[str, str], str] = {}
    unresolved: list[UnresolvedTable] = []
    for entity_type, field_name in keys:
        required = f"{field_name}{required_suffix}" if required_suffix else None
        table = index.table_for(entity_type, field_name, known.get(entity_type, frozenset()), required)
        if table is None:
            unresolved.append(UnresolvedTable(entity_type, field_name, f"{entity_type}__{field_name}", purpose))
        else:
            resolved[(entity_type, field_name)] = table
    return resolved, unresolved
