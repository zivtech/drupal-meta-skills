---
type: llm
focus: last_message
weight: 1
---
The review must challenge whether this module should exist at all, not merely
tidy up the code it contains.

It must name the contrib modules that already solve this, by name:
- **pathauto** (with **token**, and core's path alias system) for the
  title-to-alias slug generation in `site_urls_node_insert()`;
- **redirect** for the stored 301 redirects and the request-time redirect
  in `RedirectSubscriber`.

Naming at least one of those two by its actual module name is required; naming
both is better. A vague gesture at "a contrib module probably exists" or
"check drupal.org" does NOT count.

It must also make the contrib-first argument concretely — for example that the
custom code re-implements a maintained, security-covered solution, that it will
carry its own upgrade and security burden across core versions, or that it
bypasses core's path alias API and so misses alias invalidation, language
handling, and admin UI that contrib already provides.

PASS if a named contrib replacement is recommended AND the reasoning above is
present. FAIL if the response only critiques the implementation (SQL style,
missing `hook_schema`, direct `\Drupal::` calls, missing delete handling)
without questioning the build-vs-adopt decision.
