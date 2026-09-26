import os

import pytest

from site_profile import ProfileError, load_profile


MINIMAL_YAML = """
project: fixture-project
config:
  dir: ./config
"""

FULL_YAML = """
project: fixture-project
config:
  dir: ./config
theme:
  dir: ./theme
db:
  docker_container: my-db-container
  database: fixture_db
  timeout_seconds: 45
domains:
  enabled: [siteA, siteB]
  ownership_field: field_domain_access
pii:
  samples: true
  max_sample_len: 40
render_signals:
  preprocess_files:
    - project_theme.theme
  overlay_path: render-verdicts.yaml
output:
  dir: ./out
"""


def test_load_profile_requires_project(tmp_path):
    path = tmp_path / "p.yaml"
    path.write_text("config:\n  dir: ./config\n")
    with pytest.raises(ProfileError):
        load_profile(path)


def test_load_profile_requires_config_dir(tmp_path):
    path = tmp_path / "p.yaml"
    path.write_text("project: x\n")
    with pytest.raises(ProfileError):
        load_profile(path)


def test_load_profile_minimal_uses_defaults(tmp_path):
    path = tmp_path / "p.yaml"
    path.write_text(MINIMAL_YAML)
    prof = load_profile(path)
    assert prof.project == "fixture-project"
    assert prof.pii.samples is False
    assert prof.db.timeout_seconds == 30
    assert prof.output_dir == "./inventory/generalized"


def test_load_profile_full(tmp_path):
    path = tmp_path / "p.yaml"
    path.write_text(FULL_YAML)
    prof = load_profile(path)
    assert prof.db.docker_container == "my-db-container"
    assert prof.db.timeout_seconds == 45
    assert prof.domains.enabled == ["siteA", "siteB"]
    assert prof.pii.samples is True
    assert prof.render_signals.overlay_path == "render-verdicts.yaml"
    assert prof.output_dir == "./out"


def test_resolve_relative_path_against_profile_location(tmp_path):
    path = tmp_path / "sub" / "p.yaml"
    path.parent.mkdir()
    path.write_text(MINIMAL_YAML)
    prof = load_profile(path)
    resolved = prof.resolve("theme.theme")
    assert resolved == (tmp_path / "sub" / "theme.theme").resolve()


def test_resolve_absolute_path_passes_through(tmp_path):
    path = tmp_path / "p.yaml"
    path.write_text(MINIMAL_YAML)
    prof = load_profile(path)
    assert prof.resolve("/absolute/path.theme") == __import__("pathlib").Path("/absolute/path.theme")


def test_db_config_reads_env_vars(monkeypatch, tmp_path):
    path = tmp_path / "p.yaml"
    path.write_text(MINIMAL_YAML)
    prof = load_profile(path)
    monkeypatch.setenv("DB_USER", "someuser")
    assert prof.db.user() == "someuser"
    monkeypatch.delenv("DB_USER", raising=False)
    assert prof.db.user() == "root"
