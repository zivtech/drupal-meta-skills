"""Config-driven bundle + field extraction.

Generalizes the pilot run's separate paragraph-only and block-content-only
config parsers into one implementation that works for any of the three
bundle-carrying entity types Drupal config
follows the same naming convention for: node, paragraph, block_content.

Per entity type this reads:
  <bundle-type-config>.*.yml                              -> bundles
  field.storage.<entity_type>.*.yml                        -> field storages
  field.field.<entity_type>.<bundle>.*.yml                 -> field instances
  core.entity_view_display.<entity_type>.<bundle>.*.yml    -> formatters
  core.entity_form_display.<entity_type>.<bundle>.*.yml    -> widgets

and cross-links entity_reference_revisions/entity_reference fields that
target 'paragraph' to build generic hosted_by/nests relationships, for
ANY host entity type (not just node->paragraph like the original script).
"""
from __future__ import annotations

from collections import defaultdict

from config_scan import handler_settings_target_bundles, iter_config
from role_hint import role_hint

BUNDLE_TYPE_PATTERN = {
    "node": "node.type.*.yml",
    "paragraph": "paragraphs.paragraphs_type.*.yml",
    "block_content": "block_content.type.*.yml",
}
# Host entity type -> component kind. paragraphs_library_item has no bundle
# config (so it is not in BUNDLE_TYPE_PATTERN), but it hosts paragraphs through
# its base field, so its reference edges need an explicit kind too.
KIND_FOR_ENTITY_TYPE = {
    "node": "node_bundle",
    "paragraph": "paragraph_type",
    "block_content": "block_content_type",
    "paragraphs_library_item": "paragraphs_library_item",
}


def parse_bundle_types(config_dir: str, entity_type: str) -> dict[str, dict]:
    pattern = BUNDLE_TYPE_PATTERN[entity_type]
    bundles: dict[str, dict] = {}
    for _path, data in iter_config(config_dir, pattern):
        bid = data.get("id") or data.get("type")
        if not bid:
            continue
        bundles[bid] = {
            "id": bid,
            "label": data.get("label") or data.get("name") or bid,
            "description": data.get("description") or "",
        }
    return bundles


def parse_field_storages(config_dir: str, entity_type: str) -> dict[str, dict]:
    storages: dict[str, dict] = {}
    for _path, data in iter_config(config_dir, f"field.storage.{entity_type}.*.yml"):
        fname = data.get("field_name")
        if not fname:
            continue
        storages[fname] = {
            "field_name": fname,
            "type": data.get("type"),
            "cardinality": data.get("cardinality"),
            "settings": data.get("settings", {}) or {},
            "module": data.get("module"),
            # Drupal hashes a long field's table name from this UUID; see
            # field_tables.drupal_field_table_name().
            "uuid": data.get("uuid"),
        }
    return storages


def storage_uuids(config_dir: str, entity_types: tuple[str, ...]) -> dict[tuple[str, str], str]:
    """(entity_type, field_name) -> field storage UUID, where the export has one."""
    out: dict[tuple[str, str], str] = {}
    for et in entity_types:
        for fname, storage in parse_field_storages(config_dir, et).items():
            if storage.get("uuid"):
                out[(et, fname)] = storage["uuid"]
    return out


def parse_field_instances(config_dir: str, entity_type: str, bundle_ids: set[str], storages: dict[str, dict]) -> dict[str, dict]:
    """Returns bundle -> {field_name -> field_entry}."""
    out: dict[str, dict] = defaultdict(dict)
    for _path, data in iter_config(config_dir, f"field.field.{entity_type}.*.yml"):
        bundle = data.get("bundle")
        fname = data.get("field_name")
        if bundle not in bundle_ids or not fname:
            continue
        fstorage = storages.get(fname, {})
        ftype = fstorage.get("type", data.get("field_type", "unknown"))
        settings = data.get("settings", {}) or {}
        entry = {
            "field_name": fname,
            "label": data.get("label", ""),
            "field_type": ftype,
            "cardinality": fstorage.get("cardinality"),
            "required": bool(data.get("required", False)),
            "description": data.get("description", "") or "",
            "settings": settings,
        }
        if ftype in ("entity_reference", "entity_reference_revisions"):
            entry["target_entity_type"] = fstorage.get("settings", {}).get("target_type")
            entry["target_bundles"] = handler_settings_target_bundles(settings)
        if ftype and ftype.startswith("list_"):
            entry["allowed_values"] = fstorage.get("settings", {}).get("allowed_values")
        out[bundle][fname] = entry
    return out


def parse_view_displays(config_dir: str, entity_type: str, bundle_ids: set[str]) -> dict[str, dict]:
    """bundle -> mode -> {field_name -> {formatter_type, label, settings, hidden}}"""
    out: dict[str, dict] = defaultdict(dict)
    for _path, data in iter_config(config_dir, f"core.entity_view_display.{entity_type}.*.yml"):
        bundle = data.get("bundle")
        mode = data.get("mode", "default")
        if bundle not in bundle_ids:
            continue
        mode_info = {}
        for fname, fconf in (data.get("content") or {}).items():
            mode_info[fname] = {
                "formatter_type": fconf.get("type"),
                "label_display": fconf.get("label"),
                "settings": fconf.get("settings", {}),
            }
        for fname in (data.get("hidden") or {}):
            mode_info.setdefault(fname, {})["hidden"] = True
        out[bundle][mode] = mode_info
    return out


def parse_form_displays(config_dir: str, entity_type: str, bundle_ids: set[str]) -> dict[str, dict]:
    out: dict[str, dict] = defaultdict(dict)
    for _path, data in iter_config(config_dir, f"core.entity_form_display.{entity_type}.*.yml"):
        bundle = data.get("bundle")
        mode = data.get("mode", "default")
        if bundle not in bundle_ids:
            continue
        widget_info = {}
        for fname, fconf in (data.get("content") or {}).items():
            widget_info[fname] = {"widget_type": fconf.get("type"), "settings": fconf.get("settings", {})}
        out[bundle][mode] = widget_info
    return out


def build_entity_type_fields(config_dir: str, entity_type: str) -> dict[str, dict]:
    """bundle -> {field_name -> enriched field entry} for one entity type."""
    bundles = parse_bundle_types(config_dir, entity_type)
    bundle_ids = set(bundles.keys())
    storages = parse_field_storages(config_dir, entity_type)
    instances = parse_field_instances(config_dir, entity_type, bundle_ids, storages)
    view_displays = parse_view_displays(config_dir, entity_type, bundle_ids)
    form_displays = parse_form_displays(config_dir, entity_type, bundle_ids)

    for bundle, fields in instances.items():
        for fname, entry in fields.items():
            modes = view_displays.get(bundle, {})
            vd = {mode: info[fname] for mode, info in modes.items() if fname in info}
            if vd:
                entry["view_display"] = vd
            widget = form_displays.get(bundle, {}).get("default", {}).get(fname)
            if widget:
                entry["widget"] = widget.get("widget_type")
    return instances


def build_relationships(all_entity_fields: dict[str, dict]) -> tuple[dict, dict]:
    """Generic host<->paragraph relationship walk, replacing the pilot run's
    node-only + paragraph-only special cases. Any host entity_type whose
    field is entity_reference_revisions/entity_reference targeting
    'paragraph' contributes an edge, regardless of whether the host is
    node, paragraph, or block_content.

    Returns (hosted_by[bundle] -> [{host_kind, host_id, field_name}],
             nests[bundle] -> [{kind, id, field_name}])  keyed by the
    TARGET paragraph bundle for hosted_by, and by the HOST bundle for nests.
    """
    hosted_by: dict[str, list] = defaultdict(list)
    nests: dict[str, list] = defaultdict(list)

    for entity_type, bundles in all_entity_fields.items():
        host_kind = KIND_FOR_ENTITY_TYPE[entity_type]
        for host_bundle, fields in bundles.items():
            for fname, entry in fields.items():
                if entry.get("field_type") not in ("entity_reference_revisions", "entity_reference"):
                    continue
                if entry.get("target_entity_type") != "paragraph":
                    continue
                for target_bundle in entry.get("target_bundles") or []:
                    hosted_by[target_bundle].append(
                        {"host_kind": host_kind, "host_id": host_bundle, "field_name": fname}
                    )
                    nests[host_bundle].append(
                        {"kind": "paragraph_type", "id": target_bundle, "field_name": fname}
                    )
    return hosted_by, nests


def build_bundle_components(config_dir: str) -> list[dict]:
    """Top-level entry point: returns a list of component dicts (kind
    node_bundle/paragraph_type/block_content_type) with fields + hosted_by +
    nests populated. Usage/duplication/render_behavior are added later by
    other extractors and merged in assemble.py.
    """
    all_entity_fields: dict[str, dict] = {}
    all_bundles: dict[str, dict] = {}
    for entity_type in ("node", "paragraph", "block_content"):
        bundles = parse_bundle_types(config_dir, entity_type)
        all_bundles[entity_type] = bundles
        all_entity_fields[entity_type] = build_entity_type_fields(config_dir, entity_type)

    hosted_by, nests = build_relationships(all_entity_fields)

    components = []
    for entity_type, bundles in all_bundles.items():
        kind = KIND_FOR_ENTITY_TYPE[entity_type]
        fields_by_bundle = all_entity_fields.get(entity_type, {})
        for bundle_id, meta in bundles.items():
            fields = fields_by_bundle.get(bundle_id, {})
            field_list = []
            for fname, entry in fields.items():
                role = role_hint(fname, entry.get("field_type", ""), entry.get("target_entity_type"))
                field_list.append({
                    "name": fname,
                    "label": entry.get("label"),
                    "field_type": entry.get("field_type"),
                    "cardinality": entry.get("cardinality"),
                    "required": entry.get("required"),
                    "role": role,
                    "role_source": "heuristic",
                    "target_entity_type": entry.get("target_entity_type"),
                    "target_bundles": entry.get("target_bundles"),
                    "allowed_values": entry.get("allowed_values"),
                })
            component = {
                "id": bundle_id,
                "kind": kind,
                "label": meta["label"],
                "description": meta.get("description") or None,
                "fields": field_list,
            }
            if kind == "paragraph_type" and hosted_by.get(bundle_id):
                component["hosted_by"] = hosted_by[bundle_id]
            if nests.get(bundle_id):
                component["nests"] = nests[bundle_id]
            components.append(component)
    return components
