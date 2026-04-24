---
name: drupal-config-executor
type: executor
model: claude-opus-4-6
description: >
  Use when you have a drupal-planner.content-model, .taxonomy, or .search spec and need actual Drupal config YAML generated. Consumes planner output and produces config/install/*.yml files ready for drush config:import.
---

# Drupal Config Executor Skill

## When to Use

**Primary triggers:**
- "generate drupal config", "scaffold content type", "create drupal fields"
- "generate config yaml", "drupal config from plan"
- "execute this content model plan", "build this content type"
- User has a drupal-planner.content-model spec and wants config YAML generated
- User describes a content type directly and wants config files produced

---

## Use When

- You have a completed drupal-planner.content-model spec and want to generate the config YAML files
- You have a completed drupal-planner.taxonomy spec and want vocabulary + facet config
- You have a completed drupal-planner.search spec and want Search API config
- You want to scaffold a content type directly without running the planner first (simple cases only)
- You need config YAML files for an existing content model design document

---

## Do Not Use When

- You need to **design** a content model — use `drupal-planner.content-model` first
- You need to **review** existing Drupal config — use `content-model-critic` or `drupal-critic`
- You need **custom module PHP code** (hooks, services, plugins) — use the OMC executor agent
- You need **theme scaffolding** (SDC components, Twig, CSS) — future `drupal-theme-executor`
- You need **migration YAML** — use `drupal-migration-planner` for the spec, then implement manually

---
