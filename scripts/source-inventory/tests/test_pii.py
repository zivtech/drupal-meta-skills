import pii


def test_scrub_value_redacts_email_regardless_of_field_name():
    text = "Questions? Email us at info@example-parks.org anytime."
    scrubbed = pii.scrub_value(text)
    assert "info@example-parks.org" not in scrubbed
    assert pii.REDACTION in scrubbed


def test_scrub_value_redacts_phone():
    text = "Call the front desk at (202) 555-0142 for group rates."
    scrubbed = pii.scrub_value(text)
    assert "555-0142" not in scrubbed
    assert pii.REDACTION in scrubbed


def test_scrub_value_leaves_clean_text_untouched():
    text = "Swim lessons are free for residents."
    assert pii.scrub_value(text) == text


def test_looks_personal_by_field_name_hint():
    assert pii.looks_personal("field_donor_email", ["hello"]) is True
    # field_question has no name hint and no PII content:
    assert pii.looks_personal("field_question", ["What time do you open?"]) is False


def test_looks_personal_by_content_even_without_name_hint():
    # The bug the original pilot script had: a free-text field with no
    # personal-sounding name but an email embedded in a sample value.
    assert pii.looks_personal("field_notes", ["reach me at staffer@example.org"]) is True


def test_prepare_sample_scrubs_then_truncates():
    value = "x" * 100 + " call me at 555-123-4567"
    out = pii.prepare_sample(value, max_len=20)
    assert len(out) <= 21  # 20 chars + ellipsis
    assert "555-123-4567" not in out


def test_table_is_denylisted():
    denylist = ["users_field_data", "webform_submission*", "sessions"]
    assert pii.table_is_denylisted("users_field_data", denylist)
    assert pii.table_is_denylisted("webform_submission_data", denylist)
    assert not pii.table_is_denylisted("paragraphs_item_field_data", denylist)


def test_assert_no_pii_finds_leaks():
    findings = pii.assert_no_pii("contact info@example.org for help")
    assert findings == ["info@example.org"]


def test_assert_no_pii_clean():
    assert pii.assert_no_pii("Swim lessons are free for residents.") == []
