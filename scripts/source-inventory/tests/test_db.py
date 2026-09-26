import subprocess

from db import DbConfig, _parse_tsv, fetch_rows


def test_parse_tsv_header_and_rows():
    output = "id\tlabel\n1\tHero Banner\n2\tFAQ Row\n"
    rows = _parse_tsv(output)
    assert rows == [{"id": "1", "label": "Hero Banner"}, {"id": "2", "label": "FAQ Row"}]


def test_parse_tsv_empty_output():
    assert _parse_tsv("") == []


def test_parse_tsv_header_only_no_rows():
    assert _parse_tsv("id\tlabel\n") == []


def test_parse_tsv_sql_null_becomes_python_none():
    # mysql --batch (without --raw) prints SQL NULL as the two-character
    # escape sequence \N. It must become Python None, not the 4-character
    # string 'NULL' -- treating a real NULL as filled text would corrupt
    # fill-rate computation.
    rows = _parse_tsv("id\tval\n1\t\\N\n")
    assert rows[0]["val"] is None


def test_parse_tsv_unescapes_embedded_newline_and_tab():
    # The bug caught by the proof run: rich-text field values often
    # contain a literal newline. mysql's default --batch escaping encodes
    # it as the two characters backslash+n; this must decode back to a
    # real newline, and must NOT be mistaken for a row separator while
    # parsing (i.e. this whole string must parse as exactly one data row).
    output = "id\tval\n1\tline one\\nline two\\twith a tab\n2\tclean\n"
    rows = _parse_tsv(output)
    assert len(rows) == 2
    assert rows[0]["val"] == "line one\nline two\twith a tab"
    assert rows[1]["val"] == "clean"


def test_parse_tsv_unescapes_literal_backslash():
    rows = _parse_tsv("id\tval\n1\tC:\\\\path\n")
    assert rows[0]["val"] == "C:\\path"


def test_parse_tsv_bare_carriage_return_does_not_split_the_row():
    # Real bug hit against the proof-run source: this mysql client
    # escapes an embedded LF as the 2-char sequence \n but does NOT escape
    # a bare CR (0x0D), which shows up raw in rich-text field values with
    # CRLF line endings (e.g. pasted from Word). A bare CR must stay part
    # of the same logical row/cell, not be mistaken for a row separator.
    output = "entity_id\tval\n211\t</p>\r\\n|basic_html\n214\tclean\n"
    rows = _parse_tsv(output)
    assert len(rows) == 2
    assert rows[0]["entity_id"] == "211"
    assert rows[0]["val"] == "</p>\r\n|basic_html"
    assert rows[1]["entity_id"] == "214"


class _FakeCompletedProcess:
    def __init__(self):
        self.returncode = 0
        self.stdout = b"id\n1\n"
        self.stderr = b""


def test_fetch_rows_local_never_puts_password_in_argv(monkeypatch):
    # Security fix: the password must travel only via the MYSQL_PWD env var
    # of the subprocess, never as a `-p<password>` command-line token (argv
    # is visible to any other local user via `ps`/`/proc`).
    monkeypatch.setenv("DB_PASSWORD", "s3cr3t-password")
    monkeypatch.setattr("shutil.which", lambda _name: "/usr/bin/mysql")

    captured = {}

    def fake_run(cmd, capture_output, text, check, env):
        captured["cmd"] = cmd
        captured["env"] = env
        return _FakeCompletedProcess()

    monkeypatch.setattr(subprocess, "run", fake_run)

    db = DbConfig(database="fixture")
    fetch_rows(db, "SELECT 1;")

    argv_text = " ".join(captured["cmd"])
    assert "s3cr3t-password" not in argv_text
    assert not any(arg.startswith("-p") for arg in captured["cmd"])  # lowercase -p only; -P<port> is unrelated
    assert captured["env"]["MYSQL_PWD"] == "s3cr3t-password"


def test_fetch_rows_docker_forwards_password_by_env_name_only(monkeypatch):
    # The docker transport must not bake the password into `docker exec`'s
    # own argv either: `-e MYSQL_PWD` (name only) tells docker to forward
    # the CURRENT value from this process's own environment.
    monkeypatch.setenv("DB_PASSWORD", "s3cr3t-password")

    captured = {}

    def fake_run(cmd, capture_output, text, check, env):
        captured["cmd"] = cmd
        captured["env"] = env
        return _FakeCompletedProcess()

    monkeypatch.setattr(subprocess, "run", fake_run)

    db = DbConfig(database="fixture", docker_container="fixture-src-db")
    fetch_rows(db, "SELECT 1;")

    argv_text = " ".join(captured["cmd"])
    assert "s3cr3t-password" not in argv_text
    assert "-e" in captured["cmd"]
    assert captured["cmd"][captured["cmd"].index("-e") + 1] == "MYSQL_PWD"
    assert captured["env"]["MYSQL_PWD"] == "s3cr3t-password"
