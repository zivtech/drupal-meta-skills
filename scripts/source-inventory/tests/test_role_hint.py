from role_hint import role_hint


def test_boolean_fact_vs_presentation_by_name_not_type():
    # Both are 'boolean' fields; the rubric says a boolean is FACT when it
    # changes meaning and PRESENTATION when it only changes rendering. The
    # heuristic can only see the type (always boolean -> PRESENTATION) --
    # this test locks in that the heuristic is name-blind for booleans
    # (documented as a heuristic limitation: a reviewer must override
    # field_residents_only to FACT; role_source stays 'heuristic' here).
    assert role_hint("field_residents_only", "boolean") == "PRESENTATION"
    assert role_hint("field_light_theme", "boolean") == "PRESENTATION"


def test_entity_reference_to_media_is_media():
    assert role_hint("field_hero_image", "entity_reference", target_entity_type="media") == "MEDIA"


def test_entity_reference_to_view_is_config():
    assert role_hint("field_listing_view", "entity_reference", target_entity_type="view") == "CONFIG"


def test_entity_reference_default_is_ref():
    assert role_hint("field_topic", "entity_reference", target_entity_type="taxonomy_term") == "REF"


def test_text_long_is_prose():
    assert role_hint("field_answer", "text_long") == "PROSE"


def test_string_with_fact_hint_is_fact():
    assert role_hint("field_price", "decimal") == "FACT"
    assert role_hint("field_fee_amount", "string") == "FACT"


def test_string_without_fact_hint_is_prose():
    assert role_hint("field_question", "string") == "PROSE"


def test_image_is_media():
    assert role_hint("field_image", "image") == "MEDIA"
