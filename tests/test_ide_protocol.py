import tempfile
import unittest
from pathlib import Path

from hython.ide_protocol import analyze_file, analyze_source, completions, diagnostics, symbols


class IdeProtocolTests(unittest.TestCase):
    def test_completions_come_from_hython_vocabulary(self):
        result = completions("프린", 1, 2)
        self.assertEqual(result["prefix"], "프린")
        self.assertIn("프린트", [item["label"] for item in result["items"]])

    def test_diagnostics_are_korean_and_structured(self):
        result = diagnostics("이프 트루\n    프린트(1)\n", "오류.hy")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["severity"], "error")
        self.assertIn("문법 오류", result[0]["message"])
        self.assertGreaterEqual(result[0]["line"], 1)

    def test_symbols_include_functions_and_classes(self):
        result = symbols("데프 작업():\n    패스\n\n클래스 상자:\n    패스\n", "구조.hy")
        self.assertEqual([item["kind"] for item in result], ["함수", "클래스"])

    def test_integrated_analysis_has_versioned_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "main.hy"
            path.write_text("프린트('안녕')\n", encoding="utf-8")
            result = analyze_file(path, line=1, column=3)
        self.assertEqual(result["protocolVersion"], 1)
        self.assertIn("hythonVersion", result)
        self.assertEqual(result["diagnostics"], [])
        self.assertIn("symbols", result)
        self.assertIn("completions", result)

    def test_unsaved_source_analysis_uses_virtual_filename(self):
        result = analyze_source("프린트(1)\n", "저장전.hy", line=1, column=3)
        self.assertEqual(result["file"], "저장전.hy")
        self.assertEqual(result["diagnostics"], [])

    def test_unsaved_source_ignores_utf8_bom(self):
        result = analyze_source("\ufeff프린트(1)\n", "저장전.hy")
        self.assertEqual(result["diagnostics"], [])
