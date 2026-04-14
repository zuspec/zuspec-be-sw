"""
MemSubsystem TLM benchmark tests.

Generates the TLM C code from the Python model, compiles it together with the
hand-written ``dram_impl.c`` and the ``bench_mem_subsystem.c`` driver, then
runs the resulting binary and reports throughput.

Run with:
    pytest tests/benchmark/tlm/ --run-benchmarks -v
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT  = Path(__file__).parents[5]
_EXAMPLES   = _REPO_ROOT / "examples"
_TLM_EXAMPLES = _EXAMPLES / "tlm"

# Make the examples package importable
if str(_EXAMPLES) not in sys.path:
    sys.path.insert(0, str(_EXAMPLES))


# ---------------------------------------------------------------------------
# Session-scoped fixture: generate + compile the benchmark binary
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def bench_binary(tmp_path_factory):
    """Generate TLM C, compile with dram_impl.c and bench driver, return binary path."""
    outdir = tmp_path_factory.mktemp("tlm_bench")

    # 1. Generate TLM C code
    from tlm.mem_subsystem import MemSubsystem
    from zuspec.be.sw import generate_tlm
    generate_tlm(MemSubsystem, outdir)

    # 2. Copy hand-written sources into outdir
    for src in ["dram_impl.c", "bench_mem_subsystem.c"]:
        src_path = _TLM_EXAMPLES / src
        if not src_path.exists():
            pytest.fail(f"Missing source file: {src_path}")
        shutil.copy(src_path, outdir / src)

    # 3. Compile with LT mode enabled
    gcc = shutil.which("gcc")
    if gcc is None:
        pytest.skip("gcc not found in PATH")

    binary = outdir / "bench_mem_subsystem"
    cmd = [
        gcc, "-O2", f"-I{outdir}",
        "-DZSP_LT_MODE", "-DZSP_LT_QUANTUM_PS=1000000",
        "-o", str(binary),
        str(outdir / "bench_mem_subsystem.c"),
        str(outdir / "dram_impl.c"),
        str(outdir / "CacheStub.c"),
        str(outdir / "DramModel.c"),
        str(outdir / "MemSubsystem.c"),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        pytest.fail(
            f"Compilation failed:\n{result.stderr}"
        )

    return binary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_bench_output(text: str) -> dict:
    """Parse key: value lines from bench_mem_subsystem output."""
    info = {}
    for line in text.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            info[key.strip()] = val.strip()
    return info


# ---------------------------------------------------------------------------
# Benchmark tests
# ---------------------------------------------------------------------------

@pytest.mark.benchmark_test
def test_bench_mem_subsystem_throughput(bench_binary):
    """Run the MemSubsystem benchmark for 2 seconds and report fetch throughput."""
    result = subprocess.run(
        [str(bench_binary), "2"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, f"Benchmark binary failed:\n{result.stderr}"

    info = _parse_bench_output(result.stdout)
    print("\n--- bench_mem_subsystem output ---")
    print(result.stdout)

    # Extract throughput
    tput_str = info.get("Throughput", "")
    assert "M-fetches/s" in tput_str, f"Unexpected throughput line: {tput_str}"
    mfps = float(tput_str.split()[0])
    assert mfps > 0.0, "Throughput should be positive"


@pytest.mark.benchmark_test
def test_bench_mem_subsystem_rtf(bench_binary):
    """Verify simulated-time / wall-time ratio is reported and positive."""
    result = subprocess.run(
        [str(bench_binary), "1"],
        capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 0, f"Benchmark binary failed:\n{result.stderr}"

    info = _parse_bench_output(result.stdout)
    rtf_str = info.get("RTF (sim/wall)", "")
    assert rtf_str, "RTF line missing from output"
    rtf = float(rtf_str)
    assert rtf > 0.0, "RTF should be positive"


@pytest.mark.benchmark_test
def test_bench_mem_subsystem_compiles(bench_binary):
    """Sanity check: the benchmark binary was compiled successfully."""
    assert bench_binary.exists(), "Benchmark binary was not produced"


# ---------------------------------------------------------------------------
# SystemC benchmark fixture + tests
# ---------------------------------------------------------------------------

_SC_INCLUDE = "/tools/systemc/3.0.0/include"
_SC_LIB     = "/tools/systemc/3.0.0/lib-linux64"


@pytest.fixture(scope="module")
def sc_bench_binary(tmp_path_factory):
    """Compile the SystemC LT benchmark; skip if SystemC not found."""
    from pathlib import Path as _P
    if not _P(_SC_INCLUDE).exists():
        pytest.skip(f"SystemC headers not found at {_SC_INCLUDE}")

    gpp = shutil.which("g++")
    if gpp is None:
        pytest.skip("g++ not found in PATH")

    src = _TLM_EXAMPLES / "bench_mem_subsystem_sc.cpp"
    if not src.exists():
        pytest.fail(f"Missing source file: {src}")

    outdir = tmp_path_factory.mktemp("tlm_sc_bench")
    binary = outdir / "bench_mem_subsystem_sc"
    cmd = [
        gpp, "-O2",
        f"-I{_SC_INCLUDE}",
        f"-L{_SC_LIB}", f"-Wl,-rpath,{_SC_LIB}",
        "-o", str(binary),
        str(src),
        "-lsystemc",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        pytest.fail(f"SystemC compilation failed:\n{result.stderr}")
    return binary


@pytest.mark.benchmark_test
def test_sc_bench_throughput(sc_bench_binary):
    """Run the SystemC TLM LT benchmark (100M fetches) and report throughput."""
    result = subprocess.run(
        [str(sc_bench_binary), "100000000"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, f"SC benchmark failed:\n{result.stderr}"

    info = _parse_bench_output(result.stdout)
    print("\n--- bench_mem_subsystem_sc output ---")
    print(result.stdout)

    tput_str = info.get("Throughput", "")
    assert "M-fetches/s" in tput_str, f"Unexpected throughput line: {tput_str}"
    mfps = float(tput_str.split()[0])
    assert mfps > 0.0, "Throughput should be positive"


@pytest.mark.benchmark_test
def test_sc_bench_compiles(sc_bench_binary):
    """Sanity check: the SystemC benchmark binary was compiled successfully."""
    assert sc_bench_binary.exists(), "SystemC benchmark binary was not produced"
