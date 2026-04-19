"""CObjFactory — compile a zdc.Component to a shared library and wrap it.

``CObjFactory`` is a drop-in replacement for the Python ``ObjFactory``
(from ``zuspec.dataclasses``).  The same pytest fixtures that work with the
pure-Python runtime can be run against generated C code by swapping the
factory class.

Usage::

    from zuspec.be.sw import CObjFactory

    factory = CObjFactory()
    core = factory.mkComponent(RVCore)
    core.pc = 0x0
    factory.bind_callable(core, "icache", my_fetch_fn)
    factory.run(core)
"""
from __future__ import annotations

import ctypes
import hashlib
import importlib.util
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Type

from zuspec.dataclasses.data_model_factory import DataModelFactory
from zuspec.be.sw.compiler import CCompiler
from zuspec.be.sw.passes.c_emit import _collect_field_meta, _FieldMeta
from zuspec.be.sw.pipeline import SwPassManager


# ---------------------------------------------------------------------------
# _RegFileProxy — BackdoorRegFile protocol implementation over C accessors
# ---------------------------------------------------------------------------

class _RegFileProxy:
    """Proxy implementing the ``BackdoorRegFile`` protocol via C accessor calls.

    Supports both subscript syntax (``proxy[idx]``) for legacy code and the
    ``BackdoorRegFile`` protocol methods (``get``, ``set``, ``get_all``) for
    backend-agnostic test code.

    Parameters
    ----------
    lib:
        Loaded ``ctypes.CDLL``.
    ptr:
        ``c_void_p`` pointing at the parent component struct.
    comp_name:
        C type name of the component (e.g. ``"MiniCore"``).
    field_name:
        Name of the IndexedRegFile field (e.g. ``"regfile"``).
    meta:
        The ``_FieldMeta`` entry for this field.
    """

    __slots__ = ("_lib", "_ptr", "_comp_name", "_field_name", "_meta")

    def __init__(
        self,
        lib: ctypes.CDLL,
        ptr: ctypes.c_void_p,
        comp_name: str,
        field_name: str,
        meta: _FieldMeta,
    ) -> None:
        object.__setattr__(self, "_lib", lib)
        object.__setattr__(self, "_ptr", ptr)
        object.__setattr__(self, "_comp_name", comp_name)
        object.__setattr__(self, "_field_name", field_name)
        object.__setattr__(self, "_meta", meta)

    # ------------------------------------------------------------------
    # BackdoorRegFile protocol
    # ------------------------------------------------------------------

    def get(self, idx: int) -> int:
        """Read register *idx* directly via C accessor."""
        lib = object.__getattribute__(self, "_lib")
        ptr = object.__getattribute__(self, "_ptr")
        comp = object.__getattribute__(self, "_comp_name")
        field = object.__getattribute__(self, "_field_name")
        return getattr(lib, f"{comp}_{field}_get")(ptr, idx)

    def set(self, idx: int, val: int) -> None:
        """Write *val* into register *idx* via C accessor.

        Writing register 0 (x0) is handled by the generated C accessor
        (it applies the same hardwired-zero convention as ``IndexedRegFileRT``).
        """
        lib = object.__getattribute__(self, "_lib")
        ptr = object.__getattribute__(self, "_ptr")
        comp = object.__getattribute__(self, "_comp_name")
        field = object.__getattribute__(self, "_field_name")
        getattr(lib, f"{comp}_{field}_set")(ptr, idx, val)

    def get_all(self) -> list:
        """Return all register values as a plain list (index 0 first).

        Uses the C ``_read_all`` bulk accessor for efficiency.
        """
        meta = object.__getattribute__(self, "_meta")
        lib = object.__getattribute__(self, "_lib")
        ptr = object.__getattribute__(self, "_ptr")
        comp = object.__getattribute__(self, "_comp_name")
        field = object.__getattribute__(self, "_field_name")
        ArrayType = ctypes.c_uint32 * meta.depth
        buf = ArrayType()
        getattr(lib, f"{comp}_{field}_read_all")(ptr, buf, meta.depth)
        return list(buf)

    # ------------------------------------------------------------------
    # Subscript convenience (kept for backwards compatibility)
    # ------------------------------------------------------------------

    def __getitem__(self, idx: int) -> int:
        return self.get(idx)

    def __setitem__(self, idx: int, val: int) -> None:
        self.set(idx, val)


class _MemoryProxy:
    """Proxy implementing the ``BackdoorMemory`` protocol via C backdoor calls.

    Supports both element-level access (``read``/``write``) and byte-level bulk
    access (``read_bytes``/``write_bytes``) for backend-agnostic test code.

    Parameters
    ----------
    lib:
        Loaded ``ctypes.CDLL``.
    ptr:
        ``c_void_p`` pointing at the parent component struct.
    comp_name:
        C type name of the component (e.g. ``"RVCore"``).
    field_name:
        Name of the Memory field (e.g. ``"mem"``).
    meta:
        The ``_FieldMeta`` entry for this field (provides ``mem_size``,
        ``elem_bits``).
    """

    __slots__ = ("_lib", "_ptr", "_comp_name", "_field_name", "_meta")

    def __init__(
        self,
        lib: ctypes.CDLL,
        ptr: ctypes.c_void_p,
        comp_name: str,
        field_name: str,
        meta: _FieldMeta,
    ) -> None:
        object.__setattr__(self, "_lib", lib)
        object.__setattr__(self, "_ptr", ptr)
        object.__setattr__(self, "_comp_name", comp_name)
        object.__setattr__(self, "_field_name", field_name)
        object.__setattr__(self, "_meta", meta)

    def _read_fn(self):
        lib = object.__getattribute__(self, "_lib")
        comp = object.__getattribute__(self, "_comp_name")
        field = object.__getattribute__(self, "_field_name")
        return getattr(lib, f"{comp}_mem_read_{field}")

    def _write_fn(self):
        lib = object.__getattribute__(self, "_lib")
        comp = object.__getattribute__(self, "_comp_name")
        field = object.__getattribute__(self, "_field_name")
        return getattr(lib, f"{comp}_mem_write_{field}")

    # ------------------------------------------------------------------
    # BackdoorMemory protocol (element access)
    # ------------------------------------------------------------------

    def read(self, addr: int) -> int:
        """Read element at *addr* (element index, not byte offset)."""
        ptr = object.__getattribute__(self, "_ptr")
        return self._read_fn()(ptr, addr)

    def write(self, addr: int, val: int) -> None:
        """Write *val* to element at *addr* (element index, not byte offset)."""
        ptr = object.__getattribute__(self, "_ptr")
        self._write_fn()(ptr, addr, val)

    # ------------------------------------------------------------------
    # Byte-level bulk access
    # ------------------------------------------------------------------

    def read_bytes(self, byte_addr: int, count: int) -> bytes:
        """Read *count* bytes starting at *byte_addr*."""
        meta = object.__getattribute__(self, "_meta")
        elem_bytes = (meta.elem_bits + 7) // 8
        results = bytearray()
        for i in range(count):
            byte_off = byte_addr + i
            elem_idx = byte_off // elem_bytes
            byte_in_elem = byte_off % elem_bytes
            elem_val = self.read(elem_idx)
            results.append((elem_val >> (8 * byte_in_elem)) & 0xFF)
        return bytes(results)

    def write_bytes(self, byte_addr: int, data: bytes) -> None:
        """Write *data* bytes starting at *byte_addr*."""
        meta = object.__getattribute__(self, "_meta")
        elem_bytes = (meta.elem_bits + 7) // 8
        mask = (1 << meta.elem_bits) - 1
        for i, b in enumerate(data):
            byte_off = byte_addr + i
            elem_idx = byte_off // elem_bytes
            byte_in_elem = byte_off % elem_bytes
            cur = self.read(elem_idx)
            cur = (cur & ~(0xFF << (8 * byte_in_elem))) | (b << (8 * byte_in_elem))
            self.write(elem_idx, cur & mask)


# ---------------------------------------------------------------------------
# ComponentProxy
# ---------------------------------------------------------------------------

class ComponentProxy:
    """Python wrapper around a C component instance.

    Attributes
    ----------
    _c_lib:
        The ``ctypes.CDLL`` handle for the compiled shared library.
    _c_ptr:
        ``ctypes.c_void_p`` pointer to the allocated component struct.
    _c_name:
        The C type name (e.g. ``"SimpleComp"``).
    _c_fmeta:
        Mapping from field name to ``_FieldMeta`` — used for access control.
    _c_type_m:
        IR type map from the SW context — used to look up sub-component dtypes
        when building sub-component proxies.
    _c_methods:
        Mapping from method name to a bound callable that executes the method
        through the C struct (currently executed via a Python shim that
        reads/writes through the C accessors).
    """

    __slots__ = ("_c_lib", "_c_ptr", "_c_name", "_c_fmeta", "_c_buf", "_c_callbacks", "_c_methods", "_c_type_m")

    def __init__(
        self,
        lib: ctypes.CDLL,
        ptr: ctypes.c_void_p,
        name: str,
        fmeta: Dict[str, _FieldMeta],
        methods: Optional[Dict[str, Any]] = None,
        type_m: Optional[Dict[str, Any]] = None,
    ) -> None:
        object.__setattr__(self, "_c_lib", lib)
        object.__setattr__(self, "_c_ptr", ptr)
        object.__setattr__(self, "_c_name", name)
        object.__setattr__(self, "_c_fmeta", fmeta)
        object.__setattr__(self, "_c_buf", None)
        object.__setattr__(self, "_c_callbacks", {})
        object.__setattr__(self, "_c_methods", methods or {})
        object.__setattr__(self, "_c_type_m", type_m or {})

    def __getattr__(self, attr: str) -> Any:
        # Check method registry first
        methods: Dict[str, Any] = object.__getattribute__(self, "_c_methods")
        if attr in methods:
            return methods[attr]

        fmeta: Dict[str, _FieldMeta] = object.__getattribute__(self, "_c_fmeta")
        lib = object.__getattribute__(self, "_c_lib")
        ptr = object.__getattribute__(self, "_c_ptr")
        name = object.__getattribute__(self, "_c_name")
        m = fmeta.get(attr)
        if m is not None:
            if m.kind == "plain" and m.accessible:
                getter = getattr(lib, f"{name}_get_{attr}")
                return getter(ptr)
            if m.kind == "indexed_regfile":
                return _RegFileProxy(lib, ptr, name, attr, m)
            if m.kind == "memory":
                return _MemoryProxy(lib, ptr, name, attr, m)
            if m.kind == "component":
                return self._get_subcomp_proxy(lib, ptr, name, attr, m)
        raise AttributeError(
            f"'{type(self).__name__}' has no accessible attribute '{attr}'"
        )

    def _get_subcomp_proxy(
        self,
        lib: ctypes.CDLL,
        ptr: ctypes.c_void_p,
        name: str,
        field_name: str,
        m: _FieldMeta,
    ) -> "ComponentProxy":
        """Return a ComponentProxy for an embedded sub-component field."""
        ptr_fn = getattr(lib, f"{name}_ptr_{field_name}")
        sub_ptr = ptr_fn(ptr)
        type_m = object.__getattribute__(self, "_c_type_m")
        from zuspec.dataclasses import ir as _ir
        sub_dtype = type_m.get(m.comp_type)
        sub_fmeta: Dict[str, _FieldMeta] = {}
        if sub_dtype is not None and isinstance(sub_dtype, _ir.DataTypeComponent):
            class _FakeCtxt:
                pass
            fake = _FakeCtxt()
            fake.type_m = type_m  # type: ignore[attr-defined]
            fake.py_globals = {}  # type: ignore[attr-defined]
            sub_fmeta = _collect_field_meta(sub_dtype, fake)  # type: ignore[arg-type]
        return ComponentProxy(lib, sub_ptr, m.comp_type, sub_fmeta, type_m=type_m)

    def __setattr__(self, attr: str, value: Any) -> None:
        if attr in ComponentProxy.__slots__:
            object.__setattr__(self, attr, value)
            return
        fmeta: Dict[str, _FieldMeta] = object.__getattribute__(self, "_c_fmeta")
        m = fmeta.get(attr)
        if m is not None and m.kind == "plain" and m.accessible:
            lib = object.__getattribute__(self, "_c_lib")
            ptr = object.__getattribute__(self, "_c_ptr")
            name = object.__getattribute__(self, "_c_name")
            setter = getattr(lib, f"{name}_set_{attr}")
            setter(ptr, value)
            return
        raise AttributeError(
            f"'{type(self).__name__}' has no accessible attribute '{attr}'"
        )


# ---------------------------------------------------------------------------
# CObjFactory
# ---------------------------------------------------------------------------

_DEFAULT_CACHE_DIR = Path(tempfile.gettempdir()) / "zuspec_be_sw_cache"


class CObjFactory:
    """Compile-and-cache factory for C-backed component proxies.

    Parameters
    ----------
    cache_dir:
        Directory in which compiled ``.so`` files are stored.  Defaults to
        ``$TMPDIR/zuspec_be_sw_cache``.
    debug:
        When ``True`` the compiled library is built with ``-g -O0``; when
        ``False`` ``-O2`` is used.  Does not affect the cache key.
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        debug: bool = False,
    ) -> None:
        self.cache_dir = Path(cache_dir) if cache_dir else _DEFAULT_CACHE_DIR
        self.debug = debug
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        # In-process cache: type_name -> (lib, fmeta)
        self._lib_cache: Dict[str, tuple] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def mkComponent(self, cls: Type) -> ComponentProxy:
        """Compile *cls* to C and return a proxy instance.

        The shared library is cached by class name + module.  A second call
        with the same class reuses the compiled ``.so`` without recompiling.

        Parameters
        ----------
        cls:
            A ``zdc.Component`` subclass decorated with ``@zdc.dataclass``.

        Returns
        -------
        ComponentProxy
            Thin Python wrapper around an allocated C struct.
        """
        type_name = cls.__name__
        cache_key = f"{cls.__module__}.{type_name}"

        if cache_key in self._lib_cache:
            lib, fmeta, unbound_methods, type_m = self._lib_cache[cache_key]
        else:
            lib, fmeta, unbound_methods, type_m = self._compile_and_load(cls, type_name)
            self._lib_cache[cache_key] = (lib, fmeta, unbound_methods, type_m)

        # Allocate C struct — use 64 KiB to be safe for any component
        import ctypes as _ct
        size = 65536

        buf = (_ct.c_uint8 * size)()
        ptr = _ct.cast(buf, _ct.c_void_p)

        # Initialise
        init_fn = getattr(lib, f"{type_name}_init")
        init_fn(ptr)

        proxy = ComponentProxy(lib, ptr, type_name, fmeta, type_m=type_m)
        # Keep buf alive via the proxy
        object.__setattr__(proxy, "_c_buf", buf)

        # Bind methods to this proxy instance
        bound: Dict[str, Any] = {}
        if unbound_methods:
            for mname, meth in unbound_methods.items():
                bound[mname] = (lambda m, p=proxy: lambda *args, **kw: m(p, *args, **kw))(meth)

        # Always expose run() and halt() on the proxy
        _run_fn = getattr(lib, f"{type_name}_run")
        _run_fn.argtypes = [ctypes.c_void_p]
        _run_fn.restype = None
        _captured_ptr = ptr
        bound.setdefault("run", lambda: _run_fn(_captured_ptr))

        _halt_fn = getattr(lib, f"{type_name}_halt", None)
        if _halt_fn is not None:
            _halt_fn.argtypes = [ctypes.c_void_p]
            _halt_fn.restype = None
            bound.setdefault("halt", lambda: _halt_fn(_captured_ptr))

        _req_halt_fn = getattr(lib, f"{type_name}_request_halt", None)
        if _req_halt_fn is not None:
            _req_halt_fn.argtypes = [ctypes.c_void_p]
            _req_halt_fn.restype = None
            bound.setdefault("request_halt", lambda: _req_halt_fn(_captured_ptr))

        object.__setattr__(proxy, "_c_methods", bound)

        return proxy

    def run(self, proxy: ComponentProxy) -> None:
        """Call ``{name}_run()`` on the component."""
        name = object.__getattribute__(proxy, "_c_name")
        lib = object.__getattribute__(proxy, "_c_lib")
        ptr = object.__getattribute__(proxy, "_c_ptr")
        run_fn = getattr(lib, f"{name}_run")
        run_fn(ptr)

    def bind_callable(
        self,
        proxy: ComponentProxy,
        port_name: str,
        fn: Any,
        ud: Any = None,
    ) -> None:
        """Bind a synchronous Python callable to a CallablePort.

        Parameters
        ----------
        proxy:
            The component proxy returned by :meth:`mkComponent`.
        port_name:
            Name of the callable port field (e.g. ``"icache"``).
        fn:
            A Python callable (must be synchronous).
        ud:
            Optional user-data pointer.  Defaults to ``None``.
        """
        import ctypes as _ct
        name = object.__getattribute__(proxy, "_c_name")
        lib = object.__getattribute__(proxy, "_c_lib")
        ptr = object.__getattribute__(proxy, "_c_ptr")
        fmeta = object.__getattribute__(proxy, "_c_fmeta")

        m = fmeta.get(port_name)
        if m is None or m.kind != "callable_port":
            raise ValueError(
                f"'{port_name}' is not a callable port on {name}"
            )

        arg_bits = m.callable_arg_bits or [32]
        ret_t = getattr(_ct, f"c_uint{m.callable_ret_bits}", _ct.c_uint32)
        arg_types = [getattr(_ct, f"c_uint{b}", _ct.c_uint32) for b in arg_bits]
        cfunc_type = _ct.CFUNCTYPE(ret_t, _ct.c_void_p, *arg_types)

        # Strip the leading ``void *ud`` from the C signature before forwarding
        # to the Python callable, which only takes the semantic arguments.
        _fn = fn
        def _wrapper(ud, *args):
            return _fn(*args)

        c_fn = cfunc_type(_wrapper)
        # Keep c_fn alive via the proxy to prevent GC
        _store = getattr(proxy, "_c_callbacks", {})  # type: ignore[union-attr]
        _store[port_name] = c_fn
        try:
            object.__setattr__(proxy, "_c_callbacks", _store)
        except Exception:
            pass

        binder = getattr(lib, f"{name}_bind_{port_name}")
        ud_ptr = _ct.c_void_p(None)
        binder(ptr, c_fn, ud_ptr)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compile_and_load(
        self, cls: Type, type_name: str
    ) -> tuple:
        """Run pipeline, write files, compile, load .so, return (lib, fmeta)."""
        # Build IR
        ir_ctx = DataModelFactory().build(cls)

        # Run SW passes, passing module globals for Python name resolution
        import sys as _sys
        py_globals = getattr(_sys.modules.get(cls.__module__), "__dict__", {}) or {}
        sw_ctx = SwPassManager().run(ir_ctx, py_globals=py_globals)

        # Write generated files
        build_dir = self.cache_dir / type_name
        build_dir.mkdir(parents=True, exist_ok=True)

        c_sources = []
        abi_path: Optional[Path] = None
        for fname, content in sw_ctx.output_files:
            fpath = build_dir / fname
            fpath.write_text(content)
            if fname.endswith(".c"):
                c_sources.append(fpath)
            if fname.endswith("_abi.py"):
                abi_path = fpath

        # Compile to shared library
        so_path = build_dir / f"{type_name}.so"
        compiler = CCompiler(output_dir=build_dir)
        result = compiler.compile_shared(c_sources, so_path)
        if not result.success:
            raise RuntimeError(
                f"CObjFactory: C compilation failed for {type_name}:\n"
                f"{result.stderr}"
            )

        # Load library — use RTLD_LAZY so undefined helper symbols (e.g. static methods
        # inlined as C function calls) don't prevent loading when they're never called.
        import os as _os
        lib = ctypes.CDLL(str(so_path), mode=_os.RTLD_LAZY)

        # Configure ctypes signatures via ABI sidecar
        if abi_path is not None and abi_path.exists():
            spec = importlib.util.spec_from_file_location(
                f"_abi_{type_name}", str(abi_path)
            )
            abi_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(abi_mod)  # type: ignore[union-attr]
            abi_mod.configure(lib)

        # Build fmeta from IR
        dtype = sw_ctx.type_m.get(type_name)
        fmeta: Dict[str, _FieldMeta] = {}
        methods: Dict[str, Any] = {}
        if dtype is not None:
            from zuspec.dataclasses import ir
            if isinstance(dtype, ir.DataTypeComponent):
                fmeta = _collect_field_meta(dtype, sw_ctx)
                methods = self._build_method_shims(cls, dtype, fmeta, lib)
                # Expose C-compiled process entry functions (those with params)
                methods.update(
                    self._build_process_method_wrappers(type_name, dtype, sw_ctx, lib)
                )

        return lib, fmeta, methods, sw_ctx.type_m

    def _build_method_shims(
        self,
        cls: Type,
        dtype: Any,
        fmeta: Dict[str, _FieldMeta],
        lib: ctypes.CDLL,
    ) -> Dict[str, Any]:
        """Build Python-shim callables for component methods.

        For each regular (non-async) Python method on *cls*, build a wrapper
        that executes the Python body using the proxy as ``self``, so that
        field reads/writes go through the C accessors.

        Also adds synthetic stub methods for process management and timebase
        operations (``start_processes``, ``timebase_current_time``,
        ``timebase_advance``) when the component has ``@zdc.process`` members.
        """
        import inspect

        _INTERNAL = frozenset(
            ("__bind__", "__init__", "__init_subclass__", "__class_getitem__",
             "shutdown", "time", "wait", "reset_count")
        )

        shims: Dict[str, Any] = {}

        # Detect whether any process IR nodes exist (before member inspection, since
        # @zdc.process decorators replace the function with a descriptor that
        # inspect.isfunction won't recognise)
        process_names = {
            func.name
            for func in list(getattr(dtype, "functions", [])) + list(getattr(dtype, "proc_processes", []))
            if type(func).__name__ == "Process"
        }
        has_process = bool(process_names)

        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if name.startswith("_"):
                continue
            if name in _INTERNAL:
                continue
            if name in process_names:
                continue

            shims[name] = method  # Store unbound; will bind to proxy on retrieval

        # Add synthetic stubs for process management if any processes exist
        if has_process:
            shims.setdefault("start_processes", lambda *a, **kw: None)
            shims.setdefault("timebase_current_time", lambda *a, **kw: 0)
            shims.setdefault("timebase_advance", lambda *a, **kw: None)

        return shims

    def _build_process_method_wrappers(
        self,
        type_name: str,
        dtype: Any,
        sw_ctx: Any,
        lib: ctypes.CDLL,
    ) -> Dict[str, Any]:
        """Expose C-compiled process entry functions (those that have parameters).

        Covers two cases:
          1. Sync-convertible @process with params → ``{TypeName}_{func}(self, ...)``
          2. Async @process with params (has coroutine entry wrapper) → same signature

        Returns a dict of ``func_name → bound-callable`` that can be merged into the
        methods dict for a ComponentProxy.
        """
        from zuspec.be.sw.ir.coroutine import SwCoroutineFrame
        from zuspec.be.sw.passes.c_emit import _c_type_from_annotation

        _CTYPES_FROM_C = {
            "uint8_t":  ctypes.c_uint8,
            "uint16_t": ctypes.c_uint16,
            "uint32_t": ctypes.c_uint32,
            "uint64_t": ctypes.c_uint64,
            "int8_t":   ctypes.c_int8,
            "int16_t":  ctypes.c_int16,
            "int32_t":  ctypes.c_int32,
            "int64_t":  ctypes.c_int64,
            "float":    ctypes.c_float,
            "double":   ctypes.c_double,
            "void":     None,
        }

        wrappers: Dict[str, Any] = {}
        nodes = sw_ctx.sw_nodes.get(type_name, [])

        # Case 1: sync-convertible @process functions with params
        for func in getattr(dtype, "functions", []):
            meta = getattr(func, "metadata", {}) or {}
            if not meta.get("is_process"):
                continue
            if not meta.get("sync_convertible"):
                continue
            args = getattr(func.args, "args", []) if func.args else []
            if not args:
                continue
            c_fn_name = f"{type_name}_{func.name}"
            c_fn = getattr(lib, c_fn_name, None)
            if c_fn is None:
                continue
            param_ctypes = []
            for arg in args:
                c_t_str = _c_type_from_annotation(getattr(arg, "annotation", None), sw_ctx)
                param_ctypes.append(_CTYPES_FROM_C.get(c_t_str, ctypes.c_uint32))
            if func.returns is None:
                ret_ct = None
            else:
                from zuspec.be.sw.passes.c_emit import _c_type
                ret_t_str = _c_type(func.returns, sw_ctx)
                ret_ct = _CTYPES_FROM_C.get(ret_t_str, ctypes.c_uint32)
            c_fn.argtypes = [ctypes.c_void_p] + param_ctypes
            c_fn.restype = ret_ct
            func_name = func.name

            def _make_sync_wrapper(fn, param_cts):
                def _wrapper(proxy_self, *args):
                    ptr = object.__getattribute__(proxy_self, "_c_ptr")
                    casted = [ctypes.cast(ptr, ctypes.c_void_p)]
                    for val, ct in zip(args, param_cts):
                        casted.append(ct(val))
                    return fn(*casted)
                return _wrapper

            wrappers[func_name] = _make_sync_wrapper(c_fn, param_ctypes)

        # Case 2: coroutine frames with process_params (async @process entry wrappers)
        for node in nodes:
            if not isinstance(node, SwCoroutineFrame):
                continue
            if not node.process_params:
                continue
            c_fn_name = node.func_name or ""
            if not c_fn_name:
                continue
            # Derive Python method name: strip "{TypeName}_" prefix
            meth_name = c_fn_name[len(type_name) + 1:] if c_fn_name.startswith(f"{type_name}_") else c_fn_name
            c_fn = getattr(lib, c_fn_name, None)
            if c_fn is None:
                continue
            param_ctypes = []
            for arg in node.process_params:
                c_t_str = _c_type_from_annotation(getattr(arg, "annotation", None), sw_ctx)
                param_ctypes.append(_CTYPES_FROM_C.get(c_t_str, ctypes.c_uint32))
            ret_ct = None  # async entry wrappers are void for now
            if node.return_dtype is not None:
                from zuspec.be.sw.passes.c_emit import _c_type
                ret_t_str = _c_type(node.return_dtype, sw_ctx)
                ret_ct = _CTYPES_FROM_C.get(ret_t_str)
            c_fn.argtypes = [ctypes.c_void_p] + param_ctypes
            c_fn.restype = ret_ct

            def _make_async_wrapper(fn, param_cts):
                def _wrapper(proxy_self, *args):
                    ptr = object.__getattribute__(proxy_self, "_c_ptr")
                    casted = [ctypes.cast(ptr, ctypes.c_void_p)]
                    for val, ct in zip(args, param_cts):
                        casted.append(ct(val))
                    return fn(*casted)
                return _wrapper

            wrappers[meth_name] = _make_async_wrapper(c_fn, param_ctypes)

        return wrappers
