"""Merge render_signals (extract_render_signals.py) with a per-project
authored overlay (render-verdicts.yaml) into a final render_behavior +
render_source per component.

Precedence, matching contracts/source-structure/README.md:
  1. An authored overlay row always wins (`render_source: authored`) — a
     human looked and decided, even if the scanner found nothing or found
     something different.
  2. Otherwise, if the scanner found any signals, its conservative rollup
     is used (`render_source: extracted`) — evidence-backed but not
     human-confirmed.
  3. Otherwise, the "own fields only" default applies (`render_source:
     none`) — nobody has looked, and the default is flagged as a default,
     never presented as if it were evidence (matches the pilot run's own
     original hand-authored default, but now honestly labeled `none`
     instead of silently implied to be a considered judgment).
"""
from __future__ import annotations

from pathlib import Path

import yaml

DEFAULT_BEHAVIOR = {
    "own_fields_only": True,
    "queries_other_content": False,
    "global_settings_or_state": False,
    "hardcoded_content": False,
}

OVERLAY_AXES = ("own_fields_only", "queries_other_content", "global_settings_or_state", "hardcoded_content")


def load_overlay(path: Path | None) -> dict[str, dict]:
    if not path or not Path(path).exists():
        return {}
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return raw.get("overlays", {}) or {}


def resolve_render_behavior(
    bundle_id: str,
    candidate_from_signals: dict | None,
    has_signals: bool,
    overlay: dict[str, dict],
) -> tuple[dict, str]:
    if bundle_id in overlay:
        row = overlay[bundle_id]
        behavior = {axis: bool(row.get(axis, DEFAULT_BEHAVIOR[axis])) for axis in OVERLAY_AXES}
        return behavior, "authored"
    if has_signals and candidate_from_signals:
        return candidate_from_signals, "extracted"
    return dict(DEFAULT_BEHAVIOR), "none"
