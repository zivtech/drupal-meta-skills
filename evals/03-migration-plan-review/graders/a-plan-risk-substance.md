---
type: llm
focus: last_message
weight: 1
---
This is a PLAN review, not a code review. The response must surface the concrete
operational risks in this migration plan. It must raise at least THREE of these
five, each tied to the plan text rather than stated as a generic caution:

1. **Idempotency / replay.** The plan runs `migrate:import` once with no
   statement of what happens on partial failure, a re-run, or a resumed batch.
   A correct finding asks how the migration behaves when replayed, or names
   migrate's highwater/track-changes/`--update` behavior.

2. **Rollback.** There is no rollback or restore path — no `migrate:rollback`,
   no database snapshot before the run, and the run happens the night before
   launch on production.

3. **Unsafe source assumption.** Step 4 maps a free-text author name to a user
   account. A correct finding says name matching is ambiguous or lossy —
   duplicates, missing accounts, renames — and asks what happens to rows that
   do not resolve.

4. **Ambiguity in step 3.** "Taxonomy terms will be mapped automatically based
   on name matching" is underspecified: which vocabulary, what happens to terms
   that do not exist, case/whitespace/duplicate handling.

5. **Config-workflow risk in cutover.** Running `drush cex` on production after
   an import and committing it risks exporting production drift, and the
   migration config itself needs to be in code before the import, not after.

PASS if at least three of the five are raised with that level of specificity.
FAIL if the response is mostly generic project-management advice ("test in
staging", "allow more time", "add monitoring") without naming the concrete
defects above, or if it reviews the plan as though it were code.
