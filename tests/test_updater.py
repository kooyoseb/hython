import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hython import updater


class UpdaterTests(unittest.TestCase):
    def test_initialize_is_automatic_state_once_and_forceable(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ,{"HYTHON_HOME":directory}):
            with patch.object(updater,"sync_runtime",return_value=Path(directory)/"runtime.json") as sync:
                first=updater.initialize()
                second=updater.initialize()
                forced=updater.initialize(force=True)
            self.assertTrue(first["initialized"])
            self.assertFalse(second["initialized"])
            self.assertTrue(forced["initialized"])
            self.assertEqual(sync.call_count,2)
            state=json.loads((Path(directory)/"state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["format"],1)
            self.assertIn("python_version",state)

    def test_refresh_records_runtime_and_package_deletions(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ,{"HYTHON_HOME":directory}):
            runtime=Path(directory)/"runtimes"/"python.json"
            with (
                patch.object(updater,"sync_runtime",return_value=runtime),
                patch.object(updater,"refresh_dictionaries",return_value=([Path("new.json")],[Path("old.json")])),
            ):
                result=updater.refresh(runtime_tag="default")
            self.assertEqual(result["runtime"],runtime)
            self.assertEqual(result["refreshed"],[Path("new.json")])
            self.assertEqual(result["removed"],[Path("old.json")])
            self.assertTrue(updater.is_initialized())
            state=json.loads((Path(directory)/"state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["runtime_tag"],"default")

    def test_hython_upgrade_reinitializes_and_preserves_active_runtime(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ,{"HYTHON_HOME":directory}):
            state=Path(directory)/"state.json"
            state.write_text(json.dumps({
                "format":1,"hython_version":"old","python_version":"old","runtime_tag":"default"
            }),encoding="utf-8")
            with (
                patch.object(updater,"sync_runtime",return_value=Path(directory)/"runtime.json"),
                patch.object(updater,"refresh_dictionaries",return_value=([],[])) as refresh_packages,
            ):
                result=updater.initialize()
            self.assertTrue(result["initialized"])
            refresh_packages.assert_called_once_with()
            self.assertEqual(json.loads(state.read_text(encoding="utf-8"))["runtime_tag"],"default")
