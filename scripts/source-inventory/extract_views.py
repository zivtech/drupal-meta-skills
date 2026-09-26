"""view_listing components from Views config.

Scope note (documented limitation, not hidden): this reads every
`views.view.*.yml` found in the config directory and treats each as a
`view_listing` component. An exported config directory normally only
contains site-authored or site-overridden views (Drupal core/contrib
default views aren't exported unless changed), so in practice this rarely
needs an administrative-view exclusion list — but if a project's config
does export an admin view, it will show up here too, and a human
disposition (DROP, most likely) is the correct way to handle it rather than
this extractor guessing which views are "real" listings.
"""
from __future__ import annotations

from config_scan import iter_config


def build_view_listing_components(config_dir: str) -> list[dict]:
    components = []
    for _path, data in iter_config(config_dir, "views.view.*.yml"):
        vid = data.get("id")
        if not vid:
            continue
        label = data.get("label", vid)
        displays = list((data.get("display") or {}).keys())
        components.append({
            "id": vid,
            "kind": "view_listing",
            "label": label,
            "description": f"Displays: {', '.join(displays)}" if displays else None,
        })
    return components
