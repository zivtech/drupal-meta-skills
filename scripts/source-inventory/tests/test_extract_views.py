from extract_views import build_view_listing_components


def test_build_view_listing_components(config_dir):
    components = build_view_listing_components(config_dir)
    ids = {c["id"] for c in components}
    assert "session_calendar" in ids
    for c in components:
        assert c["kind"] == "view_listing"
