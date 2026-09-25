# drupal-source-inventory

`drupal-source-inventory` is a Bash-capable, read-only executor that
inventories a live Drupal source (exported config + database + theme) into
`source-structure.json`, validated against
`contracts/source-structure/source-structure.schema.json`.

## Command

- `/drupal-source-inventory`

## Role

- Downstream: `drupal-migration-planner` / `wordpress-migration-planner`
  (consume `source-structure.json` + an authored `dispositions.json`),
  `drupal-content-model-planner` / `wordpress-content-model-planner`
  (consume STRUCTURED-dispositioned rows)
- Review: `drupal-critic` (a plan without dispositions, or with
  undispositioned components, is a MAJOR finding)

## Not a planner

This skill inventories and data-classifies. It never authors a
STRUCTURED/QUERY/REUSE/LAYOUT/CONTENT/DROP/DEFER disposition itself — that
is a separate, human-authored `dispositions.json` step. See
`contracts/source-structure/README.md`.
