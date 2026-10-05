#!/usr/bin/env python3
"""Serve one operator-bound IDAlib database over stdio without opening a GUI.

Run with the installed IDA Python. Each game needs distinct input/database
paths. Factory independently attests the canonical PE and mapped database on
every session; this helper has no acceptance authority.
"""

from __future__ import annotations

import argparse
import ast
from contextlib import contextmanager, redirect_stdout
from functools import wraps
import importlib
import inspect
import os
from pathlib import Path
import sys
from types import ModuleType
import typing


@contextmanager
def database_lock(path: Path):
    """Coordinate game-bound IDAlib sessions across hot MCP instances."""
    import msvcrt

    with path.with_suffix(".factory.lock").open("a+b") as stream:
        stream.seek(0)
        stream.write(b"\0")
        stream.flush()
        stream.seek(0)
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            raise RuntimeError("headless IDA database is busy; retry after its active session finishes") from error
        try:
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


def load_protocol_types(plugin):
    """Reuse the installed stdio server's Python 3.11-compatible type schema."""
    path = Path(plugin.__file__).with_name("server_generated.py")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    nodes = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom, ast.ClassDef))
             or (isinstance(node, ast.If) and all(isinstance(item, (ast.Import, ast.ImportFrom))
                                                for item in node.body + node.orelse))
             or (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
                 and isinstance(node.value.func, ast.Name) and node.value.func.id == "TypeVar")]
    module = ModuleType("_factory_ida_protocol_types")
    sys.modules[module.__name__] = module
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec", dont_inherit=True), module.__dict__)
    return module.__dict__


def protocol_annotation(annotation, types):
    origin = typing.get_origin(annotation)
    if origin is None:
        if isinstance(annotation, type) and hasattr(annotation, "__required_keys__"):
            return types.get(annotation.__name__, annotation)
        return annotation
    arguments = typing.get_args(annotation)
    if origin is typing.Annotated:
        return typing.Annotated[protocol_annotation(arguments[0], types), *arguments[1:]]
    if hasattr(origin, "__required_keys__"):
        origin = types.get(origin.__name__, origin)
    return origin[tuple(protocol_annotation(argument, types) for argument in arguments)]


def on_kernel_thread(function, *, save=None, types=None):
    """FastMCP runs async tools on the IDAlib initialization thread."""
    @wraps(function)
    async def invoke(*args, **kwargs):
        result = function(*args, **kwargs)
        if save is not None:
            save()
        return result
    if types is not None:
        signature = inspect.signature(function)
        invoke.__signature__ = signature.replace(
            parameters=[parameter.replace(annotation=protocol_annotation(parameter.annotation, types))
                        for parameter in signature.parameters.values()],
            return_annotation=protocol_annotation(signature.return_annotation, types))
        invoke.__annotations__ = {key: protocol_annotation(value, types)
                                  for key, value in function.__annotations__.items()}
    return invoke


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--database", required=True, type=Path)
    args = parser.parse_args()
    source = args.input.resolve(strict=True)
    database = args.database.resolve()
    if database.suffix.lower() != ".i64" or source == database:
        parser.error("--database must name a separate .i64 file")
    database.parent.mkdir(parents=True, exist_ok=True)
    ida_home = Path(sys.executable).resolve().parents[1]
    if not (ida_home / "idalib.dll").is_file():
        parser.error("run with the bundled Windows IDA Python containing idalib.dll")
    os.environ["IDADIR"] = str(ida_home)
    # Keep IDAlib's generated configuration and user state game-bound as well.
    for name, directory in (("APPDATA", "appdata"), ("IDAUSR", "ida-user")):
        directory = database.parent / directory
        directory.mkdir(exist_ok=True)
        os.environ[name] = str(directory)

    with database_lock(database):
        # Library initialization and plugin diagnostics must not enter the
        # newline-delimited JSON protocol. Restore stdout only for MCP itself.
        protocol_fd = os.dup(sys.stdout.fileno())
        try:
            os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
            with redirect_stdout(sys.stderr):
                import idapro
                import ida_auto
                import ida_hexrays
                import ida_loader
                from mcp.server.fastmcp import FastMCP

                idapro.enable_console_messages(False)
                selected = database if database.exists() else source
                options = None if database.exists() else f'-o"{database}"'
                if idapro.open_database(str(selected), run_auto_analysis=True, args=options):
                    raise RuntimeError("cannot open the operator-bound headless IDA database")
                try:
                    ida_auto.auto_wait()
                    ida_hexrays.init_hexrays_plugin()
                    plugin = importlib.import_module("ida_pro_mcp.mcp-plugin")
                    types = load_protocol_types(plugin)
                    server = FastMCP("factory-headless-ida", log_level="ERROR")
                    def save():
                        if not ida_loader.save_database(str(database), 0):
                            raise RuntimeError("cannot save the game-bound headless IDA database")
                    save()
                    for name, function in plugin.rpc_registry.methods.items():
                        if name not in plugin.rpc_registry.unsafe:
                            # Read tools do not write per call. Metadata changes
                            # persist before responding, even if stdio closes.
                            metadata_write = name.startswith(("set_", "rename_", "create_stack_", "delete_stack_", "declare_"))
                            server.add_tool(on_kernel_thread(function, save=save if metadata_write else None, types=types), name=name)
                except BaseException:
                    idapro.close_database(save=True)
                    raise
            os.dup2(protocol_fd, sys.stdout.fileno())
            try:
                server.run(transport="stdio")
            finally:
                os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
                with redirect_stdout(sys.stderr):
                    idapro.close_database(save=True)
        finally:
            os.dup2(protocol_fd, sys.stdout.fileno())
            os.close(protocol_fd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
