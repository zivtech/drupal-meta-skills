# Changelog — contracts/source-structure

Versioning rule (see README.md "Versioning and forward compatibility"):

- **Minor = additive only.** A new optional property, anywhere. From 1.2.0
  onward, a consumer holding an older minor's vendored schema must still
  validate a newer minor's output; every object in both schemas therefore
  accepts additional properties. (1.0.0 and 1.1.0 did not; see 1.2.0.)
- **Major = anything an older consumer cannot safely read.** A new or
  removed required property, a removed or renamed property, a changed
  meaning, and a new or removed enum member (`kind`, `verdict`, `role`,
  `render_source`, `role_source`, `renderSignal.signal_type`): an older
  consumer's closed enum would reject the new value, and it has no rule
  for handling it.
- Consumers vendor a copy of the schemas plus a drift check against
  `contract_version`, and reject an unknown major.

## 1.2.0 — 2026-09-25

- `source-structure.schema.json`: every object now accepts additional
  properties (`additionalProperties: true`), including `usage`,
  `component`, `field`, `data_quality` and the document root. 1.1.0 left
  them closed, so a 1.1.0 producer's new `usage` keys failed a vendored
  1.0.0 schema; that broke the "minor = additive" promise. Producers keep
  their own output honest by validating against a closed copy of the
  schema (the skill's `assemble.strict_schema()`).
- **Re-vendor required for 1.0.0 and 1.1.0 consumers.** Opening the objects
  only helps from 1.2.0 on: the 1.0.0 and 1.1.0 `source-structure.schema.json`
  files are closed, so they reject 1.2.0 output (on
  `data_quality.unresolved_tables`, and 1.0.0 also on the 1.1.0 `usage`
  keys). A consumer on either must re-vendor the 1.2.0 schemas. From 1.2.0
  on, later 1.x output validates against a vendored 1.2.0 copy; the
  skill's tests check this against pinned byte-for-byte copies of the
  earlier schemas. `dispositions.schema.json` is unaffected (opened in
  1.1.0; 1.2.0 changed only its description text).
- The versioning rule above is now written down, and a new enum member is
  explicitly **major** (it was listed as minor before, which older
  consumers could not honor).
- `data_quality.unresolved_tables` (optional array): each configured field
  whose dedicated storage table could not be found in the live schema,
  with the extraction that lost its rows (`usage`, `library_items`,
  `domains`, `field_profile`). Producers resolve long field names to
  Drupal's hashed table names instead of guessing, and record what still
  cannot be resolved here rather than silently counting zero rows.

## 1.1.0 — 2026-09-25

- `dispositions.schema.json` now allows additional (consumer-owned)
  properties at the document root, `dispositionRow`, `fieldDisposition`,
  and `conditionalVerdict` — a runtime consumer can carry its own per-row
  bookkeeping (e.g. a resolved destination id) alongside this contract's
  core keys without a schema fork. See README.md's "Consumer checklist"
  item 5. `additionalProperties: false` is kept everywhere else (the
  contract's own enums and fixed-shape sub-objects).
- `source-structure.schema.json`'s `usage` object gains two optional
  fields: `shared_by_multiple_hosts` (a paragraph instance reachable from
  more than one currently-live root host, e.g. via node cloning, counted
  once per distinct host rather than as unresolved) and
  `block_hosted_instances` (paragraph instances whose resolved root is a
  block_content entity, broken out of the generic distinct-host bucket).
  Both are additive and optional; a 1.0.0 producer's output remains valid.
  (A 1.0.0 *consumer* could not validate 1.1.0 output that used them,
  because `usage` was still closed; fixed in 1.2.0.)

## 1.0.0 — 2026-09-24

Initial contract. Promotes the vocabulary and shapes that already existed as
pilot-specific artifacts into a target-agnostic public contract:

- `source-structure.schema.json` — the generated-inventory shape, promoted
  from the pilot run's paragraph-type and block-content records (fields,
  usage, duplication, render behavior; placements, menus, library items),
  generalized to a `kind`-tagged `components[]` envelope covering 14
  component kinds.
- `dispositions.schema.json` — the authored-decision shape, promoted
  verbatim from the pilot run's paragraph-map schema: the seven
  verdicts (STRUCTURED, QUERY, REUSE, LAYOUT, CONTENT, DROP, DEFER) and the
  `types{}` keying scheme, extended from paragraph-only to every `kind`.
- By design decision: a runtime's destination-prefix grammar (e.g.
  `block:core/accordion-item`) is **not** part of this public contract.
  `dispositions.schema.json` only requires `destinations` to be a non-empty
  array of strings when the verdict is not `DROP`; the runtime interprets
  the string grammar.
- `render_source: extracted | authored | none` distinguishes render-behavior
  claims a static scanner found (with `file:line` evidence in
  `render_signals[]`) from verdicts a human authored in a per-project
  overlay. Neither is silently treated as the other.
- `components[].key` (`{kind}:{id}`) added as the required disposition-
  matching identity, found necessary during a proof run against a
  live source: bare `id` collided across kinds (`paragraphs_library_item`
  and `block_content` are separate tables whose auto-increment ids both
  start at 1, so both had an id `1`; a `placement` and a `menu` shared the
  machine name `footer`).
  `dispositions.schema.json`'s `types{}` is keyed by `key`, not bare `id`.
