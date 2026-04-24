---
name: drupal-planner.content-model
description: Plan Drupal content model architectures — entity types, bundles, paragraphs, field architecture, composition patterns, and editorial workflows. Use when designing or redesigning Drupal content structures before implementation.
---

# Drupal Content Model Planner

## Overview

drupal-planner.content-model designs Drupal content model architectures before implementation. It produces specifications for entity types, bundles, paragraphs, field architecture, composition patterns, taxonomy integration, and editorial workflows — all expressed in Drupal-specific terms.

This is a focused sub-planner of `/drupal-planner`. Use it when the planning scope is specifically about content model architecture rather than a full feature implementation.

## Use_When

- User says "plan the content model", "design content types", "how should we structure content in Drupal"
- User needs to decide: content type vs paragraph vs Layout Builder component vs ECK entity vs block content
- User is designing entity types, bundles, field architecture, or entity relationships
- User is planning a content model migration or redesign
- User needs to design editorial workflows that match how editors actually work
- User has content-model-critic REVISE findings to address

## Do_Not_Use_When

- User needs full feature planning (entity + modules + permissions + cache + migrations) — use `/drupal-planner`
- User wants to review an existing content model — use `content-model-critic` or `drupal-critic`
- User is focused on taxonomy/classification — use `/drupal-planner.taxonomy`
- User is focused on search/discovery — use `/drupal-planner.search`

## Steps

1. **Identify scope**: What content model is being designed or redesigned?
2. **Detect context**: Drupal version, existing content types, modules (Paragraphs, Layout Builder, ECK, Field Group)
3. **Route to agent**: Delegate to the drupal-content-model-planner agent
   - `Agent(subagent_type="drupal-planner", model="opus", prompt=<content_model_planning_prompt>)`
4. **Return the plan**: Present content model specification
