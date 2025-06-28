import ctypes
import dataclasses as dc
from typing import ClassVar

@dc.dataclass
class Api(object):
    _inst : ClassVar = None
    _librt : ctypes.CDLL = None
    _zsp_alloc_malloc_create = None
    _zsp_scheduler_create = None
    _zsp_actor_start = None
    _zsp_actor_type = None

    def __post_init__(self):
        from zsp_be_sw import lib_rt
        from .actor_type import zsp_actor_type_t

        self._librt = ctypes.cdll.LoadLibrary(lib_rt())
        rt = self._librt

        self._zsp_alloc_malloc_create = rt.zsp_alloc_malloc_create
        self._zsp_alloc_malloc_create.restype = ctypes.c_void_p

        self._zsp_scheduler_create = rt.zsp_scheduler_create
        self._zsp_scheduler_create.argtypes = [ctypes.c_void_p]
        self._zsp_scheduler_create.restype = ctypes.c_void_p

        self._zsp_actor_type = rt.zsp_actor_type
        self._zsp_actor_type.restype = ctypes.POINTER(zsp_actor_type_t)

    @classmethod
    def inst(cls):
        if cls._inst is None:
            cls._inst = Api()
        return cls._inst

