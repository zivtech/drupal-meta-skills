# Source-Structure Contract

**contract_version:** see [`VERSION`](VERSION) (currently `1.1.0`). Every
file produced or consumed against this contract carries a `contract_version`
field; consumers vendor a copy of the two schemas here and reject an unknown
major (see [`CHANGELOG.md`](CHANGELOG.md)).

## What this is

A target-agnostic rubric and pair of JSON Schemas for inventorying a CMS
source and classifying every component it contains before a migration or
conversion plan is allowed to touch it. It answers two separable questions:

1. **What is here, and what does the data mean?** (`source-structure.schema.json`
   — machine-generated, by an inventory tool such as `drupal-source-inventory`)
2. **What happens to each thing?** (`dispositions.schema.json` — human-authored,
   one row per inventoried component)

Splitting these into two files is deliberate: a regenerated inventory must
never silently clobber an authored decision. `dispositions.json` carries a
`source_structure_hash` so staleness is detectable (see "Staleness
detection" below).

This contract is **target-agnostic**. It does not know whether the
destination is WordPress, a different Drupal content model, or something
else. The seven verdicts below describe *what kind of thing happens to a
component*, not *which WordPress block or Drupal field it becomes*. By
design decision, the destination-prefix grammar (e.g.
`block:core/accordion-item`, `meta:unit_price`) is deliberately **not**
part of this public contract — it is runtime-side, because it is
target-specific and a real deployment's prefixes can be specific to one
site. `dispositions.schema.json` only requires a non-empty list of
free-text destination strings.

## Field roles

Applied to every field on every FACT-bearing component (paragraph types,
node bundles, block content types, and their nested fields). A role is a
claim about **what the data means**, independent of how it renders today.

| Role | Definition | Decision rule |
|---|---|---|
| **FACT** | A value that changes the *meaning* of the content if changed — a price, a date, a phone number, a boolean that gates behavior. | If flipping/changing the value would make the content wrong or would gate different behavior, it's FACT. A boolean is FACT when it changes meaning (`field_is_free`), not just rendering. |
| **REF** | A relationship to another entity — an entity reference to a node, term, media item, or another paragraph/block — where the *target* carries the meaning, not the reference itself. | If the field's value is an ID/UUID pointing at something else, and what matters is which thing it points to, it's REF. |
| **PROSE** | Free-text or rich-text authored content meant to be read — body copy, descriptions, captions. | Long text / text_long / text_with_summary fields whose value is prose, not a structured fact. |
| **MEDIA** | A reference to an image, video, file, or other binary asset. | entity_reference to `media` or `file`, or an `image`/`file` field type. |
| **PRESENTATION** | A value that only changes *how* something renders, not what it means — a color theme, a boolean toggle for a visual variant, a spacing/width option. | A boolean is PRESENTATION when it only controls rendering (`field_light_theme`). List/select fields whose options are visual variants (theme, alignment, layout) are PRESENTATION. |
| **CONFIG** | A value that configures *behavior* rather than carrying content or presentation — which View to embed, which display mode to use, a machine-readable selector. | entity_reference to a `view` config entity; a list field whose options select a display mode or behavior variant. |

Every field row carries `role_source: heuristic | reviewed`. A **heuristic**
role was assigned by the extractor from field type + field machine name
(see the skill's `role_hint()` — a name/type pattern match, not a read of
the actual data). A **reviewed** role was confirmed by a human. Gate G2 (see
"Gates this contract feeds," below) forbids a reviewed FACT/REF field from
landing in a CONTENT or LAYOUT disposition without a per-field destination —
heuristic roles do not block that gate, because they are not yet trusted.

## Dispositions (verdicts)

Promoted verbatim from the pilot run's own authored classification schema
(its `legend.verdicts`), generalized to every `kind`, not just
paragraph types. A disposition is a claim about **what happens to a
component as a whole** (or, via `conditional_verdicts`, to a subset of its
instances).

| Verdict | Definition | Decision rule |
|---|---|---|
| **STRUCTURED** | Facts extracted to structured storage (a custom post type field, post meta, an option, a taxonomy term, a relationship) — rendered by binding, by a query, or by a custom block that reads structured data, not by copying markup. | Choose STRUCTURED when the component's FACT/REF fields need to survive as queryable/bindable data at the destination, not just as flattened HTML. |
| **QUERY** | The component is (or becomes) a live query against other content — a "query loop," a "terms query," or a custom block that queries at render time. | Choose QUERY when the render behavior itself is "go fetch other content," not "display my own fields." |
| **REUSE** | The component is (or becomes) a synced/reusable pattern with named override slots — one definition, referenced by many placements, with per-placement overrides. | Choose REUSE when duplication-by-design is the point (a library item referenced by many hosts is the paradigm case), not incidental content duplication. |
| **LAYOUT** | The component is presentation/structure only — a layout pattern, a block style, a variation, a template slot — carrying no FACT/REF data of its own. | Choose LAYOUT when removing the component would lose no facts, only arrangement. |
| **CONTENT** | The component's content lands as flattened markup in the main content area, with no structured extraction. | Choose CONTENT for PROSE-dominant components with no FACT/REF fields worth preserving as structured data. Kept as a first-class verdict (not merged into STRUCTURED) because the CONTENT/STRUCTURED boundary is a judgment call the rubric should not paper over — see the boundary note below. |
| **DROP** | The component is not migrated. Requires a `note` explaining why and, when data exists, an explicit declared-loss statement. | Choose DROP only with evidence (e.g., dead: 0 live instances; test/junk samples; superseded by another type). Never drop silently. |
| **DEFER** | An interim/legacy-embed disposition pending a named downstream decision — used when the destination isn't known yet, not as a way to avoid deciding. | Choose DEFER only when you can name what decision is pending and who/what makes it. An undated DEFER is a DROP wearing a disguise; the critic rubric flags it. |

**The CONTENT/STRUCTURED boundary is intentionally not fully mechanical.**
A component with a `price` field that's 90% empty test junk and 10%
real prices is a judgment call (see the worked `faq_accordion_row` example
below) — the rubric gives you the axis (does a FACT/REF field carry real,
non-junk data at a fill rate worth preserving?) but the threshold is a
per-project decision, recorded in `note` and `evidence`.

### Conditional verdicts

A single component `kind` can split by field-fill: most instances get one
verdict, a data-bearing minority gets another. `dispositions.schema.json`
supports this via `conditional_verdicts[]`: `{when, verdict, destinations,
note}`. Worked example (generalized from the pilot run): a `faq_accordion_row`
paragraph type is 88% plain FAQ prose (verdict: CONTENT) but 12% of rows
carry a price field that switches them into a pricing/tier construct
(verdict: STRUCTURED) — same component `kind`, two verdicts, because the
*data*, not the *type*, determines behavior for that slice.

## Component identity: `id` vs `key`

Every component has both an `id` (the source's own native id — a Drupal
machine name, or a raw database primary key for DB-only kinds like
`block_content` and `paragraphs_library_item`) and a `key`
(`{kind}:{id}`).

**Always disposition and cross-reference by `key`, never by bare `id`.**
This was verified as a real, not theoretical, collision during a
proof run against a live Drupal source: `paragraphs_library_item` and
`block_content` are separate MySQL tables that both auto-increment from 1,
so a real source had a `paragraphs_library_item` with id `"1"` **and** a
`block_content` with id `"1"` — same bare id, different components. The
same run found a `placement` and a `menu` both named `"footer"`. A
`dispositions.json` keyed by bare `id` would silently merge two unrelated
components' decisions into one row. `dispositions.schema.json`'s `types{}`
is keyed by `key` for exactly this reason, and
`validate-dispositions.py`'s completeness check (Gate G1) reconciles on
`key`, not `id`.

## Component `kind`

`source-structure.schema.json`'s `components[].kind` enum:

| `kind` | What it is |
|---|---|
| `node_bundle` | A node content type. |
| `paragraph_type` | A Paragraphs bundle. |
| `paragraphs_library_item` | A reusable Paragraphs Library entity (the specific saved item, not the type) — kept distinct from `paragraph_type` because reuse-by-reference is itself disposition-relevant (REUSE). |
| `block_content_type` | A custom block type (bundle). |
| `block_content` | A specific block_content entity (an instance of a `block_content_type`). |
| `placement` | A `block.block.*` placement: theme + region + visibility conditions binding a block plugin/content to a page. |
| `code_plugin` | A block plugin that is not `block_content:*` — i.e., a hand-coded block plugin, not an editor-authored block. |
| `menu` | A menu definition. |
| `menu_attachment` | A menu link that carries extra attached behavior beyond navigation (e.g., a link that also attaches a block placement to its dropdown) — kept distinct from a plain nav link because it has migration-relevant behavior beyond "link to a URL." |
| `view_listing` | A Views display used as a content listing (as opposed to an administrative view). |
| `state_setting` | A State API key (`\Drupal::state()`), enumerated by key only (see PII rules). |
| `webform` | A Webform config entity, including its handlers. |
| `layout_builder` | A Layout Builder (or Experience Builder) component tree. **Reserved, no extractor in this contract's v1** — the skill records that Layout Builder/XB is present, not its structure. |
| `template_hardcoded` | A rollup marker: a component whose render template contains hardcoded content/markup not backed by any field (see render signals, below), significant enough to be its own disposition-relevant fact. |

This `kind` universe is intentionally limited to what the inventory
actually classifies (node, paragraph, and block_content bundles/instances,
plus the placement/menu/view/webform/state surfaces above) — a consumer
must not invent a new `kind` locally (e.g. for media, taxonomy, user, or
other entity types out of this scope) instead of proposing it as a
minor-version addition to this contract, so every consumer keeps reading
the same fixed vocabulary.

Reverse-direction platform mapping (WP → Drupal-shaped source, or vice
versa) is out of scope for this contract; it lives in the target-side
planner (e.g. `wordpress-content-model-planner`, `drupal-content-model-planner`).
As a pointer only: ACF flexible-content layouts and page-builder modules map
to `paragraph_type`/`block_content_type`-shaped components; synced patterns
(`wp_block`) and Paragraphs Library items are both REUSE; a Query Loop and
`view_listing` are both QUERY; widgets and Drupal `placement`s are both
`placement`.

## Render behavior: extracted vs. authored

A component's render behavior is described along four axes (kept from
the pilot run's authored notes, now backed by an extractor):

- `own_fields_only` — renders only its own (and nested) fields.
- `queries_other_content` — its render path fetches/queries content outside
  itself (a Views embed, an entity load of an unrelated entity, a
  programmatic View build).
- `global_settings_or_state` — its render path reads global config/state
  (`\Drupal::config()`, `\Drupal::state()`, `Settings::get()`) rather than
  its own fields.
- `hardcoded_content` — its template contains content-shaped literals
  (prices, copy) that no field backs.

Each component carries `render_source: extracted | authored | none`:

- **`extracted`** — a static scanner (this contract's companion skill's
  `render_signals.py`) found `file:line` evidence and a human overlay
  confirmed it, or the four axes are the scanner's own conservative signal
  rollup with no overlay yet.
- **`authored`** — a human wrote the verdict directly (the pilot run's
  own original hand-authored shape), because the scanner cannot yet
  reliably decide the axis (this is expected and explicitly allowed by
  design: "render signals can be extracted deterministically" is treated
  as a fragile assumption on purpose).
- **`none`** — nobody has looked; the four axes default to the
  "own fields only" assumption and that default is itself flagged, never
  presented as if it were evidence.

`extracted` and `authored` are never conflated. A verdict rendered from
signals alone, without a human overlay confirming it, must say so.

## Data quality: parent-chain resolution

Verified against a live Drupal source during a proof run: a
revisionable child entity's denormalized parent pointer (Paragraphs'
`parent_id`/`parent_type`/`parent_field_name` columns) is **not reliably
updated when the entity is detached from that parent** — a meaningful
minority of node-parented rows in the proof-run source pointed at a host
that no longer references them in the live reference field table. This is a known
Drupal behavior, not a bug specific to one project: revisions can drop a
paragraph reference without the orphaned paragraph's own denormalized
pointer being cleared.

Consequently, `drupal-source-inventory` (and any tool producing a
`source-structure.json`) **must** resolve `usage`, `hosted_by`, and `nests`
by walking the live `entity_reference_revisions` field tables (`target_id` /
`target_revision_id` on the host's own field table) rather than trusting a
denormalized parent pointer, when the source exposes one. `data_quality.
parent_chain` records how often the two disagreed, as a trust signal for the
rest of the source's own denormalized data — it is not optional
instrumentation, because a tool that silently used the denormalized pointer
would under- or over-count usage by roughly a quarter on a source shaped
like the one this was verified against.

**What "unresolved" means.** `usage.unresolved_instances` counts an
instance whose live-reference-edge walk never reached a root host —
concretely, this means **not referenced by any host's default revision**.
The walk reads the base (non-`_revision`) reference field tables, which
Drupal keeps in sync with each host's *default* revision only. A paragraph
that exists solely on a pending `content_moderation` draft revision (not
yet the default/published one) has no row in that base table and is
therefore counted unresolved — this is expected, not a bug: it reflects
"not part of the content that would actually render," which is exactly
what a migration/conversion plan should measure. It is also the outcome
for a genuinely orphaned paragraph (no live reference row at all), a
cycle, or a walk that exceeded `MAX_HOPS` — see `resolve_roots()`'s
`errors` in the skill's `extract_usage.py`. All of these collapse into the
same counter; this contract does not currently distinguish "detached
draft-only content" from "truly orphaned" within `unresolved_instances`.

**Reading the usage counts.** Every resolved root host of an instance is
counted once in exactly one bucket: `published_hosts` or
`unpublished_hosts` (a node root, by its status), `library_owned_instances`
(a Paragraphs Library item root), or `block_hosted_instances` (a
block_content root). An instance that reaches no root is counted once in
`unresolved_instances`. An instance that reaches more than one distinct
root is counted in each of its roots' buckets **and** once in
`shared_by_multiple_hosts`. So:

```
published_hosts + unpublished_hosts + library_owned_instances
  + block_hosted_instances + unresolved_instances
  - shared_by_multiple_hosts                      == total_instances
```

holds exactly when every shared instance has exactly two roots and every
root is a node, library item, or block. In general the left side exceeds
`total_instances` by the number of hosts beyond the second on multi-host
instances, minus the number of roots of any other entity type (those are
counted only in `distinct_host_count`). A consumer should read a nonzero
difference as exactly that, not as a bug. `distinct_host_count` counts
distinct hosts, not instances, and is not part of the identity.

## Data quality: unresolved field tables

A configurable field's rows live in a dedicated table, normally
`{entity_type}__{field_name}`; Drupal core shortens the name to
`{entity_type}__` plus 10 hex characters of a hash of the field storage's
UUID once the plain name would pass 48 characters
(`DefaultTableMapping::generateFieldTableName()`). A producer must resolve
each field's table from the live schema rather than guess it, and must
list every field whose table it still cannot find in
`data_quality.unresolved_tables` (entity type, field name, the plain name it
looked for, and which extraction lost the rows: `usage`, `library_items`,
`domains`, or `field_profile`). The list is present and empty when every
table resolved. A non-empty list means those numbers are knowingly
incomplete; a database failure (timeout, authentication, SQL error) is
never reported this way; it stops the run.

One entry is not a dedicated table: a Paragraphs Library item holds its
paragraph in the item's own base field (`paragraphs__target_id` on
`paragraphs_library_item_field_data`). When library items exist but neither
that column nor a dedicated `paragraphs_library_item__*` table can be
found, the producer lists `paragraphs_library_item.paragraphs` with purpose
`library_items`, and every `library_items[].paragraph_bundle` is `""`.
Outside that case, `paragraph_bundle` is `""` only for an item whose
wrapped paragraph no longer exists in the source (a dangling reference);
the producer names those items in a warning when it runs.

## Staleness detection

`dispositions.json.source_structure_hash` is the sha256 of the
`source-structure.json` it was authored against, over its canonical JSON
form (sorted keys, no extra whitespace — see `validate-dispositions.py`'s
`canonical_json_bytes()`, the single implementation every hash producer
and checker must match). A validator that finds a mismatch must fail —
the inventory changed since a human last reviewed the dispositions, and the
counts in `dispositions.json.counts` can no longer be trusted to reconcile.
Recompute and re-review, don't silently proceed.

## Gates this contract feeds

The two schemas here are inert data shapes; the gates that read them and
refuse to proceed live in the *runtime* (this contract does not execute
anything against a live migration). For traceability, the four gates this
contract's shapes exist to support:

- **G1 Completeness** — every inventoried component has exactly one
  dispositions row; this repo's `validate-dispositions.py` implements the
  completeness half of this gate (component ↔ disposition reconciliation;
  nonzero exit on any undispositioned component). The
  dispositioned-but-unwired distinction (`pending_wiring`) and the
  `--strict` behavior are runtime-side.
- **G2 No data-blind flattening** — a *reviewed* FACT/REF field cannot land
  in a CONTENT/LAYOUT disposition without a per-field destination. Enforced
  by the converter/runtime, not by this schema (a schema can't see whether
  a destination is semantically empty).
- **G3 Non-node export completeness** — a full entity-relationship graph
  walk reaches every component. Runtime-side (graph walk over the live
  export), not this contract.
- **G4 Non-empty destination** — a component reachable and dispositioned as
  CONTENT/PROSE must not resolve to an empty destination at conversion
  time. Runtime-side verification.

## Files in this directory

| File | Produced by | Consumed by |
|---|---|---|
| `README.md` (this file) | humans | humans, the `drupal-source-inventory` skill, downstream planners |
| `VERSION` | humans | `validate-dispositions.py`, consumers' drift checks |
| `CHANGELOG.md` | humans | humans |
| `source-structure.schema.json` | humans (the schema itself) | `drupal-source-inventory` (validates its own output), `validate-dispositions.py`, downstream planners/runtimes that vendor a copy |
| `dispositions.schema.json` | humans (the schema itself) | migration planners (author `dispositions.json` against it), `validate-dispositions.py`, runtime's disposition generator |
| `validate-dispositions.py` | humans | CI, anyone authoring a `dispositions.json` |
| `fixtures/valid/` | humans (an invented multi-site parks district; ids, labels, and numbers are made up for these tests, not taken from any real site; no sample values) | pytest, `validate-dispositions.py` self-test |
| `fixtures/invalid/` | humans | pytest negative control — must fail validation |

## Versioning and forward compatibility

`VERSION` is `major.minor.patch`, and the rule is:

- **Minor = additive only**: a new optional property, anywhere in either
  schema. **From 1.2.0 onward, a consumer that vendored an older minor
  must still validate a newer minor's output.** That is why every object
  in both schemas accepts additional properties
  (`additionalProperties: true`): output from 1.3.0 or any later 1.x minor
  must validate against a vendored 1.2.0 schema, and an older consumer
  simply ignores keys it does not know.
- **1.0.0 and 1.1.0 are the exception.** Their `source-structure.schema.json`
  closed its objects (`additionalProperties: false`, including the root,
  `usage`, and `data_quality`), so a consumer that vendored either one
  rejects 1.2.0 output (on `data_quality.unresolved_tables`, and for 1.0.0
  also on `usage.shared_by_multiple_hosts` / `usage.block_hosted_instances`).
  Such a consumer must re-vendor the 1.2.0 schemas. `dispositions.schema.json`
  is not affected: it was opened in 1.1.0 and 1.2.0 added nothing to it.
- **Major = anything an older consumer cannot safely read**: adding,
  removing, or renaming a required property; removing or renaming any
  property; changing a property's meaning; and adding or removing an enum
  member (`kind`, `verdict`, `role`, `role_source`, `render_source`,
  `renderSignal.signal_type`). Enums stay closed on purpose, because a
  consumer that meets an unknown `kind` or `signal_type` has no rule for
  handling it; that is a break, not an addition.
- **Patch** = documentation and fixtures only; no schema shape change.

Open objects move the typo-catching job to the producer: a producer
validates its own output against a *closed* copy of the schema (every
object with `properties` gets `additionalProperties: false`), so a
misspelled or undocumented key in its own output still fails.
`drupal-source-inventory` does this with `assemble.strict_schema()`.

Its test suite checks the promise against byte-for-byte copies of earlier
schemas (`scripts/source-inventory/tests/fixtures/pinned-contract-schemas/`:
`source-structure.schema.json` at 1.0.0 and 1.1.0, both schemas at 1.2.0): the
current fixtures must fail the pinned 1.0.0 and 1.1.0 copies on exactly the
keys added since (the documented break above), and must pass the pinned
1.2.0 copy, including with an unknown key injected into every record. Each
new minor adds its own pinned copy; 1.2.0 stays the baseline every later
1.x minor is checked against.

`validate-dispositions.py` refuses a file whose major differs from
`VERSION`, and accepts any minor within the same major.

## Consumer checklist (for a repo adopting this contract)

1. Vendor a copy of `source-structure.schema.json` and
   `dispositions.schema.json` (don't import over the network at runtime).
2. Record the `contract_version` you vendored (e.g. a comment or a
   `CONTRACT_VERSION` constant next to the vendored copy).
3. Add a drift check: on a schedule or in CI, diff your vendored copy
   against this directory; fail (or at least warn) on a mismatch, and hard
   fail on a major-version mismatch you haven't explicitly migrated to.
4. Never invent a new `kind` or `verdict` value locally — extend this
   contract instead (a new enum member is a major-version change here; see
   "Versioning and forward compatibility"), so all consumers see the same
   vocabulary.
5. A consumer (e.g. a runtime that needs to carry its own per-row destination
   bookkeeping) may add its own keys alongside `dispositionRow`'s,
   `fieldDisposition`'s, `conditionalVerdict`'s, and the document root's core
   keys — `dispositions.schema.json` allows additional properties at every
   level (see "Versioning and forward compatibility") so a consumer's
   runtime-side fields (e.g. a resolved destination id, a migration-batch
   tag) can live in the same document without a schema fork. This contract
   does not validate those keys; that is the consumer's own responsibility.
6. Migrating a legacy, bare-`id`-keyed map: because `types{}` is keyed by
   `key` (`{kind}:{id}`) and every row requires `kind`, the transform is
   (a) prefix every `types{}` key with its kind and a `:`
   (`hero_banner` → `paragraph_type:hero_banner`), (b) set `kind` on each
   row to that same kind, and (c) add the envelope fields the map lacks
   (`contract_version`, `project`, `source_structure_hash`, `counts`). All
   three are needed for the schema check; skipping (b) fails every row on
   the required `kind`. `validate-dispositions.py` then also needs a
   non-empty `destinations` list on every non-DROP/DEFER row (a legacy
   single destination string becomes a one-item list) and a
   `source_structure_hash` computed from the real inventory.
