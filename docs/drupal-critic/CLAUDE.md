# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

drupal-critic is a Drupal-specific harsh-review orchestrator for Claude Code. It provides evidence-backed critique of Drupal plans, code, and operational workflows by coordinating external specialist skills — it does **not** vendor or copy external skill content.

The project ships as:
- A Claude Code **skill** (`.claude/skills/drupal-critic/SKILL.md`) — invoked via `/drupal-critic`
- A Claude Code **agent** (`.claude/agents/drupal-critic.md`) — read-only reviewer (opus model, no Write/Edit tools)

## Commands

```bash
# Refresh external skill pinned commits (fetches HEAD SHA from each upstream repo)
python3 scripts/refresh_external_skills.py

# Check if manifest pins are stale (CI mode — exits non-zero if updates needed)
python3 scripts/refresh_external_skills.py --check

# Verify no-copy policy and manifest integrity
python3 scripts/verify_no_copied_skills.py
```

Both scripts require PyYAML: `pip install pyyaml`

CI runs `verify_no_copied_skills.py` on every push/PR via `.github/workflows/validate.yml` (Python 3.12). The `--check` freshness test runs weekly (and on manual dispatch) via `.github/workflows/external-skills-drift.yml`, not on push/PR: its result depends on upstream repos' current HEAD, so it would fail unrelated changes whenever an upstream repo commits. A red drift run means the pins need a reviewed refresh, not that the repo is broken.

## Architecture

```
.claude/skills/drupal-critic/
├── SKILL.md                          # Skill behavior: review protocol, output contract, routing rules
├── references/
│   ├── external-skills-manifest.yaml # 24 external skills with pinned commits (source of truth)
│   ├── drupal-review-rubric.md       # 9-dimension review checklist
│   ├── audience-activation-matrix.md # Which perspectives activate for which content
│   └── skill-routing-map.md          # How to select max 2-3 external skills per review run
└── agents/
    └── openai.yaml                   # OpenAI interface metadata

.claude/agents/
└── drupal-critic.md                  # Read-only agent prompt (disallows Write/Edit)

scripts/
├── refresh_external_skills.py        # Manifest pin updater
└── verify_no_copied_skills.py        # Policy enforcement (manifest validity, no copied content, no tracked upstream)
```

### Key Design Decisions

- **No-copy policy**: External skills are referenced by ID, `skills_url`, `repo_url`, and `pinned_commit` SHA. Never copy SKILL.md content from external repos into this repository.
- **Orchestration pattern**: drupal-critic loads max 2-3 external specialist skills per review run, selected via the routing map based on review context. Each skill has a JTBD (Jobs-To-Be-Done) statement that agents match against the review context before selecting.
- **Tooling disambiguation**: `drupal-ddev` for project setup/config, `drupal-tooling` for CLI/Drush/Composer operations, `ddev-expert` for troubleshooting/custom services/CI.
- **Audience model**: Three perspectives always run (Security, New-hire, Ops). Three more activate based on context (Open Source Contributor, Site Builder, Content Editor/Marketer).
- **Evidence requirement**: All CRITICAL/MAJOR findings must include file:line or artifact references.

### External Skills Manifest

`external-skills-manifest.yaml` is the single source of truth for all 24 referenced skills. Each entry contains:
- `id`, `skills_url`, `repo_url`, `pinned_commit` (40-char SHA)
- `categories`, `audiences_supported`, `priority` (40-100), `status` (active/deprecated)

Categories: core-review, security, operations, contrib, cache, canvas, tooling.

### Validation Scripts

`verify_no_copied_skills.py` checks:
1. Manifest field integrity (valid URLs, 40-char SHAs, valid status values)
2. Org allowlist — repo owners must be in `TRUSTED_OWNERS` (Tier 1 supply chain)
3. No suspicious copied content markers in SKILL.md
4. All manifest skill IDs referenced in local markdown docs
5. No forbidden tracked paths under `research/drupal-skills/upstream/` or `extracted/`

`refresh_external_skills.py`:
1. Fetches current HEAD SHA from each upstream GitHub repo via `git ls-remote`
2. Generates GitHub compare URLs for changed pins (clickable diff review)
3. Fetches SKILL.md at new commit and scans for 10 prompt injection patterns
4. Blocks manifest update if scan warnings found (exit code 2, `--no-scan` to override)
5. Computes SHA-256 content hashes and stores as `content_hash` in manifest (Tier 2)
6. Appends pin changes to `research/drupal-skills/reports/refresh-audit.log` (Tier 2)

## Supply Chain Security for External Skills

The external skills manifest pins upstream skills by commit SHA. These skills are prompt text injected into Claude's context, so supply chain integrity matters.

### Tier 1: Implemented (low effort, high impact)

- **Org allowlist** — `verify_no_copied_skills.py` rejects any manifest entry whose `repo_url` owner is not in the `TRUSTED_OWNERS` allowlist. New upstream sources require explicit vetting before addition.
- **Compare URLs** — `refresh_external_skills.py` generates GitHub compare links for every changed pin so you can review upstream diffs before committing.
- **Content scanning** — on refresh, each changed skill's SKILL.md is fetched and scanned for 10 prompt injection patterns (instruction overrides, identity reassignment, base64 payloads, eval calls, fake system tags, HTML injection). Warnings block the manifest update until reviewed.
- **Scan gate** — if any warnings are found, the manifest is NOT updated (exit code 2). Re-run with `--no-scan` to force update after human review.

GitHub settings (manual, apply to this repo and all upstream repos you control):
- **Require signed commits** on main branch (Settings > Branches > Branch protection).
- **Require PR reviews** before merge to main. No direct pushes, no force pushes.

### Tier 2: Implemented (medium effort)

- **Content hashes** — `refresh_external_skills.py` computes SHA-256 of each SKILL.md at the pinned commit and stores it as `content_hash` in the manifest. Future verification can detect unexpected content changes.
- **Audit log** — every pin change is appended to `research/drupal-skills/reports/refresh-audit.log` with timestamp, old/new SHAs, and content hash. Provides a tamper-evident history of all manifest changes.
- **Tool access restriction** — the `drupal-critic` agent has `disallowedTools: Write, Edit`. It reviews but cannot modify files.

### Still open (Tier 3)

- **Pre-commit hook** for prompt content scanning in agent `.md` files (flag URLs to non-allowlisted domains, instructions to read sensitive files, Bash usage in critic agents).
- **Copy-on-install instead of live symlinks** — not applicable to this repo (manifest-based, not symlink-based), but relevant for zivtech-meta-skills.
- **Per-skill scan allowlist** — security-focused skills (drupal-security, drupal-expert) legitimately mention `eval()` and `<script>` as anti-patterns. A per-skill allowlist would reduce noise.

See also: react-critic has the same architecture and needs the same fixes ported.

## Working With This Repo

- The `research/` directory contains analysis reports and upstream clones — it is `.gitignore`d except for `reports/`.
- When adding a new external skill reference, add it to the manifest YAML and ensure it is referenced in the routing map and/or rubric docs. Run both validation scripts before committing.
- The agent at `.claude/agents/drupal-critic.md` is intentionally read-only. Do not add Write or Edit to its allowed tools.
