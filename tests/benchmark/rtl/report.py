#!/usr/bin/env python3
"""
Benchmark report generator.

Reads a pytest-benchmark JSON output file and emits a Markdown table with
Mcycles/sec and speedup vs iverilog columns.

Usage:
    python -m zuspec.be.sw.benchmark.report benchmark.json
  or
    pytest ... --benchmark-json=benchmark.json
    python packages/zuspec-be-sw/tests/benchmark/rtl/report.py benchmark.json
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def _load(path: str) -> List[dict]:
    with open(path) as f:
        data = json.load(f)
    return data.get("benchmarks", [])


def _parse_benchmarks(benchmarks: List[dict]) -> Dict[Tuple, float]:
    """Return {(component, simulator, n_cycles): Mcycles_per_sec}."""
    out = {}
    for b in benchmarks:
        info = b.get("extra_info", {})
        comp = info.get("component")
        sim  = info.get("simulator")
        n    = info.get("n_cycles")
        mcs  = info.get("Mcycles_per_sec")
        if None in (comp, sim, n, mcs):
            continue
        out[(comp, sim, int(n))] = float(mcs)
    return out


def _format_n(n: int) -> str:
    if n >= 1_000_000:
        return f"{n // 1_000_000}M"
    return str(n)


def generate_markdown(data: Dict[Tuple, float]) -> str:
    # Group: component → simulator → n_cycles → Mcycles/sec
    by_comp: Dict[str, Dict[str, Dict[int, float]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for (comp, sim, n), mcs in data.items():
        by_comp[comp][sim][n] = mcs

    lines: List[str] = []
    lines.append("# Benchmark Results\n")

    for comp in sorted(by_comp):
        lines.append(f"## {comp}\n")

        sims = sorted(by_comp[comp])
        all_n = sorted({n for s in by_comp[comp].values() for n in s})

        # Header
        header = ["Simulator"] + [_format_n(n) + " cycles" for n in all_n]
        if "iverilog" in sims:
            header += [_format_n(n) + " speedup" for n in all_n]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "|".join("---" for _ in header) + "|")

        for sim in sims:
            row = [sim]
            for n in all_n:
                mcs = by_comp[comp][sim].get(n)
                row.append(f"{mcs:.1f}" if mcs is not None else "—")
            if "iverilog" in sims:
                for n in all_n:
                    mcs = by_comp[comp][sim].get(n)
                    iv  = by_comp[comp].get("iverilog", {}).get(n)
                    if mcs is not None and iv and iv > 0:
                        row.append(f"{mcs / iv:.1f}×")
                    else:
                        row.append("—")
            lines.append("| " + " | ".join(row) + " |")

        lines.append("")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} benchmark.json", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    benchmarks = _load(path)
    data = _parse_benchmarks(benchmarks)

    if not data:
        print(
            "No benchmark data found. Run benchmarks with --benchmark-json=<file> "
            "and ensure extra_info fields are set.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(generate_markdown(data))


if __name__ == "__main__":
    main()
