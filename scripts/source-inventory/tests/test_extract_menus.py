from extract_menus import build_menu_components, detect_menu_attachments, parse_menu_configs


def test_parse_menu_configs(config_dir):
    menus = parse_menu_configs(config_dir)
    assert menus["main"]["label"] == "Main navigation"


def test_detect_menu_attachments_generic_substring_scan():
    # Generalizes a pilot-specific custom-module mechanism: a
    # menu link's serialized link__options blob happens to contain a
    # placement id. No module name is hardcoded anywhere in the detector.
    menu_links = [
        {"id": "link-1", "menu_name": "main",
         "link_options": 'a:1:{s:23:"project_attach_block";a:1:{s:4:"name";s:19:"footer_social_main";}}'},
        {"id": "link-2", "menu_name": "main", "link_options": 'a:0:{}'},
    ]
    attachments = detect_menu_attachments(menu_links, placement_ids=["footer_social_main", "custom_code_block"])
    assert attachments == [{"menu_link_id": "link-1", "menu_name": "main", "attached_placement_id": "footer_social_main"}]


def test_detect_menu_attachments_empty_when_no_match():
    menu_links = [{"id": "link-1", "menu_name": "main", "link_options": ""}]
    assert detect_menu_attachments(menu_links, placement_ids=["footer_social_main"]) == []


def test_build_menu_components_without_db_has_zero_counts(config_dir):
    menu_components, details, attachments = build_menu_components(config_dir, db=None, placement_ids=["footer_social_main"])
    assert menu_components == [{"id": "main", "kind": "menu", "label": "Main navigation"}]
    assert details[0]["link_count"] == 0
    assert attachments == []
