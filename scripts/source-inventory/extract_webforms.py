"""Webforms and their handlers.

`submission_count` is a COUNT(*) only — no submission content is ever read
(webform_submission / webform_submission_data / webform_submission_log are
all in the default PII table denylist for sample-value extraction; a bare
row count touches no content column and is safe to report).
"""
from __future__ import annotations

from db import fetch_rows
from config_scan import iter_config
from site_profile import DbConfig


def parse_webform_configs(config_dir: str) -> dict[str, dict]:
    webforms = {}
    for _path, data in iter_config(config_dir, "webform.webform.*.yml"):
        wid = data.get("id")
        if not wid:
            continue
        handlers = []
        for handler_id, handler in (data.get("handlers") or {}).items():
            handlers.append({
                "id": handler_id,
                "plugin": handler.get("id", handler_id),
                "status": "enabled" if handler.get("status", True) else "disabled",
            })
        webforms[wid] = {
            "id": wid,
            "label": data.get("title", wid),
            "status": data.get("status", "open"),
            "handlers": handlers,
        }
    return webforms


def fetch_submission_counts(db: DbConfig, webform_ids: list[str]) -> dict[str, int]:
    if not webform_ids:
        return {}
    rows = fetch_rows(db, "SELECT webform_id, COUNT(*) AS n FROM webform_submission GROUP BY webform_id;")
    return {r["webform_id"]: int(r["n"]) for r in rows if r["webform_id"] in webform_ids}


def build_webform_components(config_dir: str, db: DbConfig | None) -> tuple[list[dict], list[dict]]:
    webforms = parse_webform_configs(config_dir)
    counts = fetch_submission_counts(db, list(webforms.keys())) if db is not None else {}

    components = []
    details = []
    for wid, w in webforms.items():
        components.append({"id": wid, "kind": "webform", "label": w["label"]})
        details.append({
            "id": wid,
            "label": w["label"],
            "status": str(w["status"]),
            "handlers": w["handlers"],
            "submission_count": counts.get(wid),
        })
    return components, details
