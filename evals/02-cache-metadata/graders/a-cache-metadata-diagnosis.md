---
type: llm
focus: last_message
weight: 1
---
This block's cache metadata is present and superficially plausible — it has
tags, a context, and an explicit max-age. It is still wrong in ways specific to
Drupal's cache system. Credit only findings that identify those.

The defects, in descending importance:

1. **Missing list cache tag.** `$tags` holds only `node:<nid>` for the five
   promotions currently loaded. Nothing invalidates the block when the *set*
   changes — publish a sixth promotion, or unpublish one of the five, and the
   cached block keeps serving the stale list forever (max-age is PERMANENT).
   A correct finding names a list tag — `node_list`, `node_list:promotion`, or
   the storage's list cache tags — or says to take the tags from the query /
   entity list cache tags rather than building them by hand.

2. **`contexts => ['user']` is the wrong granularity.** The output varies only
   by whether the viewer has `view promo codes`. The `user` context forks the
   cache per individual account, so every authenticated user gets a private
   entry and nothing is shared; anonymous sharing also suffers. A correct
   finding says to use `user.permissions` (or `user.roles`, which is acceptable
   here) instead of `user`.

Bonus, not required: `$node->toUrl()->toString()` discards bubbleable
cacheability metadata (`toString(TRUE)` returns a `GeneratedUrl` carrying it);
`accessCheck(TRUE)` implies access-related cache contexts that are not
declared.

PASS only if BOTH 1 and 2 are identified, each naming the concrete replacement
(a list tag; `user.permissions`/`user.roles`).

FAIL if the response calls the cache metadata correct or does not question it;
if it only says "add cache tags" / "review the cache settings" without the list
tag; if it names the context problem but not the stale-list problem, or the
reverse; or if it treats `Cache::PERMANENT` as the root problem (permanent is
fine — the tags are what make it safe).
