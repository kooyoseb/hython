import unittest
import tomllib
from pathlib import Path

import hython
from hython.bytecode import MAGIC, dumps
from hython.compiler import compile_source
from hython.translator import to_hython, to_python
from hython.vocabulary import BUILTINS, KEYWORDS, LIBRARY_NAMES, SPECIAL_NAMES

class ReleaseContractTests(unittest.TestCase):
    def test_public_version(self):
        self.assertEqual(hython.__version__,"2.0.1")

    def test_stable_release_metadata(self):
        root = Path(__file__).resolve().parents[1]
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        self.assertEqual(project["version"], "2.0.1")
        self.assertIn("Development Status :: 5 - Production/Stable", project["classifiers"])
        self.assertNotIn("Development Status :: 4 - Beta", project["classifiers"])

    def test_every_canonical_spelling_round_trips(self):
        for python_name,hython_name in (KEYWORDS | BUILTINS | SPECIAL_NAMES).items():
            with self.subTest(python_name=python_name):
                self.assertEqual(to_python(hython_name),python_name)
                self.assertEqual(to_hython(python_name),hython_name)
        for python_name,hython_name in LIBRARY_NAMES.items():
            with self.subTest(python_name=python_name):
                self.assertEqual(to_python(f"객체.{hython_name}"),f"객체.{python_name}")
                self.assertEqual(to_hython(f"obj.{python_name}"),f"obj.{hython_name}")

    def test_hbc_is_not_python_pyc(self):
        artifact=dumps(compile_source("값 = 1\n"))
        self.assertTrue(artifact.startswith(MAGIC))
        self.assertFalse(artifact.startswith(__import__("importlib.util").util.MAGIC_NUMBER))

    def test_advanced_syntax_compatibility_backend(self):
        source="어싱크 데프 작업(값):\n    매치 값:\n        케이스 1:\n            리턴 트루\n        케이스 _:\n            리턴 폴스\n"
        compile(to_python(source),"<호환성>","exec")
