# Skill Routing Map

Use this map to decide which specialist Drupal skill(s) to load during review.
Source of truth for IDs/status/pins is [external-skills-manifest.yaml](external-skills-manifest.yaml).

## How to Use JTBD for Skill Selection

Before selecting skills, match the review context against each skill's JTBD statement. Load the skill whose `[situation]` most closely matches the artifact under review. When multiple skills match, prefer higher priority (from manifest) and tighter situational fit.

## Core Review Skills

- `madsnorgaard/agent-resources/drupal-expert`
  - JTBD: When I'm reviewing any Drupal module, theme, or config change, I want comprehensive Drupal 10/11 development expertise, so I can catch DI violations, coding standard gaps, and contrib-first failures.
- `madsnorgaard/agent-resources/drupal-security`
  - JTBD: When the review target handles user input, defines routes, builds entity queries, or renders user-supplied content, I want Drupal-specific security analysis, so I can identify XSS, SQL injection, and access bypass vulnerabilities before they ship.
- `bethamil/agent-skills/drupal-update`
  - JTBD: When the review covers a module update, Composer dependency change, or deployment workflow involving drush updb/cim, I want update automation expertise, so I can verify safety snapshots, config exports, and rollback paths are in place.
- `mindrally/skills/drupal-development`
  - JTBD: When I need broad Drupal development best practices as a baseline check, I want general coding guidelines, so I can verify standard patterns (hooks, services, config schema, test structure) are followed correctly.

## Open Source Contributor and Issue Queue

- `scottfalconer/drupal-issue-queue/drupal-issue-queue`
  - JTBD: When the review involves triage of a Drupal.org issue or assessing whether known bugs in contrib modules affect the code under review, I want issue queue search and summarization, so I can ground findings in existing upstream reports.
- `scottfalconer/drupal-contribute-fix/drupal-contribute-fix`
  - JTBD: When custom code overrides or patches contrib/core behavior, I want contribution packaging expertise, so I can assess whether the fix should go upstream and if the patch is structured for acceptance.
- `kanopi/cms-cultivator/drupalorg-issue-helper`
  - JTBD: When the review recommends filing an upstream bug report or feature request, I want Drupal.org issue template expertise, so I can verify the recommendation includes proper HTML formatting, categorization, and reproduction steps.
- `kanopi/cms-cultivator/drupalorg-contribution-helper`
  - JTBD: When the review identifies changes that should become merge requests on git.drupalcode.org, I want contribution workflow guidance, so I can verify the MR path is actionable and follows drupal.org conventions.

## Cache and Rendering Focus

- `sparkfabrik/sf-awesome-copilot/drupal-cache-contexts`
  - JTBD: When the review target serves different content per user role, language, URL parameter, or session state, I want cache context expertise, so I can verify the correct contexts are declared and no over- or under-caching occurs.
- `sparkfabrik/sf-awesome-copilot/drupal-cache-tags`
  - JTBD: When entities, config objects, or lists are rendered and need invalidation on data change, I want cache tag expertise, so I can verify tag assignment and propagation prevent stale content.
- `sparkfabrik/sf-awesome-copilot/drupal-cache-maxage`
  - JTBD: When render arrays or responses set time-based expiration, I want max-age expertise, so I can verify TTL propagation doesn't accidentally make uncacheable content cacheable or vice versa.
- `sparkfabrik/sf-awesome-copilot/drupal-dynamic-cache`
  - JTBD: When personalized or per-user content appears in otherwise cacheable pages, I want dynamic page cache expertise, so I can verify auto-placeholdering and #cache properties handle the variation correctly.
- `sparkfabrik/sf-awesome-copilot/drupal-cache-debugging`
  - JTBD: When the review identifies suspected stale content, unexpected cache misses, or performance regressions tied to caching, I want cache debugging techniques, so I can recommend concrete diagnostic steps and header inspection methods.
- `sparkfabrik/sf-awesome-copilot/drupal-lazy-builders`
  - JTBD: When uncacheable or expensive render elements are embedded in otherwise cached pages, I want lazy builder expertise, so I can verify deferred rendering is implemented correctly and BigPipe compatibility is maintained.

## Canvas / Component Ecosystem

- `drupal-canvas/skills/canvas-component-definition`
  - JTBD: When the review covers Canvas Code Component creation or structural setup, I want component definition patterns, so I can verify components follow Canvas conventions and register correctly.
- `drupal-canvas/skills/canvas-component-metadata`
  - JTBD: When Canvas component props, schemas, or type definitions are under review, I want metadata expertise, so I can verify prop contracts are complete, typed, and valid for the Canvas runtime.
- `drupal-canvas/skills/canvas-component-utils`
  - JTBD: When Canvas helper functions or shared utilities are under review, I want utility pattern guidance, so I can verify reuse patterns avoid duplication and follow Canvas conventions.
- `drupal-canvas/skills/canvas-data-fetching`
  - JTBD: When Canvas components fetch data from Drupal entities, views, or external APIs, I want data fetching patterns, so I can verify server-side vs client-side loading is correct and efficient.
- `drupal-canvas/skills/canvas-styling-conventions`
  - JTBD: When CSS, design tokens, or visual conventions in Canvas components are under review, I want styling standards, so I can verify consistency with the Canvas design system.
- `drupal-canvas/skills/canvas-component-composability`
  - JTBD: When Canvas components nest, compose, or use slots with other components, I want composability patterns, so I can verify parent-child relationships and data flow are architecturally sound.
- `drupal-canvas/skills/canvas-component-push`
  - JTBD: When the review covers pushing validated Canvas components to a Drupal site, I want push workflow expertise, so I can verify setup, deployment scope, dependencies, and failure recovery are handled correctly.

## Tooling and Environment

- `grasmash/drupal-claude-skills/drupal-ddev`
  - JTBD: When the review covers DDEV project configuration, .ddev/config.yaml settings, or initial local environment setup, I want DDEV configuration expertise, so I can verify project settings, PHP versions, and database config are correct.
- `omedia/drupal-skill/drupal-tooling`
  - JTBD: When the review involves Drush command sequences, Composer workflows, or deployment scripting that chains CLI operations, I want Drupal CLI tooling expertise, so I can verify command ordering, flag usage, and automation scripts follow best practices.
- `madsnorgaard/drupal-agent-resources/ddev-expert`
  - JTBD: When DDEV troubleshooting, custom service configuration (Redis, Solr, Elasticsearch), or CI/CD pipeline integration is under review, I want deep DDEV expertise, so I can diagnose container issues and verify complex multi-service setups.

## Routing Rules

- Match the review context against each skill's JTBD statement before selecting.
- Default: load one core review skill plus one specialist skill.
- Max loaded external skills per run: 3.
- Avoid overlapping core skills unless scope is explicitly broad.
- If two options overlap, prefer higher `priority` and `active` status from the manifest.
- For overlapping tooling skills: `drupal-ddev` for project setup/config, `drupal-tooling` for CLI/Drush/Composer operations, `ddev-expert` for troubleshooting/custom services/CI.
