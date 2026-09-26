from pathlib import Path

from extract_render_signals import (
    extract_render_signals_for_bundle,
    find_twig_file,
    rollup_candidate_behavior,
    scan_php_case_blocks,
    scan_twig_template,
)


def test_scan_twig_template_finds_view_embed_with_file_line(theme_dir):
    twig_path = Path(theme_dir) / "templates/paragraphs/paragraph--upcoming-sessions.html.twig"
    text = twig_path.read_text()
    signals = scan_twig_template(text, str(twig_path), has_own_fields=False)
    view_signals = [s for s in signals if s.signal_type == "view_embed"]
    assert len(view_signals) == 1
    assert view_signals[0].file == str(twig_path)
    assert view_signals[0].line == 8  # the drupal_view(...) line
    assert "drupal_view" in view_signals[0].snippet


def test_scan_twig_template_finds_hardcoded_currency(theme_dir):
    twig_path = Path(theme_dir) / "templates/paragraphs/paragraph--fee-schedule.html.twig"
    text = twig_path.read_text()
    signals = scan_twig_template(text, str(twig_path), has_own_fields=False)
    hardcoded = [s for s in signals if s.signal_type == "hardcoded_literal"]
    # at least one per-line currency hit, plus the "0 fields + substantial
    # static content" rollup signal
    assert len(hardcoded) >= 2
    assert any("$3" in s.snippet for s in hardcoded)


def test_scan_twig_template_no_false_positive_on_own_fields_template():
    text = "<p>{{ content.field_answer }}</p>"
    signals = scan_twig_template(text, "fake.html.twig", has_own_fields=True)
    assert signals == []


def test_find_twig_file_requires_exact_theme_suggestion_prefix(theme_dir):
    twig_dirs = [Path(theme_dir) / "templates" / "paragraphs"]
    found = find_twig_file(twig_dirs, "paragraph", "upcoming_sessions")
    assert found is not None
    assert found.name == "paragraph--upcoming-sessions.html.twig"

    # No file exists for a bundle with no template -> None, not a guess.
    assert find_twig_file(twig_dirs, "paragraph", "hero_banner") is None


def test_scan_php_case_blocks_categorizes_every_signal_type(theme_dir):
    theme_file = Path(theme_dir) / "parks_fixture_theme.theme"
    blocks = scan_php_case_blocks(theme_file.read_text(), str(theme_file))
    assert blocks["hero_banner"] == []
    assert {s.signal_type for s in blocks["trail_conditions"]} == {"state_read"}
    assert {s.signal_type for s in blocks["facility_map"]} == {"config_read"}
    assert {s.signal_type for s in blocks["nearby_facilities"]} == {"entity_query"}
    assert {s.signal_type for s in blocks["session_picker"]} == {"view_embed", "service_call"}


def test_scan_php_case_blocks_line_numbers_are_absolute():
    php_text = "\n".join([
        "<?php",
        "switch ($x) {",
        "  case 'a':",
        "    $v = Views::getView('y');",  # line 4
        "    break;",
        "  default:",
        "    break;",
        "}",
    ])
    blocks = scan_php_case_blocks(php_text, "fake.theme")
    assert blocks["a"][0].line == 4


def test_rollup_candidate_behavior_matches_signal_types():
    from extract_render_signals import Signal
    signals = [Signal("view_embed", "f.twig", 1, "x")]
    behavior = rollup_candidate_behavior(signals)
    assert behavior == {
        "own_fields_only": False,
        "queries_other_content": True,
        "global_settings_or_state": False,
        "hardcoded_content": False,
    }


def test_rollup_candidate_behavior_default_own_fields_only_when_no_signals():
    assert rollup_candidate_behavior([]) == {
        "own_fields_only": True,
        "queries_other_content": False,
        "global_settings_or_state": False,
        "hardcoded_content": False,
    }


def test_extract_render_signals_for_bundle_combines_twig_and_php(theme_dir):
    twig_dirs = [Path(theme_dir) / "templates" / "paragraphs"]
    signals = extract_render_signals_for_bundle(
        "upcoming_sessions", has_own_fields=False, twig_dirs=twig_dirs, prefix="paragraph", case_blocks={},
    )
    assert any(s.signal_type == "view_embed" for s in signals)
