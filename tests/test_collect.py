"""Tests for the surprise standardisation, run entirely offline.

The network parts (Wikipedia universe, yfinance fetch) are not tested here on
purpose: a test that needs Yahoo to be up is a test that fails for reasons that
have nothing to do with the code. What is tested is the arithmetic that turns
raw announcements into SUEs, which is where a mistake would silently corrupt
every result downstream.
"""

import numpy as np
import pandas as pd
import pytest

from drift.collect import COLUMNS, describe, standardised_surprise


def make_events(ticker, estimates, reported, start="2020-01-15"):
    dates = pd.date_range(start, periods=len(estimates), freq="91D")
    return pd.DataFrame(
        {
            "ticker": ticker,
            "event_time": dates,
            "eps_estimate": estimates,
            "eps_reported": reported,
        }
    )


def test_empty_input_returns_empty_frame_with_schema():
    out = standardised_surprise(pd.DataFrame(columns=["ticker", "event_time"]))
    assert out.empty
    assert list(out.columns) == COLUMNS


def test_surprise_is_reported_minus_estimate():
    events = make_events("AAA", [1.0, 1.0, 1.0], [1.2, 0.8, 1.0])
    out = standardised_surprise(events)
    assert out["surprise"].tolist() == pytest.approx([0.2, -0.2, 0.0])


def test_sue_is_nan_until_enough_history():
    events = make_events("AAA", [1.0] * 6, [1.1, 0.9, 1.2, 0.8, 1.3, 0.7])
    out = standardised_surprise(events, min_history=4)
    # Four prior surprises are only available from the fifth announcement on.
    assert out["sue"].iloc[:4].isna().all()
    assert out["sue"].iloc[4:].notna().all()


def test_sue_uses_past_surprises_only():
    events = make_events("AAA", [1.0] * 5, [1.1, 0.9, 1.1, 0.9, 5.0])
    out = standardised_surprise(events, min_history=4)
    past = np.array([0.1, -0.1, 0.1, -0.1])
    expected = (5.0 - 1.0) / past.std(ddof=1)
    assert out["sue"].iloc[4] == pytest.approx(expected)
    assert out["history_used"].iloc[4] == 4


def test_history_window_is_capped():
    # Ten quarters of history, a max_history of 8: the two oldest are dropped.
    reported = [1.0 + 0.1 * (-1) ** i for i in range(10)] + [2.0]
    events = make_events("AAA", [1.0] * 11, reported)
    out = standardised_surprise(events, min_history=4, max_history=8)
    assert out["history_used"].iloc[-1] == 8
    past = np.array(reported[2:10]) - 1.0
    assert out["sue"].iloc[-1] == pytest.approx(1.0 / past.std(ddof=1))


def test_zero_dispersion_gives_nan_not_infinity():
    # A firm that hits the estimate exactly, then beats it once.
    events = make_events("AAA", [1.0] * 6, [1.0, 1.0, 1.0, 1.0, 1.0, 1.5])
    out = standardised_surprise(events, min_history=4)
    assert out["surprise_std"].iloc[-1] == 0.0
    assert np.isnan(out["sue"].iloc[-1])
    assert not np.isinf(out["sue"]).any()


def test_tickers_do_not_contaminate_each_other():
    calm = make_events("CALM", [1.0] * 5, [1.01, 0.99, 1.01, 0.99, 1.05])
    wild = make_events("WILD", [1.0] * 5, [2.0, 0.0, 2.0, 0.0, 1.05])
    out = standardised_surprise(pd.concat([calm, wild], ignore_index=True))
    sue = out.set_index(["ticker", out.groupby("ticker").cumcount()])["sue"]
    # Same 0.05 beat, but it is a big deal for the calm firm and noise for the
    # other one. If the groupby leaked, these two would be equal.
    assert abs(sue[("CALM", 4)]) > 10 * abs(sue[("WILD", 4)])


def test_rows_are_sorted_by_ticker_then_time():
    events = make_events("AAA", [1.0] * 3, [1.1, 0.9, 1.2])
    shuffled = events.iloc[::-1].reset_index(drop=True)
    out = standardised_surprise(shuffled)
    assert out["event_time"].is_monotonic_increasing


def test_rows_missing_a_date_are_dropped():
    events = make_events("AAA", [1.0] * 3, [1.1, 0.9, 1.2])
    events.loc[1, "event_time"] = pd.NaT
    out = standardised_surprise(events)
    assert len(out) == 2


def test_describe_reports_counts_without_crashing_on_empty():
    assert "No usable announcements" in describe(pd.DataFrame())
    events = make_events("AAA", [1.0] * 6, [1.1, 0.9, 1.2, 0.8, 1.3, 0.7])
    text = describe(standardised_surprise(events))
    assert "announcements     : 6" in text
    assert "usable SUEs       : 2" in text
