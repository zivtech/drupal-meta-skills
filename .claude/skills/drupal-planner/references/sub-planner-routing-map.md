# Sub-Planner Routing Map

Detailed routing logic for selecting the right drupal-planner sub-skill based on the user's request.

## Routing Decision Tree

```
User request arrives
│
├─ Is this about content types, entity types, bundles, paragraphs,
│  field architecture, composition patterns, editorial workflows?
│  → Route to: /drupal-planner.content-model
│
├─ Is this about vocabularies, taxonomy terms, classification,
│  categories, tags, faceted navigation, term hierarchies?
│  → Route to: /drupal-planner.taxonomy
│
├─ Is this about theme architecture, base theme, CSS methodology,
│  Twig templates, components (SDC), preprocess functions, asset
│  libraries, responsive design, design system?
│  → Route to: /drupal-planner.theme
│
├─ Is this about search configuration, Search API, Solr, Elasticsearch,
│  search indexing, autocomplete, search facets, content discovery?
│  → Route to: /drupal-planner.search
│
├─ Is this about Canvas Code Components, Canvas component architecture,
│  component definition, component metadata/props, component composability,
│  component data fetching, Canvas styling, component upload/deploy?
│  → Route to: /drupal-planner.canvas
│
├─ Does the request span multiple concerns (entity + permissions +
│  cache + migration)?
│  → Route to: /drupal-planner (main, covers all 10 phases)
│
└─ Is the request vague or unclear?
   → Ask clarifying questions, then route
```

## Keyword-Based Routing

| Keywords in Request | Primary Route | May Also Need |
|---|---|---|
| "content model", "content types", "entity types", "paragraphs", "bundles", "fields", "Layout Builder components" | `.content-model` | `.taxonomy` (if classification involved) |
| "taxonomy", "vocabularies", "terms", "categories", "tags", "classification", "tagging" | `.taxonomy` | `.search` (if faceted search involved) |
| "theme", "frontend", "CSS", "Twig", "templates", "components", "SDC", "design system", "base theme", "responsive" | `.theme` | Main planner (if also needs entity/module design) |
| "search", "Search API", "Solr", "Elasticsearch", "indexing", "facets", "autocomplete", "discovery" | `.search` | `.taxonomy` (if facets from vocabularies) |
| "Canvas", "Canvas Code Component", "component definition", "component metadata", "component props", "component composability", "component upload", "Canvas styling", "Canvas data fetching" | `.canvas` | `.theme` (if also needs SDC/traditional theming) |
| "module", "feature", "permissions", "cache", "migration", "hooks", "services", "plugins" | Main planner | Sub-planners for deep-dive phases |
| "redesign", "refactor", "architecture", "plan the system" | Main planner | Sub-planners as needed |

## Multi-Planner Workflows

For complex projects, multiple planners may be needed in sequence:

### New Site Build
1. `/drupal-planner.content-model` — Design entity types and field architecture
2. `/drupal-planner.taxonomy` — Design classification system
3. `/drupal-planner.search` — Design search and discovery
4. `/drupal-planner.canvas` — Design Canvas Code Component architecture (if Drupal CMS)
5. `/drupal-planner.theme` — Design theme architecture (SDC, traditional theming)
6. `/drupal-planner` — Tie it together with permissions, cache, migrations

### Content Model Redesign
1. `/drupal-planner.content-model` — Redesign entities and fields
2. `/drupal-planner.taxonomy` — Update taxonomy to match new model
3. `/drupal-planner` — Plan migration from old to new model

### Search Overhaul
1. `/drupal-planner.search` — Design new search architecture
2. `/drupal-planner.taxonomy` — Align taxonomies with facet requirements
3. `/drupal-planner` — Plan implementation tasks and review checkpoints

### Theme Rebuild
1. `/drupal-planner.theme` — Design theme architecture (SDC, traditional theming)
2. `/drupal-planner.canvas` — Design Canvas Code Components (if Drupal CMS)
3. `/drupal-planner` — Plan any module-level changes needed for theme (render arrays, preprocess)

### Canvas Component Ecosystem
1. `/drupal-planner.canvas` — Design Canvas Code Component architecture
2. `/drupal-planner.content-model` — Ensure content model supports Canvas data needs
3. `/drupal-planner.theme` — Plan traditional theme layer alongside Canvas components
4. `/drupal-planner` — Plan module-level support (data endpoints, permissions)

## Sub-Planner ↔ Critic Companion Mapping

Each sub-planner has a companion critic for review after implementation:

| Sub-Planner | Companion Critic | Review Focus |
|---|---|---|
| `drupal-planner.content-model` | `content-model-critic` | Entity proliferation, field duplication, composition patterns, taxonomy coupling |
| `drupal-planner.taxonomy` | `taxonomy-critic` | Hierarchy depth, mutual exclusivity, term naming, governance |
| `drupal-planner.theme` | `drupal-theme-critic` | Preprocess scope, template organization, CSS methodology, render pipeline |
| `drupal-planner.search` | `search-discovery-critic` | Index design, facet strategy, relevance tuning, zero-result handling |
| `drupal-planner.canvas` | `drupal-critic` (Canvas skills) | Component definition, prop schemas, data fetching, composability, styling, upload pipeline |
| `drupal-planner` (main) | `drupal-critic` | Full implementation review (permissions, cache, hooks, migrations) |
