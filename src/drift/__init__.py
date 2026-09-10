"""Post-earnings announcement drift on the current S&P 500 universe.

`drift.collect` builds the event table: one row per (ticker, announcement)
with the analyst estimate, the reported EPS, the raw surprise and the
standardised surprise (SUE). Prices around the event come next.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
