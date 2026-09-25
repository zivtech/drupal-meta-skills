"""PII rules shared by every extractor that could ever see field values.

Defaults matter more than options here: an early raw field-samples pass in
the pilot run held a large number of emails and phone numbers because
samples were on by default and the only defense was a field-*name*
heuristic (`looks_personal`), which does not catch an email typed into a
free-text "notes" field. The rules this module enforces:

1. Samples are OFF by default (samples_enabled=False in the profile). This
   module doesn't enforce that switch itself (the CLI does) — it enforces
   what happens to a value if sampling *is* on.
2. Even with samples on, every value is regex-scrubbed for emails and phone
   numbers BEFORE it is considered for a sample, regardless of field name.
   A field-name hint (`looks_personal`) is a SEPARATE, stronger check that
   suppresses the field's samples entirely — it does not replace scrubbing.
3. A table denylist (users_field_data, webform_submission*, sessions,
   watchdog, etc., extendable per-profile) is checked before a table is
   ever queried for sample values, independent of #1/#2.
4. Samples are truncated to a configurable length (default 80 chars) after
   scrubbing.
"""
from __future__ import annotations

import fnmatch
import re

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"\b(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

REDACTION = "[redacted]"

PERSONAL_NAME_HINTS = (
    "email", "phone", "ssn", "social_security", "contact_name", "donor",
    "member_name", "applicant", "address", "birthdate", "dob",
)


def scrub_value(value: str) -> str:
    """Regex-scrub emails/phones/SSNs out of a single value. Always runs,
    regardless of field name — this is the content-level check, not the
    name-based one."""
    if not value:
        return value
    value = EMAIL_RE.sub(REDACTION, value)
    value = PHONE_RE.sub(REDACTION, value)
    value = SSN_RE.sub(REDACTION, value)
    return value


def contains_pii(value: str) -> bool:
    if not value:
        return False
    return bool(EMAIL_RE.search(value) or PHONE_RE.search(value) or SSN_RE.search(value))


def looks_personal(field_name: str, sample_values: list[str]) -> bool:
    """Field-name heuristic PLUS a content check across the given samples.
    This is the stronger, field-level suppression: if True, the field's
    samples are omitted entirely rather than merely scrubbed.
    """
    name_l = (field_name or "").lower()
    if any(hint in name_l for hint in PERSONAL_NAME_HINTS):
        return True
    return any(contains_pii(v) for v in sample_values[:50])


def truncate(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    return value[:max_len] + "…"


def prepare_sample(value: str, max_len: int) -> str:
    """The one function extractors should call before a value is allowed
    into a sample_values[] list: scrub, then truncate."""
    return truncate(scrub_value(value), max_len)


def table_is_denylisted(table: str, denylist_patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(table, pattern) for pattern in denylist_patterns)


def assert_no_pii(*texts: str) -> list[str]:
    """Used by tests (and can be used by CI) to assert a batch of output
    text contains no unscrubbed email/phone/SSN. Returns the list of
    matches found (empty = clean)."""
    findings: list[str] = []
    for text in texts:
        if not text:
            continue
        findings.extend(EMAIL_RE.findall(text))
        findings.extend(m.group(0) for m in PHONE_RE.finditer(text))
        findings.extend(SSN_RE.findall(text))
    return findings
