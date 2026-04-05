"""
Resource component fixtures for ResourceLowerPass tests.

Must be in a source file so inspect.getsource() can find it.
"""
import zuspec.dataclasses as zdc
from zuspec.dataclasses.types import ClaimPool


@zdc.dataclass
class Worker(zdc.Component):
    pass


@zdc.dataclass
class PoolComp(zdc.Component):
    pool: ClaimPool[Worker] = zdc.field()

    async def do_work(self):
        async with self.pool.lock() as unit:
            pass
