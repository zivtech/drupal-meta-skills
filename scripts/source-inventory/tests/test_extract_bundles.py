from extract_bundles import build_bundle_components, build_entity_type_fields, parse_bundle_types


def test_parse_bundle_types_finds_node_and_paragraph_and_block_content(config_dir):
    node_bundles = parse_bundle_types(config_dir, "node")
    assert "program_page" in node_bundles

    paragraph_bundles = parse_bundle_types(config_dir, "paragraph")
    assert {"faq_accordion_row", "hero_banner", "upcoming_sessions", "fee_schedule",
            "gallery_item", "photo_showcase", "orphaned_widget"} <= set(paragraph_bundles)

    block_bundles = parse_bundle_types(config_dir, "block_content")
    assert "footer_social" in block_bundles


def test_build_bundle_components_kinds_and_counts(config_dir):
    components = build_bundle_components(config_dir)
    by_id = {c["id"]: c for c in components}

    assert by_id["program_page"]["kind"] == "node_bundle"
    assert by_id["faq_accordion_row"]["kind"] == "paragraph_type"
    assert by_id["footer_social"]["kind"] == "block_content_type"

    # fee_schedule has 0 configured fields (hardcoded-template negative control)
    assert by_id["fee_schedule"]["fields"] == []

    # gallery_item is an IEF-only child: hosted only by photo_showcase (a
    # paragraph), never referenced by a node bundle field directly.
    hosted_by = by_id["gallery_item"]["hosted_by"]
    assert hosted_by == [{"host_kind": "paragraph_type", "host_id": "photo_showcase", "field_name": "field_gallery_items"}]
    assert not any(h["host_kind"] == "node_bundle" for h in hosted_by)


def test_field_roles_assigned_heuristically(config_dir):
    components = build_bundle_components(config_dir)
    by_id = {c["id"]: c for c in components}
    fields = {f["name"]: f for f in by_id["faq_accordion_row"]["fields"]}

    assert fields["field_price"]["role"] == "FACT"
    assert fields["field_price"]["role_source"] == "heuristic"
    assert fields["field_answer"]["role"] == "PROSE"


def test_boolean_fact_vs_presentation_pair_present_in_fixture(config_dir):
    fields_by_bundle = build_entity_type_fields(config_dir, "paragraph")
    hero = fields_by_bundle["hero_banner"]
    assert hero["field_residents_only"]["field_type"] == "boolean"
    assert hero["field_light_theme"]["field_type"] == "boolean"


def test_kind_for_entity_type_maps_library_item_and_matches_the_contract_enum():
    import json
    from pathlib import Path

    from extract_bundles import BUNDLE_TYPE_PATTERN, KIND_FOR_ENTITY_TYPE
    from extract_usage import LIBRARY_ITEM_HOST, build_reference_edges

    assert KIND_FOR_ENTITY_TYPE["paragraphs_library_item"] == "paragraphs_library_item"
    # Every bundle-carrying entity type has a kind; every kind is a contract kind.
    assert set(BUNDLE_TYPE_PATTERN) <= set(KIND_FOR_ENTITY_TYPE)
    schema_path = Path(__file__).resolve().parents[3] / "contracts" / "source-structure" / "source-structure.schema.json"
    kinds = set(json.loads(schema_path.read_text())["definitions"]["kind"]["enum"])
    assert set(KIND_FOR_ENTITY_TYPE.values()) <= kinds

    edges = build_reference_edges({LIBRARY_ITEM_HOST: [{"entity_id": "7", "target_id": "900"}]})
    assert edges["900"] == [{"host_kind": "paragraphs_library_item", "host_id": "7", "field_name": "paragraphs"}]
