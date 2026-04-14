"""Integration tests: Counter code generation pipeline."""
import subprocess
import sys
import pytest
from pathlib import Path

_EXAMPLES = Path(__file__).parents[5] / "examples"


@pytest.fixture(scope="module")
def Counter():
    if str(_EXAMPLES / "01_counter") not in sys.path:
        sys.path.insert(0, str(_EXAMPLES / "01_counter"))
    import counter as _mod
    return _mod.Counter


@pytest.fixture(scope="module")
def counter_outdir(tmp_path_factory, Counter):
    from zuspec.be.sw import generate
    outdir = tmp_path_factory.mktemp("counter")
    generate(Counter, outdir)
    return outdir


def test_generates_header_and_source(counter_outdir):
    assert (counter_outdir / "Counter.h").exists()
    assert (counter_outdir / "Counter.c").exists()
    assert (counter_outdir / "Counter_ctypes.py").exists()


def test_header_compiles(counter_outdir):
    result = subprocess.run(
        ["cc", "-c", "-x", "c", str(counter_outdir / "Counter.h"),
         "-I", str(counter_outdir), "-o", "/dev/null"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr


def test_source_links_to_so(counter_outdir):
    so = counter_outdir / "Counter.so"
    result = subprocess.run(
        ["cc", "-O2", "-shared", "-fPIC", "-o", str(so),
         str(counter_outdir / "Counter.c"), "-I", str(counter_outdir)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert so.exists()


def test_ctypes_wrapper_loadable(counter_outdir):
    ns = {}
    exec((counter_outdir / "Counter_ctypes.py").read_text(), ns)
    State = ns["State"]
    st = State()
    assert hasattr(st, "count")
    assert hasattr(st, "enable")
    assert hasattr(st, "count_nxt")
    # Counter uses domain-based reset: no explicit reset field
    assert not hasattr(st, "reset")
