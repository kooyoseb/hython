import importlib
import sys
import tempfile
import unittest
from pathlib import Path

from hython.importer import install_importer, uninstall_importer


class ImporterTests(unittest.TestCase):
    def tearDown(self):
        uninstall_importer()
        sys.modules.pop("계산기", None)
        sys.modules.pop("도구", None)
        sys.modules.pop("도구.값", None)

    def test_imports_hython_module(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "계산기.hy").write_text(
                "데프 더하기(가, 나):\n    리턴 가 + 나\n", encoding="utf-8"
            )
            sys.path.insert(0, directory)
            try:
                install_importer()
                module = importlib.import_module("계산기")
                self.assertEqual(module.더하기(2, 3), 5)
                self.assertTrue(module.__file__.endswith("계산기.hy"))
            finally:
                sys.path.remove(directory)

    def test_imports_hython_package(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory, "도구")
            package.mkdir()
            Path(package, "__init__.hy").write_text(
                "프롬 .값 인폴트 정답\n", encoding="utf-8"
            )
            Path(package, "값.hy").write_text("정답 = 42\n", encoding="utf-8")
            sys.path.insert(0, directory)
            try:
                install_importer()
                module = importlib.import_module("도구")
                self.assertEqual(module.정답, 42)
            finally:
                sys.path.remove(directory)

