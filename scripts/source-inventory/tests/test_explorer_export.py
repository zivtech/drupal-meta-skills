import json

from explorer_export import write_explorer_data


def test_write_explorer_data_shapes_by_kind(tmp_path):
    source_structure = {
        "components": [
            {"id": "hero_banner", "kind": "paragraph_type", "label": "Hero Banner"},
            {"id": "footer_social", "kind": "block_content_type", "label": "Footer Social"},
        ],
        "placements": [{"id": "footer_social_main", "theme": "t", "region": "footer", "status": True, "plugin": "p"}],
        "menus": [{"id": "main", "label": "Main", "link_count": 0}],
    }
    out_dir = write_explorer_data(source_structure, str(tmp_path))
    assert (out_dir / "paragraphs.json").exists()
    assert (out_dir / "blocks.json").exists()

    paragraphs = json.loads((out_dir / "paragraphs.json").read_text())
    assert "hero_banner" in paragraphs
    assert "footer_social" not in paragraphs

    blocks = json.loads((out_dir / "blocks.json").read_text())
    assert "footer_social" in blocks["block_content_types"]
    assert "footer_social_main" in blocks["placements"]
    assert "main" in blocks["menus"]
