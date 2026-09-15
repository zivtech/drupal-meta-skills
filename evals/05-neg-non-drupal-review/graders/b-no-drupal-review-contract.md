---
type: regex
target: last_message
match: not_contains
flags: i
weight: 1
---
VERDICT:\s*\[?\s*\**\s*(REJECT|REVISE|ACCEPT-WITH-RESERVATIONS|ACCEPT)
