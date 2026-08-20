# earnings-drift: does post-earnings announcement drift still hold?

## Goal
Replicate one of the most famous anomalies in empirical finance: after an earnings
surprise, the price keeps drifting in the direction of the surprise for weeks.
The question: is that still true today?

## Data
- `yfinance`: `.earnings_dates` gives estimated and reported EPS for recent quarters.
- Universe: S&P 500, over whatever history depth is actually available.
- If the depth is insufficient, document the limitation rather than hiding it.

## Steps
- [x] Set up repo and dependencies
- [ ] Collect the (estimated EPS, reported EPS) pairs and compute the standardised surprise
- [ ] Pull the prices around each announcement (D-5 to D+60)
- [ ] Compute cumulative abnormal returns, net of the index return
- [ ] Sort the events into surprise deciles
- [ ] Plot the mean CAR per decile: the signature of the drift, if it exists
- [ ] Split by period to see whether the effect erodes over time
- [ ] Estimate what transaction costs would take out of a naive strategy
- [ ] README: does the anomaly survive, and does it survive costs?

## Done when
The CAR by decile chart is produced, and the README takes a side on "tradeable or not".

## Traps
- Survivorship bias: today's S&P 500 universe is not the one from ten years ago.
  Flag it explicitly even if you cannot correct for it.
