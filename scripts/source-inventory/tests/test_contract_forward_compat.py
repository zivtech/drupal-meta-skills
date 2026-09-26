"""The contract's versioning promise, checked against the REAL schemas of
earlier versions (pinned byte-for-byte under
tests/fixtures/pinned-contract-schemas/<version>/), not a reconstruction.
Only source-structure.schema.json is pinned for 1.0.0 and 1.1.0: that is
the file whose closed objects cause the break, and dispositions.schema.json
did not change shape between 1.1.0 and 1.2.0.

- 1.0.0 and 1.1.0 closed their objects (additionalProperties: false), so a
  consumer that vendored one of them rejects 1.2.0 output. That is the
  documented break: those consumers must re-vendor.
- From 1.2.0 onward every object is open, so output from any later 1.x
  minor must validate against the pinned 1.2.0 copy. When a new minor
  ships, pin its schemas here too; the pinned 1.2.0 copy stays the
  baseline every later minor is checked against.
- The producer checks its own output against a closed copy of the current
  schema (assemble.strict_schema), so typos still fail.
"""
import json
import re
from pathlib import Path

import jsonschema
import pytest

from assemble import CONTRACT_DIR, strict_schema

PINNED_DIR = Path(__file__).parent / "fixtures" / "pinned-contract-schemas"
SCHEMA_NAMES = ("source-structure", "dispositions")
FIRST_OPEN_MINOR = "1.2.0"
VERSION = (CONTRACT_DIR / "VERSION").read_text(encoding="utf-8").strip()


def _v(version: str) -> tuple[int, ...]:
    return tuple(int(p) for p in version.split("."))


PINNED_VERSIONS = sorted((p.name for p in PINNED_DIR.iterdir() if p.is_dir()), key=_v)
CLOSED_VERSIONS = [v for v in PINNED_VERSIONS if _v(v) < _v(FIRST_OPEN_MINOR)]
OPEN_VERSIONS = [v for v in PINNED_VERSIONS if _v(v) >= _v(FIRST_OPEN_MINOR)]

# Properties each minor added to source-structure, as the key a closed older
# schema reports as unexpected. Extend when a minor adds a property.
ADDED_IN_MINOR = {
    "1.1.0": ["shared_by_multiple_hosts", "block_hosted_instances"],
    "1.2.0": ["unresolved_tables"],
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _pinned(version: str, name: str) -> dict:
    return _load(PINNED_DIR / version / f"{name}.schema.json")


def _current(name: str) -> dict:
    return _load(CONTRACT_DIR / f"{name}.schema.json")


def _fixture(name: str) -> dict:
    return _load(CONTRACT_DIR / "fixtures" / "valid" / f"{name}.json")


def _errors(schema: dict, instance: dict) -> list[str]:
    validator = jsonschema.validators.validator_for(schema)(schema)
    return [f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in validator.iter_errors(instance)]


def test_pins_cover_the_closed_history_and_the_open_baseline():
    assert CLOSED_VERSIONS == ["1.0.0", "1.1.0"]
    assert FIRST_OPEN_MINOR in OPEN_VERSIONS
    for version in CLOSED_VERSIONS:
        assert (PINNED_DIR / version / "source-structure.schema.json").is_file()
    for version in OPEN_VERSIONS:
        for name in SCHEMA_NAMES:
            assert (PINNED_DIR / version / f"{name}.schema.json").is_file()


def test_current_version_is_pinned():
    # A new minor must pin its own schemas so the next one is checked against it.
    major, minor, _patch = VERSION.split(".")
    assert any(v.startswith(f"{major}.{minor}.") for v in PINNED_VERSIONS), (
        f"pin contracts/source-structure/*.schema.json for {VERSION} under {PINNED_DIR.name}/"
    )


def _strip_descriptions(node):
    if isinstance(node, dict):
        return {k: _strip_descriptions(v) for k, v in node.items() if k != "description"}
    if isinstance(node, list):
        return [_strip_descriptions(v) for v in node]
    return node


@pytest.mark.parametrize("name", SCHEMA_NAMES)
def test_published_schema_shape_matches_the_pin_for_its_minor(name):
    # Within one minor only documentation may change (patch rule): any shape
    # change must come with a new minor (and a new pin).
    major, minor, _patch = VERSION.split(".")
    pin = max((v for v in PINNED_VERSIONS if v.startswith(f"{major}.{minor}.")), key=_v)
    assert _strip_descriptions(_current(name)) == _strip_descriptions(_pinned(pin, name))


@pytest.mark.parametrize("version", CLOSED_VERSIONS)
def test_closed_pre_1_2_schema_rejects_current_output_exactly_on_later_additions(version):
    # The documented break: a consumer that vendored 1.0.0 or 1.1.0 cannot
    # read 1.2.0 output and must re-vendor. It fails only on keys added after
    # its own version, which is what re-vendoring fixes.
    errors = _errors(_pinned(version, "source-structure"), _fixture("source-structure"))
    added_later = {k for v, keys in ADDED_IN_MINOR.items() if _v(v) > _v(version) for k in keys}
    assert errors
    unexpected = {k for e in errors for k in re.findall(r"'([^']+)'", e.split(": ", 1)[1])}
    assert unexpected == added_later, errors


@pytest.mark.parametrize("version", OPEN_VERSIONS)
@pytest.mark.parametrize("name", SCHEMA_NAMES)
def test_current_output_validates_against_every_pinned_open_schema(version, name):
    assert _errors(_pinned(version, name), _fixture(name)) == []


def _resolve(root: dict, schema_node: dict) -> dict:
    while "$ref" in schema_node:
        target = root
        for key in schema_node["$ref"].lstrip("#/").split("/"):
            target = target[key]
        schema_node = target
    return schema_node


def _inject_everywhere(root, node, schema_node, key="added_in_a_future_minor"):
    """Adds an unknown key to every instance object whose schema declares
    `properties` (a record, not a free-form map), recursively."""
    schema_node = _resolve(root, schema_node)
    if isinstance(node, list):
        return [_inject_everywhere(root, v, schema_node.get("items", {}), key) for v in node]
    if not isinstance(node, dict):
        return node
    props = schema_node.get("properties")
    if props is None:
        extra = schema_node.get("additionalProperties")
        sub = extra if isinstance(extra, dict) else {}
        return {k: _inject_everywhere(root, v, sub, key) for k, v in node.items()}
    out = {k: _inject_everywhere(root, v, props.get(k, {}), key) for k, v in node.items()}
    out[key] = 1
    return out


@pytest.mark.parametrize("version", OPEN_VERSIONS)
@pytest.mark.parametrize("name", SCHEMA_NAMES)
def test_output_carrying_future_minor_keys_validates_against_pinned_open_schema(version, name):
    pinned = _pinned(version, name)
    future = _inject_everywhere(pinned, _fixture(name), pinned)
    assert json.dumps(future).count("added_in_a_future_minor") > 3  # not vacuous
    assert _errors(pinned, future) == []
    assert _errors(strict_schema(pinned), future)  # a closed schema would reject it


def test_future_keys_reach_every_record_in_source_structure():
    pinned = _pinned(FIRST_OPEN_MINOR, "source-structure")
    future = _inject_everywhere(pinned, _fixture("source-structure"), pinned)
    assert json.dumps(future).count("added_in_a_future_minor") > 20


def test_fixture_exercises_every_added_key():
    doc = _fixture("source-structure")
    present = {k for c in doc["components"] for k in (c.get("usage") or {})} | set(doc.get("data_quality", {}))
    for keys in ADDED_IN_MINOR.values():
        for key in keys:
            assert key in present, f"fixture does not exercise {key}; the break test would be vacuous"


def test_producer_strict_schema_still_rejects_an_unknown_key():
    doc = _fixture("source-structure")
    doc["components"][0]["fields"][0]["fill_rate_pctt"] = 1.0  # a typo
    current = _current("source-structure")
    assert _errors(current, doc) == []  # the open, published schema accepts it...
    errors = _errors(strict_schema(current), doc)  # ...the producer's closed copy does not
    assert any("fill_rate_pctt" in e for e in errors), errors


def _enum_names(node, path=()):
    """Documented name of every enum: the property name when the enum sits on
    a property, else the definition name in snake_case (roleSource ->
    role_source)."""
    if isinstance(node, dict):
        if "enum" in node:
            if len(path) >= 2 and path[-2] == "properties":
                yield path[-1]
            else:
                yield re.sub(r"(?<!^)(?=[A-Z])", "_", path[-1]).lower()
        for k, v in node.items():
            yield from _enum_names(v, (*path, k))
    elif isinstance(node, list):
        for v in node:
            yield from _enum_names(v, path)


def test_versioning_rule_lists_every_enum_in_both_schemas():
    names = {n for name in SCHEMA_NAMES for n in _enum_names(_current(name))}
    assert names == {"kind", "verdict", "role", "role_source", "render_source", "signal_type"}
    readme = (CONTRACT_DIR / "README.md").read_text(encoding="utf-8")
    changelog = (CONTRACT_DIR / "CHANGELOG.md").read_text(encoding="utf-8")
    rule_readme = readme[readme.index("**Major = anything"):readme.index("**Patch**")]
    rule_changelog = changelog[changelog.index("**Major = anything"):changelog.index("- Consumers vendor")]
    for n in names:
        assert f"`{n}`" in rule_readme or f".{n}`" in rule_readme, n
        assert f"`{n}`" in rule_changelog or f".{n}`" in rule_changelog, n
