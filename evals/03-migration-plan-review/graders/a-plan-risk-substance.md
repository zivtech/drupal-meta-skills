---
type: llm
focus: last_message
weight: 1
---
This is a PLAN review. The plan already covers the obvious process ground — a
staging dry run against a production copy, a pre-migration snapshot, and a named
rollback command. Raising any of those as a gap is NOT a finding and earns no
credit, nor does generic advice ("test more", "allow buffer time", "add
monitoring", "get sign-off", "the QA sample is small").

Two conditions must BOTH hold.

## Condition A — the architecture is questioned (required)

The plan proposes "a custom `SqlBase` source plugin against the `legacy`
connection", reading `node`, `field_data_body`, `field_data_field_author`
directly. The review must challenge that decision itself, not merely audit the
steps as written: Drupal core ships a maintained D7 upgrade path
(`migrate_drupal`, `d7_node` / `d7_node_complete`, `d7_taxonomy_term`,
`d7_user`, `d7_url_alias`, or `drush migrate:upgrade`), and hand-rolling over
the D7 storage tables re-implements it while losing what it handles.

To satisfy A the response must BOTH name core's D7 migration path (any of the
plugin names above, `migrate_drupal`, or `migrate:upgrade`) AND say what the
custom approach costs — for example that `field_data_*` holds only the current
revision while `field_revision_*` holds the rest, or that revisions,
translations/language, publish status, field deltas, text format, or URL
aliases are dropped.

A response that discusses the source plugin only as something needing a WHERE
clause, a filter, or extra field mappings has NOT satisfied A.

## Condition B — at least two further Drupal-specific findings

Count any two of these, or any equivalent finding of the same depth that is not
listed here. This list is illustrative, not exhaustive — credit a reviewer who
finds a different real Drupal problem just as readily, and do not penalise a
review for organising its findings differently:

- `taxonomy_index` is a denormalised D7 listing aid, not field data: incomplete
  for unpublished nodes, flattens hierarchy, per-language rows.
- Terms created inline get no migrate map rows, so `drush migrate:rollback`
  cannot remove them and a re-run duplicates them; needs its own migration plus
  `migration_lookup` / `migration_dependencies`.
- The stated rollback is narrower than the plan implies — it reverses tracked
  map rows only, not side effects.
- Deferring files to DM-118 breaks the body migration: D7 `body_value` carries
  inline `<img src="/sites/default/files/...">` and file references, and D7
  files need mapping to D11 media entities.
- URL aliases and redirects are unaddressed, losing 42,000 inbound paths.
- Text format / filter format mapping, including CKEditor 4 → 5 markup.
- `user 1` as the author fallback attributes content to the superuser.
- The `legacy` connection lives in `settings.php`, which is per-environment and
  not exportable as config.
- A single unbounded `migrate:import` of 42,000 rows with no batching,
  `--limit`, or `--feedback`.

## Verdict

PASS only if A holds AND at least two items under B are present.

FAIL if A is missing, however many B items are found — a review that lists a
broad sweep of process risks but never questions whether this migration should
have been written by hand does not pass this grader.
