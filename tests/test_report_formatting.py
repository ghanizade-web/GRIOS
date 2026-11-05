from cftc_cot import render_persian_report as render_cftc
from eia_petroleum_stocks import build_persian_report as render_eia
from fred_release_calendar import render_persian_report as render_fred
from report_formatting import social_footer_lines
from scanner import persian_score_reason
from scripts.ingest_sec_13f_watchlist import render_persian_watchlist_summary


def test_social_footer_contains_all_project_channels():
    footer = "\\n".join(social_footer_lines())
    for link in (
        "https://t.me/drghanizade",
        "https://www.instagram.com/dr.ghanizade",
        "https://x.com/DrGhanizadeh",
        "https://www.linkedin.com/in/drghanizade",
        "https://farcaster.xyz/drghanizade",
        "https://github.com/ghanizade-web",
        "https://www.tradingview.com/u/DrGhanizadeh",
    ):
        assert link in footer


def test_daily_score_explanations_are_persian():
    assert "زمینه‌سازی" in persian_score_reason("Context/reference series; not independently tradable.")
    assert "بازده ۲۰ دوره‌ای" in persian_score_reason("20-period return 12.5%; technical heuristic only.")
    assert "توضیح فنی امتیاز" in persian_score_reason("unrecognized English explanation")


def test_all_human_report_families_append_social_footer():
    cftc = render_cftc({
        "retrieved_at": "2026-11-05T00:00:00+00:00",
        "publish": {"status": "SKIPPED", "accepted": 0},
        "contracts": [],
    })
    fred = render_fred({
        "status": "NO_UPCOMING_EVENTS",
        "calendar_start": "2026-11-05",
        "calendar_end": "2026-11-19",
        "event_count": 0,
        "events": [],
    })
    eia = render_eia([], generated_at="2026-11-05T00:00:00+00:00")
    sec = render_persian_watchlist_summary({
        "report_period": "2026-09-30",
        "status": "SUCCESS",
        "filers_total": 0,
        "filers_published": 0,
        "filers_failed": 0,
        "filers_skipped": 0,
        "results": [],
    })
    for report in (cftc, fred, eia, sec):
        assert "Farcaster: https://farcaster.xyz/drghanizade" in report
        assert "GitHub: https://github.com/ghanizade-web" in report
