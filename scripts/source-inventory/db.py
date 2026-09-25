"""Read-only DB access for drupal-source-inventory.

Two transports, both selected by the profile (never hardcoded):

- `docker_container` set -> `timeout <n> docker exec <container> mysql ...`
- otherwise -> a local `mysql` client using env vars named by the profile
  (`db.host_env`, `db.user_env`, etc.)

Every call is wrapped in `timeout` per the repo rule ("wrap docker calls in
timeout"). All queries this module issues are read-only (SELECT/SHOW); nothing
here ever writes to the source DB.

Unit tests do NOT exercise this module's subprocess path. They call the pure
"compute" functions in the extract_* modules directly with rows built from an
in-memory sqlite3 connection (see tests/conftest.py), so the DB *mechanism*
(docker vs local client) is decoupled from the logic under test.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass

from site_profile import DbConfig


class DbError(RuntimeError):
    pass


@dataclass
class QueryResult:
    rows: list[dict]

    def __iter__(self):
        return iter(self.rows)

    def __len__(self):
        return len(self.rows)


_MYSQL_ESCAPE_MAP = {"t": "\t", "n": "\n", "r": "\r", "0": "\0", "Z": "\x1a", "\\": "\\", "'": "'", '"': '"'}


def _unescape_mysql_cell(value: str) -> str | None:
    """Reverse mysql --batch's default escaping of tab/newline/backslash/NUL
    within a cell value. Returns None for SQL NULL (`\\N`).

    This matters more than it looks: an earlier version of this function
    ran mysql with --raw (no escaping) and split naively on tab/newline,
    which silently corrupted every multi-line rich-text field value (a
    literal newline inside a paragraph's body HTML was indistinguishable
    from a row separator) — caught during a proof run against a real
    source with rich text content, not by any fixture, because none of the
    hand-built fixtures happened to contain an embedded newline.
    """
    if value == "\\N":
        return None
    if "\\" not in value:
        return value
    out: list[str] = []
    i = 0
    while i < len(value):
        c = value[i]
        if c == "\\" and i + 1 < len(value):
            out.append(_MYSQL_ESCAPE_MAP.get(value[i + 1], value[i + 1]))
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _parse_tsv(output: str) -> list[dict]:
    """Parse `mysql --batch` TSV output (first row = column names) into
    dicts, unescaping each cell. SQL NULL becomes Python None (so
    `row.get('val') or ''` treats it as empty, matching fill-rate
    semantics — a real NULL is not "filled" content).

    Deliberately NOT the `csv` module: mysql escapes an embedded LF/TAB in
    data as a 2-char `\\n`/`\\t` sequence, so splitting the raw output on
    literal LF (rows) and literal TAB (columns) is unambiguous -- real
    row/column separators are always literal, embedded ones are always
    escaped. The `csv` module's own embedded-newline safety check rejects
    a field containing a bare, unescaped CR (which this mysql client does
    NOT escape -- see _run's docstring), even though that CR is not a row
    separator at all; splitting by hand sidesteps that false positive.
    """
    lines = output.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if not lines:
        return []
    header = lines[0].split("\t")
    return [
        {k: _unescape_mysql_cell(v) for k, v in zip(header, line.split("\t"))}
        for line in lines[1:]
        if line != ""
    ]


def _run(cmd: list[str], timeout_seconds: int, password: str | None = None) -> str:
    # Deliberately capture BYTES (text=False) and decode by hand, not
    # subprocess's text=True: text=True enables universal-newline
    # translation, which silently rewrites a lone \r byte to \n. This
    # mysql client escapes an embedded \n in data as the 2-char sequence
    # \n but does NOT escape a lone \r -- common in rich-text field values
    # with copy-pasted CRLF line endings -- so text=True's translation
    # turned that raw \r into a spurious row break, corrupting every field
    # value that happened to contain one. Caught by the proof run,
    # not by any fixture (none of the hand-built fixtures had a \r in them).
    wrapped = ["timeout", str(timeout_seconds), *cmd]
    # The DB password never goes on the command line (visible to any other
    # local user via `ps`/`/proc`): it travels only through the MYSQL_PWD
    # env var of this subprocess, never as a `-p<password>` argv token.
    env = {**os.environ, "MYSQL_PWD": password} if password is not None else None
    try:
        proc = subprocess.run(wrapped, capture_output=True, text=False, check=False, env=env)
    except FileNotFoundError as exc:
        raise DbError(f"command not found: {cmd[0]}") from exc
    if proc.returncode == 124:
        raise DbError(f"query timed out after {timeout_seconds}s: {' '.join(cmd[:3])}...")
    if proc.returncode != 0:
        stderr_text = proc.stderr.decode("utf-8", errors="replace")
        raise DbError(f"query failed (exit {proc.returncode}): {stderr_text.strip()[:500]}")
    return proc.stdout.decode("utf-8", errors="replace")


def fetch_rows(db: DbConfig, sql: str) -> list[dict]:
    """Run a read-only SQL statement and return rows as a list of dicts."""
    database = db.database_name()
    if not database:
        raise DbError("no database name: set db.database in the profile or db.database_env")

    # Deliberately NOT --raw: mysql's default --batch escaping is what makes
    # embedded tabs/newlines in real content (rich text fields routinely
    # contain literal newlines) distinguishable from column/row separators.
    # _parse_tsv/_unescape_mysql_cell reverse it. See _unescape_mysql_cell's
    # docstring for what --raw silently broke.
    #
    # The password is deliberately NEVER a `-p<password>` argv token (visible
    # to any other local user via `ps`/`/proc`): `_run` sets it as this
    # subprocess's MYSQL_PWD env var instead, which the local `mysql` client
    # reads on its own. For the docker transport, `-e MYSQL_PWD` (the bare
    # name, no `=value`) tells `docker exec` to forward that same env var's
    # CURRENT value from this process's own environment into the container
    # -- so the value never appears in the `docker` command's argv either.
    if db.docker_container:
        cmd = [
            "docker", "exec", "-e", "MYSQL_PWD", db.docker_container,
            "mysql", f"-u{db.user()}",
            "--batch", database, "-e", sql,
        ]
    else:
        if not shutil.which("mysql"):
            raise DbError(
                "no db.docker_container set and no local 'mysql' client found; "
                "set db.docker_container or install a mysql client"
            )
        cmd = [
            "mysql",
            f"-h{db.host()}", f"-P{db.port()}", f"-u{db.user()}",
            "--batch", database, "-e", sql,
        ]

    output = _run(cmd, db.timeout_seconds, password=db.password())
    return _parse_tsv(output)


def list_tables_like(db: DbConfig, pattern: str) -> list[str]:
    """pattern uses SQL LIKE syntax, e.g. 'node\\_\\_field\\_%'."""
    rows = fetch_rows(db, f"SHOW TABLES LIKE '{pattern}';")
    if not rows:
        return []
    key = next(iter(rows[0].keys()))
    return [r[key] for r in rows]


def table_exists(db: DbConfig, table: str) -> bool:
    escaped = table.replace("_", r"\_")
    return bool(list_tables_like(db, escaped))
