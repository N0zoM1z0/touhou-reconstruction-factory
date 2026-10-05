from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest


SCRIPT = Path(__file__).parents[1] / "scripts/ida-headless-stdio.py"
SPEC = importlib.util.spec_from_file_location("headless_ida_stdio", SCRIPT)
HEADLESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HEADLESS)


class HeadlessIdaTests(unittest.IsolatedAsyncioTestCase):
    async def test_tools_and_durable_save_execute_on_the_initialization_thread(self):
        kernel_thread = threading.get_ident()
        observations = []

        def operation(address: str) -> str:
            observations.append(("operation", threading.get_ident()))
            return address

        def save():
            observations.append(("save", threading.get_ident()))

        wrapped = HEADLESS.on_kernel_thread(operation, save=save)
        self.assertTrue(inspect.iscoroutinefunction(wrapped))
        self.assertEqual(inspect.signature(wrapped), inspect.signature(operation))
        self.assertEqual(await wrapped("0x401000"), "0x401000")
        self.assertEqual(observations, [("operation", kernel_thread), ("save", kernel_thread)])

    async def test_protocol_types_do_not_inherit_future_annotations_or_execute_tools(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "server_generated.py"
            source.write_text('''import sys
if sys.version_info >= (3, 12):
    from typing import TypedDict, Generic, TypeVar, Optional
else:
    from typing_extensions import TypedDict, Generic, TypeVar, Optional
T = TypeVar("T")
class Function(TypedDict):
    name: str
    prototype: Optional[str]
class Page(TypedDict, Generic[T]):
    data: list[T]
    next_offset: Optional[int]
raise RuntimeError("generated RPC startup must not execute")
''')
            types = HEADLESS.load_protocol_types(SimpleNamespace(__file__=str(root / "mcp-plugin.py")))
            self.assertIs(types["Function"].__annotations__["name"], str)
            self.assertEqual(types["Function"].__annotations__["prototype"], types["Optional"][str])
            original = types["Page"][types["Function"]]
            self.assertEqual(HEADLESS.protocol_annotation(original, types), original)
