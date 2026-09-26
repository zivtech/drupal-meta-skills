# Drupal Review Rubric

## Security
- Route permissions explicit and least-privilege.
- Entity queries use `accessCheck(TRUE)` unless justified.
- Input validation/sanitization present.
- Safe rendering (`#plain_text`, sanitized markup), no unsafe Twig raw output.
- SQL built via query builder/placeholders.

## Architecture and Drupal Fit
- Contrib module / recipe considered before custom implementation.
- DI and service patterns used in classes; avoid static service lookups in class code.
- Appropriate use of hooks vs subscribers vs plugins.
- Config schema and module structure follow Drupal conventions.

## Open Source Contributor Lens
- Custom workaround evaluated for upstream patch viability.
- Issue queue research performed before local-only divergence.
- Proposed fixes include contrib/core contribution path when appropriate.
- Local patch maintenance burden is explicitly acknowledged.

## Site Builder (Admin UI) Lens
- Config UX in admin UI remains understandable and maintainable.
- Permissions, workflows, and display settings are practical for site builders.
- Views/content type changes avoid hidden coupling and brittle admin flows.
- Drush/config sync steps align with real admin-managed workflows.

## Content Editor/Marketer Lens
- Editorial workflow remains clear (draft/review/publish scheduling states).
- Content model supports real authoring needs without technical workarounds.
- Metadata/SEO fields are present and usable.
- Day-to-day editing friction is minimized.

## Operational Safety
- Update/deploy workflow includes rollback path.
- Composer changes are constraint-safe and compatible with current core.
- Drush DB/config/cache steps are complete and ordered.
- Error paths and logs are actionable.

## Caching and Performance
- Cache tags, contexts, and max-age are defined correctly.
- Personalized content avoids broad cache busting.
- BigPipe/lazy builders used correctly when needed.

## Testing and Verification
- Test strategy is proportional (unit/kernel/functional/JS as needed).
- Risky paths have explicit validation steps.
- Acceptance checks include critical user journeys.

## Migration and Source-Structure Coverage
- **MAJOR:** A migration/conversion plan proceeds with no `source-structure.json` inventory (see `contracts/source-structure/`), or with one or more components present in it that have no row in the accompanying `dispositions.json` (undispositioned — Gate G1). Point the author at `drupal-source-inventory` and `contracts/source-structure/validate-dispositions.py`.
- A reviewed FACT/REF field lands in a CONTENT/LAYOUT disposition with no per-field destination (Gate G2) is a MAJOR finding, not a style note — it silently drops structured data as flattened markup.
- A `dispositions.json` whose `source_structure_hash` doesn't match the current inventory is stale; counts in it should not be trusted until re-validated.

## Review Confidence
- High confidence findings have direct evidence.
- Medium/low confidence concerns are labeled and moved to open questions.
