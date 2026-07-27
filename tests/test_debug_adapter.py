from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from hython.debug_adapter import run


class DebugAdapterTests(unittest.TestCase):
    def events(self, source: str, commands: list[dict], breakpoints=()):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "debug.hy"
            path.write_text(source, encoding="utf-8")
            stdin = io.StringIO("".join(
                json.dumps(command) + "\n" for command in commands
            ))
            stdout = io.StringIO()
            with patch("sys.stdin", stdin), redirect_stdout(stdout):
                result = run(path, breakpoints)
            return result, [
                json.loads(line) for line in stdout.getvalue().splitlines()
            ]

    def test_breakpoint_continue_and_variables(self):
        result, events = self.events(
            "값 = 1\n값 = 값 + 2\n프린트(값)\n",
            [{"command": "continue"}, {"command": "continue"}],
            breakpoints=[2],
        )
        self.assertEqual(result, 0)
        stopped = next(event for event in events if event["event"] == "stopped")
        self.assertEqual(stopped["line"], 2)
        self.assertEqual(stopped["variables"]["값"]["value"], "1")
        self.assertEqual(events[-1]["event"], "terminated")

    def test_step_then_stop(self):
        result, events = self.events(
            "값 = 1\n값 = 2\n",
            [{"command": "step"}, {"command": "stop"}],
        )
        self.assertEqual(result, 0)
        self.assertEqual([event["event"] for event in events],
                         ["initialized", "stopped", "terminated"])
        self.assertTrue(events[-1]["stopped"])

    def test_exception_is_reported(self):
        result, events = self.events(
            "레이즈 밸류에러(\"문제\")\n",
            [{"command": "continue"}],
        )
        self.assertEqual(result, 1)
        exception = next(event for event in events if event["event"] == "exception")
        self.assertEqual(exception["type"], "ValueError")
        self.assertIn("문제", exception["message"])

    def test_debugger_runs_native_hbc_vm(self):
        result, events = self.events(
            "값 = 10\n값 = 값 * 2\n",
            [{"command": "continue"}, {"command": "continue"}],
            breakpoints=[2],
        )
        self.assertEqual(result, 0)
        stopped = next(event for event in events if event["event"] == "stopped")
        self.assertEqual(stopped["function"], "<module>")
        self.assertEqual(stopped["variables"]["값"]["value"], "10")


if __name__ == "__main__":
    unittest.main()
