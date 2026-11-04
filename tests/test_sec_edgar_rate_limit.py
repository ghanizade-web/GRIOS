import pytest

from sec_edgar_client import SecEdgarClient


def test_request_pacing_waits_to_respect_configured_interval(monkeypatch):
    clock = {"now": 100.0}
    sleeps = []

    def monotonic():
        return clock["now"]

    def sleep(seconds):
        sleeps.append(seconds)
        clock["now"] += seconds

    monkeypatch.setattr("sec_edgar_client.time.monotonic", monotonic)
    monkeypatch.setattr("sec_edgar_client.time.sleep", sleep)

    client = SecEdgarClient(
        user_agent="GRIOS Research research@example.org",
        min_request_interval=0.11,
    )
    client._pace_request()
    clock["now"] += 0.05
    client._pace_request()

    assert sleeps == pytest.approx([0.06])
    assert clock["now"] == pytest.approx(100.11)


def test_request_pacing_can_be_disabled_for_controlled_callers():
    client = SecEdgarClient(
        user_agent="GRIOS Research research@example.org",
        min_request_interval=0,
    )
    assert client.min_request_interval == 0


@pytest.mark.parametrize("value", [-0.01, float("inf"), float("nan"), True, "0.1"])
def test_request_pacing_rejects_invalid_intervals(value):
    with pytest.raises(ValueError, match="min_request_interval"):
        SecEdgarClient(
            user_agent="GRIOS Research research@example.org",
            min_request_interval=value,
        )
