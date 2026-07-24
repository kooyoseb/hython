import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hython.cli import entrypoint
from hython.bytecode import write
from hython.compiler import compile_source


class CliDiagnosticsTests(unittest.TestCase):
    def test_compatibility_run_prints_korean_name_error(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/"오류.hy"
            source.write_text("프린트(없는이름)\n",encoding="utf-8")
            stderr=io.StringIO()
            with patch.object(sys,"argv",["hython","run",str(source)]),contextlib.redirect_stderr(stderr):
                result=entrypoint()
        rendered=stderr.getvalue()
        self.assertEqual(result,1)
        self.assertIn("이름 오류",rendered)
        self.assertIn("이름 '없는이름'이 정의되지 않았습니다",rendered)
        self.assertIn(str(source),rendered)
        self.assertNotIn("Traceback (most recent call last)",rendered)

    def test_compile_syntax_error_shows_source_and_korean_label(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/"문법.hy"
            source.write_text("이프 트루 프린트(1)\n",encoding="utf-8")
            stderr=io.StringIO()
            with patch.object(sys,"argv",["hython","run",str(source)]),contextlib.redirect_stderr(stderr):
                result=entrypoint()
        rendered=stderr.getvalue()
        self.assertEqual(result,1)
        self.assertIn("문법 오류",rendered)
        self.assertIn("^",rendered)

    def test_hbc_execute_uses_same_korean_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact=Path(directory)/"오류.hbc"
            write(artifact,compile_source("값 = 1 / 0\n","오류.hy"))
            stderr=io.StringIO()
            with patch.object(sys,"argv",["hython","execute",str(artifact)]),contextlib.redirect_stderr(stderr):
                result=entrypoint()
        rendered=stderr.getvalue()
        self.assertEqual(result,1)
        self.assertIn("0 나누기 오류",rendered)
        self.assertIn("0으로 나눌 수 없습니다",rendered)
        self.assertIn("하이썬 위치",rendered)
