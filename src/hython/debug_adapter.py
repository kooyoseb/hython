"""Line-oriented JSON debug adapter for Hython source files."""
from __future__ import annotations

import contextlib
import json
import sys
import traceback
from pathlib import Path

from .compiler import compile_source
from .vm import VM


class DebugStop(SystemExit):
    pass


def _safe_value(value, limit: int = 240) -> dict:
    try:
        text = repr(value)
    except BaseException:
        text = f"<{type(value).__name__}>"
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return {"type": type(value).__name__, "value": text}


class _OutputWriter:
    def __init__(self, adapter, category):
        self.adapter, self.category = adapter, category

    def write(self, text):
        if text:
            self.adapter.emit("output", category=self.category, text=text)
        return len(text)

    def flush(self):
        self.adapter.protocol.flush()


class DebugAdapter:
    def __init__(self, path: Path, breakpoints=()):
        self.path = path.resolve()
        self.breakpoints = {int(line) for line in breakpoints if int(line) > 0}
        self.step = False
        self.stopped = False
        self.protocol = sys.stdout
        self.previous_location = None

    def emit(self, event: str, **payload) -> None:
        print(json.dumps({"event": event, **payload}, ensure_ascii=False),
              file=self.protocol, flush=True)

    def command(self) -> str:
        line = sys.stdin.readline()
        if not line:
            return "stop"
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            self.emit("error", message="디버그 명령 JSON을 읽을 수 없습니다.")
            return self.command()
        command = message.get("command", "")
        if command == "setBreakpoints":
            self.breakpoints = {
                int(item) for item in message.get("lines", ())
                if isinstance(item, int) and item > 0
            }
            self.emit("breakpoints", lines=sorted(self.breakpoints))
            return self.command()
        return command

    def wait(self, code, line, local) -> None:
        variables = {
            name: _safe_value(value)
            for name, value in VM.visible_locals(local).items()
            if not name.startswith("__") and not name.startswith("$")
        }
        function_name = code.name
        try:
            if Path(code.name).resolve() == self.path:
                function_name = "<module>"
        except (OSError, ValueError):
            pass
        self.emit(
            "stopped", reason="step" if self.step else "breakpoint",
            file=str(self.path), line=line,
            function=function_name, variables=variables,
        )
        while True:
            command = self.command()
            if command == "continue":
                self.step = False
                return
            if command in ("step", "next"):
                self.step = True
                return
            if command == "stop":
                self.stopped = True
                raise DebugStop()
            self.emit("error", message=f"알 수 없는 디버그 명령: {command}")

    def trace(self, code, ip, local, stack):
        if self.stopped:
            raise DebugStop()
        line = code.lines[ip] if code.lines and ip < len(code.lines) else 0
        if line <= 0:
            return
        location = (id(code), line)
        if location == self.previous_location:
            return
        self.previous_location = location
        if self.step or line in self.breakpoints:
            self.wait(code, line, local)

    def run(self) -> int:
        source = self.path.read_text(encoding="utf-8-sig")
        old_argv, old_path = sys.argv, sys.path[:]
        sys.argv = [str(self.path)]
        sys.path.insert(0, str(self.path.parent))
        self.emit("initialized", file=str(self.path),
                  breakpoints=sorted(self.breakpoints))
        initial = self.command()
        if initial == "stop":
            self.emit("terminated", exitCode=0)
            return 0
        self.step = initial in ("step", "next")
        try:
            code = compile_source(source, str(self.path))
            vm = VM([self.path.parent], instruction_hook=self.trace)
            vm.globals.update({
                "__name__": "__main__", "__file__": str(self.path),
                "__package__": None, "__cached__": None,
            })
            with contextlib.redirect_stdout(_OutputWriter(self, "stdout")), \
                 contextlib.redirect_stderr(_OutputWriter(self, "stderr")):
                vm.run(code)
        except DebugStop:
            self.emit("terminated", exitCode=0, stopped=True)
            return 0
        except BaseException as exc:
            self.emit(
                "exception", type=type(exc).__name__, message=str(exc),
                traceback="".join(traceback.format_exception(exc)),
            )
            self.emit("terminated", exitCode=1)
            return 1
        finally:
            sys.argv, sys.path[:] = old_argv, old_path
        self.emit("terminated", exitCode=0)
        return 0


def run(path: Path, breakpoints=()) -> int:
    return DebugAdapter(path, breakpoints).run()
