"""Shared conftest for behavioral tests."""
import ctypes
import subprocess
import sys
from pathlib import Path
import pytest

from zuspec.be.sw import generate

_EXAMPLES = Path(__file__).parents[5] / "examples"


def _load_class(subdir: str, module: str, classname: str):
    ex_dir = str(_EXAMPLES / subdir)
    if ex_dir not in sys.path:
        sys.path.insert(0, ex_dir)
    import importlib
    mod = importlib.import_module(module)
    return getattr(mod, classname)


@pytest.fixture(scope="session")
def compile_so_behav(tmp_path_factory):
    """Factory: compile_and_load(ComponentClass, period_ps) → (lib, State)."""
    cache: dict = {}

    def _compile(comp_cls, domain_period_ps=10_000):
        key = (comp_cls, domain_period_ps)
        if key not in cache:
            outdir = tmp_path_factory.mktemp(comp_cls.__name__)
            paths = generate(comp_cls, outdir, domain_period_ps=domain_period_ps)
            so = outdir / f"{comp_cls.__name__}.so"
            c_files = [str(p) for p in paths if str(p).endswith(".c")]
            subprocess.check_call(
                ["cc", "-O2", "-shared", "-fPIC", "-o", str(so)]
                + c_files
                + ["-I", str(outdir)]
            )
            lib = ctypes.CDLL(str(so))
            ns: dict = {}
            exec((outdir / f"{comp_cls.__name__}_ctypes.py").read_text(), ns)
            cache[key] = (lib, ns["State"])
        return cache[key]

    return _compile


@pytest.fixture(scope="session")
def DelayCounter():
    return _load_class("06_delay_counter", "delay_counter", "DelayCounter")
