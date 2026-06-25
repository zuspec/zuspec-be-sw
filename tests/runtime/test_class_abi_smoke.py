"""Compile + run the class-model runtime ABI smoke test.

This validates the zsp_object / zsp_class C ABI (prefix-layout inheritance,
vtable dispatch, the zsp_object_alloc allocation seam, refcount teardown, and
the precise GC root map) that the class-model codegen will target. It is a
hand-written analogue of the generated code, so the ABI is locked before the
generator depends on it.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

_HERE = Path(__file__).parent
_SHARE = _HERE.parent.parent / "src" / "zuspec" / "be" / "sw" / "share"
_INCLUDE = _SHARE / "include"
_RT = _SHARE / "rt"


def _find_cc():
    for cc in ("gcc", "clang", "cc"):
        if shutil.which(cc):
            return cc
    return None


@pytest.mark.skipif(_find_cc() is None, reason="no C compiler available")
def test_class_abi_smoke(tmp_path):
    cc = _find_cc()
    exe = tmp_path / "class_abi_smoke"
    cmd = [
        cc, "-g", "-O0", "-Wall", "-Wextra",
        f"-I{_INCLUDE}",
        str(_HERE / "class_abi_smoke.c"),
        str(_RT / "zsp_object.c"),
        str(_RT / "zsp_alloc.c"),
        "-o", str(exe),
    ]
    compile_res = subprocess.run(cmd, capture_output=True, text=True)
    assert compile_res.returncode == 0, f"compile failed:\n{compile_res.stderr}"

    run_res = subprocess.run([str(exe)], capture_output=True, text=True)
    assert run_res.returncode == 0, (
        f"run failed (exit {run_res.returncode}):\n"
        f"{run_res.stdout}\n{run_res.stderr}"
    )
    assert "class_abi_smoke: OK" in run_res.stdout
