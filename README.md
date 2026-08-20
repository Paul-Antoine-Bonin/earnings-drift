# earnings-drift

Does post-earnings announcement drift still hold?

After an earnings surprise, the price is supposed to keep drifting in the
direction of the surprise for weeks. This repo tests whether that is still
true, on the S&P 500, with the history depth `yfinance` actually gives.

No results yet. The earnings-surprise collector is the next step.

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
