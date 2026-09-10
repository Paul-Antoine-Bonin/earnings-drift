# earnings-drift

Does post-earnings announcement drift still hold?

After an earnings surprise, the price is supposed to keep drifting in the
direction of the surprise for weeks. This repo tests whether that is still
true, on the S&P 500, with the history depth `yfinance` actually gives.

No results yet. The earnings-surprise collector is in place; prices around
each announcement are the next step.

## Collecting the surprises

```bash
python -m drift.collect                 # the whole index, into data/
python -m drift.collect --limit 8       # a quick check on eight tickers
```

The universe is the S&P 500 as listed on Wikipedia today, and the earnings
dates come from `yfinance`. Each announcement gets a raw surprise (reported
EPS minus estimate) and a SUE: that surprise divided by the standard deviation
of the same firm's own past surprises, over the previous eight quarters,
current quarter excluded. Scaling by the firm's own dispersion is what makes a
two-cent beat at a stable utility comparable to a two-cent beat at a name that
misses by a dime every other quarter. Fewer than four prior announcements, or a
dispersion of exactly zero, gives a NaN SUE rather than a fabricated one.

### What the first full run got

Run on 10 September 2026, 503 tickers requested:

```
tickers with data : 501
announcements     : 42778
date range        : 1999-08-04 to 2026-09-09
usable SUEs       : 40594 (94.9% of announcements)
```

Two tickers came back with nothing usable. The depth is much better than the
brief assumed: `yfinance` gives roughly a hundred quarters per name, not the
handful of recent years expected, so history is not the binding constraint
here. The missing 5% are announcements without four prior quarters on record,
mostly the first ones for each ticker.

**Survivorship bias.** The universe is today's index. Firms that were in it
years ago and have since been delisted, acquired or demoted are missing, and
they are exactly the ones whose post-earnings behaviour was worst. Any drift
measured on this sample is an upper bound on what was actually tradeable. This
is not correctable with the data at hand, so it stays flagged.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install -e .
```

The `pip install --upgrade` line is not decoration: an old pip refuses the
editable install because the project has no `setup.py`.

## Run the tests

```bash
pytest
```

## Layout

```
src/drift/      the package
tests/          test suite
notebooks/      01-drift-demo.ipynb, the readable walkthrough
data/           downloaded data, not versioned
```

Roadmap and progress: [TODO.md](TODO.md)
