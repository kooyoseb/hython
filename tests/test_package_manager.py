import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hython import package_manager


class PackageManagerTests(unittest.TestCase):
    def test_distribution_specifier_module_inference(self):
        self.assertEqual(package_manager.infer_module_name("beautiful-soup4[html]>=4.12"),"beautiful_soup4")
        self.assertEqual(package_manager.infer_module_name("requests~=2.32"),"requests")
        self.assertEqual(package_manager.infer_module_name("project @ https://example.invalid/project.whl"),"project")
        with self.assertRaisesRegex(ValueError,"--module"):
            package_manager.infer_module_name("https://example.invalid/project.whl")

    def test_distribution_discovers_all_import_modules(self):
        with patch(
            "importlib.metadata.packages_distributions",
            return_value={"yaml":["PyYAML"],"_private":["PyYAML"],"other":["Other"]},
        ):
            self.assertEqual(
                package_manager.modules_for_distribution("pyyaml>=6"),
                ["_private","yaml"],
            )

    def test_dotted_scan_does_not_execute_parent_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); package=root/"safe_package"; child=package/"child"; child.mkdir(parents=True)
            marker=root/"executed.txt"
            (package/"__init__.py").write_text(f'from pathlib import Path\nPath({str(marker)!r}).write_text("executed")\n',encoding="utf-8")
            (child/"__init__.py").write_text('__all__=["PublicThing"]\nclass PublicThing: pass\nclass HiddenByAll: pass\n',encoding="utf-8")
            output_dir=root/"dictionaries"
            sys.path.insert(0,str(root))
            try:
                with patch.object(package_manager,"dictionary_dir",return_value=output_dir):
                    output_dir.mkdir(); output=package_manager.scan("safe_package.child")
            finally:
                sys.path.remove(str(root)); sys.modules.pop("safe_package",None); sys.modules.pop("safe_package.child",None)
            payload=json.loads(output.read_text(encoding="utf-8"))
            self.assertFalse(marker.exists())
            self.assertEqual(payload["module"],"safe_package.child")
            self.assertEqual(
                set(payload["python_to_hython"]),
                {"safe_package","child","PublicThing"},
            )

    def test_scan_includes_module_and_public_methods(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); package=root/"widgetkit"; package.mkdir()
            (package/"__init__.py").write_text(
                "class Window:\n    def show_window(self): pass\n    def _hidden(self): pass\n",
                encoding="utf-8",
            )
            output_dir=root/"dictionaries"; output_dir.mkdir()
            sys.path.insert(0,str(root))
            try:
                with patch.object(package_manager,"dictionary_dir",return_value=output_dir):
                    output=package_manager.scan("widgetkit")
            finally:
                sys.path.remove(str(root))
            entries=json.loads(output.read_text(encoding="utf-8"))["python_to_hython"]
            self.assertIn("widgetkit",entries)
            self.assertIn("Window",entries)
            self.assertIn("show_window",entries)
            self.assertNotIn("_hidden",entries)

    def test_load_dictionaries_ignores_malformed_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/"valid.json").write_text(json.dumps({"python_to_hython":{"PublicThing":"퍼블릭띵"}}),encoding="utf-8")
            (root/"broken.json").write_text("{",encoding="utf-8")
            (root/"wrong.json").write_text(json.dumps({"python_to_hython":[]}),encoding="utf-8")
            with patch.object(package_manager,"dictionary_dir",return_value=root):
                self.assertEqual(package_manager.load_dictionaries(),{"퍼블릭띵":"PublicThing"})
                self.assertEqual(package_manager.load_python_dictionaries(),{"PublicThing":"퍼블릭띵"})

    def test_remove_dictionary_deactivates_package_syntax(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            path=root/"demo.json"
            path.write_text(json.dumps({"python_to_hython":{"PublicThing":"퍼블릭띵"}}),encoding="utf-8")
            with patch.object(package_manager,"dictionary_dir",return_value=root):
                self.assertTrue(package_manager.remove_dictionary("demo"))
                self.assertFalse(path.exists())
                self.assertFalse(package_manager.remove_dictionary("demo"))

    def test_refresh_prunes_missing_modules_and_rescans_installed_ones(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for module in ("present", "missing"):
                (root/f"{module}.json").write_text(
                    json.dumps({"module":module,"python_to_hython":{}}),encoding="utf-8"
                )
            with (
                patch.object(package_manager,"dictionary_dir",return_value=root),
                patch.object(package_manager,"_find_spec_static",side_effect=lambda name: object() if name=="present" else None),
                patch.object(package_manager,"scan",return_value=root/"present.json") as scan,
            ):
                refreshed,removed=package_manager.refresh_dictionaries()
            self.assertEqual(refreshed,[root/"present.json"])
            self.assertEqual(removed,[root/"missing.json"])
            self.assertFalse((root/"missing.json").exists())
            scan.assert_called_once_with("present",deep=False)

    def test_deep_scan_merges_runtime_extension_api(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); module=root/"binarylike.py"
            module.write_text("STATIC = 1\n",encoding="utf-8")
            dictionaries=root/"dictionaries"; dictionaries.mkdir()
            sys.path.insert(0,str(root))
            try:
                with (
                    patch.object(package_manager,"dictionary_dir",return_value=dictionaries),
                    patch.object(package_manager,"_deep_public_names",return_value={"DynamicAPI"}),
                ):
                    output=package_manager.scan("binarylike",deep=True)
            finally:
                sys.path.remove(str(root))
            payload=json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["scan_mode"],"deep")
            self.assertIn("DynamicAPI",payload["python_to_hython"])

    def test_colliding_pronunciations_are_never_dropped(self):
        with patch.object(package_manager,"pronounce_identifier",return_value="같은발음"):
            result=package_manager._unique_spellings({"First","Second"})
        self.assertEqual(set(result),{"First","Second"})
        self.assertEqual(len(set(result.values())),2)

    def test_frozen_install_uses_managed_python_target_store(self):
        with tempfile.TemporaryDirectory() as directory:
            store=Path(directory)/"packages"
            with (
                patch.object(package_manager,"is_frozen",return_value=True),
                patch.object(package_manager,"package_store",return_value=store),
                patch("hython.runtime_manager.find_manager",return_value="py-manager"),
                patch("subprocess.run") as run,
            ):
                package_manager.install("demo>=1",upgrade=True)
            command=run.call_args.args[0]
            self.assertEqual(command[:5],["py-manager","exec","-V:default","-m","pip"])
            self.assertIn("--target",command)
            self.assertIn(str(store),command)
            self.assertIn("--upgrade",command)
