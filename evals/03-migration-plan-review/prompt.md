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
Move 42,000 articles from the old Drupal 7 site into the new Drupal 11 install
before the marketing launch on the 30th.

## Source
The D7 database is available as a read replica (`legacy` connection key). We
read `node`, `field_data_body`, `field_data_field_author`, and
`taxonomy_index`.

## Approach
1. Point a `migrate` source plugin at the `legacy` connection.
2. Map `node.title` to `title`, `field_data_body.body_value` to `body`.
3. Taxonomy terms will be mapped automatically based on name matching.
4. Author is mapped from `field_data_field_author.field_author_value`, which is
   a free-text name on the old site; we look up the matching user account.
5. Run the migration on the production site the night before launch.

## Cutover
Run `drush migrate:import legacy_articles` once. Then export config with
`drush cex` and commit.

## Open items
- Media/file migration is handled in a separate ticket.
```
