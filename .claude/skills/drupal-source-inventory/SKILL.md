---
name: drupal-source-inventory
type: executor
model: claude-opus-4-8
description: "Inventory a Drupal source (config + live DB + theme) into a target-agnostic source-structure.json: every paragraph/block/placement/menu/webform/state-key/library-item component, data-classified and ready for a migration or conversion plan to disposition."
---

# Drupal Source Inventory Skill

## When to Use

**Primary triggers:**
- "inventory this Drupal site before we migrate it"
- "what paragraph types / block types / placements does this site actually have"
- "run drupal-source-inventory", "generate source-structure.json"
- A migration or conversion plan needs live per-type counts, fill rates, or
  usage data that a Bash-disallowed planner cannot collect itself
- Before any migration plan claims block-editor or content-model fidelity

---

## Use When

- You need a machine-readable inventory of a Drupal source's content
  structure (node bundles, paragraph types, block content, placements,
  menus, webforms, library items, state keys, Views listings) before
  designing a migration or conversion
- A `drupal-migration-planner` or `wordpress-migration-planner` run has
  stalled at "Phase 2: Source Content Audit" needing live counts it cannot
  collect (it is Bash-disallowed by design; this skill is not)
- You need field-level data quality (fill rate, duplication, suspected PII)
  before deciding what's worth preserving as structured data
- You need evidence (not a guess) about whether a paragraph/block type's
  render path queries other content, reads global state, or hardcodes
  content its fields don't back

---

## Do Not Use When

- You need to **decide** what happens to each component (STRUCTURED vs
  CONTENT vs DROP, etc.) — that's a human-authored `dispositions.json`
  against this skill's output, not something this skill does for you. See
  `contracts/source-structure/README.md`.
- You need the **destination-side** mapping (which WordPress block, which
  Drupal field) — that's `wordpress-migration-planner` /
  `drupal-content-model-planner`, consuming this skill's output.
- You need to **execute** a migration or conversion — that's the target
  runtime, not this skill (this skill is read-only against the source).
- You need Layout Builder/Experience Builder component-tree extraction —
  this contract version records only whether Layout Builder is present
  (reserved `kind`, no tree walk).

---

## Resolution Paths

| Situation | Route |
|---|---|
| Need the source inventory itself | This skill — run `analyze` |
| Need to decide dispositions from the inventory | Author `dispositions.json` by hand against `contracts/source-structure/dispositions.schema.json`, validate with `contracts/source-structure/validate-dispositions.py` |
| Need the destination-side content model | `drupal-content-model-planner` / `wordpress-content-model-planner`, fed by STRUCTURED rows |
| Need a migration plan gated on this inventory existing | `drupal-migration-planner` Phase 2 — if no `source-structure.json` exists, it should tell you to run this skill first |
| Need render-behavior verdicts confirmed, not just signals | Author a `render-verdicts.yaml` overlay (see `scripts/source-inventory/render-verdicts.example.yaml`) |

---

## What You Get

- **`source-structure.json`**, validated against
  `contracts/source-structure/source-structure.schema.json`: every
  component (`node_bundle`, `paragraph_type`, `paragraphs_library_item`,
  `block_content_type`, `block_content`, `placement`, `code_plugin`,
  `menu`, `menu_attachment`, `view_listing`, `state_setting`, `webform`,
  `layout_builder`, `template_hardcoded`) with fields (role-hinted,
  fill-rated), usage, duplication, render behavior (with `file:line`
  evidence when extracted), placements/visibility, menus, library-item
  hosts, webform handlers, state keys (never values), and a
  `data_quality` block: the `parent_chain` disagreement rate and
  `unresolved_tables` (fields whose storage table was not found in the
  live schema, so their rows are knowingly missing).
- **A completeness contract**: every component in the output is meant to
  receive exactly one row in a `dispositions.json` you author against it —
  `contracts/source-structure/validate-dispositions.py` fails closed on
  any component with no disposition.
- **PII-safe by default**: sample field values are off unless you pass
  `--samples`, and even then every sample is regex-scrubbed
  (emails/phones/SSNs) regardless of field name, on top of a
  field-name+content heuristic that suppresses a field's samples entirely
  when it looks personal.

---

## Running It

```bash
python3 scripts/source-inventory/cli.py analyze --profile /path/to/project.profile.yaml
```

Copy `scripts/source-inventory/profile.example.yaml` to a path **outside**
this repo for a real project (it names real paths and possibly a Docker
container). See that file for every field. Nothing project-specific is
hardcoded in the extractor scripts — the profile is the only place a
config directory, DB connection, theme directory, domain list, or
ownership field name may appear.

Flags:
- `--samples` — enable sample field values (off by default; always scrubbed)
- `--no-db` — config-only dry run, skips every DB-backed extractor
- `--output-dir DIR` — override the profile's `output.dir`
- `--render-explorer` — also write explorer-ready data files (documented
  follow-up; does **not** port the explorer HTML/JS viewer itself)

---

## Companion Skills

- **drupal-migration-planner / wordpress-migration-planner** (downstream):
  consume `source-structure.json` + your authored `dispositions.json`
- **drupal-content-model-planner / wordpress-content-model-planner**
  (downstream): consume STRUCTURED-dispositioned rows for destination
  content-model design
- **drupal-critic** (review): a migration plan without dispositions, or
  with undispositioned components, is a MAJOR finding per
  `drupal-review-rubric.md`

---

## PII Rules (read before enabling `--samples`)

1. Sample values are **off by default**.
2. A table denylist (`users_field_data`, `webform_submission*`,
   `sessions`, `watchdog`, extendable per-profile) blocks sample-*value*
   extraction from those tables. A bare `COUNT(*)` (e.g. webform submission
   counts) is not content and is not blocked.
3. Even with samples on, every candidate value is regex-scrubbed for
   emails/phones/SSNs before it can appear in output, regardless of field
   name — this is the fix for the exact failure mode the pilot run
   hit (an early raw field-samples pass held a large number of emails and
   phone numbers because only a field-*name* heuristic gated samples).
4. A field whose name OR content looks personal has its samples suppressed
   entirely (stronger than scrubbing — see `pii.looks_personal`).
5. State API values are **never** read — only key name and size in bytes.

---

## Data Quality: Parent-Chain Resolution

Verified during this skill's own proof run against a live Drupal source: a
revisionable child entity's denormalized parent pointer (Paragraphs'
`parent_id`/`parent_type`) is not reliably cleared when the entity is
detached from its host across revisions (a meaningful share of node-parented
rows disagreed with the live reference tables in the verified case). This skill
**always** resolves usage/hosted-by/nests from the live
`entity_reference_revisions` reference field tables, never from a
denormalized pointer, and reports the disagreement rate as
`data_quality.parent_chain`. See `contracts/source-structure/README.md`
"Data quality: parent-chain resolution" for the full write-up.

Field-table names are read from the live schema, never guessed: Drupal
shortens a field's table name to `{entity_type}__{10-char hash}` once
`{entity_type}__{field_name}` passes 48 characters, so the extractor maps
each field to its real table (plain name, core's hash of the storage UUID,
or column match) and lists anything it still cannot find in
`data_quality.unresolved_tables`. A database error (timeout, auth, SQL)
stops the run; it is never treated as "no rows".

A Paragraphs Library item's wrapped paragraph (and so its
`paragraph_bundle`) is read from the item's base field
(`paragraphs_library_item_field_data.paragraphs__target_id`), with a
dedicated `paragraphs_library_item__*` table only as a fallback. If
neither exists the gap is listed in `unresolved_tables`; an item whose
paragraph is missing from the source keeps `paragraph_bundle: ""` and the
CLI names it in a warning.

---

## meta-router Registry Note

Listed under the **Executors** table.
Trigger signals: `inventory this drupal site, source structure inventory, run drupal-source-inventory, generate source-structure.json, what paragraph types does this site have`
