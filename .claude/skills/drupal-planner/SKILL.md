---
name: drupal-planner
description: Plan Drupal implementations (entity types, config schema, migrations, cache strategy, permissions, module architecture) before coding. Use when designing new features, modules, config entities, or migrating existing sites. Routes to focused sub-planners for content model, taxonomy, theme, and search architecture.
---

# Drupal Planner

## Overview

drupal-planner helps you design Drupal implementations before writing code. It produces architecture plans that specify entity types, field relationships, module decisions, config schemas, permission models, cache strategies, and migration paths — precise enough that a developer can implement them without architectural guessing.

For focused subsystem planning, use the dot-notation sub-planners:
- `/drupal-planner.content-model` — Drupal content model architecture (entity types, bundles, paragraphs, field architecture)
- `/drupal-planner.taxonomy` — Drupal taxonomy architecture (vocabularies, term hierarchies, faceted navigation)
- `/drupal-planner.theme` — Drupal theme architecture (base theme, components, CSS, preprocess, assets)
- `/drupal-planner.canvas` — Canvas Code Component architecture (component definition, props, data fetching, composability, deploy)
- `/drupal-planner.search` — Drupal search architecture (Search API, Solr/Elasticsearch, facets, Views)

## Sub-Planner Routing

When the user's request is clearly focused on one subsystem, suggest the appropriate sub-planner:

| Signal | Route To |
|--------|----------|
| "content model", "entity types", "content types", "paragraphs", "field architecture", "bundles" | `/drupal-planner.content-model` |
| "taxonomy", "vocabularies", "classification", "tagging", "categories", "facets" | `/drupal-planner.taxonomy` |
| "theme", "templates", "CSS", "Twig", "SDC", "design system", "frontend" | `/drupal-planner.theme` |
| "Canvas", "Canvas Code Component", "component definition", "component props", "component composability", "Canvas styling", "component upload" | `/drupal-planner.canvas` |
| "search", "Search API", "Solr", "Elasticsearch", "discovery", "autocomplete" | `/drupal-planner.search` |
| General feature, module, migration, or multi-concern request | Stay with `/drupal-planner` (covers all 10 phases) |

When a request spans multiple subsystems (e.g., "plan a new events system" touches content model + taxonomy + search), use the main `/drupal-planner` for the overall architecture and suggest sub-planners for deep-dive phases.

## Purpose

Use Drupal Planner when you need to:
- Design a new feature (e.g., "add product reviews with ratings")
- Plan a new content type, config entity, or field structure
- Make contrib vs custom decisions
- Plan a configuration schema for a custom module
- Design a migration from an existing site
- Plan permission and access control models
- Design a caching strategy for performance-critical features
- Plan hooks, plugins, services, and event subscribers
- Refactor an existing Drupal architecture to fix performance or maintainability issues

## Use_When

- User says "plan the architecture for X", "design the data model for Y", "how should we structure Z in Drupal"
- User is about to build a new Drupal module, custom entity type, or config entity
- User needs to decide between contrib modules and custom code
- User is migrating from an existing site and needs to plan the content model
- User is designing a feature that spans multiple entity types or modules
- User has a drupal-critic REVISE finding and needs architectural fixes
- User is implementing a permission model or access control strategy
- User needs to plan cache tags/contexts for a performance-critical feature

## Do_Not_Use_When

- User wants to review existing Drupal code for bugs/style/correctness — use drupal-critic instead
- User wants to write Drupal code or implement a feature — use their development workflow instead
- User wants general Drupal knowledge (what's an entity? how does the cache API work?) — answer directly
- User is just asking a question, not designing something — answer directly instead

## Steps

1. **Identify the scope**: Determine what Drupal implementation needs planning. If no arguments provided, ask the user what they want to plan.

2. **Route check**: If the request is clearly focused on content model, taxonomy, theme, or search, suggest the appropriate sub-planner. If it spans multiple concerns, proceed with the full planner.

3. **Check for companion skills**: Check if brainstorming, code-archaeology are installed. If brainstorming is available AND this is a new feature (not a fix), invoke it first.

4. **Understand the context**:
   - If modifying/extending existing code, invoke code-archaeology first to understand current entity structure, modules, services, hooks
   - Detect Drupal version from composer.json or code (Drupal 7, 10, 11, CMS)
   - Identify existing conventions: entity types, field naming, module structure, config export strategy
   - Understand what's driving the architecture: performance requirements? Multi-tenancy? Legacy migration? SEO? Content workflow?

5. **Route to planner agent**: Delegate planning to the drupal-planner agent.
   - **With oh-my-claudecode (preferred)**: `Agent(subagent_type="oh-my-claudecode:drupal-planner", model="opus", prompt=<planning_prompt>)`
   - **Without oh-my-claudecode**: `Agent(subagent_type="drupal-planner", model="opus", prompt=<planning_prompt>)`

6. **Return the plan**: Present the plan document to the user and offer execution options.
