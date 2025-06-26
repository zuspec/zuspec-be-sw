import ctypes
import dataclasses as dc
from typing import Any, Dict, List
from .model_types import zsp_actor_type_t, mk_signature
from .actor_type import ActorType

@dc.dataclass
class Model(object):
    api_t : Any
    actor_type_m : Dict[str,ActorType] = dc.field(default_factory=dict)
    
    @staticmethod
    def load(file) -> 'Model':
        model_lib = ctypes.cdll.LoadLibrary(file)

        zsp_get_method_types = model_lib.zsp_get_method_types
        zsp_get_method_types.restype = ctypes.POINTER(ctypes.c_char_p)

        zsp_get_actor_types = model_lib.zsp_get_actor_types
        zsp_get_actor_types.restype = ctypes.POINTER(ctypes.POINTER(zsp_actor_type_t))

        methods = zsp_get_method_types()

        fields = [
            ("print", ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_char_p))
        ]
        i=0
        while methods[i]:
            print("method[%d] %s" % (i, methods[i].decode()))
            fname, ftype = mk_signature(methods[i].decode())
            fields.append((fname, ftype))
            i += 1

        api_t = type("api_t", (ctypes.Structure,), {
            "_fields_": fields
        })

        actors = zsp_get_actor_types()

        ret = Model(api_t=api_t)

        i=0
        while actors[i]:
            actor_type = ActorType(api_t, actors[i])
            ret.actor_type_m[actor_type.name] = actor_type
            i += 1

        return ret

