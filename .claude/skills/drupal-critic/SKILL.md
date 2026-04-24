---
name: drupal-critic
description: Drupal-specific harsh review orchestration for plans, code, and implementation notes. Use when reviewing Drupal modules/themes/config/deploy workflows, contrib patch decisions, cache behavior, migration plans, Drush/DDEV/Composer updates, or any Drupal change where you need evidence-backed critique. Always run security/new-hire/ops perspectives; activate open-source-contributor, site-builder, and content-editor perspectives when context indicates they will reveal additional fixes.
---

# Drupal Critic

## Overview
Run a harsh-critic style review with Drupal-specific checks, explicit evidence requirements, and context-driven audience perspectives.

## External Skill References (No Copy Policy)
Use external skills as references only.

- Canonical reference file: [external-skills-manifest.yaml](references/external-skills-manifest.yaml)
- Routing policy: [skill-routing-map.md](references/skill-routing-map.md)

Rules:
- Do not copy external skill body content into this repository.
- Use manifest IDs/URLs and pinned commit metadata for traceability.
- If a referenced skill is unavailable in runtime, continue with local rubric fallback and state the limitation.

## Workflow
1. Confirm review target and scope.
2. Make 3-5 pre-commitment predictions about likely failure points before deep review.
3. Run protocol phases in order: verification, multi-perspective analysis, explicit gap analysis, synthesis.
4. If reviewing plans/specs, also run plan-specific checks: key assumptions extraction, pre-mortem, dependency audit, ambiguity scan, feasibility check, rollback analysis, and devil's-advocate challenge for major decisions.
5. Run mandatory self-audit before finalizing findings:
   - LOW confidence or easily-refutable claims move to `Open Questions (unscored)`.
   - Preference/style-only points are downgraded or removed from scored sections.
   - Keep scored sections evidence-backed and high-confidence.
6. Run Realist Check on every surviving CRITICAL/MAJOR finding:
   - "If we shipped this as-is today, what is the realistic worst-case outcome?" (not theoretical — the likely worst case given actual usage, traffic, and environment)
   - "Is there a mitigating factor that limits the blast radius?" (e.g., feature flag, low traffic path, existing monitoring, downstream validation, limited user exposure)
   - "How quickly could this be detected and fixed in production?" Minutes (monitoring) vs days (silent corruption) vs never (subtle logic error).
   - "Is the severity proportional to actual risk, or was it inflated by investigation momentum?"

   SECURITY EXPLOITABILITY GATE (mandatory for all security-related findings):
   - "Who can trigger this? What privilege level is required to reach this code path?"
   - "Can a non-privileged user actually exploit this, or does it require admin/superuser access?"
   - "Does the existing access control model already make this moot?"

   Drupal privilege model awareness:
   - Drupal administrators can already execute arbitrary PHP, inject code via UI, and modify all site configuration. Flagging admin-only surfaces as security vulnerabilities is a false positive unless the issue allows non-admins to bypass access controls.
   - `settings.php` is only accessible to users with server/code access (effectively site admins/developers). Issues in settings.php are configuration concerns, not security vulnerabilities.
   - Admin screens (`/admin/*`) are not security risks unless they enable: privilege escalation to non-admins, CSRF that tricks admins into unintended destructive actions, or stored XSS that persists beyond the admin session and affects non-admin users.
   - Focus security findings on: anonymous access, authenticated non-admin access, and privilege escalation paths.

   If you cannot demonstrate a concrete exploit path accessible to non-admin/non-privileged users:
   - Tag the finding as `[UNCONFIRMED]` and move it to Open Questions
   - Add the note: "Security finding unconfirmed — no demonstrated exploit path for non-privileged users."
   - Do NOT leave unconfirmed security findings in scored sections

   A theoretical vulnerability that requires admin access in Drupal — where admins already have full control — is not a finding. It is manufactured alarmism that damages review credibility.

   Recalibration rules:
   - Minor inconvenience with easy rollback → downgrade CRITICAL to MAJOR
   - Mitigating factors substantially contain blast radius → downgrade CRITICAL to MAJOR or MAJOR to MINOR
   - Fast detection + straightforward fix → note context in the finding but keep it
   - Survives all four questions → correctly rated, keep it
   - NEVER downgrade findings involving data loss, security breach, or financial impact
   - Every downgrade MUST include a "Mitigated by: ..." statement explaining what real-world factor justifies the lower severity. No downgrade without an explicit mitigation rationale.
   Report any recalibrations in the Verdict Justification (e.g., "Realist check downgraded finding #2 from CRITICAL to MAJOR — mitigated by the fact that the affected endpoint handles <1% of traffic and has retry logic upstream").
7. Apply Drupal rubric from [drupal-review-rubric.md](references/drupal-review-rubric.md).
8. Activate perspectives based on [audience-activation-matrix.md](references/audience-activation-matrix.md).
9. Load at most 2-3 specialist external skills from the routing map when needed.
10. Return structured verdict with evidence.
