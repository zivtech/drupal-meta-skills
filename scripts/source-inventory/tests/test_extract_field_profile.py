import pytest

import pii
from site_profile import PiiConfig

from extract_field_profile import (
    build_field_union_sql,
    compute_duplication,
    compute_field_profile,
    value_columns,
)


def test_value_columns_excludes_key_columns():
    cols = ["bundle", "deleted", "entity_id", "revision_id", "langcode", "delta", "field_price_value"]
    assert value_columns(cols) == ["field_price_value"]


def test_build_field_union_sql_shape():
    sql = build_field_union_sql("paragraph", "faq_accordion_row", {"field_price": ["field_price_value"]})
    assert "SELECT 'field_price' AS fname" in sql
    assert "FROM `paragraph__field_price`" in sql
    assert "WHERE bundle='faq_accordion_row'" in sql


def test_build_field_union_sql_none_when_no_fields():
    assert build_field_union_sql("paragraph", "x", {}) is None


def test_compute_field_profile_fill_rate_and_no_samples_by_default():
    rows = [
        {"fname": "field_price", "entity_id": "1", "delta": 0, "val": "24.00"},
        {"fname": "field_price", "entity_id": "2", "delta": 0, "val": ""},
    ]
    profile = compute_field_profile(rows, total_instances=2, pii_config=PiiConfig(), samples_enabled=False)
    assert profile["field_price"]["fill_rate_pct"] == 50.0
    assert profile["field_price"]["non_empty_instances"] == 1
    assert profile["field_price"]["sample_values"] == []  # samples off by default


def test_compute_field_profile_scrubs_samples_even_without_name_hint():
    rows = [
        {"fname": "field_notes", "entity_id": "1", "delta": 0, "val": "reach staffer@example.org for details"},
    ]
    profile = compute_field_profile(rows, total_instances=1, pii_config=PiiConfig(), samples_enabled=True)
    assert profile["field_notes"]["sample_values"] == []  # looks_personal (content check) suppresses entirely
    assert profile["field_notes"]["personal_data_suspected"] is True


def test_compute_field_profile_samples_are_scrubbed_when_field_not_flagged_personal():
    rows = [
        {"fname": "field_description", "entity_id": "1", "delta": 0, "val": "Open daily, call 555-123-4567 for hours"},
    ]
    profile = compute_field_profile(rows, total_instances=1, pii_config=PiiConfig(), samples_enabled=True)
    # 'field_description' has no name hint, and content check catches the phone -> suppressed entirely, matching
    # the stronger looks_personal() rule. Verify no raw phone number ever appears.
    assert all("555-123-4567" not in s for s in profile["field_description"]["sample_values"])


def test_compute_field_profile_defense_in_depth_beyond_personal_check_window():
    # looks_personal() only content-checks the first 50 values (matching the
    # original script's window) as a fast field-level suppression check.
    # Unconditional per-value scrubbing (prepare_sample) is the second,
    # independent layer that still protects a PII value sitting past that
    # window, at value #55, which the field-level check alone would miss.
    rows = [{"fname": "field_staff_note", "entity_id": str(i), "delta": 0, "val": f"Staff note {i}, nothing sensitive here"}
            for i in range(50)]
    rows.append({"fname": "field_staff_note", "entity_id": "55", "delta": 0, "val": "reach me at hidden@example.org"})

    # Force the PII-bearing row to the front of sample selection (priority)
    # so this test actually exercises per-value scrubbing rather than the
    # value simply never being chosen among the top 3 samples.
    profile = compute_field_profile(
        rows, total_instances=51, pii_config=PiiConfig(), samples_enabled=True,
        priority_entity_ids={"55"},
    )
    assert profile["field_staff_note"]["personal_data_suspected"] is False  # the 50-value window alone misses it
    assert len(profile["field_staff_note"]["sample_values"]) == 3
    assert all("hidden@example.org" not in s for s in profile["field_staff_note"]["sample_values"])
    assert any(pii.REDACTION in s for s in profile["field_staff_note"]["sample_values"])


def test_compute_duplication_detects_identical_instances():
    rows = [
        {"fname": "field_a", "entity_id": "1", "delta": 0, "val": "X"},
        {"fname": "field_a", "entity_id": "2", "delta": 0, "val": "X"},
        {"fname": "field_a", "entity_id": "3", "delta": 0, "val": "Y"},
    ]
    dup = compute_duplication(rows)
    assert dup["instances_with_field_content"] == 3
    assert dup["instances_in_a_duplicate_group"] == 2
    assert dup["duplication_pct"] == pytest.approx(66.7, abs=0.1)
