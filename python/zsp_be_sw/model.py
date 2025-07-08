import ctypes
import dataclasses as dc
import sys
from typing import Any, Callable, Dict, List
from .action_t import ActionT
from .closure import Closure, TaskClosure
from .comp_t import CompT
from .model_types import zsp_actor_type_t, mk_signature, Signature
from .actor_type import ActorType
from .import_linker import ImportLinker
from .import_linker_scope import ImportLinkerScope
from .scheduler import Scheduler

class zsp_model_t(ctypes.Structure):
    _fields_ = [
        ("action_types", ctypes.POINTER(ctypes.c_void_p)),
        ("comp_types", ctypes.POINTER(ctypes.c_void_p)),
        ("methods", ctypes.POINTER(ctypes.c_char_p))
    ]

@dc.dataclass
class Model(object):
    api_t : Any
    signatures : List[Signature] = dc.field(default_factory=list)
    actor_type_m : Dict[str,ActorType] = dc.field(default_factory=dict)
    action_type_m : Dict[str,ActionT] = dc.field(default_factory=dict)
    comp_type_m : Dict[str,CompT] = dc.field(default_factory=dict)
    _dflt_func_m : Dict[str, Callable] = dc.field(default_factory=dict)

    def __post_init__(self):
        self._dflt_func_m.update({
            "print": self._print,
            "message": self._message,
        })

    def _print(self, msg):
        sys.stdout.write(msg.decode())

    def _message(self, level, msg):
        sys.stdout.write(msg.decode())

    @property
    def action_types(self):
        return self.action_type_m.keys()

    @property
    def comp_types(self):
        return self.comp_type_m.keys()
    
    def mk_actor(self, action_t, comp_t=None, sched : Scheduler = None, linker : ImportLinkerScope=None):
        from .actor import Actor
        from .api import Api

        api = Api.inst()
        if type(action_t) == str:
            action_t = self.action_type_m[action_t]

        if comp_t is None:
            if "pss_top" in self.comp_type_m.keys():
                comp_t = self.comp_type_m["pss_top"]
            else:
                raise Exception("No root component specified and pss_top doesn't exist")

        if sched is None:
            sched = Scheduler.default()
        if linker is None:
            linker = ImportLinkerScope(uplevel=1)

        imp_api = self.api_t()
        self.init_api(imp_api, linker)

        print("comp: %s action: %s" % (comp_t.name, action_t.name))
        actor = Actor(sched, comp_t.hndl, action_t.hndl, imp_api)

        return actor

    def init_api(self, api, linker : ImportLinker):
        i = 0
        for sig in self.signatures:
            name = sig.name
            print("name: %s, istask: %s" % (name, sig.istask), flush=True)

            impl = None

            # TODO: Search for an available implementation

            if impl is None and name in self._dflt_func_m.keys():
                if sig.istask:
                    impl = TaskClosure(
                        sig, 
                        self._dflt_func_m[name], 
                        self.sched)
                else:
                    impl = Closure(sig, self._dflt_func_m[name])
            
            if impl is None:
                impl = linker.get_closure(sig)

            if impl is None:
                raise Exception("No implementation found for %s" % name)

            setattr(api, name, sig.ftype(impl.func))
        pass
    
    @staticmethod
    def load(file) -> 'Model':
        model_lib = ctypes.cdll.LoadLibrary(file)

        pss_model = model_lib.pss_model
        pss_model.restype = ctypes.POINTER(zsp_model_t)

        model = pss_model()

        methods = model.contents.methods

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

        ret = Model(api_t=api_t, signatures=signatures)

        i=0
        while model.contents.action_types[i]:
            print("ActionT")
            action_t = ActionT.mk(model.contents.action_types[i])
            ret.action_type_m[action_t.name] = action_t
            i += 1

        i=0
        while model.contents.comp_types[i]:
            comp_t = CompT.mk(model.contents.comp_types[i])
            ret.comp_type_m[comp_t.name] = comp_t
            i += 1

        return ret

