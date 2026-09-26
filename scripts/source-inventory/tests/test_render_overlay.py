import yaml

from render_overlay import DEFAULT_BEHAVIOR, load_overlay, resolve_render_behavior


def test_authored_overlay_wins_over_extracted_signal(tmp_path):
    overlay_path = tmp_path / "render-verdicts.yaml"
    overlay_path.write_text(yaml.safe_dump({
        "overlays": {
            "event_roundup": {
                "own_fields_only": False,
                "queries_other_content": True,
                "global_settings_or_state": True,
                "hardcoded_content": False,
            }
        }
    }))
    overlay = load_overlay(overlay_path)
    candidate_from_signals = {"own_fields_only": True, "queries_other_content": False,
                               "global_settings_or_state": False, "hardcoded_content": False}
    behavior, source = resolve_render_behavior("event_roundup", candidate_from_signals, True, overlay)
    assert source == "authored"
    assert behavior["global_settings_or_state"] is True  # overlay's claim, not the (wrong) candidate


def test_extracted_used_when_no_overlay_row():
    candidate = {"own_fields_only": False, "queries_other_content": True,
                 "global_settings_or_state": False, "hardcoded_content": False}
    behavior, source = resolve_render_behavior("upcoming_sessions", candidate, True, overlay={})
    assert source == "extracted"
    assert behavior == candidate


def test_none_default_when_no_signals_and_no_overlay():
    behavior, source = resolve_render_behavior("hero_banner", None, False, overlay={})
    assert source == "none"
    assert behavior == DEFAULT_BEHAVIOR


def test_load_overlay_missing_file_returns_empty(tmp_path):
    assert load_overlay(tmp_path / "does-not-exist.yaml") == {}


def test_load_overlay_none_path_returns_empty():
    assert load_overlay(None) == {}
