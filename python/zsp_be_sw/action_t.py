import ctypes
import dataclasses as dc
from .zsp_object_type_s import zsp_object_type_s

@dc.dataclass
class ActionT(object):
    name : str
    hndl : ctypes.c_void_p

    @staticmethod
    def mk(hndl):
        action_t = ctypes.cast(hndl, ctypes.POINTER(zsp_object_type_s))
        return ActionT(action_t.contents.name.decode(), hndl)
