# zuspec_gdb.py — Auto-loading GDB helper for zuspec-be-sw RTL debug builds.
#
# Embedded in the .debug_gdb_scripts ELF section; GDB >= 7.2 loads it
# automatically when the shared library is opened.  Also usable standalone:
#   (gdb) source zuspec_gdb.py
#
# Provides:
#   - Source map loader from .zuspec_srcmap ELF section symbols
#   - ZspComponentPrinter: pretty-printer hiding nxt/coro internal fields
#   - ZspFrameFilter: synthetic backtrace frames from zsp_coro_top linked list
#   - zs-bt:    Python-level coroutine backtrace
#   - zs-break: convenience alias for break with Python file:line
#   - zs-print: show component fields with Python names and widths applied
#   - zs-coro:  list all active coroutines and their current source location
#
# Field names on ZspCoroFrame_t (must match zsp_rtl_debug.h):
#   co_name  (const char*)
#   loc      (ZspLoc_t: .file const char*, .line int32_t)
#   prev     (struct ZspCoroFrame*)

from __future__ import annotations

import json
import re

try:
    import gdb  # type: ignore[import]
except ImportError:
    # Allow import outside GDB for testing / embedding the script as a string
    gdb = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Source map registry
# ---------------------------------------------------------------------------

_srcmaps: dict = {}   # keyed by c_type name (e.g. "Counter")


def _load_srcmaps_via_symbols() -> None:
    """Enumerate _zuspec_srcmap_* globals in the inferior and parse them."""
    if gdb is None:
        return
    try:
        output = gdb.execute("info variables ^_zuspec_srcmap_", to_string=True)
    except gdb.error:
        return
    for line in output.splitlines():
        m = re.search(r"(_zuspec_srcmap_\w+)\s*$", line)
        if not m:
            continue
        sym_name = m.group(1)
        try:
            val = gdb.parse_and_eval(sym_name)
            payload = val.string()
            sm = json.loads(payload)
            _srcmaps[sm["c_type"]] = sm
            gdb.write(f"[zuspec] loaded srcmap for {sm['component']}\n")
        except Exception:  # noqa: BLE001
            pass


if gdb is not None:
    gdb.events.new_objfile.connect(lambda _e: _load_srcmaps_via_symbols())
    _load_srcmaps_via_symbols()


# ---------------------------------------------------------------------------
# Pretty-printer: ZspComponentPrinter
# ---------------------------------------------------------------------------

class ZspComponentPrinter:
    """Hide internal fields; apply bit-width masking; label with Python names."""

    def __init__(self, val, sm: dict) -> None:
        self.val = val
        self.sm  = sm

    def to_string(self) -> str:
        return f"{self.sm['component']} (Zuspec component)"

    def children(self):
        hidden = set(
            self.sm.get("nxt_fields", []) + self.sm.get("coro_fields", [])
        )
        for fd in self.sm.get("fields", []):
            c_name = fd["c_name"]
            if c_name in hidden:
                continue
            try:
                raw = int(self.val[c_name])
                w   = fd.get("width", 64)
                masked = raw & ((1 << w) - 1) if w < 64 else raw
                yield fd["src_name"], masked
            except Exception:  # noqa: BLE001
                yield fd["src_name"], "<unavailable>"

    def display_hint(self) -> str:
        return "map"


def _register_printers() -> None:
    global gdb
    if gdb is None:
        return
    try:
        import gdb.printing  # type: ignore[import]
    except ImportError:
        return
    pp = gdb.printing.RegexpCollectionPrettyPrinter("zuspec")
    for ctype, sm in _srcmaps.items():
        pp.add_printer(ctype, f"^{ctype}$",
                       lambda v, s=sm: ZspComponentPrinter(v, s))
    gdb.printing.register_pretty_printer(None, pp, replace=True)


_register_printers()


# ---------------------------------------------------------------------------
# Frame filter: synthetic coroutine frames from zsp_coro_top linked list
# ---------------------------------------------------------------------------

class ZspLocalVar:
    def __init__(self, name: str, val) -> None:
        self._name = name
        self._val  = val

    def sym(self):
        return self._name

    def value(self):
        return self._val


class ZspCoroFrameDecorator:
    """One synthetic frame for a suspended (or active) zuspec coroutine."""

    def __init__(self, info: dict) -> None:
        self._info = info

    def function(self) -> str:
        return f"[zsp-coro] {self._info['name']}"

    def filename(self):
        return self._info.get("file")

    def line(self):
        return self._info.get("line")

    def frame_args(self):
        return None

    def frame_locals(self):
        return None


class ZspFrameIterator:
    """Wraps native GDB frame iterator, appending synthetic coroutine frames."""

    def __init__(self, native) -> None:
        self._native = native

    def __iter__(self):
        yield from self._native
        if gdb is None:
            return
        try:
            head = gdb.parse_and_eval("zsp_coro_top")
        except gdb.error:
            return
        while int(head) != 0:
            try:
                info = {
                    "name": head["co_name"].string(),
                    "file": head["loc"]["file"].string(),
                    "line": int(head["loc"]["line"]),
                }
            except Exception:  # noqa: BLE001
                break
            yield ZspCoroFrameDecorator(info)
            head = head["prev"]


class ZspFrameFilter:
    name     = "ZuspecCoroutines"
    priority = 100
    enabled  = True

    def filter(self, frame_iter):
        return ZspFrameIterator(frame_iter)


if gdb is not None:
    gdb.frame_filters[ZspFrameFilter.name] = ZspFrameFilter()


# ---------------------------------------------------------------------------
# Custom GDB commands
# ---------------------------------------------------------------------------

if gdb is not None:

    class ZsBt(gdb.Command):
        """zs-bt — show Zuspec coroutine chain in Python source terms."""

        def __init__(self) -> None:
            super().__init__("zs-bt", gdb.COMMAND_STACK)

        def invoke(self, arg: str, from_tty: bool) -> None:
            frame = gdb.newest_frame()
            while frame:
                sal = frame.find_sal()
                fn  = frame.name() or "?"
                if sal and sal.symtab:
                    gdb.write(f"  {fn}  at {sal.symtab.filename}:{sal.line}\n")
                else:
                    gdb.write(f"  {fn}  at <unknown>\n")
                frame = frame.older()
            try:
                head = gdb.parse_and_eval("zsp_coro_top")
                while int(head) != 0:
                    name = head["co_name"].string()
                    f    = head["loc"]["file"].string()
                    l    = int(head["loc"]["line"])
                    gdb.write(f"  [suspended] {name}  at {f}:{l}\n")
                    head = head["prev"]
            except gdb.error:
                pass

    ZsBt()

    class ZsBreak(gdb.Command):
        """zs-break file.py:line — set a breakpoint at a Python source location.

        Because #line directives redirect DWARF, this is equivalent to
        ``break file.py:line`` — provided as a named alias for discoverability.
        """

        def __init__(self) -> None:
            super().__init__("zs-break", gdb.COMMAND_BREAKPOINTS)

        def invoke(self, arg: str, from_tty: bool) -> None:
            gdb.execute(f"break {arg.strip()}")

    ZsBreak()

    class ZsPrint(gdb.Command):
        """zs-print EXPR — display component fields with Python names."""

        def __init__(self) -> None:
            super().__init__("zs-print", gdb.COMMAND_DATA)

        def invoke(self, arg: str, from_tty: bool) -> None:
            try:
                val = gdb.parse_and_eval(arg.strip())
            except gdb.error as e:
                gdb.write(f"zs-print: {e}\n")
                return
            t  = str(val.type.strip_typedefs())
            sm = _srcmaps.get(t)
            if sm is None:
                gdb.write(f"No zuspec source map for type '{t}'\n")
                return
            hidden = set(sm.get("nxt_fields", []) + sm.get("coro_fields", []))
            for fd in sm.get("fields", []):
                if fd["c_name"] in hidden:
                    continue
                try:
                    raw = int(val[fd["c_name"]])
                    w   = fd.get("width", 64)
                    masked = raw & ((1 << w) - 1) if w < 64 else raw
                    gdb.write(f"  {fd['src_name']:20s} = {masked}\n")
                except Exception:  # noqa: BLE001
                    gdb.write(f"  {fd['src_name']:20s} = <unavailable>\n")

    ZsPrint()

    class ZsCoro(gdb.Command):
        """zs-coro — list all active Zuspec coroutines and their Python location."""

        def __init__(self) -> None:
            super().__init__("zs-coro", gdb.COMMAND_STATUS)

        def invoke(self, arg: str, from_tty: bool) -> None:
            try:
                head = gdb.parse_and_eval("zsp_coro_top")
            except gdb.error:
                gdb.write("zsp_coro_top not found — is this a debug build?\n")
                return
            if int(head) == 0:
                gdb.write("No active Zuspec coroutines.\n")
                return
            i = 0
            while int(head) != 0:
                try:
                    name = head["co_name"].string()
                    f    = head["loc"]["file"].string()
                    l    = int(head["loc"]["line"])
                    gdb.write(f"  [{i}] {name:<24s}  {f}:{l}\n")
                    head = head["prev"]
                    i += 1
                except Exception:  # noqa: BLE001
                    break

    ZsCoro()
