from extract_state import build_state_components, fetch_state_keys


class FakeDb:
    """Stand-in for site_profile.DbConfig, used only to prove fetch_state_keys
    never asks for a `value` column (see the SQL assertion below) --
    the KEYS ONLY rule is structural, not just documented."""


def test_fetch_state_keys_sql_never_selects_value(monkeypatch):
    captured_sql = {}

    def fake_fetch_rows(db, sql):
        captured_sql["sql"] = sql
        return [{"name": "system.maintenance_mode", "size_bytes": "1"}]

    import extract_state
    monkeypatch.setattr(extract_state, "fetch_rows", fake_fetch_rows)

    keys = fetch_state_keys(FakeDb(), collection="state")
    sql_lower = captured_sql["sql"].lower()
    assert "length(value)" in sql_lower  # size only
    assert "select value" not in sql_lower
    assert ", value" not in sql_lower  # never selected as a plain column alongside name
    assert keys[0]["key"] == "system.maintenance_mode"
    assert keys[0]["size_bytes"] == 1
    assert keys[0]["changed"] is None


def test_build_state_components_without_db_returns_empty():
    assert build_state_components(None) == ([], [])
