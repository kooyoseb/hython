from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class StudioContractTests(unittest.TestCase):
    def text(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_studio_release_surface_is_complete(self):
        xaml = self.text("studio/HythonStudio/MainWindow.xaml")
        for marker in (
            "Hython Studio 1.0.1", "ProjectTree", "SearchResultsList",
            "DebugVariables", "TerminalInput", "PackageSpecInput",
            "ProblemsList", "SymbolsList",
        ):
            self.assertIn(marker, xaml)

    def test_services_cover_required_editor_workflows(self):
        services = {
            path.name for path in (ROOT / "studio/HythonStudio/Services").glob("*.cs")
        }
        self.assertTrue({
            "HythonAnalysisService.cs", "DebugSession.cs", "TerminalService.cs",
            "PackageService.cs", "ProjectSearchService.cs",
            "EngineManagementService.cs", "ConversionService.cs",
        }.issubset(services))

    def test_installer_registers_studio_and_shell_actions(self):
        wix = self.text("installer/hython.wxs") + self.text("installer/studio.wxs")
        for marker in (
            "HythonStudioExe", r"Software\Classes\.hy",
            r"Software\Classes\.hbc", "--build-hbc", "--convert-python",
        ):
            self.assertIn(marker, wix)

    def test_standalone_studio_installer_has_stable_identity(self):
        wix = self.text("installer/studio.wxs")
        self.assertIn('Package Name="Hython Studio"', wix)
        self.assertIn("E34AC48E-E305-48F2-AC51-24FBE48FB3B2", wix)
        self.assertIn("StudioDesktopFeature", wix)

    def test_start_page_uses_embedded_hython_icon(self):
        project = self.text("studio/HythonStudio/HythonStudio.csproj")
        xaml = self.text("studio/HythonStudio/MainWindow.xaml")
        self.assertIn('Link="Resources\\hython-icon.png"', project)
        self.assertIn(
            'Source="/HythonStudio;component/Resources/hython-icon.png"',
            xaml,
        )

    def test_no_unfinished_ui_placeholders_remain(self):
        source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / "studio/HythonStudio").rglob("*")
            if path.suffix in {".cs", ".xaml"} and "obj" not in path.parts
            and "bin" not in path.parts
        )
        for marker in ("연결 예정", "연결 영역", "TODO", "미구현"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
