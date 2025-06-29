import dataclasses as dc
import inspect as ins
from typing import Any
from .closure import Closure, TaskClosure
from .import_linker import ImportLinker
from .model_types import Signature

@dc.dataclass
class ImportLinkerScope(ImportLinker):
    """
    An ImportLinkerScope is a scope that can be used to resolve imports
    within a specific context, such as an actor or module.
    """
    scope : Any = None
    uplevel : int = 0

    _locals : dict = dc.field(default=None)
    _globals : dict = dc.field(default=None)

    def __post_init__(self):
        if self.scope is None:
            # Assume the caller is the scope
            stack = ins.stack()
            # [0] is __post_init__
            # [1] is __init__
            scope = stack[2+self.uplevel].frame

            self._locals = scope.f_locals
            self._globals = scope.f_globals

    def get_closure(self, sig : Signature, ):
        """
        Get a closure for the specified method. If the method is not found
        in the current scope, it will be searched in the global scope.
        """
        method = None
        closure = None

        if closure is None and sig.name in self._locals:
            method = self._locals[sig.name]
        
        if closure is None and "self" in self._locals:
            caller_self = self._locals["self"]
            if hasattr(caller_self, sig.name):
                method = getattr(caller_self, sig.name)

        if method is None and sig.name in self._globals:
            method = self._globals[sig.name]

        if method is not None:
            code = method.__code__
            if sig.istask:
                if not ins.iscoroutinefunction(method):
                    raise Exception("Require async") 
                closure = TaskClosure(sig, method)
            else:
                closure = Closure(sig, method)

            # TODO: Check arguments


        return closure