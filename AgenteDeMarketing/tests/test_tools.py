import os
import re
import urllib

import pytest

from agente_ventas import tools


def test_get_cdp_candidates_default(monkeypatch):
    # Ensure environment does not provide a custom value
    monkeypatch.delenv("LIGHTPANDA_CDP_URL", raising=False)
    monkeypatch.delenv("LIGHTPANDA_CDP_URLS", raising=False)
    candidates = tools._get_cdp_candidates()
    assert isinstance(candidates, list)
    assert any("127.0.0.1" in c or "localhost" in c or "9222" in c for c in candidates)


def test_get_cdp_candidates_from_env(monkeypatch):
    monkeypatch.setenv("LIGHTPANDA_CDP_URL", "ws://a:9222, ws://b:9222")
    candidates = tools._get_cdp_candidates()
    assert candidates[0] == "ws://a:9222"
    assert "ws://b:9222" in candidates


def test_html_fallback_regex_parsing():
    html = '''
    <html>
      <body>
        <a href="/url?q=https://example.com/test&sa=U&ved=0"> <h3>Test Title</h3> </a>
        <div class="IsZvec">This is a snippet</div>
      </body>
    </html>
    '''

    pattern = re.compile(r'<a[^>]+href="/url\?q=([^"&]+)[^"]*"[^>]*>(.*?)</a>', re.S)
    matches = list(pattern.finditer(html))
    assert len(matches) == 1
    href = urllib.parse.unquote(matches[0].group(1))
    inner = matches[0].group(2)
    title_match = re.search(r'<h3[^>]*>(.*?)</h3>', inner, re.S)
    title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip() if title_match else re.sub(r'<[^>]+>', '', inner).strip()
    assert href == "https://example.com/test"
    assert title == "Test Title"
