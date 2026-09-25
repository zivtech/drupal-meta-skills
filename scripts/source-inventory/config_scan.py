"""Shared helpers for scanning a Drupal config/sync directory.

Every extractor that reads `*.yml` config goes through here so there is
exactly one place that knows how to glob and parse config, and profile
`config.dir` is the only source of the path (never hardcoded per-project).
"""
from __future__ import annotations

import glob
import os
from typing import Iterator

import yaml


def load_yaml(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def config_glob(config_dir: str, pattern: str) -> list[str]:
    return sorted(glob.glob(os.path.join(config_dir, pattern)))


def iter_config(config_dir: str, pattern: str) -> Iterator[tuple[str, dict]]:
    for path in config_glob(config_dir, pattern):
        yield path, load_yaml(path)


def handler_settings_target_bundles(field_settings: dict) -> list[str] | None:
    """Extract target_bundles from a field.field.* config's settings.handler_settings,
    normalizing the dict-or-list shape Drupal allows."""
    handler_settings = (field_settings or {}).get("handler_settings", {}) or {}
    target_bundles = handler_settings.get("target_bundles")
    if isinstance(target_bundles, dict):
        return list(target_bundles.keys())
    if isinstance(target_bundles, list):
        return list(target_bundles)
    return None
