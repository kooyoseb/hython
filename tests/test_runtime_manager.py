import tempfile
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from hython.runtime_manager import get_preference, set_preference

class RuntimeManagerTests(unittest.TestCase):
    def test_project_runtime_is_inherited(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            child = root / "src" / "app"
            child.mkdir(parents=True)
            set_preference(root, "3.14")
            self.assertEqual(get_preference(child), "3.14")

    def test_rejects_invalid_tag(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                set_preference(Path(directory), "3.14 bad")

    def test_global_updated_runtime_is_fallback_preference(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ,{"HYTHON_HOME":directory}):
            (Path(directory)/"state.json").write_text(
                json.dumps({"format":1,"runtime_tag":"default"}),encoding="utf-8"
            )
            project=Path(directory)/"project"
            project.mkdir()
            self.assertEqual(get_preference(project),"default")
