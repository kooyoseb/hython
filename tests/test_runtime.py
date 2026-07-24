import tempfile
import unittest
from pathlib import Path

from hython.runtime import check_tree, inspect_runtime


class RuntimeTests(unittest.TestCase):
    def test_runtime_has_keywords(self):
        profile = inspect_runtime()
        self.assertIn("if", profile["hard_keywords"])
        self.assertTrue(profile["version_info"])

    def test_checks_tree_without_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "ok.hy").write_text("프린트('실행되지 않음')\n", encoding="utf-8")
            (root / "bad.hy").write_text("이프:\n", encoding="utf-8")
            failures = check_tree(root)
            self.assertEqual([path.name for path, _ in failures], ["bad.hy"])

