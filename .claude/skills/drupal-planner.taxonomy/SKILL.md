---
name: drupal-planner.taxonomy
description: Plan Drupal taxonomy architectures — vocabularies, term hierarchies, faceted navigation, Views integration, and Drupal-specific classification patterns. Use when designing or redesigning Drupal taxonomy structures.
---

# Drupal Taxonomy Planner

## Overview

drupal-planner.taxonomy designs Drupal taxonomy and classification architectures before implementation. It produces specifications for vocabularies, term hierarchies, term reference field configuration, Views integration, Facets module setup, Pathauto patterns, and taxonomy governance — all expressed in Drupal Taxonomy module terms.

This is a focused sub-planner of `/drupal-planner`. Use it when the planning scope is specifically about taxonomy and classification rather than a full feature implementation.

## Use_When

- User says "plan the taxonomy", "design vocabularies", "how should we classify content"
- User needs to design vocabulary structures, term hierarchies, or classification systems
- User is planning faceted navigation with the Facets module
- User needs to configure term reference fields, Views exposed filters, or Pathauto patterns
- User is migrating or consolidating existing taxonomies
- User has taxonomy-critic REVISE findings to address

## Do_Not_Use_When

- User needs full feature planning — use `/drupal-planner`
- User wants to review existing taxonomy — use `taxonomy-critic`
- User is focused on content types/entity architecture — use `/drupal-planner.content-model`
- User is focused on search beyond taxonomy facets — use `/drupal-planner.search`

## Steps

1. **Identify scope**: What taxonomy/classification is being designed?
2. **Detect context**: Drupal version, existing vocabularies, modules (Facets, Pathauto, Taxonomy Manager, Search API)
3. **Route to agent**: Delegate to the drupal-taxonomy-planner agent
   - `Agent(subagent_type="drupal-planner", model="opus", prompt=<taxonomy_planning_prompt>)`
4. **Return the plan**: Present taxonomy specification
