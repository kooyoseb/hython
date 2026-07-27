import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXTENSION = ROOT / "vscode-extension"


class VSCodeExtensionContractTests(unittest.TestCase):
    def text(self, relative):
        return (EXTENSION / relative).read_text(encoding="utf-8")

    def test_manifest_registers_hython_language_and_commands(self):
        manifest = json.loads(self.text("package.json"))
        languages = manifest["contributes"]["languages"]
        self.assertEqual(languages[0]["id"], "hython")
        self.assertIn(".hy", languages[0]["extensions"])
        commands = {
            item["command"] for item in manifest["contributes"]["commands"]
        }
        self.assertTrue({
            "hython.runFile",
            "hython.compileFile",
            "hython.buildExe",
            "hython.debugFile",
            "hython.selectEngine",
            "hython.newProject",
            "hython.installPackage",
            "hython.updateEngine",
        }.issubset(commands))

    def test_extension_uses_engine_ide_protocol(self):
        source = self.text("extension.js")
        for marker in (
            '"ide", "analyze"',
            '"--stdin"',
            "registerCompletionItemProvider",
            "registerDocumentSymbolProvider",
            "createDiagnosticCollection",
            "new vscode.ShellExecution",
            "registerDefinitionProvider",
            "registerReferenceProvider",
            "registerRenameProvider",
            "registerHoverProvider",
        ):
            self.assertIn(marker, source)

    def test_grammar_contains_core_hython_spellings(self):
        grammar = self.text("syntaxes/hython.tmLanguage.json")
        for spelling in ("인폴트", "데프", "클래스", "프린트", "트루", "넌"):
            self.assertIn(spelling, grammar)

    def test_packaging_script_exists(self):
        self.assertTrue((ROOT / "build-vscode-extension.bat").is_file())
        manifest = json.loads(self.text("package.json"))
        self.assertIn("package", manifest["scripts"])

    def test_native_debugger_is_registered(self):
        manifest = json.loads(self.text("package.json"))
        self.assertEqual(manifest["contributes"]["debuggers"][0]["type"], "hython")
        self.assertEqual(
            manifest["contributes"]["breakpoints"][0]["language"], "hython"
        )
        adapter = self.text("debugAdapter.js")
        for marker in (
            '"ide", "debug"',
            '"setBreakpoints"',
            '"stackTrace"',
            '"variables"',
            '"continue"',
        ):
            self.assertIn(marker, adapter)

    def test_extension_host_suite_covers_runtime_features(self):
        test_source = self.text("test/suite/extension.test.js")
        for marker in (
            "vscode.executeCompletionItemProvider",
            "vscode.executeDefinitionProvider",
            "vscode.debug.startDebugging",
            "onDidTerminateDebugSession",
        ):
            self.assertIn(marker, test_source)

    def test_snippets_and_project_workflow_are_packaged(self):
        manifest = json.loads(self.text("package.json"))
        self.assertEqual(
            manifest["contributes"]["snippets"][0]["path"],
            "./snippets/hython.json",
        )
        snippets = json.loads(self.text("snippets/hython.json"))
        self.assertIn("Hython 함수", snippets)
        source = self.text("extension.js")
        self.assertIn('"hython.newProject"', source)
        self.assertIn('"launch.json"', source)
        self.assertIn('"tasks.json"', source)
        icon = EXTENSION / manifest["icon"]
        self.assertTrue(icon.is_file())
        self.assertGreater(icon.stat().st_size, 10_000)


if __name__ == "__main__":
    unittest.main()
