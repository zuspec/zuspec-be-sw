"""Phase-6 e2e: every example under examples/pss/ compiles and runs.

Discovers each ``examples/pss/*.pss``, runs it through the full
parse → lower → emit → compile → run flow, and asserts a clean exit. The
constrained example additionally has its solutions checked.
"""
import re
import subprocess
from pathlib import Path

import pytest

from _pss_harness import require_toolchain

_EXAMPLES = sorted(
    (Path(__file__).resolve().parents[2] / "examples" / "pss").glob("*.pss"))


def _build_run(tmp_path, pss_path, seed=12345, iters=2):
    from zuspec.be.sw.scenario import generate_c_files, build_executable
    out = tmp_path / "gen"
    sources = generate_c_files([pss_path], out, root="pss_top")
    exe = out / "case"
    result, _ = build_executable(sources, exe, out)
    if not result.success:
        pytest.fail(f"{pss_path.name} compile failed:\n{result.stderr}")
    run = subprocess.run([str(exe), str(seed), str(iters)],
                         capture_output=True, text=True, timeout=30)
    return run.stdout, run.returncode


@pytest.mark.parametrize("pss_path", _EXAMPLES, ids=lambda p: p.name)
def test_example_compiles_and_runs(tmp_path, pss_path):
    # Examples that solve constraints need the solver; others just need a CC.
    needs_solver = "constraint" in pss_path.read_text()
    require_toolchain(needs_solver=needs_solver)
    stdout, rc = _build_run(tmp_path, pss_path)
    assert rc == 0, stdout
    assert stdout.strip(), f"{pss_path.name} produced no output"


def test_examples_present():
    names = {p.name for p in _EXAMPLES}
    assert {"01_hello.pss", "02_constrained_regs.pss",
            "03_sequence.pss", "04_parallel.pss"} <= names


def test_constrained_regs_satisfies(tmp_path):
    pss = next(p for p in _EXAMPLES if p.name == "02_constrained_regs.pss")
    require_toolchain(needs_solver=True)
    stdout, rc = _build_run(tmp_path, pss, seed=999, iters=5)
    assert rc == 0
    rows = re.findall(r"addr=0x([0-9a-f]+) data=0x([0-9a-f]+)", stdout)
    assert rows
    for a, d in rows:
        addr, data = int(a, 16), int(d, 16)
        assert addr & 3 == 0 and 0x1000 <= addr <= 0x1FFF
        assert 0 <= data <= 0xFF
