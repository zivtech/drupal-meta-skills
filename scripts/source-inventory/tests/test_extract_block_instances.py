from extract_block_instances import build_block_instance_components


def test_build_block_instance_components_without_db_returns_empty():
    assert build_block_instance_components(None) == []


def test_build_block_instance_components_shape(monkeypatch):
    import extract_block_instances

    def fake_fetch_rows(db, sql):
        return [{"id": "footer_social_main", "info": "Footer Social (main)", "type": "footer_social"}]

    monkeypatch.setattr(extract_block_instances, "fetch_rows", fake_fetch_rows)
    components = build_block_instance_components(db=object())
    assert components == [{
        "id": "footer_social_main", "kind": "block_content", "label": "Footer Social (main)",
        "description": "bundle: footer_social",
    }]
