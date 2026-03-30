# drupal-meta-skills

This repository is the consolidated public package for Zivtech's Drupal planner-critic-executor workflow.

## Included Skills

| Skill | Type | Command |
|-------|------|---------|
| drupal-planner | planner | `/drupal-planner` |
| drupal-planner.content-model | planner | `/drupal-planner.content-model` |
| drupal-planner.taxonomy | planner | `/drupal-planner.taxonomy` |
| drupal-planner.theme | planner | `/drupal-planner.theme` |
| drupal-planner.canvas | planner | `/drupal-planner.canvas` |
| drupal-planner.search | planner | `/drupal-planner.search` |
| drupal-critic | critic | `/drupal-critic` |
| drupal-config-executor | executor | `/drupal-config-executor` |

## Structure

- Root `.claude/skills/*/SKILL.md` files are the installable skill definitions.
- Root `.claude/agents/*.md` files are the companion agent prompts.
- `scripts/` contains the external skill manifest maintenance tooling.
- `research/` contains tracked Drupal ecosystem analysis assets.
- `templates/` contains the copied planner, critic, and executor base protocols.

## Working In This Repo

- Keep the repo installable from the root `.claude/` directory.
- Preserve the planner -> executor -> critic workflow.
- Do not vendor upstream third-party skill bodies; maintain the manifest-and-reference model.
- Keep supply-chain validation scripts and workflow checks working.
