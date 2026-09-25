from config_scan import config_glob, handler_settings_target_bundles, iter_config, load_yaml


def test_load_yaml_and_config_glob(config_dir):
    paths = config_glob(config_dir, "node.type.*.yml")
    assert len(paths) == 1
    data = load_yaml(paths[0])
    assert data["id"] == "program_page"


def test_iter_config_yields_path_and_data(config_dir):
    found = list(iter_config(config_dir, "block_content.type.*.yml"))
    assert len(found) == 1
    path, data = found[0]
    assert path.endswith("block_content.type.footer_social.yml")
    assert data["id"] == "footer_social"


def test_handler_settings_target_bundles_dict_shape():
    settings = {"handler_settings": {"target_bundles": {"a": "a", "b": "b"}}}
    assert handler_settings_target_bundles(settings) == ["a", "b"]


def test_handler_settings_target_bundles_list_shape():
    settings = {"handler_settings": {"target_bundles": ["a", "b"]}}
    assert handler_settings_target_bundles(settings) == ["a", "b"]


def test_handler_settings_target_bundles_missing():
    assert handler_settings_target_bundles({}) is None
    assert handler_settings_target_bundles(None) is None
