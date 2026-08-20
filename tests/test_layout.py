"""Checks that the src/ layout is installed and importable.

These are deliberately thin. They exist so that a broken packaging setup fails
here rather than halfway through a data collection run.
"""

import importlib

import drift


def test_package_imports():
    assert drift.__version__ == "0.1.0"


def test_package_resolves_from_src_layout():
    # The package must come from src/, not from a stray copy in the repo root.
    spec = importlib.util.find_spec("drift")
    assert spec is not None and spec.origin is not None
    assert "src" in spec.origin.split("/")


def test_dependencies_available():
    for name in ("numpy", "pandas", "matplotlib", "yfinance"):
        assert importlib.import_module(name) is not None
