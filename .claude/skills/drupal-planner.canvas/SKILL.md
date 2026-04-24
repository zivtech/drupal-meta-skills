---
name: drupal-planner.canvas
description: Plan Canvas Code Component architectures — component definition, metadata/props, data fetching, styling, composability, utilities, and upload/deploy pipelines. Use when designing Canvas components for Drupal CMS site building before coding.
---

# Drupal Canvas Planner

## Overview

drupal-planner.canvas designs Canvas Code Component architectures before the first component file is written. It produces specifications for component definition structure, prop/schema contracts, data fetching patterns (server vs client), styling conventions and design tokens, component composability (nesting, slots, parent-child data flow), shared utilities, and upload/deploy pipelines — all grounded in Canvas conventions and Drupal CMS site-building patterns.

This is a focused sub-planner of `/drupal-planner` and the companion planner to `drupal-critic` (which loads Canvas-specific external skills for review). The planner designs FOR everything the critic's Canvas skills check.

## Use_When

- User says "plan a Canvas component", "design Canvas architecture", "plan the component ecosystem"
- User needs to decide component boundaries, prop contracts, or data fetching strategy for Canvas
- User is designing a Canvas component library for a Drupal CMS site
- User is planning how Canvas components compose with each other (nesting, slots, data flow)
- User needs to plan the upload/deploy pipeline for Canvas components
- User is migrating from SDC or Layout Builder to Canvas Code Components
- User has drupal-critic Canvas-related REVISE findings to address

## Do_Not_Use_When

- User needs traditional Drupal theme planning (SDC, Twig, preprocess) — use `/drupal-planner.theme`
- User needs full feature planning — use `/drupal-planner`
- User wants to review existing Canvas components — use `drupal-critic` (loads Canvas external skills)
- User is focused on content model or entity architecture — use `/drupal-planner.content-model`
- User is writing Canvas component code — use their development workflow

## Steps

1. **Identify scope**: What Canvas component architecture is being designed?
2. **Detect context**: Drupal CMS version, existing Canvas components, design system, content model dependencies
3. **Route to agent**: Delegate to the drupal-canvas-planner agent
   - `Agent(subagent_type="drupal-planner", model="opus", prompt=<canvas_planning_prompt>)`
4. **Return the plan**: Present Canvas component architecture specification
