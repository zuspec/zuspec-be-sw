"""C runtime string constants for the zuspec-be-sw C backend.

Each submodule exposes ``HEADER`` and ``SOURCE`` string constants containing
the C text to emit alongside generated component code.  The generator calls
``crt.emit_all(output_dir)`` once per compilation to write them out.
"""
from __future__ import annotations
from pathlib import Path

from .zdc_completion import HEADER as _CH, SOURCE as _CS
from .zdc_queue      import HEADER as _QH, SOURCE as _QS
from .zdc_spawn      import HEADER as _SPH, SOURCE as _SPS
from .zdc_select     import HEADER as _SEH, SOURCE as _SES
from .zdc_runtime    import HEADER as RUNTIME_HEADER

__all__ = [
    "RUNTIME_HEADER",
    "emit_all",
]


def emit_all(output_dir: Path) -> list[Path]:
    """Write all C runtime headers and sources to *output_dir*.

    Returns the list of files written.  Existing files with identical content
    are not re-written (avoids spurious rebuilds).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "zdc_completion.h": _CH,
        "zdc_completion.c": _CS,
        "zdc_queue.h":      _QH,
        "zdc_queue.c":      _QS,
        "zdc_spawn.h":      _SPH,
        "zdc_spawn.c":      _SPS,
        "zdc_select.h":     _SEH,
        "zdc_select.c":     _SES,
        "zdc_runtime.h":    RUNTIME_HEADER,
    }

    written: list[Path] = []
    for name, text in files.items():
        path = output_dir / name
        if path.exists() and path.read_text() == text:
            continue
        path.write_text(text)
        written.append(path)
    return written
