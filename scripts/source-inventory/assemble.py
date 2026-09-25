"""The orchestrator: combines every extract_*.py module into one
source-structure.json, validated against the contract schema before it is
written. `analyze()` is the one function pytest exercises end-to-end,
over the committed raw fixture config and theme.
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path

import jsonschema

import extract_bundles
import extract_block_instances
import extract_field_profile
import extract_library_items
import extract_menus
import extract_placements
import extract_render_signals
import extract_state
import extract_usage
import extract_views
import extract_webforms
import field_tables
import render_overlay
from config_scan import iter_config
from site_profile import Profile

CONTRACT_DIR = Path(__file__).resolve().parents[2] / "contracts" / "source-structure"
ENTITY_TYPES = ("node", "paragraph", "block_content")
TWIG_PREFIX_FOR_ENTITY_TYPE = {"paragraph": "paragraph", "block_content": "block"}


def contract_version() -> str:
    return (CONTRACT_DIR / "VERSION").read_text(encoding="utf-8").strip()


def _reference_field_map(all_entity_fields: dict[str, dict], target_entity_type: str) -> dict[tuple[str, str], None]:
    out: dict[tuple[str, str], None] = {}
    for entity_type, bundles in all_entity_fields.items():
        for _bundle, fields in bundles.items():
            for fname, entry in fields.items():
                if entry.get("field_type") in ("entity_reference_revisions", "entity_reference") and \
                        entry.get("target_entity_type") == target_entity_type:
                    out[(entity_type, fname)] = None
    return out


def _build_vocabularies(config_dir: str, all_entity_fields: dict[str, dict]) -> list[dict]:
    vocabs: dict[str, dict] = {}
    for _path, data in iter_config(config_dir, "taxonomy.vocabulary.*.yml"):
        vid = data.get("vid")
        if not vid:
            continue
        vocabs[vid] = {"id": vid, "label": data.get("name", vid), "bundles_attached": set(),
                        "fields_attached": [], "term_id_hits_in_views": [], "term_id_hits_in_theme": []}

    for entity_type, bundles in all_entity_fields.items():
        for bundle, fields in bundles.items():
            for fname, entry in fields.items():
                if entry.get("target_entity_type") != "taxonomy_term":
                    continue
                for vid in entry.get("target_bundles") or []:
                    if vid not in vocabs:
                        continue
                    vocabs[vid]["bundles_attached"].add(bundle)
                    vocabs[vid]["fields_attached"].append(
                        {"entity_type": entity_type, "bundle": bundle, "field_name": fname}
                    )

    field_names_by_vocab = {
        vid: {f["field_name"] for f in v["fields_attached"]} for vid, v in vocabs.items()
    }
    for _path, data in iter_config(config_dir, "views.view.*.yml"):
        view_id = data.get("id")
        for display in (data.get("display") or {}).values():
            filters = ((display.get("display_options") or {}).get("filters") or {})
            for filter_name, filter_conf in filters.items():
                plugin = str(filter_conf.get("plugin", ""))
                field = str(filter_conf.get("field", filter_name))
                if "taxonomy" not in plugin and "term" not in plugin:
                    continue
                for vid, names in field_names_by_vocab.items():
                    if any(n in field for n in names) or not names:
                        vocabs[vid]["term_id_hits_in_views"].append(f"{view_id}:filter:{filter_name}")

    out = []
    for v in vocabs.values():
        v["bundles_attached"] = sorted(v["bundles_attached"])
        out.append(v)
    return out


def _rollup_template_hardcoded(bundle_components: list[dict], render_by_id: dict[str, dict]) -> list[dict]:
    extra = []
    for c in bundle_components:
        if c["kind"] not in ("paragraph_type", "block_content_type"):
            continue
        rb = render_by_id.get(c["id"], {})
        if rb.get("render_behavior", {}).get("hardcoded_content") and not c.get("fields"):
            extra.append({
                "id": f"{c['id']}::template",
                "kind": "template_hardcoded",
                "label": f"{c['label']}: hardcoded template content",
                "description": "Template renders content-shaped literals with 0 configured fields backing them.",
            })
    return extra


def _detect_layout_builder(config_dir: str) -> list[dict]:
    count = 0
    for _path, data in iter_config(config_dir, "core.entity_view_display.*.yml"):
        lb = ((data.get("third_party_settings") or {}).get("layout_builder") or {})
        if lb.get("enabled"):
            count += 1
    if not count:
        return []
    return [{
        "id": "layout_builder",
        "kind": "layout_builder",
        "label": "Layout Builder",
        "description": f"{count} entity view display(s) have Layout Builder enabled. Reserved kind: presence only, no component-tree extractor in this contract version.",
    }]


def analyze(prof: Profile, db=None, samples_enabled: bool = False) -> dict:
    config_dir = prof.config_dir

    all_entity_fields = {et: extract_bundles.build_entity_type_fields(config_dir, et) for et in ENTITY_TYPES}
    bundle_components = extract_bundles.build_bundle_components(config_dir)
    bundle_by_id = {c["id"]: c for c in bundle_components}

    # --- usage / parent-chain (DB-backed; skipped gracefully without a DB) ---
    usage_by_bundle: dict[str, dict] = {}
    data_quality: dict = {}
    edges: dict[str, list[dict]] = {}
    library_components: list[dict] = []
    library_details: list[dict] = []
    block_instance_components: list[dict] = []
    state_components: list[dict] = []
    state_details: list[dict] = []
    webform_components: list[dict] = []
    webform_details: list[dict] = []

    unresolved_tables: list = []
    field_index = None
    known_fields = {
        et: frozenset(f for fields in bundles.values() for f in fields)
        for et, bundles in all_entity_fields.items()
    }
    if db is not None:
        # One live-schema read; every field-table name below is resolved from
        # it (Drupal hashes long field-table names), never guessed.
        field_index = field_tables.fetch_field_table_index(
            db, ENTITY_TYPES, extract_bundles.storage_uuids(config_dir, ENTITY_TYPES),
        )
        reference_field_map = _reference_field_map(all_entity_fields, "paragraph")
        reference_tables, domain_table, usage_unresolved = extract_usage.resolve_usage_tables(
            field_index, sorted(reference_field_map), prof.domains, known_fields,
        )
        unresolved_tables.extend(usage_unresolved)
        rows_by_field_table = {
            key: extract_usage.fetch_reference_rows(db, table, key[1])
            for key, table in reference_tables.items()
        }
        rows_by_field_table[extract_usage.LIBRARY_ITEM_HOST] = extract_usage.fetch_library_item_reference_rows(db)
        edges = extract_usage.build_reference_edges(rows_by_field_table)
        paragraph_rows = extract_usage.fetch_paragraph_rows(db)
        node_status, node_bundle = extract_usage.fetch_node_status_and_bundle(db)
        node_domains = extract_usage.fetch_node_domains(db, prof.domains, domain_table)
        usage_by_bundle = extract_usage.compute_usage(paragraph_rows, edges, node_status, node_bundle, node_domains)
        data_quality = extract_usage.compute_stale_parent_metric(paragraph_rows, edges)

        library_components, library_details, library_unresolved = (
            extract_library_items.build_library_item_components(db, all_entity_fields, edges, field_index)
        )
        unresolved_tables.extend(library_unresolved)
        block_instance_components = extract_block_instances.build_block_instance_components(db)
        state_components, state_details = extract_state.build_state_components(db)
        webform_components, webform_details = extract_webforms.build_webform_components(config_dir, db)
    else:
        webform_components, webform_details = extract_webforms.build_webform_components(config_dir, None)

    # --- field fill-rate / duplication (DB-backed) ---
    field_profile_by_bundle: dict[str, dict] = {}
    duplication_by_bundle: dict[str, dict] = {}
    if db is not None:
        for entity_type in ("paragraph", "block_content"):
            for bundle, fields in all_entity_fields.get(entity_type, {}).items():
                if not fields:
                    continue
                tables, profile_unresolved = field_tables.resolve_fields(
                    field_index, [(entity_type, f) for f in sorted(fields)], "field_profile", known_fields,
                )
                unresolved_tables.extend(profile_unresolved)
                field_cols = {}
                table_by_field = {}
                for (_et, fname), table in tables.items():
                    cols = extract_field_profile.value_columns(sorted(field_index.columns(table)))
                    if cols:
                        field_cols[fname] = cols
                        table_by_field[fname] = table
                rows = extract_field_profile.fetch_bundle_field_rows(
                    db, entity_type, bundle, field_cols, table_by_field,
                )
                if not rows:
                    continue
                total_instances = usage_by_bundle.get(bundle, {}).get("total_instances", 0) if entity_type == "paragraph" else len(
                    {r["entity_id"] for r in rows}
                )
                field_profile_by_bundle[bundle] = extract_field_profile.compute_field_profile(
                    rows, total_instances, prof.pii, samples_enabled=samples_enabled
                )
                duplication_by_bundle[bundle] = extract_field_profile.compute_duplication(rows)

    # --- render signals + overlay ---
    twig_dirs = [Path(prof.render_signals.theme_dir)] if prof.render_signals.theme_dir else []
    case_blocks: dict[str, list] = {}
    for rel_path in prof.render_signals.preprocess_files:
        resolved = prof.resolve(rel_path)
        if not resolved or not resolved.exists():
            continue
        text = resolved.read_text(encoding="utf-8", errors="replace")
        for bundle, sigs in extract_render_signals.scan_php_case_blocks(text, str(resolved)).items():
            case_blocks.setdefault(bundle, []).extend(sigs)

    overlay_path = prof.resolve(prof.render_signals.overlay_path)
    overlay = render_overlay.load_overlay(overlay_path)

    render_by_id: dict[str, dict] = {}
    for c in bundle_components:
        if c["kind"] not in ("paragraph_type", "block_content_type"):
            continue
        prefix = TWIG_PREFIX_FOR_ENTITY_TYPE["paragraph" if c["kind"] == "paragraph_type" else "block_content"]
        signals = extract_render_signals.extract_render_signals_for_bundle(
            c["id"], bool(c.get("fields")), twig_dirs, prefix, case_blocks
        )
        candidate = extract_render_signals.rollup_candidate_behavior(signals) if signals else None
        behavior, source = render_overlay.resolve_render_behavior(c["id"], candidate, bool(signals), overlay)
        render_by_id[c["id"]] = {
            "render_behavior": behavior,
            "render_source": source,
            "render_signals": [s.to_dict() for s in signals],
        }

    # --- placements / menus / views / vocabularies / rollups ---
    theme_regions = extract_placements.load_theme_regions(prof.render_signals.theme_dir)
    placement_components, placement_details, code_plugin_components = extract_placements.build_placement_components(
        config_dir, prof.domains.enabled, theme_regions
    )
    placement_ids = [p["id"] for p in placement_components]
    menu_components, menu_details, menu_attachment_components = extract_menus.build_menu_components(
        config_dir, db, placement_ids
    )
    view_listing_components = extract_views.build_view_listing_components(config_dir)
    vocabularies = _build_vocabularies(config_dir, all_entity_fields)
    layout_builder_components = _detect_layout_builder(config_dir)

    # --- assemble components[] ---
    components = []
    for c in bundle_components:
        comp = dict(c)
        bundle_id = c["id"]
        if bundle_id in usage_by_bundle:
            comp["usage"] = usage_by_bundle[bundle_id]
            u = usage_by_bundle[bundle_id]
            comp["flags"] = {
                "dead_zero_instances": u["total_instances"] == 0,
                "only_in_unpublished_content": (
                    u["total_instances"] > 0 and u["published_hosts"] == 0
                    and u["library_owned_instances"] == 0 and u["unpublished_hosts"] > 0
                ),
                "only_orphaned_detached_instances": (
                    u["total_instances"] > 0 and u["published_hosts"] == 0
                    and u["unpublished_hosts"] == 0 and u["library_owned_instances"] == 0
                    and u["unresolved_instances"] > 0
                ),
            }
        if bundle_id in duplication_by_bundle:
            comp["duplication"] = duplication_by_bundle[bundle_id]
        if bundle_id in field_profile_by_bundle:
            profile_by_field = field_profile_by_bundle[bundle_id]
            for f in comp.get("fields", []):
                fp = profile_by_field.get(f["name"])
                if fp:
                    f.update(fp)
        if bundle_id in render_by_id:
            comp.update(render_by_id[bundle_id])
        components.append(comp)

    components += library_components + block_instance_components + placement_components
    components += code_plugin_components + menu_components + menu_attachment_components
    components += view_listing_components + state_components + webform_components
    components += _rollup_template_hardcoded(bundle_components, render_by_id)
    components += layout_builder_components

    # `id` is only unique WITHIN a kind (verified against a live source:
    # paragraphs_library_item and block_content are separate tables whose
    # auto-increment ids both start at 1, so the same integer id occurs in
    # both; a placement and a menu can share a machine name).
    # `key` (`{kind}:{id}`) is the actual disposition-matching identity.
    for c in components:
        c["key"] = f"{c['kind']}:{c['id']}"

    counts: dict[str, int] = {}
    for c in components:
        counts[c["kind"]] = counts.get(c["kind"], 0) + 1
    counts["total"] = len(components)

    domains_block = {
        "enabled_domains": prof.domains.enabled,
        "ownership_field": prof.domains.ownership_field or "",
        "per_component_domain_fill": {
            bid: u["domain_owned_hosts"] for bid, u in usage_by_bundle.items() if u.get("domain_owned_hosts")
        },
    }

    result = {
        "contract_version": contract_version(),
        "project": prof.project,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "profile": prof.path,
        "generator": {"name": "drupal-source-inventory", "version": contract_version()},
        "samples_enabled": samples_enabled,
        "counts": counts,
        "components": components,
        "library_items": library_details,
        "webforms": webform_details,
        "vocabularies": vocabularies,
        "state_keys": state_details,
        "domains": domains_block,
        "placements": placement_details,
        "menus": menu_details,
    }
    if db is not None:
        result["data_quality"] = {
            "parent_chain": data_quality,
            "unresolved_tables": _dedupe_unresolved(unresolved_tables),
        }
    return result


def _dedupe_unresolved(unresolved: list) -> list[dict]:
    seen: dict[tuple, dict] = {}
    for u in unresolved:
        d = u.to_dict()
        seen.setdefault((d["entity_type"], d["field_name"], d["purpose"]), d)
    return [seen[k] for k in sorted(seen)]


def strict_schema(schema):
    """Producer-side copy of the published schema with every object closed.

    The published schema accepts additional properties everywhere so that a
    consumer holding an older minor's copy (1.2.0 or later; 1.0.0 and 1.1.0
    were closed) still validates a newer minor's output. The producer, which knows exactly which keys its own version
    defines, validates against this closed copy instead, so a typo or an
    undocumented key in our own output still fails.
    """
    if isinstance(schema, list):
        return [strict_schema(item) for item in schema]
    if not isinstance(schema, dict):
        return schema
    closed = {k: strict_schema(v) for k, v in schema.items()}
    if "properties" in closed and closed.get("additionalProperties", True) is True:
        closed["additionalProperties"] = False
    return closed


def validate_against_schema(source_structure: dict, strict: bool = True) -> list[str]:
    schema = json.loads((CONTRACT_DIR / "source-structure.schema.json").read_text(encoding="utf-8"))
    if strict:
        schema = strict_schema(schema)
    validator_cls = jsonschema.validators.validator_for(schema)
    validator = validator_cls(schema)
    return [f"{'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in validator.iter_errors(source_structure)]


def write_source_structure(source_structure: dict, output_dir: str) -> Path:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "source-structure.json"
    out_path.write_text(json.dumps(source_structure, indent=2) + "\n", encoding="utf-8")
    return out_path
