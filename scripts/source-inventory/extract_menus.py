"""Menus and menu attachments.

`menu_attachment` generalizes a pattern first seen in the pilot run as a
custom module: a menu link's `link__options`
serialized blob can carry extra behavior beyond "link to a URL" — in that
case, the id of a block placement to render under the link's dropdown.
Rather than hardcode that one module's name, this extractor generically
scans every menu link's `link__options` text for any known placement id
appearing as a substring. That is deliberately conservative (a substring
match can't fail to find a real reference, though it could in principle
false-positive on an id that happens to appear inside unrelated
options data) and is recorded as evidence (kind=menu_attachment), not as a
verdict.
"""
from __future__ import annotations

from db import fetch_rows
from config_scan import iter_config
from site_profile import DbConfig


def parse_menu_configs(config_dir: str) -> dict[str, dict]:
    menus = {}
    for _path, data in iter_config(config_dir, "system.menu.*.yml"):
        mid = data.get("id")
        if not mid:
            continue
        menus[mid] = {"id": mid, "label": data.get("label", mid)}
    return menus


def fetch_menu_link_counts(db: DbConfig, menu_ids: list[str]) -> dict[str, int]:
    if not menu_ids:
        return {}
    rows = fetch_rows(db, "SELECT menu_name, COUNT(*) AS n FROM menu_link_content_data GROUP BY menu_name;")
    return {r["menu_name"]: int(r["n"]) for r in rows if r["menu_name"] in menu_ids}


def fetch_menu_links(db: DbConfig) -> list[dict]:
    return fetch_rows(
        db,
        "SELECT id, menu_name, link__options AS link_options FROM menu_link_content_data;",
    )


def detect_menu_attachments(menu_links: list[dict], placement_ids: list[str]) -> list[dict]:
    """Pure: given menu link rows (id, link_options text) and the full list
    of placement ids, returns [{menu_link_id, menu_name, attached_placement_id}]
    for every link whose serialized options text contains a placement id as
    a substring."""
    attachments = []
    candidate_ids = [p for p in placement_ids if p]
    for link in menu_links:
        options_text = link.get("link_options") or ""
        if not options_text:
            continue
        for pid in candidate_ids:
            if pid in options_text:
                attachments.append({
                    "menu_link_id": link["id"],
                    "menu_name": link.get("menu_name"),
                    "attached_placement_id": pid,
                })
    return attachments


def build_menu_components(
    config_dir: str,
    db: DbConfig | None,
    placement_ids: list[str],
) -> tuple[list[dict], list[dict], list[dict]]:
    """Returns (menu_components, menu_details, menu_attachment_components)."""
    menus = parse_menu_configs(config_dir)
    menu_ids = list(menus.keys())

    link_counts: dict[str, int] = {}
    menu_links: list[dict] = []
    if db is not None:
        link_counts = fetch_menu_link_counts(db, menu_ids)
        menu_links = fetch_menu_links(db)

    attachments = detect_menu_attachments(menu_links, placement_ids)
    attachments_by_menu: dict[str, list[dict]] = {}
    for a in attachments:
        attachments_by_menu.setdefault(a.get("menu_name") or "", []).append(
            {"menu_link_id": a["menu_link_id"], "attached_placement_id": a["attached_placement_id"]}
        )

    menu_components = []
    menu_details = []
    attachment_components = []
    for mid, meta in menus.items():
        menu_components.append({"id": mid, "kind": "menu", "label": meta["label"]})
        menu_details.append({
            "id": mid,
            "label": meta["label"],
            "link_count": link_counts.get(mid, 0),
            "attachments": attachments_by_menu.get(mid, []),
        })

    for a in attachments:
        attachment_id = f"{a['menu_link_id']}:{a['attached_placement_id']}"
        attachment_components.append({
            "id": attachment_id,
            "kind": "menu_attachment",
            "label": f"Menu link {a['menu_link_id']} attaches placement {a['attached_placement_id']}",
        })

    return menu_components, menu_details, attachment_components
