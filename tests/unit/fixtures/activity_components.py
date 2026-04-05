"""
Activity component fixtures for ActivityLowerPass tests.

These classes must live in a file so ActivityParser can call inspect.getsource().
"""
import zuspec.dataclasses as zdc


@zdc.dataclass
class Leaf(zdc.Action):
    pass


@zdc.dataclass
class SeqParent(zdc.Action):
    a: Leaf = zdc.field()
    b: Leaf = zdc.field()

    async def activity(self):
        await self.a()
        await self.b()


@zdc.dataclass
class ParParent(zdc.Action):
    a: Leaf = zdc.field()
    b: Leaf = zdc.field()

    async def activity(self):
        with zdc.parallel():
            await self.a()
            await self.b()


@zdc.dataclass
class SelectParent(zdc.Action):
    a: Leaf = zdc.field()
    b: Leaf = zdc.field()

    async def activity(self):
        with zdc.select():
            with zdc.branch():
                await self.a()
            with zdc.branch():
                await self.b()
