"""End-to-end 'analyze on a committed raw fixture' test (no live DB). Also
the main integration point where every extractor module's output has to
actually cohere into one schema-valid source-structure.json.
"""
from pathlib import Path

import assemble
from site_profile import DomainsConfig, PiiConfig, Profile, RenderSignalsConfig


def build_fixture_profile(config_dir: str, theme_dir: str) -> Profile:
    from site_profile import DbConfig
    return Profile(
        project="example-parks-district-fixture",
        config_dir=config_dir,
        db=DbConfig(database="fixture"),
        domains=DomainsConfig(enabled=["central", "aquatics"], ownership_field="field_domain_access"),
        pii=PiiConfig(samples=False),
        render_signals=RenderSignalsConfig(
            theme_dir=theme_dir,
            preprocess_files=[str(Path(theme_dir) / "parks_fixture_theme.theme")],
            overlay_path=None,
        ),
        output_dir="./unused-in-this-test",
    )


def test_analyze_without_db_is_schema_valid(config_dir, theme_dir):
    prof = build_fixture_profile(config_dir, theme_dir)
    result = assemble.analyze(prof, db=None, samples_enabled=False)

    issues = assemble.validate_against_schema(result)
    assert issues == [], f"schema violations: {issues}"

    assert result["counts"]["total"] == len(result["components"])
    assert result["samples_enabled"] is False


def test_analyze_without_db_covers_expected_kinds(config_dir, theme_dir):
    prof = build_fixture_profile(config_dir, theme_dir)
    result = assemble.analyze(prof, db=None, samples_enabled=False)
    by_id = {c["id"]: c for c in result["components"]}

    assert by_id["program_page"]["kind"] == "node_bundle"
    assert by_id["faq_accordion_row"]["kind"] == "paragraph_type"
    assert by_id["footer_social"]["kind"] == "block_content_type"
    assert by_id["footer_social_main"]["kind"] == "placement"
    assert by_id["main"]["kind"] == "menu"
    assert by_id["contact_us"]["kind"] == "webform"
    assert by_id["session_calendar"]["kind"] == "view_listing"
    assert by_id["views_block:session_calendar-block_1"]["kind"] == "code_plugin"

    # IEF-only child relationship survives assembly untouched.
    assert by_id["gallery_item"]["hosted_by"][0]["host_id"] == "photo_showcase"


def test_analyze_render_behavior_from_signals_no_db_required(config_dir, theme_dir):
    prof = build_fixture_profile(config_dir, theme_dir)
    result = assemble.analyze(prof, db=None, samples_enabled=False)
    by_id = {c["id"]: c for c in result["components"]}

    related = by_id["upcoming_sessions"]
    assert related["render_source"] == "extracted"
    assert related["render_behavior"]["queries_other_content"] is True
    assert len(related["render_signals"]) >= 1

    hero = by_id["hero_banner"]
    assert hero["render_source"] == "none"
    assert hero["render_behavior"]["own_fields_only"] is True

    fees = by_id["fee_schedule"]
    assert fees["render_behavior"]["hardcoded_content"] is True


def test_analyze_rolls_up_template_hardcoded_component(config_dir, theme_dir):
    prof = build_fixture_profile(config_dir, theme_dir)
    result = assemble.analyze(prof, db=None, samples_enabled=False)
    by_id = {c["id"]: c for c in result["components"]}
    assert "fee_schedule::template" in by_id
    assert by_id["fee_schedule::template"]["kind"] == "template_hardcoded"


def test_analyze_vocabulary_and_term_id_view_filter_hit(config_dir, theme_dir):
    prof = build_fixture_profile(config_dir, theme_dir)
    result = assemble.analyze(prof, db=None, samples_enabled=False)
    vocabs = {v["id"]: v for v in result["vocabularies"]}
    program_topics = vocabs["program_topics"]
    assert "program_page" in program_topics["bundles_attached"]
    assert any("session_calendar" in hit for hit in program_topics["term_id_hits_in_views"])


def test_analyze_samples_enabled_false_means_every_sample_list_empty(config_dir, theme_dir):
    prof = build_fixture_profile(config_dir, theme_dir)
    result = assemble.analyze(prof, db=None, samples_enabled=False)
    for c in result["components"]:
        for f in c.get("fields", []):
            assert f.get("sample_values", []) == []


# ---------------------------------------------------------------------------
# Mocked-DB end-to-end test. The --no-db tests above never exercise the
# field-profile merge path (usage_by_bundle / field_profile_by_bundle stay
# empty with db=None) -- that's exactly the path where a real schema-key
# mismatch ("samples" vs the contract's "sample_values") reached the proof
# run undetected by the --no-db-only test suite. This test drives the
# whole pipeline through one fake db.fetch_rows so every DB-backed
# extractor runs, and asserts the result is still schema-valid.
# ---------------------------------------------------------------------------

LIVE_FIELD_TABLES = {
    "paragraph__field_question": ["entity_id", "bundle", "delta", "field_question_value"],
    "paragraph__field_answer": ["entity_id", "bundle", "delta", "field_answer_value", "field_answer_format"],
    "paragraph__field_price": ["entity_id", "bundle", "delta", "field_price_value"],
    "paragraph__field_image": ["entity_id", "bundle", "delta", "field_image_target_id", "field_image_alt"],
    "paragraph__field_light_theme": ["entity_id", "bundle", "delta", "field_light_theme_value"],
    "paragraph__field_residents_only": ["entity_id", "bundle", "delta", "field_residents_only_value"],
    "paragraph__field_gallery_items": ["entity_id", "deleted", "field_gallery_items_target_id",
                                       "field_gallery_items_target_revision_id"],
    "block_content__field_social_facebook": ["entity_id", "bundle", "delta", "field_social_facebook_uri"],
    "node__field_content": ["entity_id", "deleted", "field_content_target_id", "field_content_target_revision_id"],
    "node__field_domain_access": ["entity_id", "deleted", "field_domain_access_target_id"],
}


def _fake_fetch_rows(_db, sql: str, missing_tables: frozenset = frozenset()) -> list[dict]:
    s = sql.lower()
    if "information_schema.columns" in s:
        if "table_name = 'paragraphs_library_item_field_data'" in s:
            # Stock Paragraphs Library layout: the item's paragraph lives in
            # its base column paragraphs__target_id (default_langcode also present).
            return [{"column_name": "present"}]
        if "paragraphs\\_library\\_item" in s:
            return []  # no dedicated paragraphs_library_item__* table: the base column is used
        return [
            {"table_name": t, "column_name": c}
            for t, cols in LIVE_FIELD_TABLES.items() if t not in missing_tables for c in cols
        ]
    if "paragraph__field_question" in s:
        return [{"fname": "field_question", "entity_id": "1", "delta": "0", "val": "Is parking free?"}]
    if "paragraph__field_answer" in s:
        return [{"fname": "field_answer", "entity_id": "1", "delta": "0", "val": "Yes, on weekends."}]
    if "paragraph__field_price" in s:
        return [{"fname": "field_price", "entity_id": "1", "delta": "0", "val": None}]
    if "block_content__field_social_facebook" in s:
        return []
    if "paragraphs__target_id as target_id" in s:
        return [{"entity_id": "7", "target_id": "2"}]
    if "paragraphs__target_id as paragraph_id" in s:
        return [{"item_id": "7", "paragraph_id": "2"}]
    if "paragraphs_item_field_data" in s:
        return [{"id": "1", "type": "faq_accordion_row", "parent_id": "100", "parent_type": "node"},
                {"id": "2", "type": "hero_banner", "parent_id": "7", "parent_type": "paragraphs_library_item"}]
    if "node_field_data" in s:
        return [{"nid": "100", "status": "1", "type": "program_page"}]
    if "node__field_content" in s:
        return [{"entity_id": "100", "target_id": "1"}]
    if "node__field_domain_access" in s:
        return [{"entity_id": "100", "target_id": "central"}]
    if "menu_link_content_data" in s and "group by" in s:
        return [{"menu_name": "main", "n": "3"}]
    if "menu_link_content_data" in s:
        return [{"id": "link-1", "menu_name": "main", "link_options": ""}]
    if "key_value" in s:
        return [{"name": "system.maintenance_mode", "size_bytes": "1"}]
    if "webform_submission" in s:
        return [{"webform_id": "contact_us", "n": "5"}]
    if "block_content_field_data" in s:
        return [{"id": "11111111-1111-1111-1111-111111111111", "info": "Footer Social (main)", "type": "footer_social"}]
    if "from paragraphs_library_item_field_data" in s:
        return [{"id": "7", "label": "Shared closing-times notice"}]
    return []


def _patch_fetch_rows(monkeypatch, fake):
    import extract_block_instances, extract_field_profile, extract_library_items
    import extract_menus, extract_state, extract_usage, extract_webforms, field_tables
    for mod in (extract_usage, extract_field_profile, extract_menus, extract_state,
                extract_webforms, extract_block_instances, extract_library_items, field_tables):
        monkeypatch.setattr(mod, "fetch_rows", fake)


def test_analyze_records_unresolved_field_tables_in_data_quality(monkeypatch, config_dir, theme_dir):
    # The nested paragraph-reference table and one profiled field's table are
    # absent from the live schema: the run still completes, and both gaps are
    # named in data_quality instead of silently counting zero rows.
    missing = frozenset({"paragraph__field_gallery_items", "paragraph__field_image"})
    _patch_fetch_rows(monkeypatch, lambda db, sql: _fake_fetch_rows(db, sql, missing))

    prof = build_fixture_profile(config_dir, theme_dir)
    result = assemble.analyze(prof, db=prof.db, samples_enabled=False)

    assert assemble.validate_against_schema(result) == []
    unresolved = {(u["entity_type"], u["field_name"], u["purpose"]) for u in result["data_quality"]["unresolved_tables"]}
    assert unresolved == {
        ("paragraph", "field_gallery_items", "usage"),
        ("paragraph", "field_gallery_items", "field_profile"),
        ("paragraph", "field_image", "field_profile"),
    }


def test_analyze_with_mocked_db_is_schema_valid(monkeypatch, config_dir, theme_dir):
    # Every extract_*.py module did `from db import fetch_rows`, binding its
    # own local name -- patching db.fetch_rows alone would NOT reach those
    # (classic from-import monkeypatch gotcha), so patch each importer.
    _patch_fetch_rows(monkeypatch, _fake_fetch_rows)

    prof = build_fixture_profile(config_dir, theme_dir)
    result = assemble.analyze(prof, db=prof.db, samples_enabled=False)

    issues = assemble.validate_against_schema(result)
    assert issues == [], f"schema violations with DB-backed extraction: {issues}"
    assert result["data_quality"]["unresolved_tables"] == []

    by_id = {c["id"]: c for c in result["components"]}
    faq_fields = {f["name"]: f for f in by_id["faq_accordion_row"]["fields"]}
    # This is the exact assertion that would have failed before the
    # "samples" -> "sample_values" fix: the key must match the contract.
    assert "sample_values" in faq_fields["field_question"]
    assert faq_fields["field_question"]["fill_rate_pct"] == 100.0

    assert result["data_quality"]["parent_chain"]["total_child_rows"] == 2
    assert result["data_quality"]["parent_chain"]["stale_denormalized_parent_rows"] == 0

    # The library item's wrapped paragraph is read from its base field, so its
    # bundle is populated and the paragraph counts as library-owned.
    assert result["library_items"] == [{
        "id": "7", "label": "Shared closing-times notice", "paragraph_bundle": "hero_banner",
        "host_count": 0, "hosts": [],
    }]
    assert by_id["hero_banner"]["usage"]["library_owned_instances"] == 1
