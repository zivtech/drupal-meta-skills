from extract_placements import build_placement_components, decode_visibility, load_theme_regions


def test_load_theme_regions(theme_dir):
    regions = load_theme_regions(theme_dir)
    assert regions == {"header", "content", "sidebar_first", "footer"}


def test_decode_visibility_domain_condition():
    visibility = {"domain": {"domains": {"central": "central", "aquatics": "aquatics"}, "negate": False}}
    decoded = decode_visibility(visibility, enabled_domains=["central", "aquatics", "trails"])
    assert decoded["conditions"] == ["domain"]
    assert decoded["domains"] == ["aquatics", "central"]
    assert decoded["negate"] is False


def test_build_placement_components_block_content_vs_code_plugin(config_dir, theme_dir):
    regions = load_theme_regions(theme_dir)
    placements, details, code_plugins = build_placement_components(
        config_dir, enabled_domains=["central", "aquatics"], theme_regions=regions
    )
    placement_ids = {p["id"] for p in placements}
    assert placement_ids == {"footer_social_main", "custom_code_block"}

    details_by_id = {d["id"]: d for d in details}
    assert details_by_id["footer_social_main"]["block_content_id"] == "11111111-1111-1111-1111-111111111111"
    assert details_by_id["footer_social_main"]["visibility_domains"] == ["aquatics", "central"]
    assert details_by_id["footer_social_main"]["non_standard_region"] is False  # 'footer' is a declared region

    assert details_by_id["custom_code_block"]["block_content_id"] is None
    assert details_by_id["custom_code_block"]["non_standard_region"] is False  # 'sidebar_first' is declared

    code_plugin_ids = {p["id"] for p in code_plugins}
    assert "views_block:session_calendar-block_1" in code_plugin_ids
    for p in code_plugins:
        assert p["kind"] == "code_plugin"


def test_non_standard_region_detected_when_region_not_declared(config_dir):
    # No theme_regions supplied (empty set) disables the check entirely --
    # this asserts the *opposite* case: a region NOT in a real declared set
    # is flagged.
    placements, details, _ = build_placement_components(
        config_dir, enabled_domains=[], theme_regions={"header", "content"}  # 'footer' and 'sidebar_first' absent
    )
    details_by_id = {d["id"]: d for d in details}
    assert details_by_id["footer_social_main"]["non_standard_region"] is True
    assert details_by_id["custom_code_block"]["non_standard_region"] is True
