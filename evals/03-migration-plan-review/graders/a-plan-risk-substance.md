---
type: llm
focus: last_message
weight: 1
---
This is a PLAN review. The plan has already been written to cover the obvious
process ground: it has a staging dry run against a production copy, a
pre-migration database snapshot, and a named rollback command. Raising any of
those as a gap is NOT a finding here and earns no credit — neither does generic
advice ("test more", "allow buffer time", "add monitoring", "get sign-off").

Credit only findings that require knowing how Drupal migrations actually
behave. The real defects:

1. **Reading `field_data_*` tables directly.** `field_data_body` holds only the
   *current* revision; `field_revision_body` holds the rest. A hand-rolled
   `SqlBase` over `field_data_*` silently drops revisions, and also loses
   translations, field deltas, and the source text format — things the
   `migrate_drupal` D7 source plugins (`d7_node`, `d7_field_instance`) handle.
   A correct finding says to use the D7 source plugins rather than raw
   `field_data_*` reads, or names revisions/translations/text format as lost.

2. **`taxonomy_index` is not a source of truth.** In D7 it is a denormalised
   index populated for *published* nodes only. Driving term assignment from it
   means unpublished articles arrive with no terms at all. A correct finding
   says to read `taxonomy_index` is wrong and to use the field tables
   (`field_data_field_tags`) or the D7 term-reference source instead, or
   explicitly names the published-only behaviour.

3. **Creating terms ad hoc defeats the stated rollback.** Terms matched or
   created inline get no entry in any migration map table, so
   `drush migrate:rollback` cannot remove them and a re-run can duplicate them.
   The correct shape is a separate terms migration plus `migration_lookup`
   with a declared `migration_dependencies`. A finding that says the rollback
   path is narrower than the plan claims — it only reverses rows in the
   `legacy_articles` map table — also counts here.

4. **Deferring files breaks the body migration.** D7 `body_value` carries inline
   `<img src="/sites/default/files/...">` markup and file/media references.
   Importing articles a week before files ships 42,000 nodes with broken
   images, and D7 files need mapping to D11 media entities, not just copying.
   A correct finding challenges the ordering or the "separate, later" framing.

5. **`user 1` as the author fallback.** Silently attributing unmatched content
   to the site's superuser account is both wrong attribution and a poor default
   for a security-sensitive account; the plan gives no count of how many of the
   42,000 rows will miss.

Also acceptable as a fifth-tier credit: the `legacy` connection lives in
`settings.php`, which is per-environment and not exportable as config, so the
production web node must reach the old database; or that a single
`migrate:import` of 42,000 rows needs batching / `--limit` / `--feedback`
rather than one unbounded run.

PASS if at least THREE of items 1-5 are raised with that level of specificity.

FAIL if fewer than three are raised, or if the response leans on the process
gaps the plan already closes, or if its findings would read the same for a
non-Drupal data migration.
