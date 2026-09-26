from extract_webforms import build_webform_components, parse_webform_configs


def test_parse_webform_configs_with_handler(config_dir):
    webforms = parse_webform_configs(config_dir)
    contact = webforms["contact_us"]
    assert contact["label"] == "Contact Us"
    assert contact["handlers"] == [{"id": "email_confirmation", "plugin": "email", "status": "enabled"}]


def test_build_webform_components_without_db(config_dir):
    components, details = build_webform_components(config_dir, db=None)
    assert components == [{"id": "contact_us", "kind": "webform", "label": "Contact Us"}]
    assert details[0]["submission_count"] is None
    assert details[0]["handlers"][0]["plugin"] == "email"
