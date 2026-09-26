#!/usr/bin/env python3
"""Refresh pinned commits in external skills manifest.

Supply chain safety features:
- Compare URLs for every changed pin (review what changed upstream)
- Content scanning for prompt injection patterns in fetched SKILL.md files
- Scan warnings surfaced in report and on stdout
- Content hashes (SHA-256) stored in manifest for integrity verification (Tier 2)
- Audit log of all pin changes with timestamps (Tier 2)
"""
import argparse
import hashlib
import re
import ssl
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except Exception as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required. Install with: pip install pyyaml") from exc

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / '.claude/skills/drupal-critic/references/external-skills-manifest.yaml'
REPORT = ROOT / 'research/drupal-skills/reports/external-skills-refresh-report.md'
AUDIT_LOG = ROOT / 'research/drupal-skills/reports/refresh-audit.log'

# Patterns that should never appear in a legitimate skill file.
# Each tuple: (compiled regex, human-readable description)
SUSPICIOUS_PATTERNS = [
    (re.compile(r'ignore\s+(previous|all|above|prior|these)\s+(instructions|prompts|rules|guidelines)', re.I),
     'prompt override attempt'),
    (re.compile(r'you\s+are\s+now\s+(a|an|in)\b', re.I),
     'identity reassignment'),
    (re.compile(r'new\s+instructions?\s*:', re.I),
     'instruction injection marker'),
    (re.compile(r'<\s*system\s*>', re.I),
     'fake system tag'),
    (re.compile(r'(?:base64[_.]?(?:encode|decode)|atob|btoa)\s*\(', re.I),
     'base64 encode/decode call'),
    (re.compile(r'(?:^|[^a-zA-Z])eval\s*\(', re.I),
     'eval() call'),
    (re.compile(r'AAAA[A-Za-z0-9+/]{40,}={0,2}', re.I),
     'possible base64 payload'),
    (re.compile(r'\\x[0-9a-fA-F]{2}(?:\\x[0-9a-fA-F]{2}){3,}'),
     'hex-encoded string'),
    (re.compile(r'do\s+not\s+(?:mention|reveal|disclose|share)\s+(?:this|these|the)\s+(?:instructions|rules|prompt)', re.I),
     'instruction hiding directive'),
    (re.compile(r'<\s*/?(?:script|iframe|object|embed)\b', re.I),
     'HTML injection tag'),
]


class FetchError(RuntimeError):
    """A fetch failed for a reason other than the file not existing."""


def build_ssl_context() -> ssl.SSLContext:
    """Return an SSL context, preferring certifi's CA bundle when installed.

    python.org macOS builds have no CA bundle until 'Install Certificates.command'
    is run, so every HTTPS fetch fails verification. certifi covers that case.
    """
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def get_head_sha(repo_url: str) -> str:
    url = repo_url + '.git' if not repo_url.endswith('.git') else repo_url
    out = subprocess.check_output(['git', 'ls-remote', url, 'HEAD'], text=True)
    return out.split()[0]


def compare_url(repo_url: str, old_sha: str, new_sha: str) -> str:
    """Return a GitHub compare URL for reviewing changes between two commits."""
    owner_repo = repo_url.replace('https://github.com/', '')
    return f"https://github.com/{owner_repo}/compare/{old_sha[:12]}...{new_sha[:12]}"


def fetch_skill_content(repo_url: str, commit: str, skill_id: str) -> str | None:
    """Fetch SKILL.md content at a specific commit, trying common paths."""
    owner_repo = repo_url.replace('https://github.com/', '')
    skill_name = skill_id.split('/')[-1]
    paths = [
        f'.claude/skills/{skill_name}/SKILL.md',
        f'{skill_name}/SKILL.md',
        'SKILL.md',
        f'skills/{skill_name}/SKILL.md',
        f'skills/drupal/{skill_name}/SKILL.md',
        f'skills/drupal/cache/{skill_name}/SKILL.md',
    ]
    context = build_ssl_context()
    for path in paths:
        url = f'https://raw.githubusercontent.com/{owner_repo}/{commit}/{path}'
        try:
            resp = urllib.request.urlopen(url, timeout=15, context=context)
            return resp.read().decode('utf-8', errors='replace')
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                continue
            raise FetchError(f'{url}: HTTP {exc.code}') from exc
        except urllib.error.URLError as exc:
            raise FetchError(f'{url}: {exc.reason}') from exc
    return None


def scan_content(text: str, skill_id: str) -> list[str]:
    """Scan skill content for suspicious prompt injection patterns."""
    warnings = []
    for pattern, description in SUSPICIOUS_PATTERNS:
        for m in pattern.finditer(text):
            line_num = text[:m.start()].count('\n') + 1
            snippet = m.group().strip()[:60]
            warnings.append(
                f"  {skill_id} line {line_num}: {description} — `{snippet}`"
            )
    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(description='Refresh pinned commits in external skills manifest.')
    parser.add_argument('--check', action='store_true',
                        help='Do not write manifest; fail if updates are needed.')
    parser.add_argument('--no-scan', action='store_true',
                        help='Skip content scanning of changed skills.')
    args = parser.parse_args()

    data = yaml.safe_load(MANIFEST.read_text(encoding='utf-8'))
    skills = data.get('skills', [])

    changed = []
    for s in skills:
        repo = s['repo_url']
        current = s.get('pinned_commit', '')
        latest = get_head_sha(repo)
        if latest != current:
            changed.append({'id': s['id'], 'repo_url': repo, 'old': current, 'new': latest})
            s['pinned_commit'] = latest

    # --- Content scanning and hash computation ---
    scan_warnings = []
    content_hashes = {}  # skill_id -> sha256 of SKILL.md at new commit
    if changed and not args.no_scan:
        print(f"Scanning {len(changed)} changed skills for suspicious content...")
        for entry in changed:
            try:
                content = fetch_skill_content(entry['repo_url'], entry['new'], entry['id'])
            except FetchError as exc:
                raise SystemExit(
                    f"Could not fetch {entry['id']} for scanning: {exc}\n"
                    "Network or TLS failure, not a missing file. On a python.org macOS "
                    "build, run 'pip install certifi' or the bundled "
                    "'Install Certificates.command'."
                ) from exc
            if content:
                warnings = scan_content(content, entry['id'])
                scan_warnings.extend(warnings)
                content_hashes[entry['id']] = hashlib.sha256(content.encode('utf-8')).hexdigest()
            else:
                scan_warnings.append(f"  {entry['id']}: could not fetch SKILL.md (unable to locate)")

    # --- Build report ---
    report_lines = [
        '# External Skill Refresh Report',
        '',
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        '',
        f"Checked skills: {len(skills)}",
        f"Changed pins: {len(changed)}",
        f"Scan warnings: {len(scan_warnings)}",
        '',
    ]

    if changed:
        report_lines.append('## Changed Pins')
        report_lines.append('')
        report_lines.append('| Skill | Old | New | Compare |')
        report_lines.append('|---|---|---|---|')
        for entry in changed:
            old_short = entry['old'][:12] if entry['old'] else '-'
            new_short = entry['new'][:12]
            cmp = compare_url(entry['repo_url'], entry['old'], entry['new']) if entry['old'] else '-'
            link = f"[diff]({cmp})" if cmp != '-' else '-'
            report_lines.append(f"| `{entry['id']}` | `{old_short}` | `{new_short}` | {link} |")
    else:
        report_lines.append('No pin changes detected.')

    if scan_warnings:
        report_lines.append('')
        report_lines.append('## Content Scan Warnings')
        report_lines.append('')
        report_lines.append('**Review these before committing updated pins.**')
        report_lines.append('')
        for w in scan_warnings:
            report_lines.append(f"- {w.strip()}")
    elif changed and not args.no_scan:
        report_lines.append('')
        report_lines.append('## Content Scan')
        report_lines.append('')
        report_lines.append('No suspicious patterns detected in changed skills.')

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text('\n'.join(report_lines) + '\n', encoding='utf-8')

    # --- Print warnings to stdout ---
    if scan_warnings:
        print(f"\n⚠ {len(scan_warnings)} content scan warning(s):")
        for w in scan_warnings:
            print(w)
        print(f"\nReview before committing: {REPORT}")

    if args.check:
        if changed:
            print(f"Manifest update required for {len(changed)} skills.")
            return 1
        print('Manifest pins are current.')
        return 0

    if scan_warnings:
        print(f"\nManifest NOT updated — {len(scan_warnings)} scan warning(s) found.")
        print("Review warnings, then re-run with --no-scan to force update.")
        return 2

    # --- Store content hashes in manifest entries ---
    for s in skills:
        if s['id'] in content_hashes:
            s['content_hash'] = content_hashes[s['id']]

    data['generated_at'] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    MANIFEST.write_text(yaml.safe_dump(data, sort_keys=False), encoding='utf-8')

    # --- Audit log (Tier 2) ---
    if changed:
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).isoformat()
        log_lines = []
        for entry in changed:
            h = content_hashes.get(entry['id'], 'not-computed')
            log_lines.append(
                f"{ts}  {entry['id']}  {entry['old'][:12] or 'initial'}..{entry['new'][:12]}"
                f"  content_hash={h[:16]}"
            )
        with open(AUDIT_LOG, 'a', encoding='utf-8') as f:
            f.write('\n'.join(log_lines) + '\n')
        print(f"Appended {len(changed)} entries to audit log: {AUDIT_LOG}")

    print(f"Updated manifest: {MANIFEST}")
    print(f"Wrote report: {REPORT}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
