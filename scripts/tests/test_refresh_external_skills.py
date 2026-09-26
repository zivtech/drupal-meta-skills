"""Tests for network handling in refresh_external_skills.py."""
import importlib.util
import io
import ssl
import sys
import urllib.error
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / 'refresh_external_skills.py'
spec = importlib.util.spec_from_file_location('refresh_external_skills', SCRIPT)
refresh = importlib.util.module_from_spec(spec)
sys.modules['refresh_external_skills'] = refresh
spec.loader.exec_module(refresh)

REPO = 'https://github.com/example/skills'
SHA = 'a' * 40


def _http_error(url, code):
    return urllib.error.HTTPError(url, code, 'err', {}, io.BytesIO())


def test_404_falls_through_to_next_candidate_path(monkeypatch):
    requested = []

    def fake_urlopen(url, timeout, context):
        requested.append(url)
        if url.endswith('/skills/drupal/my-skill/SKILL.md'):
            return io.BytesIO(b'# body')
        raise _http_error(url, 404)

    monkeypatch.setattr(refresh.urllib.request, 'urlopen', fake_urlopen)
    assert refresh.fetch_skill_content(REPO, SHA, 'example/skills/my-skill') == '# body'
    assert len(requested) > 1


def test_all_404_returns_none(monkeypatch):
    def fake_urlopen(url, timeout, context):
        raise _http_error(url, 404)

    monkeypatch.setattr(refresh.urllib.request, 'urlopen', fake_urlopen)
    assert refresh.fetch_skill_content(REPO, SHA, 'example/skills/my-skill') is None


def test_tls_failure_raises_fetch_error_instead_of_not_found(monkeypatch):
    def fake_urlopen(url, timeout, context):
        raise urllib.error.URLError(ssl.SSLCertVerificationError('certificate verify failed'))

    monkeypatch.setattr(refresh.urllib.request, 'urlopen', fake_urlopen)
    with pytest.raises(refresh.FetchError, match='certificate verify failed'):
        refresh.fetch_skill_content(REPO, SHA, 'example/skills/my-skill')


def test_non_404_http_error_raises_fetch_error(monkeypatch):
    def fake_urlopen(url, timeout, context):
        raise _http_error(url, 429)

    monkeypatch.setattr(refresh.urllib.request, 'urlopen', fake_urlopen)
    with pytest.raises(refresh.FetchError, match='429'):
        refresh.fetch_skill_content(REPO, SHA, 'example/skills/my-skill')


def test_ssl_context_uses_certifi_bundle_when_available(monkeypatch):
    certifi = pytest.importorskip('certifi')
    seen = {}
    real = ssl.create_default_context

    def spy(*args, **kwargs):
        seen.update(kwargs)
        return real(*args, **kwargs)

    monkeypatch.setattr(refresh.ssl, 'create_default_context', spy)
    refresh.build_ssl_context()
    assert seen.get('cafile') == certifi.where()


def test_ssl_context_falls_back_without_certifi(monkeypatch):
    monkeypatch.setitem(sys.modules, 'certifi', None)
    assert isinstance(refresh.build_ssl_context(), ssl.SSLContext)
