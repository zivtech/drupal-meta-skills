---
max_turns: 8
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill]
runs: 3
---
Here's the migration plan we're about to sign off on. Tear it apart before we commit to it.

`docs/plans/legacy-migration.md`
```markdown
# Legacy Article Migration — Plan

## Goal
Move 42,000 articles from the Drupal 7 site into the new Drupal 11 install
before the marketing launch on the 30th.

## Source
The D7 database is attached as the `legacy` connection, added to `settings.php`
on each environment. We read from `node`, `field_data_body`,
`field_data_field_author`, and `taxonomy_index`.

## Approach
1. A custom `SqlBase` source plugin against the `legacy` connection.
2. Map `node.title` → `title`, `field_data_body.body_value` → `body`.
3. Taxonomy: read `taxonomy_index` for each node, match the D7 term names
   against the new `tags` vocabulary, and create the term if it isn't there yet.
4. Author: `field_author_value` is free text on the old site. Match it against
   `users.name`; where there's no match, fall back to user 1.

## Testing and rollback
- Full dry run on staging against a copy of the production database.
- `drush migrate:rollback legacy_articles` is our rollback path.
- Database snapshot taken immediately before the production run.

## Cutover
1. Snapshot production.
2. `drush migrate:import legacy_articles`
3. Spot-check 20 nodes, then open the site.

## Out of scope
Files and images are a separate migration, tracked in DM-118, scheduled for the
week after launch.
```
