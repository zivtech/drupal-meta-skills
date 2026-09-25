"""Render-signals extractor: a real, static-analysis extractor, replacing
the pilot run's original 100% hand-authored evidence pass (not an
extractor at all).

This module does NOT claim to produce verdicts. It finds `file:line`
evidence of four signal categories in Twig templates and PHP preprocess
`case` blocks, and rolls that evidence up into a CONSERVATIVE candidate for
the four render_behavior axes (render_source='extracted'). A human overlay
(render_overlay.py + a project's render-verdicts.yaml) is what turns this
into `render_source='authored'` truth — see contracts/source-structure/
README.md "Render behavior: extracted vs. authored". By design,
"render signals can be extracted deterministically" is treated as a
fragile assumption on purpose: this extractor is expected to under- and
over-detect relative to a careful human read, and a proof run should report
its hit rate against the hand-authored pilot notes precisely so that gap
is visible, not hidden.

Signal categories (signal_type):
  view_embed        - drupal_view()/views_embed_view()/Views::getView()
  entity_query       - ::load(), ->loadByProperties(), entityTypeManager(),
                        \\Drupal::entityQuery()
  state_read          - \\Drupal::state()
  config_read         - \\Drupal::config(), Settings::get()
  service_call        - \\Drupal::service(), ->getForm(), formBuilder(),
                         \\Drupal::routeMatch() (recorded as evidence; does
                         NOT by itself flip any of the four booleans, since
                         many service calls are presentation utilities, e.g.
                         path_alias.manager, not content queries)
  hardcoded_literal   - currency-shaped literals in Twig, or a twig template
                        with substantial static content backing a type with
                        zero configured fields
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from pathlib import Path

VIEW_EMBED_RE = re.compile(r"\b(?:drupal_view|views_embed_view)\s*\(|Views::getView\s*\(")
ENTITY_QUERY_RE = re.compile(
    r"::load\s*\(|->loadByProperties\s*\(|\\Drupal::entityTypeManager\s*\(|\\Drupal::entityQuery\s*\("
)
STATE_READ_RE = re.compile(r"\\Drupal::state\s*\(\s*\)")
CONFIG_READ_RE = re.compile(r"\\Drupal::config\s*\(|Settings::get\s*\(")
SERVICE_CALL_RE = re.compile(
    r"\\Drupal::service\s*\(|\\Drupal::routeMatch\s*\(|formBuilder\s*\(\s*\)|->getForm\s*\("
)
CURRENCY_LITERAL_RE = re.compile(r"\$\s?\d")

CASE_RE = re.compile(r"^\s*case\s*'([A-Za-z0-9_]+)'\s*:")


@dataclass
class Signal:
    signal_type: str
    file: str
    line: int
    snippet: str
    detail: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _scan_line_patterns(lines: list[str], file_label: str, extra_detail: str = "") -> list[Signal]:
    signals: list[Signal] = []
    seen_on_line: set[tuple[int, str]] = set()

    def emit(signal_type: str, i: int, detail: str):
        key = (i, signal_type)
        if key in seen_on_line:
            return
        seen_on_line.add(key)
        signals.append(Signal(
            signal_type=signal_type,
            file=file_label,
            line=i + 1,
            snippet=lines[i].strip()[:200],
            detail=detail,
        ))

    for i, line in enumerate(lines):
        if VIEW_EMBED_RE.search(line):
            emit("view_embed", i, f"View-embed call.{(' ' + extra_detail) if extra_detail else ''}")
        if ENTITY_QUERY_RE.search(line):
            emit("entity_query", i, f"Entity load/query call.{(' ' + extra_detail) if extra_detail else ''}")
        if STATE_READ_RE.search(line):
            emit("state_read", i, "Reads \\Drupal::state().")
        if CONFIG_READ_RE.search(line):
            emit("config_read", i, "Reads config/settings.")
        if SERVICE_CALL_RE.search(line):
            emit("service_call", i, "Calls a Drupal service (not auto-classified as a content query).")
    return signals


def scan_php_case_blocks(php_text: str, file_label: str) -> dict[str, list[Signal]]:
    """Finds `case '<bundle>':` blocks in a flat switch statement (the
    pattern *_preprocess_paragraph()/_preprocess_block() hooks use) and
    scans each block's body for signals. Heuristic, not a PHP parser: a
    block runs from its `case` line to the line before the next `case`/
    `default:` at the same left-indentation, or end of file. This means a
    second, unreachable `case` for the same bundle (dead code after an
    earlier `break`) is still scanned — flagged as a known limitation, not
    silently hidden, because the extractor cannot tell reachable from
    unreachable without executing the switch.
    """
    lines = php_text.splitlines()
    case_starts: list[tuple[int, str, str]] = []  # (line_index, bundle, indent)
    for i, line in enumerate(lines):
        m = CASE_RE.match(line)
        if m:
            indent = line[: len(line) - len(line.lstrip())]
            case_starts.append((i, m.group(1), indent))

    out: dict[str, list[Signal]] = {}
    for idx, (start, bundle, indent) in enumerate(case_starts):
        end = len(lines)
        for later_start, _b, later_indent in case_starts[idx + 1:]:
            if later_indent == indent:
                end = later_start
                break
        default_re = re.compile(rf"^{re.escape(indent)}default\s*:")
        for j in range(start + 1, end):
            if default_re.match(lines[j]):
                end = j
                break
        block_lines = lines[start:end]
        signals = _scan_line_patterns(block_lines, file_label)
        for s in signals:
            s.line += start
        out.setdefault(bundle, []).extend(signals)
    return out


def scan_twig_template(twig_text: str, file_label: str, has_own_fields: bool) -> list[Signal]:
    lines = twig_text.splitlines()
    signals = _scan_line_patterns(lines, file_label)

    for i, line in enumerate(lines):
        # Twig has no bare `$var` interpolation syntax (unlike PHP/Blade), so
        # a literal '$' followed by a digit in a .html.twig file is reliably
        # a hardcoded currency string, not a variable reference.
        if CURRENCY_LITERAL_RE.search(line):
            signals.append(Signal(
                signal_type="hardcoded_literal", file=file_label, line=i + 1,
                snippet=line.strip()[:200],
                detail="Currency-shaped literal not inside a print statement.",
            ))

    if not has_own_fields and len("\n".join(lines)) > 1500:
        signals.append(Signal(
            signal_type="hardcoded_literal", file=file_label, line=1,
            snippet=f"({len(lines)} lines)",
            detail="Template has substantial static content (>1500 chars) backing a type with 0 configured fields.",
        ))
    return signals


def find_twig_file(twig_dirs: list[Path], prefix: str, bundle: str) -> Path | None:
    """prefix is e.g. 'paragraph' or 'block'. Looks for an exact Drupal
    theme-suggestion filename (`{prefix}--{bundle-dashed}.html.twig`, or a
    `--<view-mode>` variant), never a loose substring match — this is what
    naturally excludes a renamed/disabled template (a file that doesn't
    start with the expected prefix is not a live theme suggestion for this
    bundle, static analysis alone can't know why, but it correctly won't be
    picked up as this bundle's active template).
    """
    dashed = bundle.replace("_", "-")
    exact = f"{prefix}--{dashed}.html.twig"
    variant_prefix = f"{prefix}--{dashed}--"
    for d in twig_dirs:
        if not d or not d.exists():
            continue
        for f in sorted(d.rglob("*.html.twig")):
            if f.name == exact:
                return f
        for f in sorted(d.rglob("*.html.twig")):
            if f.name.startswith(variant_prefix):
                return f
    return None


def extract_render_signals_for_bundle(
    bundle: str,
    has_own_fields: bool,
    twig_dirs: list[Path],
    prefix: str,
    case_blocks: dict[str, list[Signal]],
) -> list[Signal]:
    signals: list[Signal] = list(case_blocks.get(bundle, []))
    twig_path = find_twig_file(twig_dirs, prefix, bundle)
    if twig_path is not None:
        text = twig_path.read_text(encoding="utf-8", errors="replace")
        signals.extend(scan_twig_template(text, str(twig_path), has_own_fields))
    return signals


def rollup_candidate_behavior(signals: list[Signal]) -> dict:
    types = {s.signal_type for s in signals}
    queries_other_content = bool(types & {"view_embed", "entity_query"})
    global_settings_or_state = bool(types & {"state_read", "config_read"})
    hardcoded_content = "hardcoded_literal" in types
    own_fields_only = not (queries_other_content or global_settings_or_state or hardcoded_content)
    return {
        "own_fields_only": own_fields_only,
        "queries_other_content": queries_other_content,
        "global_settings_or_state": global_settings_or_state,
        "hardcoded_content": hardcoded_content,
    }
