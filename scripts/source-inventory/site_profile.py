"""Profile loading for drupal-source-inventory.

A profile is the one place project-specific facts live: config directory,
DB connection, theme/module source dirs to scan for render signals, the
domain/site list and which field owns domain access, PII settings, and
output location. Nothing about a specific project may be hardcoded in the
extractor scripts themselves — if an extractor needs a project fact, it
comes from the profile.

See profile.example.yaml for a fully-commented template.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_TABLE_DENYLIST = [
    "users_field_data",
    "users_field_*",
    "user__*",
    "webform_submission",
    "webform_submission_*",
    "contact_message*",
    "comment_field_data",
    "comment__*",
    "sessions",
    "watchdog",
    "flood",
    "key_value_expire",
]


class ProfileError(ValueError):
    """A profile is missing a required field or has an invalid value."""


@dataclass
class DbConfig:
    docker_container: str | None = None
    database: str = ""
    host_env: str = "DB_HOST"
    port_env: str = "DB_PORT"
    user_env: str = "DB_USER"
    password_env: str = "DB_PASSWORD"
    database_env: str = "DB_NAME"
    timeout_seconds: int = 30

    def user(self) -> str:
        return os.environ.get(self.user_env, "root")

    def password(self) -> str:
        return os.environ.get(self.password_env, "")

    def host(self) -> str:
        return os.environ.get(self.host_env, "127.0.0.1")

    def port(self) -> str:
        return os.environ.get(self.port_env, "3306")

    def database_name(self) -> str:
        return os.environ.get(self.database_env) or self.database


@dataclass
class DomainsConfig:
    enabled: list[str] = field(default_factory=list)
    ownership_field: str | None = None
    source_field: str | None = None


@dataclass
class PiiConfig:
    samples: bool = False
    table_denylist: list[str] = field(default_factory=lambda: list(DEFAULT_TABLE_DENYLIST))
    max_sample_len: int = 80


@dataclass
class RenderSignalsConfig:
    theme_dir: str | None = None
    module_dirs: list[str] = field(default_factory=list)
    preprocess_files: list[str] = field(default_factory=list)
    overlay_path: str | None = None


@dataclass
class Profile:
    project: str
    config_dir: str
    db: DbConfig
    domains: DomainsConfig
    pii: PiiConfig
    render_signals: RenderSignalsConfig
    output_dir: str = "./inventory/generalized"
    path: str = ""

    def resolve(self, p: str | None) -> Path | None:
        """Resolve a profile-relative path. Absolute paths pass through."""
        if not p:
            return None
        pp = Path(p)
        if pp.is_absolute():
            return pp
        base = Path(self.path).resolve().parent if self.path else Path.cwd()
        return (base / pp).resolve()


def _get(d: dict[str, Any], key: str, default=None):
    return d.get(key, default) if isinstance(d, dict) else default


def load_profile(path: str | os.PathLike) -> Profile:
    path = str(path)
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    project = raw.get("project")
    if not project:
        raise ProfileError(f"{path}: 'project' is required")

    config_dir = _get(raw, "config", {}).get("dir") if isinstance(raw.get("config"), dict) else None
    if not config_dir:
        raise ProfileError(f"{path}: 'config.dir' is required")

    db_raw = raw.get("db", {}) or {}
    db = DbConfig(
        docker_container=db_raw.get("docker_container"),
        database=db_raw.get("database", ""),
        host_env=db_raw.get("host_env", "DB_HOST"),
        port_env=db_raw.get("port_env", "DB_PORT"),
        user_env=db_raw.get("user_env", "DB_USER"),
        password_env=db_raw.get("password_env", "DB_PASSWORD"),
        database_env=db_raw.get("database_env", "DB_NAME"),
        timeout_seconds=int(db_raw.get("timeout_seconds", 30)),
    )

    domains_raw = raw.get("domains", {}) or {}
    domains = DomainsConfig(
        enabled=list(domains_raw.get("enabled", []) or []),
        ownership_field=domains_raw.get("ownership_field"),
        source_field=domains_raw.get("source_field"),
    )

    pii_raw = raw.get("pii", {}) or {}
    pii = PiiConfig(
        samples=bool(pii_raw.get("samples", False)),
        table_denylist=list(pii_raw.get("table_denylist", DEFAULT_TABLE_DENYLIST) or DEFAULT_TABLE_DENYLIST),
        max_sample_len=int(pii_raw.get("max_sample_len", 80)),
    )

    rs_raw = raw.get("render_signals", {}) or {}
    theme_raw = raw.get("theme", {}) or {}
    render_signals = RenderSignalsConfig(
        theme_dir=theme_raw.get("dir") or rs_raw.get("theme_dir"),
        module_dirs=list(rs_raw.get("module_dirs", []) or []),
        preprocess_files=list(rs_raw.get("preprocess_files", []) or []),
        overlay_path=rs_raw.get("overlay_path"),
    )

    output_raw = raw.get("output", {}) or {}
    output_dir = output_raw.get("dir", "./inventory/generalized")

    return Profile(
        project=project,
        config_dir=config_dir,
        db=db,
        domains=domains,
        pii=pii,
        render_signals=render_signals,
        output_dir=output_dir,
        path=path,
    )
