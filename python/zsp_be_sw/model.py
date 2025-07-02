import ctypes
import dataclasses as dc
from typing import Any, Dict, List
from .model_types import zsp_actor_type_t, mk_signature, Signature
from .actor_type import ActorType
from .import_linker import ImportLinker
from .import_linker_scope import ImportLinkerScope
from .scheduler import Scheduler

@dc.dataclass
class Model(object):
    api_t : Any
    signatures : List[Signature] = dc.field(default_factory=list)
    actor_type_m : Dict[str,ActorType] = dc.field(default_factory=dict)

    @property
    def actor_types(self):
        return self.actor_type_m.keys()
    
    def mk_actor(self, type=None, sched : Scheduler = None, linker : ImportLinkerScope=None):
        if type is None:
            if len(self.actor_type_m) != 1:
                raise Exception("Must specify actor type: (%s)" % ",".join(self.actor_type_m.keys()))
            else:
                type = next(iter(self.actor_type_m.keys()))
        if sched is None:
            sched = Scheduler.default()
        if linker is None:
            linker = ImportLinkerScope(uplevel=1)
        return self.actor_type_m[type].mk(sched, linker)
    
    @staticmethod
    def load(file) -> 'Model':
        model_lib = ctypes.cdll.LoadLibrary(file)

        model_get_import_types = model_lib.model_get_import_types
        model_get_import_types.restype = ctypes.POINTER(ctypes.c_char_p)

        model_get_actor_types = model_lib.model_get_actor_types
        model_get_actor_types.restype = ctypes.POINTER(ctypes.POINTER(zsp_actor_type_t))

        methods = model_get_import_types()

        signatures = []
        signatures.append(Signature(
            name="print",
            istask=False,
            ftype=ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_char_p),
            rtype=None,
            ptypes=[ctypes.c_void_p, ctypes.c_char_p]))
        signatures.append(Signature(
            name="message",
            istask=False,
            ftype=ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_char_p),
            rtype=None,
            ptypes=[ctypes.c_void_p, ctypes.c_char_p]))

        fields = [
            ("print", ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_char_p)),
            ("message", ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_char_p))
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

        actors = model_get_actor_types()

        ret = Model(api_t=api_t, signatures=signatures)

        i=0
        while actors[i]:
            actor_type = ActorType(ret, actors[i])
            ret.actor_type_m[actor_type.name] = actor_type
            i += 1

        return ret

