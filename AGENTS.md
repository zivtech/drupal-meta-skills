# AGENTS.md — drupal-meta-skills

| Agent | Type | Command | Companion / Role |
|-------|------|---------|------------------|
| drupal-planner | planner | `/drupal-planner` | Main Drupal architecture planner |
| drupal-content-model-planner | planner | `/drupal-planner.content-model` | Content model deep dive |
| drupal-taxonomy-planner | planner | `/drupal-planner.taxonomy` | Taxonomy deep dive |
| drupal-theme-planner | planner | `/drupal-planner.theme` | Theme architecture deep dive |
| drupal-canvas-planner | planner | `/drupal-planner.canvas` | Canvas Code Component architecture |
| drupal-search-planner | planner | `/drupal-planner.search` | Search architecture deep dive |
| drupal-critic | critic | `/drupal-critic` | Read-only Drupal review surface |
| drupal-config-executor | executor | `/drupal-config-executor` | Generates config YAML from planner specs |

## The 8-Step Drupal Lifecycle

The critic serves at **two checkpoints** — after planning and after implementation. This dual-review loop catches architecture gaps early and implementation regressions late.

| Step | Action | Agent | Role |
|------|--------|-------|------|
| 1 | Plan | `drupal-planner` | Planner |
| 2 | Critique Plan | `drupal-critic` | Critic (Checkpoint 1) |
| 3 | Revise | manual | Manual |
| 4 | Generate Config | `drupal-config-executor` | Executor |
| 5 | Implement | executor | Executor |
| 6 | Critique Impl | `drupal-critic` | Critic (Checkpoint 2) |
| 7 | Fix | executor | Executor |
| 8 | Re-review | `drupal-critic` | Critic |

## Notes

- All planner, critic, and executor surfaces are shipped from this repository.
- The config executor is the concrete generation step between planning and review.
- The same dual-checkpoint pattern applies to accessibility work — see the [visual explainer](https://zivtech.github.io/drupal-meta-skills/) for the a11y lifecycle variant using `a11y-planner`, `a11y-critic`, and `a11y-test`.
