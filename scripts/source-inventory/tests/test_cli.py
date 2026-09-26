import json

import assemble
import cli


def write_profile(tmp_path, config_dir, theme_dir, output_dir):
    path = tmp_path / "fixture.profile.yaml"
    path.write_text(
        f"""
project: fixture-project
config:
  dir: {config_dir}
theme:
  dir: {theme_dir}
domains:
  enabled: [central, aquatics]
  ownership_field: field_domain_access
render_signals:
  preprocess_files:
    - {theme_dir}/parks_fixture_theme.theme
output:
  dir: {output_dir}
"""
    )
    return path


def test_cli_analyze_no_db_writes_valid_source_structure(tmp_path, config_dir, theme_dir):
    output_dir = tmp_path / "out"
    profile_path = write_profile(tmp_path, config_dir, theme_dir, output_dir)

    exit_code = cli.main(["analyze", "--profile", str(profile_path), "--no-db"])
    assert exit_code == 0

    out_file = output_dir / "source-structure.json"
    assert out_file.exists()
    data = json.loads(out_file.read_text())
    assert assemble.validate_against_schema(data) == []


def test_cli_analyze_render_explorer_flag(tmp_path, config_dir, theme_dir):
    output_dir = tmp_path / "out"
    profile_path = write_profile(tmp_path, config_dir, theme_dir, output_dir)

    exit_code = cli.main(["analyze", "--profile", str(profile_path), "--no-db", "--render-explorer"])
    assert exit_code == 0
    assert (output_dir / "explorer" / "paragraphs.json").exists()


def test_cli_analyze_missing_profile_field_exits_nonzero(tmp_path):
    path = tmp_path / "bad.profile.yaml"
    path.write_text("config:\n  dir: /tmp\n")
    exit_code = cli.main(["analyze", "--profile", str(path)])
    assert exit_code == 2


def test_cli_no_command_prints_help_and_exits_nonzero(capsys):
    import pytest
    with pytest.raises(SystemExit):
        cli.main([])


def test_cli_warns_when_a_library_item_has_no_wrapped_bundle(capsys):
    cli._report_library_bundles([
        {"id": "7", "paragraph_bundle": "notice_banner"},
        {"id": "8", "paragraph_bundle": ""},
    ])
    captured = capsys.readouterr()
    assert "WARNING: 1/2 library item(s) have no wrapped paragraph bundle" in captured.err
    assert ": 8" in captured.err


def test_cli_reports_all_library_bundles_resolved(capsys):
    cli._report_library_bundles([{"id": "7", "paragraph_bundle": "notice_banner"}])
    captured = capsys.readouterr()
    assert captured.err == ""
    assert "Library items: 1/1 wrapped paragraph bundles resolved" in captured.out
