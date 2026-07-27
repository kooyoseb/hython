from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ManagerContractTests(unittest.TestCase):
    def text(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_manager_is_tray_enabled_single_file_wpf_app(self):
        project = self.text("manager/HythonManager/HythonManager.csproj")
        app = self.text("manager/HythonManager/App.xaml.cs")
        build = self.text("build-manager.bat")
        self.assertIn("<UseWPF>true</UseWPF>", project)
        self.assertIn("<UseWindowsForms>true</UseWindowsForms>", project)
        self.assertIn("NotifyIcon", app)
        self.assertIn("Global\\Kooyoseb.Hython.Manager", app)
        self.assertIn("PublishSingleFile=true", build)
        self.assertIn("<Version>1.0.0</Version>", project)

    def test_catalog_recognizes_products_without_mixing_release_tags(self):
        source = self.text(
            "manager/HythonManager/Services/ProductCatalogService.cs"
        )
        for marker in (
            r"^v(?<v>\d+\.\d+\.\d+)$",
            r"^studio-v(?<v>\d+\.\d+\.\d+)$",
            r"^hython-development-v(?<v>\d+\.\d+\.\d+)$",
            r"^manager-v(?<v>\d+\.\d+\.\d+)$",
            r"^(?<id>[a-z0-9][a-z0-9-]*)-v(?<v>\d+\.\d+\.\d+)$",
            "ReadUninstallRegistry",
            "--list-extensions --show-versions",
            "AssetDigest",
            "SHA256.HashDataAsync",
        ):
            self.assertIn(marker, source)

    def test_checksum_is_bound_to_selected_asset(self):
        source = self.text(
            "manager/HythonManager/Services/ProductCatalogService.cs"
        )
        self.assertIn("selectedName + \".sha256\"", source)
        self.assertIn("다운로드 파일의 SHA-256 검증에 실패했습니다.", source)
        self.assertIn("await using FileStream output = File.Create(path)", source)
        self.assertLess(
            source.index("await output.FlushAsync();"),
            source.index("FileStream verification = File.OpenRead(path)"),
        )
        self.assertIn("await using (FileStream verification", source)

    def test_manager_has_install_update_remove_and_tray_ui(self):
        xaml = self.text("manager/HythonManager/MainWindow.xaml")
        code = self.text("manager/HythonManager/MainWindow.xaml.cs")
        service = self.text(
            "manager/HythonManager/Services/ProductCatalogService.cs"
        )
        for marker in ("모든 제품", "새로 고침", "제거", "ActionText"):
            self.assertIn(marker, xaml)
        for marker in ("Install_Click", "Uninstall_Click", "RefreshProductsAsync"):
            self.assertIn(marker, code)
        for marker in ("InstallAsync", "UninstallAsync", "msiexec.exe", "--install-extension"):
            self.assertIn(marker, service)

    def test_vscode_extension_is_managed_only_through_code_cli(self):
        source = self.text(
            "manager/HythonManager/Services/ProductCatalogService.cs"
        )
        for marker in (
            "--list-extensions --show-versions",
            "--install-extension kooyoseb.hython-development --force",
            "--uninstall-extension kooyoseb.hython-development",
            "FindCodeCommand",
        ):
            self.assertIn(marker, source)
        self.assertNotIn('Directory.EnumerateDirectories(root, "kooyoseb.', source)

    def test_manager_has_persistent_settings_and_bulk_updates(self):
        settings = self.text(
            "manager/HythonManager/Services/ManagerSettings.cs"
        )
        app = self.text("manager/HythonManager/App.xaml.cs")
        window = self.text("manager/HythonManager/MainWindow.xaml.cs")
        for marker in (
            "StartWithWindows", "BackgroundChecks", "CheckIntervalHours",
            "Windows\\CurrentVersion\\Run",
        ):
            self.assertIn(marker, settings)
        self.assertIn("DispatcherTimer", app)
        self.assertIn("InstallOrUpdateAllAsync", window)
        self.assertIn("StartManagerUpgrade", window)

    def test_manager_msi_supports_upgrade_remove_and_shortcuts(self):
        wix = self.text("installer/manager.wxs")
        builder = self.text("scripts/build_manager_installer.py")
        for marker in (
            'Package Name="Hython Manager"',
            'Scope="perUser"',
            "MajorUpgrade",
            "ManagerStartMenu",
            "ManagerDesktopFeature",
            'Title="Hython Manager 1.0.0"',
        ):
            self.assertIn(marker, wix)
        self.assertIn('VERSION = "1.0.0"', builder)
        self.assertIn("HythonManager-{VERSION}-x64.msi", builder)
        self.assertIn("removeOnUninstall", wix)

    def test_manager_has_animated_bilingual_setup_launcher(self):
        project = self.text(
            "manager/HythonManagerSetup/HythonManagerSetup.csproj"
        )
        xaml = self.text("manager/HythonManagerSetup/MainWindow.xaml")
        code = self.text("manager/HythonManagerSetup/MainWindow.xaml.cs")
        app = self.text("manager/HythonManagerSetup/App.xaml.cs")
        build = self.text("build-manager-setup.bat")
        self.assertIn("HythonManagerInstaller.msi", project)
        for marker in ("Opacity=\"0\"", "ContentTranslate", "ProgressBar", "English"):
            self.assertIn(marker, xaml)
        for marker in ("DoubleAnimation", "CubicEase", "RunMsiAsync", "FindInstalled"):
            self.assertIn(marker, code)
        self.assertIn("PublishSingleFile=true", build)
        self.assertIn("window.Show()", app)
        self.assertIn("--install-silent", app)
        self.assertIn("--uninstall-silent", app)


if __name__ == "__main__":
    unittest.main()
