"""Field-role heuristic: FACT / REF / PROSE / MEDIA / PRESENTATION / CONFIG.

Generalizes the pilot run's `role_hint()` (originally embedded in its own
assembly script) into a standalone, project-agnostic function. This is
always a HEURISTIC (role_source='heuristic' in the caller) — it pattern
matches on field type + field machine name, it never reads field values.
See contracts/source-structure/README.md "Field roles" for the definitions
this heuristic is trying to approximate.
"""
from __future__ import annotations

CONFIG_NAME_HINTS = ("view", "display_mode", "display_id", "mode")
PRESENTATION_NAME_HINTS = (
    "color", "theme", "style", "align", "variation", "layout", "full_width",
    "background", "offset", "width_", "_width", "spacing", "caps",
    "hide_", "bg_", "remove_",
)
FACT_STRING_HINTS = (
    "price", "cost", "date", "time", "phone", "address", "admission",
    "hour", "zip", "amount", "number", "url",
)


def role_hint(field_name: str, field_type: str, target_entity_type: str | None = None) -> str:
    name_l = (field_name or "").lower()
    ft = field_type or ""

    if ft == "boolean":
        return "PRESENTATION"
    if ft in ("entity_reference", "entity_reference_revisions"):
        if target_entity_type == "media":
            return "MEDIA"
        if target_entity_type == "view":
            return "CONFIG"
        if any(hint in name_l for hint in ("color", "theme", "style")):
            return "PRESENTATION"
        return "REF"
    if ft == "link":
        return "FACT"
    if ft == "datetime":
        return "FACT"
    if ft in ("integer", "decimal", "float"):
        if any(hint in name_l for hint in ("weight", "count", "order", "sort")):
            return "CONFIG"
        return "FACT"
    if ft in ("list_string", "list_integer", "list_float"):
        if any(hint in name_l for hint in CONFIG_NAME_HINTS):
            return "CONFIG"
        return "PRESENTATION"
    if ft in ("text", "text_long", "text_with_summary"):
        return "PROSE"
    if ft in ("string", "string_long"):
        if any(hint in name_l for hint in FACT_STRING_HINTS):
            return "FACT"
        return "PROSE"
    if ft in ("image", "file"):
        return "MEDIA"
    if ft == "viewsreference":
        return "CONFIG"
    if any(hint in name_l for hint in PRESENTATION_NAME_HINTS):
        return "PRESENTATION"
    return "REF" if "reference" in ft else "PROSE"
