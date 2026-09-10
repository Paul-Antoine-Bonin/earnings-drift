"""Collect earnings surprises for the current S&P 500 and standardise them.

The output of this module is one row per (ticker, announcement) with the
analyst estimate, the reported figure, the raw surprise and the standardised
surprise (SUE). Everything downstream -- prices around the event, cumulative
abnormal returns, decile sorts -- keys off that table.

Survivorship bias, stated once and not hidden afterwards: the universe is the
S&P 500 *as of today*. Firms that were in the index years ago and have since
been delisted, acquired or demoted are absent, and they are exactly the firms
whose post-earnings behaviour was worst. Any drift measured here is therefore
an upper bound on what was actually tradeable.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd

SP500_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

# yfinance returns at most a handful of years of earnings dates. 80 quarters is
# simply "as much as the endpoint is willing to give"; the real depth is
# reported by the collector rather than assumed here.
DEFAULT_QUARTERS = 80

# A SUE needs a dispersion estimate, and a dispersion estimate needs history.
# Foster-Olsen-Shevlin use eight quarters; we accept four to avoid throwing away
# most of a shallow sample, and record how many quarters each SUE rests on.
MIN_HISTORY = 4
MAX_HISTORY = 8

COLUMNS = [
    "ticker",
    "event_time",
    "eps_estimate",
    "eps_reported",
    "surprise",
    "surprise_std",
    "history_used",
    "sue",
]


def sp500_tickers(url: str = SP500_WIKI_URL) -> List[str]:
    """Return the tickers of the S&P 500 as currently listed on Wikipedia.

    Needs network. Class shares are written BRK.B on Wikipedia and BRK-B by
    Yahoo, so dots become dashes.
    """
    import io

    import requests  # a yfinance dependency, so no new requirement

    # Wikipedia answers 403 to pandas' default user agent; identify the caller.
    headers = {"User-Agent": "earnings-drift/0.1 (research script)"}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    tables = pd.read_html(io.StringIO(response.text))
    for table in tables:
        if "Symbol" in table.columns:
            symbols = table["Symbol"].astype(str).str.strip()
            return [s.replace(".", "-") for s in symbols if s and s != "nan"]
    raise ValueError(f"No table with a 'Symbol' column found at {url}")


def fetch_earnings(ticker: str, quarters: int = DEFAULT_QUARTERS) -> pd.DataFrame:
    """Estimated and reported EPS for one ticker, oldest announcement first.

    Rows without both an estimate and a reported figure are dropped: future
    announcements carry an estimate only, and some historical rows come back
    empty. Returns an empty frame with the right columns when nothing usable
    comes back, so callers can concatenate without special-casing.
    """
    import yfinance as yf  # imported lazily: the SUE maths must stay testable offline

    empty = pd.DataFrame(columns=["ticker", "event_time", "eps_estimate", "eps_reported"])
    try:
        raw = yf.Ticker(ticker).get_earnings_dates(limit=quarters)
    except Exception as exc:  # a single bad ticker must not sink a 500-name run
        print(f"  {ticker}: fetch failed ({exc})", file=sys.stderr)
        return empty
    if raw is None or raw.empty:
        return empty

    df = raw.reset_index()
    # The index name has moved between yfinance versions ("Earnings Date",
    # "Earnings Datetime"); take whatever the first column ended up being.
    date_col = df.columns[0]
    rename = {
        date_col: "event_time",
        "EPS Estimate": "eps_estimate",
        "Reported EPS": "eps_reported",
    }
    missing = [c for c in ("EPS Estimate", "Reported EPS") if c not in df.columns]
    if missing:
        print(f"  {ticker}: missing columns {missing}", file=sys.stderr)
        return empty

    df = df.rename(columns=rename)[["event_time", "eps_estimate", "eps_reported"]]
    df["ticker"] = ticker
    df = df.dropna(subset=["eps_estimate", "eps_reported"])
    df = df[["ticker", "event_time", "eps_estimate", "eps_reported"]]
    return df.sort_values("event_time").reset_index(drop=True)


def standardised_surprise(
    events: pd.DataFrame,
    min_history: int = MIN_HISTORY,
    max_history: int = MAX_HISTORY,
) -> pd.DataFrame:
    """Add the raw surprise and the SUE to a frame of earnings announcements.

    SUE is the surprise divided by the standard deviation of that firm's own
    past surprises -- past only, so the number is usable on the announcement
    day. A firm with fewer than `min_history` prior announcements gets NaN
    rather than a dispersion estimate built on two points.

    Scaling by the firm's own surprise dispersion, rather than by price or by
    EPS, is what makes a $0.02 beat at a stable utility comparable to a $0.02
    beat at a name that misses by a dime every other quarter.
    """
    if events.empty:
        return pd.DataFrame(columns=COLUMNS)

    df = events.copy()
    df["event_time"] = pd.to_datetime(df["event_time"], utc=True, errors="coerce")
    df = df.dropna(subset=["event_time"])
    df = df.sort_values(["ticker", "event_time"]).reset_index(drop=True)
    df["surprise"] = df["eps_reported"].astype(float) - df["eps_estimate"].astype(float)

    grouped = df.groupby("ticker", sort=False)["surprise"]
    prior = grouped.shift(1)  # past surprises only, current one excluded
    by_ticker = prior.groupby(df["ticker"], sort=False)
    df["surprise_std"] = by_ticker.rolling(
        window=max_history, min_periods=min_history
    ).std().reset_index(level=0, drop=True)
    df["history_used"] = by_ticker.rolling(
        window=max_history, min_periods=min_history
    ).count().reset_index(level=0, drop=True)

    # A zero dispersion means the firm hit the estimate exactly every quarter of
    # the window. Dividing by it would manufacture an infinite SUE.
    std = df["surprise_std"].where(df["surprise_std"] > 0)
    df["sue"] = df["surprise"] / std
    return df[COLUMNS]


def collect(
    tickers: Iterable[str],
    quarters: int = DEFAULT_QUARTERS,
    pause: float = 0.4,
    progress_every: int = 25,
) -> pd.DataFrame:
    """Fetch every ticker, concatenate, and standardise the surprises."""
    tickers = list(tickers)
    frames = []
    for i, ticker in enumerate(tickers, start=1):
        frames.append(fetch_earnings(ticker, quarters=quarters))
        if progress_every and i % progress_every == 0:
            print(f"  {i}/{len(tickers)} tickers", file=sys.stderr)
        if pause:
            time.sleep(pause)  # Yahoo throttles a 500-name loop that runs flat out
    usable = [f for f in frames if not f.empty]
    if not usable:
        return pd.DataFrame(columns=COLUMNS)
    return standardised_surprise(pd.concat(usable, ignore_index=True))


def describe(events: pd.DataFrame) -> str:
    """A short human-readable summary of what a collection run actually got."""
    if events.empty:
        return "No usable announcements collected."
    with_sue = events["sue"].notna().sum()
    return "\n".join(
        [
            f"tickers with data : {events['ticker'].nunique()}",
            f"announcements     : {len(events)}",
            f"date range        : {events['event_time'].min().date()} "
            f"to {events['event_time'].max().date()}",
            f"usable SUEs       : {with_sue} "
            f"({100 * with_sue / len(events):.1f}% of announcements)",
        ]
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/earnings_surprises.csv"),
        help="where to write the collected table (default: %(default)s)",
    )
    parser.add_argument(
        "--quarters",
        type=int,
        default=DEFAULT_QUARTERS,
        help="quarters of history to ask yfinance for (default: %(default)s)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="only collect the first N tickers, for a quick check",
    )
    parser.add_argument(
        "--pause",
        type=float,
        default=0.4,
        help="seconds between tickers (default: %(default)s)",
    )
    args = parser.parse_args(argv)

    tickers = sp500_tickers()
    if args.limit:
        tickers = tickers[: args.limit]
    print(f"Collecting {len(tickers)} tickers.", file=sys.stderr)

    events = collect(tickers, quarters=args.quarters, pause=args.pause)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    events.to_csv(args.out, index=False)
    print(describe(events))
    print(f"\nWritten to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
