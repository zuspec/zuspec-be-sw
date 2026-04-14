"""Shared conftest for correctness tests — compile_and_load fixture."""
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
def compile_and_load(tmp_path_factory):
    """Factory: compile_and_load(ComponentClass) → (lib, State)."""
    cache: dict = {}

    def _compile(comp_cls):
        if comp_cls not in cache:
            outdir = tmp_path_factory.mktemp(comp_cls.__name__)
            paths = generate(comp_cls, outdir)
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
            cache[comp_cls] = (lib, ns["State"])
        return cache[comp_cls]

    return _compile


@pytest.fixture(scope="session")
def Counter():
    return _load_class("01_counter", "counter", "Counter")


@pytest.fixture(scope="session")
def PriorityEncoder():
    return _load_class("02_priority_encoder", "priority_encoder", "PriorityEncoder")


@pytest.fixture(scope="session")
def TrafficLight():
    return _load_class("03_traffic_light", "traffic_light", "TrafficLight")


@pytest.fixture(scope="session")
def DataSource():
    return _load_class("04_handshake", "handshake", "DataSource")


@pytest.fixture(scope="session")
def DataSink():
    return _load_class("04_handshake", "handshake", "DataSink")
