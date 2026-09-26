# External Skill Refresh Report

Refreshed: 2026-09-26 (manual review, then `refresh_external_skills.py --no-scan`)

Checked skills: 24
Changed pins: 20
Scan warnings: 5 (all reviewed, all false positives)

## Changed Pins

The compare links cover whole repos. Review was scoped to each referenced
skill's directory (SKILL.md plus references/) between the old and new pin.

| Skill | Old | New | Compare | Skill content |
|---|---|---|---|---|
| `madsnorgaard/agent-resources/drupal-expert` | `776e73407d08` | `8bdcb0f304fe` | [diff](https://github.com/madsnorgaard/agent-resources/compare/776e73407d08...8bdcb0f304fe) | reviewed, see notes |
| `madsnorgaard/agent-resources/drupal-security` | `776e73407d08` | `8bdcb0f304fe` | [diff](https://github.com/madsnorgaard/agent-resources/compare/776e73407d08...8bdcb0f304fe) | skill files unchanged |
| `mindrally/skills/drupal-development` | `47f47c12e62f` | `97184105b5da` | [diff](https://github.com/mindrally/skills/compare/47f47c12e62f...97184105b5da) | skill files unchanged |
| `kanopi/cms-cultivator/drupalorg-issue-helper` | `e2e8783a3158` | `b11091b58d8e` | [diff](https://github.com/kanopi/cms-cultivator/compare/e2e8783a3158...b11091b58d8e) | skill files unchanged |
| `kanopi/cms-cultivator/drupalorg-contribution-helper` | `e2e8783a3158` | `b11091b58d8e` | [diff](https://github.com/kanopi/cms-cultivator/compare/e2e8783a3158...b11091b58d8e) | skill files unchanged |
| `sparkfabrik/sf-awesome-copilot/drupal-cache-contexts` | `233c2e9f637e` | `0b17a929f3d2` | [diff](https://github.com/sparkfabrik/sf-awesome-copilot/compare/233c2e9f637e...0b17a929f3d2) | skill files unchanged |
| `sparkfabrik/sf-awesome-copilot/drupal-cache-tags` | `233c2e9f637e` | `0b17a929f3d2` | [diff](https://github.com/sparkfabrik/sf-awesome-copilot/compare/233c2e9f637e...0b17a929f3d2) | skill files unchanged |
| `sparkfabrik/sf-awesome-copilot/drupal-cache-maxage` | `233c2e9f637e` | `0b17a929f3d2` | [diff](https://github.com/sparkfabrik/sf-awesome-copilot/compare/233c2e9f637e...0b17a929f3d2) | skill files unchanged |
| `sparkfabrik/sf-awesome-copilot/drupal-dynamic-cache` | `233c2e9f637e` | `0b17a929f3d2` | [diff](https://github.com/sparkfabrik/sf-awesome-copilot/compare/233c2e9f637e...0b17a929f3d2) | skill files unchanged |
| `sparkfabrik/sf-awesome-copilot/drupal-cache-debugging` | `233c2e9f637e` | `0b17a929f3d2` | [diff](https://github.com/sparkfabrik/sf-awesome-copilot/compare/233c2e9f637e...0b17a929f3d2) | skill files unchanged |
| `sparkfabrik/sf-awesome-copilot/drupal-lazy-builders` | `233c2e9f637e` | `0b17a929f3d2` | [diff](https://github.com/sparkfabrik/sf-awesome-copilot/compare/233c2e9f637e...0b17a929f3d2) | skill files unchanged |
| `drupal-canvas/skills/canvas-component-definition` | `5547352118a6` | `ee67425e1ab2` | [diff](https://github.com/drupal-canvas/skills/compare/5547352118a6...ee67425e1ab2) | reviewed, see notes |
| `drupal-canvas/skills/canvas-component-metadata` | `5547352118a6` | `ee67425e1ab2` | [diff](https://github.com/drupal-canvas/skills/compare/5547352118a6...ee67425e1ab2) | reviewed, see notes |
| `drupal-canvas/skills/canvas-component-utils` | `5547352118a6` | `ee67425e1ab2` | [diff](https://github.com/drupal-canvas/skills/compare/5547352118a6...ee67425e1ab2) | reviewed, see notes |
| `drupal-canvas/skills/canvas-data-fetching` | `5547352118a6` | `ee67425e1ab2` | [diff](https://github.com/drupal-canvas/skills/compare/5547352118a6...ee67425e1ab2) | reviewed, see notes |
| `drupal-canvas/skills/canvas-styling-conventions` | `5547352118a6` | `ee67425e1ab2` | [diff](https://github.com/drupal-canvas/skills/compare/5547352118a6...ee67425e1ab2) | reviewed, see notes |
| `drupal-canvas/skills/canvas-component-composability` | `5547352118a6` | `ee67425e1ab2` | [diff](https://github.com/drupal-canvas/skills/compare/5547352118a6...ee67425e1ab2) | reviewed, see notes |
| `drupal-canvas/skills/canvas-component-push` | `5547352118a6` | `ee67425e1ab2` | [diff](https://github.com/drupal-canvas/skills/compare/5547352118a6...ee67425e1ab2) | reviewed, see notes |
| `grasmash/drupal-claude-skills/drupal-ddev` | `008bd15c66d6` | `eb9b3d371732` | [diff](https://github.com/grasmash/drupal-claude-skills/compare/008bd15c66d6...eb9b3d371732) | reviewed, see notes |
| `madsnorgaard/drupal-agent-resources/ddev-expert` | `776e73407d08` | `8bdcb0f304fe` | [diff](https://github.com/madsnorgaard/drupal-agent-resources/compare/776e73407d08...8bdcb0f304fe) | skill files unchanged |

## Content Scan Warnings (reviewed)

- `madsnorgaard/agent-resources/drupal-expert` line 286, eval(): a shell comment, `# Create via PHP eval (for scripts/automation)`, above a `drush php:eval` example.
- `madsnorgaard/agent-resources/drupal-security` line 158, eval(): a table row warning *against* `eval()`/`exec()`.
- `sparkfabrik/sf-awesome-copilot/drupal-dynamic-cache` lines 131 and 135, `<script>`: sample BigPipe output (`<script type="application/vnd.drupal-ajax">`) inside an html code fence.
- `madsnorgaard/drupal-agent-resources/ddev-expert` line 35, `<script`: `ddev php <script>`, where `<script` is a placeholder argument.

## Review Notes

- **drupal-expert**: 9 lines deleted (the legacy annotation-style plugin example). Benign.
- **drupal-canvas/skills** (7 skills, about 1,000 added lines, commits by the repo's maintainers):
  - `canvas-component-push` adds an activation guard: run only on an explicit user push/publish/sync request, never automatically after edits.
  - Auth discovery broadens to the shell env, `~/.canvasrc`, and `npx canvas login` tokens in `~/.config/drupal-canvas/oauth.json`.
  - A page-media flow uses `npx canvas push --yes --include-pages`, gated by that activation guard.
  - Other skills add Canvas Headless / portable React guidance.
  - `canvas-component-push` now links to a `canvas-headless` skill that this manifest does not reference.
- **grasmash/drupal-claude-skills/drupal-ddev** (770 added lines, repo owner's commit): database, snapshot and Solr reference docs. Destructive commands (`DROP DATABASE`, `TRUNCATE`) target the local DDEV container only. Solr credentials are the documented DDEV-Solr defaults.
  - Quality defect upstream: the sample `sanitize-db` script writes a truncated placeholder hash and claims all passwords become `admin`. It would instead lock users out. Treat it as bad advice, not as a threat.
- **All other changed pins**: the referenced skill directories are byte-identical between the old and new pin. The pin moved because other files in those repos changed.

`content_hash` is not recorded for this refresh: `--no-scan`, the documented
override after review, skips the fetch that computes it.
