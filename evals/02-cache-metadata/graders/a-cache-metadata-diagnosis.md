---
type: llm
focus: last_message
weight: 1
---
The review must diagnose the cache metadata on `PromoBlock::build()` specifically
— not offer generic caching advice.

It must make BOTH of these points:

1. `'max-age' => 0` is the wrong instrument. The block is uncacheable on every
   request, which defeats the render cache and forces the Dynamic Page Cache /
   BigPipe to re-render it for every visitor. The fix is cache *tags* that
   invalidate when the promotion nodes change — naming `node_list`, a
   `node_list:promotion` list tag, or per-node `node:<nid>` tags — instead of
   disabling caching.

2. The block varies its output by the visitor's roles (`$show_codes` is derived
   from `$account->getRoles()`) but declares no cache context for it. It must
   name the missing context: `user.roles` (or `user.roles:member`, or
   `user.permissions`). It is also correct to note that access-checked entity
   queries imply `user.permissions`.

PASS only if both points are present and specific: point 1 must connect max-age 0
to the caching consequence AND name tags as the alternative; point 2 must name a
concrete cache context string.

FAIL if the response only says "add caching", "consider cache tags", or
"review the cache settings" without naming the concrete tags and the concrete
context, or if it misses the role-variance problem entirely.
