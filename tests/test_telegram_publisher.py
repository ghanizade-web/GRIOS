from __future__ import annotations

import json
import urllib.error

import pytest

import telegram_publisher as publisher


def test_chunk_message_preserves_lines_and_respects_limit():
    chunks = publisher.chunk_message("alpha\nbeta\ngamma", limit=8)
    assert chunks == ["alpha", "beta", "gamma"]
    assert all(len(chunk) <= 8 for chunk in chunks)


def test_chunk_message_splits_long_lines():
    assert publisher.chunk_message("abcdefghij", limit=4) == ["abcd", "efgh", "ij"]


def test_chunk_message_rejects_empty_text():
    with pytest.raises(ValueError):
        publisher.chunk_message("  ")


def test_send_uses_chat_and_plain_text(monkeypatch):
    seen = {}

    class Response:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return b'{"ok": true}'

    def fake_urlopen(request, timeout):
        seen["payload"] = json.loads(request.data.decode("utf-8"))
        seen["timeout"] = timeout
        return Response()

    monkeypatch.setattr(publisher.urllib.request, "urlopen", fake_urlopen)
    publisher._send("dummy", "@grios", "daily report")
    assert seen["payload"]["chat_id"] == "@grios"
    assert seen["payload"]["text"] == "daily report"
    assert seen["timeout"] == 20


def test_send_retries_rate_limit(monkeypatch):
    calls = {"count": 0}
    sleeps = []

    class Response:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return b'{"ok": true}'

    def fake_urlopen(request, timeout):
        calls["count"] += 1
        if calls["count"] == 1:
            raise urllib.error.HTTPError(
                request.full_url, 429, "Too Many Requests", {},
                __import__("io").BytesIO(b'{"parameters":{"retry_after":2}}'),
            )
        return Response()

    monkeypatch.setattr(publisher.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(publisher.time, "sleep", sleeps.append)
    publisher._send("dummy", "@grios", "report")
    assert calls["count"] == 2
    assert sleeps == [2]


def test_send_does_not_retry_client_error(monkeypatch):
    calls = {"count": 0}

    def fake_urlopen(request, timeout):
        calls["count"] += 1
        raise urllib.error.HTTPError(request.full_url, 400, "Bad Request", {}, None)

    monkeypatch.setattr(publisher.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(RuntimeError, match="TELEGRAM_HTTP_400"):
        publisher._send("dummy", "@grios", "report")
    assert calls["count"] == 1
