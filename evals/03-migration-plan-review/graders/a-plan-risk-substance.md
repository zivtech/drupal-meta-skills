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

Credit only findings that require knowing how Drupal migrations actually
behave. Count any THREE of these, or any equivalent finding of the same depth
that is not listed here. This list is illustrative, not exhaustive — credit a
reviewer who finds a different real Drupal problem just as readily, and do not
penalise a review for organising its findings differently:

- The plan hand-rolls a `SqlBase` source plugin over D7's storage tables
  instead of core's maintained D7 upgrade path (`migrate_drupal`, `d7_node` /
  `d7_node_complete`, `d7_taxonomy_term`, `drush migrate:upgrade`), losing what
  that path handles — `field_data_*` holds only the current revision while
  `field_revision_*` holds the rest, plus translations, publish status, field
  deltas, text format, URL aliases.
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

PASS if at least three qualifying findings are present.

FAIL if fewer than three are raised, if the response leans on the process gaps
the plan already closes, or if its findings would read the same for a
non-Drupal data migration.
