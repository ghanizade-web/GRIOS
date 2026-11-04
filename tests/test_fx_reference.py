from unittest.mock import Mock

import scanner


def test_fetch_fx_reference_preserves_safe_openbb_error_detail():
    obb = Mock()
    obb.ecb.exchange_rates.side_effect = RuntimeError(
        "Invalid symbol EURUSD; see https://example.test/path?api_key=SECRET"
    )

    rows, errors = scanner.fetch_fx_reference(obb, ["EURUSD"])

    assert rows == []
    assert len(errors) == 1
    assert "EURUSD: ECB unavailable (RuntimeError)" in errors[0]
    assert "Invalid symbol EURUSD" in errors[0]
    assert "[URL]" in errors[0]
    assert "SECRET" not in errors[0]


def test_sanitized_exception_message_redacts_credential_like_values():
    message = scanner.sanitized_exception_message(
        RuntimeError("token=abc123 authorization: BearerSecret")
    )

    assert "abc123" not in message
    assert "BearerSecret" not in message
    assert "[REDACTED]" in message


def test_sanitized_exception_message_is_bounded():
    message = scanner.sanitized_exception_message(RuntimeError("x" * 500))

    assert len(message) == 240
