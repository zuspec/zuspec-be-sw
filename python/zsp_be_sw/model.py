import ctypes
import dataclasses as dc
from typing import Any, Dict, List
from .model_types import zsp_actor_type_t, mk_signature, Signature
from .actor_type import ActorType
from .scheduler import Scheduler

@dc.dataclass
class Model(object):
    api_t : Any
    signatures : List[Signature] = dc.field(default_factory=list)
    actor_type_m : Dict[str,ActorType] = dc.field(default_factory=dict)

    @property
    def actor_types(self):
        return self.actor_type_m.keys()
    
    def mk_actor(self, type, sched):
        return self.actor_type_m[type].mk(sched)
    
    @staticmethod
    def load(file) -> 'Model':
        model_lib = ctypes.cdll.LoadLibrary(file)

        zsp_get_method_types = model_lib.zsp_get_method_types
        zsp_get_method_types.restype = ctypes.POINTER(ctypes.c_char_p)

        zsp_get_actor_types = model_lib.zsp_get_actor_types
        zsp_get_actor_types.restype = ctypes.POINTER(ctypes.POINTER(zsp_actor_type_t))

        methods = zsp_get_method_types()

        signatures = []
        signatures.append(Signature(
            name="print",
            istask=False,
            ftype=ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_char_p),
            rtype=None,
            ptypes=[ctypes.c_void_p, ctypes.c_char_p]))

        fields = [
            ("print", ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_char_p))
        ]
        i=0
        while methods[i]:
            sig = mk_signature(methods[i].decode())
            signatures.append(sig)
            fields.append((sig.name, sig.ftype))
            i += 1

        api_t = type("api_t", (ctypes.Structure,), {
            "_fields_": fields
        })

        for f in api_t._fields_:
            print("api_t field: %s %s" % (f[0], getattr(f[1], "_istask_", False)), flush=True)

        actors = zsp_get_actor_types()

        ret = Model(api_t=api_t, signatures=signatures)

        i=0
        while actors[i]:
            actor_type = ActorType(ret, actors[i])
            ret.actor_type_m[actor_type.name] = actor_type
            i += 1

        return ret

