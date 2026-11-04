from unittest.mock import Mock, call

import pandas as pd

import scanner


class FrameResult:
    def __init__(self, rows):
        self.frame = pd.DataFrame(rows)

    def to_dataframe(self):
        return self.frame


def test_fetch_energy_uses_eia_henry_hub_daily_spot_series():
    obb = Mock()
    obb.eia.data_browser.side_effect = [
        FrameResult([{"date": "2026-11-03", "value": 72.5}]),
        FrameResult([{"date": "2026-11-03", "value": 3.45}]),
    ]

    rows, errors = scanner.fetch_energy(obb, key_present=True)

    assert not errors
    assert [item.symbol for item in rows] == ["BRENT_SPOT", "HENRY_HUB_SPOT"]
    henry = rows[1]
    assert henry.provider == "OpenBB EIA"
    assert henry.observations[-1]["close"] == 3.45
    assert henry.observations[-1]["date"] == "2026-11-03"
    assert obb.eia.data_browser.call_args_list == [
        call(
            provider="eia",
            route="petroleum/pri/spt",
            frequency="daily",
            facets="product:EPCBRENT",
            data_type="value",
            limit=260,
        ),
        call(
            provider="eia",
            route="natural-gas/pri/fut",
            frequency="daily",
            facets="series:RNGWHHD",
            data_type="value",
            limit=260,
        ),
    ]


def test_fetch_energy_keeps_henry_hub_unavailable_when_eia_returns_no_data():
    obb = Mock()
    obb.eia.data_browser.side_effect = [
        FrameResult([{"date": "2026-11-03", "value": 72.5}]),
        FrameResult([]),
    ]

    rows, errors = scanner.fetch_energy(obb, key_present=True)

    assert [item.symbol for item in rows] == ["BRENT_SPOT"]
    assert any("Henry Hub spot" in error and "داده قابل استفاده نداد" in error for error in errors)


def test_fetch_energy_does_not_call_provider_without_eia_key():
    obb = Mock()

    rows, errors = scanner.fetch_energy(obb, key_present=False)

    assert rows == []
    assert errors == ["EIA_API_KEY تنظیم نشده است."]
    obb.eia.data_browser.assert_not_called()
