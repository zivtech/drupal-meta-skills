"""Block placements (`block.block.*.yml`) and their visibility decode.

Generalizes the pilot run's own placement-assembly script. Two
generalizations away from the pilot-specific original:

1. The enabled domain list and the field/condition that carries domain
   ownership come from the profile (`domains.enabled`), never a hardcoded
   `SITES = ["site_a", "site_b", "site_c"]` list.
2. "Non-standard region" (a placement whose region isn't one of the active
   theme's declared regions — a strong signal that something other than
   the normal region-render pipeline is putting it on the page, the same
   fact the pilot run manually annotated for a handful of placements) is
   detected generically by reading the theme's own `*.info.yml` `regions:`
   key, not by hardcoding region names.
"""
from __future__ import annotations

import glob
import os

import yaml

from config_scan import iter_config

BLOCK_CONTENT_PLUGIN_PREFIX = "block_content:"


def load_theme_regions(theme_dir: str | None) -> set[str]:
    if not theme_dir:
        return set()
    for info_path in glob.glob(os.path.join(theme_dir, "*.info.yml")):
        with open(info_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        regions = data.get("regions")
        if regions:
            return set(regions.keys())
    return set()


def decode_visibility(visibility: dict, enabled_domains: list[str]) -> dict:
    conditions = sorted(visibility.keys())
    domains: list[str] = []
    negate = None
    if "domain" in visibility:
        dom = visibility["domain"] or {}
        listed = [d for d in (dom.get("domains", {}) or {}).keys() if not enabled_domains or d in enabled_domains]
        domains = sorted(listed)
        negate = bool(dom.get("negate", False))
    return {"conditions": conditions, "domains": domains, "negate": negate}


def build_placement_components(
    config_dir: str,
    enabled_domains: list[str],
    theme_regions: set[str],
) -> tuple[list[dict], list[dict], list[dict]]:
    """Returns (placement_components, placement_details, code_plugin_components)."""
    placement_components = []
    placement_details = []
    code_plugins: dict[str, dict] = {}

    for _path, data in iter_config(config_dir, "block.block.*.yml"):
        bid = data.get("id")
        if not bid:
            continue
        plugin = data.get("plugin", "")
        region = data.get("region", "")
        visibility = decode_visibility(data.get("visibility", {}) or {}, enabled_domains)

        block_content_id = None
        if plugin.startswith(BLOCK_CONTENT_PLUGIN_PREFIX):
            block_content_id = plugin[len(BLOCK_CONTENT_PLUGIN_PREFIX):]
        else:
            code_plugins.setdefault(plugin, {
                "id": plugin,
                "kind": "code_plugin",
                "label": plugin,
                "description": f"Block plugin (not editor-authored block_content): used by placement(s) including '{bid}'.",
            })

        non_standard = bool(theme_regions) and region not in theme_regions

        placement_components.append({
            "id": bid,
            "kind": "placement",
            "label": bid,
        })
        placement_details.append({
            "id": bid,
            "theme": data.get("theme", ""),
            "region": region,
            "weight": data.get("weight"),
            "status": bool(data.get("status", True)),
            "plugin": plugin,
            "block_content_id": block_content_id,
            "visibility_conditions": visibility["conditions"],
            "visibility_domains": visibility["domains"],
            "visibility_negate": visibility["negate"],
            "non_standard_region": non_standard,
        })

    return placement_components, placement_details, list(code_plugins.values())
