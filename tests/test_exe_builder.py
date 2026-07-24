import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from hython.bytecode import dumps
from hython.compiler import compile_source
from hython import exe_builder


class ExeBuilderTests(unittest.TestCase):
    def test_import_analysis_includes_nested_code_and_from_import(self):
        code=compile_source(
            "인폴트 json\n데프 작업():\n    프롬 pathlib 인폴트 Path\n    리턴 Path\n"
        )
        self.assertEqual(exe_builder.imported_modules(code),{"json","pathlib"})

    def test_command_uses_onefile_console_icon_and_external_collection(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); launcher=root/"launch.py"; icon=root/"app.ico"; icon.write_bytes(b"ico")
            with patch("importlib.metadata.packages_distributions",return_value={"requests":["requests"]}):
                command=exe_builder._pyinstaller_command(
                    launcher,name="app",work=root,console=False,icon=icon,
                    imports={"json","requests"},source_root=root,modules=[],resources=[],
                )
            self.assertIn("--onefile",command)
            self.assertIn("--windowed",command)
            self.assertIn("--icon",command)
            self.assertEqual(command.count("--collect-all"),1)
            self.assertIn("requests",command)

    def test_tkinter_import_collects_gui_submodules(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            command=exe_builder._pyinstaller_command(
                root/"launcher.py",name="gui",work=root,console=True,icon=None,
                imports={"tkinter"},source_root=root,modules=[],resources=[],
            )
            hidden=[command[index+1] for index,item in enumerate(command[:-1]) if item=="--hidden-import"]
            self.assertIn("tkinter",hidden)
            self.assertIn("tkinter.ttk",hidden)
            self.assertIn("tkinter.filedialog",hidden)

    def test_success_atomically_replaces_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); hbc=root/"program.hbc"; output=root/"program.exe"
            hbc.write_bytes(dumps(compile_source("인폴트 helper\n값 = 1\n")))
            (root/"helper.hbc").write_bytes(dumps(compile_source("도움 = 2\n")))
            output.write_bytes(b"old")
            observed=[]
            def fake_run(command,**kwargs):
                observed.extend(command)
                dist=Path(command[command.index("--distpath")+1]); name=command[command.index("--name")+1]
                dist.mkdir(parents=True,exist_ok=True); (dist/(name+".exe")).write_bytes(b"MZ"+b"x"*2048)
                return SimpleNamespace(returncode=0,stdout="",stderr="")
            with patch("importlib.util.find_spec",return_value=object()),patch("subprocess.run",side_effect=fake_run):
                result=exe_builder.build_exe(hbc,output)
            self.assertEqual(result,output.resolve())
            self.assertTrue(output.read_bytes().startswith(b"MZ"))
            self.assertIn("--add-data",observed)
            hidden=[observed[index+1] for index,item in enumerate(observed[:-1]) if item=="--hidden-import"]
            self.assertNotIn("helper",hidden)

    def test_failed_build_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); hbc=root/"program.hbc"; output=root/"program.exe"
            hbc.write_bytes(dumps(compile_source("값 = 1\n"))); output.write_bytes(b"old")
            failure=SimpleNamespace(returncode=1,stdout="",stderr="build failed")
            with patch("importlib.util.find_spec",return_value=object()),patch("subprocess.run",return_value=failure):
                with self.assertRaisesRegex(exe_builder.ExeBuildError,"build failed"):
                    exe_builder.build_exe(hbc,output)
            self.assertEqual(output.read_bytes(),b"old")

    def test_project_entry_resolution_and_ambiguity(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/"main.hbc").write_bytes(b"x")
            entry,module_root=exe_builder.resolve_entry(root)
            self.assertEqual(entry,root/"main.hbc"); self.assertEqual(module_root,root)
            (root/"other.hbc").write_bytes(b"x")
            self.assertEqual(exe_builder.resolve_entry(root,"other.hbc")[0],root/"other.hbc")
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/"a.hbc").write_bytes(b"x"); (root/"b.hbc").write_bytes(b"x")
            with self.assertRaisesRegex(exe_builder.ExeBuildError,"--entry"):
                exe_builder.resolve_entry(root)

    def test_resource_destination_and_version_metadata_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            resource=Path(directory)/"config.json"; resource.write_text("{}")
            self.assertEqual(exe_builder._validate_resources([(resource,Path("config/config.json"))])[0][1],Path("config/config.json"))
            with self.assertRaisesRegex(exe_builder.ExeBuildError,"안전하지 않은"):
                exe_builder._validate_resources([(resource,Path("../escape"))])
        version=exe_builder._version_source({"version":"2.3.4","product":"Demo"})
        self.assertIn("(2, 3, 4, 0)",version)
        self.assertIn("Demo",version)
        with self.assertRaises(exe_builder.ExeBuildError):
            exe_builder._version_source({"version":"2.beta"})

    def test_archive_writes_sha256_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); artifact=root/"app.exe"; artifact.write_bytes(b"MZ-demo")
            archive,checksum=exe_builder.create_archive(artifact,root/"release.zip")
            self.assertTrue(archive.is_file()); self.assertTrue(checksum.is_file())
            digest=__import__("hashlib").sha256(archive.read_bytes()).hexdigest()
            self.assertEqual(checksum.read_text(encoding="ascii"),f"{digest}  release.zip\n")
