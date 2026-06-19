"""Phase-2 end-to-end test: PSS atomic action → C → compile → run.

Mirrors the ``test_smoke.py`` harness but drives the new scenario backend
(``zuspec.be.sw.scenario``): parse a hello-world PSS, lower to Layer 1, emit C,
compile with ``CCompiler``, run, and assert stdout.

Gated on a working C toolchain and the ``zuspec.fe.pss`` frontend; skips with a
reason otherwise (per the existing pattern).
"""
import shutil
import subprocess
from pathlib import Path

import pytest

pytest.importorskip("zuspec.fe.pss")
from zuspec.be.sw.scenario import generate_c_files  # noqa: E402
from zuspec.be.sw.compiler import CCompiler  # noqa: E402

_HAS_CC = any(shutil.which(c) for c in ("gcc", "clang", "cc"))

# Phase-2 walking skeleton: non-rand fields, so no solver is involved and the
# emitted program is self-contained (constrained-random is covered by the
# Phase-3 e2e tests).
HELLO_WORLD = """
component pss_top {
    action write_reg {
        bit[32] addr;
        bit[32] data;
        exec body {
            message(NONE, "write_reg: addr=0x%x data=0x%x", addr, data);
        }
    }
    action read_reg {
        bit[32] addr;
        exec body {
            message(NONE, "read_reg: addr=0x%x", addr);
        }
    }
    action do_test {
        activity { do write_reg; do read_reg; }
    }
}
"""


def _write_pss(tmp_path: Path) -> Path:
    p = tmp_path / "hello_world.pss"
    p.write_text(HELLO_WORLD)
    return p


def test_generate_c_files_shape(tmp_path):
    """Lowering + emission produce the expected source set and content,
    without needing a compiler."""
    pss = _write_pss(tmp_path)
    out = tmp_path / "gen"
    srcs = generate_c_files([pss], out, root="pss_top")
    names = sorted(s.name for s in srcs)
    # No solver here → a single TU (main folded into scenario_gen.c).
    assert names == ["scenario_gen.c"]

    src = (out / "scenario_gen.c").read_text()
    # message() lowered to fprintf (not a silent comment stub).
    assert 'fprintf(stdout, "write_reg: addr=0x%x data=0x%x\\n"' in src
    assert "self->addr" in src and "self->data" in src

    hdr = (out / "scenario_gen.h").read_text()
    assert "typedef struct write_reg_s" in hdr
    assert "uint32_t addr;" in hdr


@pytest.mark.skipif(not _HAS_CC, reason="no C compiler available")
def test_pss_hello_compile_and_run(tmp_path):
    pss = _write_pss(tmp_path)
    out = tmp_path / "gen"
    srcs = generate_c_files([pss], out, root="pss_top")

    cc = CCompiler(output_dir=out)
    exe = out / "pss_hello"
    result = cc.compile(srcs, exe, extra_includes=[out])
    assert result.success, result.stderr

    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=10)
    assert run.returncode == 0, run.stderr
    # Phase 2 has no solver, so rand fields are zero.
    assert "write_reg: addr=0x0 data=0x0" in run.stdout
    assert "read_reg: addr=0x0" in run.stdout
