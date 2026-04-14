"""
Benchmark conftest — shared across all benchmark subdirectories.

Tests marked with ``benchmark_test`` are skipped by default.
Pass ``--run-benchmarks`` to enable them.
"""
from __future__ import annotations

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-benchmarks",
        action="store_true",
        default=False,
        help="Run benchmark tests (skipped by default).",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "benchmark_test: performance benchmark (requires --run-benchmarks)",
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-benchmarks", default=False):
        skip = pytest.mark.skip(reason="pass --run-benchmarks to run")
        for item in items:
            if "benchmark_test" in item.keywords:
                item.add_marker(skip)
