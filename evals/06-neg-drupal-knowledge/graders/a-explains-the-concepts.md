---
type: llm
focus: last_message
weight: 1
---
The response must directly answer the conceptual question.

It must convey both halves of the distinction:
- **Cache tags** express a *dependency on data*. They are used to invalidate
  cached output when the underlying thing changes (e.g. `node:5`, `node_list`,
  `config:system.site`). Tags answer "when does this become stale?"
- **Cache contexts** express *variation by request*. They cause a separate
  cached variant per dimension (e.g. `user.roles`, `url.path`, `languages`,
  `user.permissions`). Contexts answer "how many different versions of this are
  there?"

It should give at least one concrete example of each. Mentioning max-age as the
third piece of cache metadata is a bonus, not a requirement.

PASS if both halves are explained correctly and distinguishably — invalidation
versus variation.

FAIL if the response instead returns a structured code/architecture review, asks
for code or a file to review, produces a verdict, or refuses to answer because
nothing was submitted for review. Also FAIL if it conflates the two (for example
describing tags as causing per-user variants).
