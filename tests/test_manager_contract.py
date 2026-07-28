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
        self.assertIn("<Version>1.1.2</Version>", project)

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
        self.assertIn("string partial = path + \".part\"", source)
        self.assertLess(
            source.index("await output.FlushAsync();"),
            source.index("File.Move(partial, path, true)"),
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
            'Title="Hython Manager 1.1.2"',
        ):
            self.assertIn(marker, wix)
        self.assertIn('VERSION = "1.1.2"', builder)
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

    def test_manager_has_resilient_operation_queue(self):
        queue = self.text(
            "manager/HythonManager/Services/OperationQueueService.cs"
        )
        operation = self.text("manager/HythonManager/Models/OperationItem.cs")
        catalog = self.text(
            "manager/HythonManager/Services/ProductCatalogService.cs"
        )
        history = self.text(
            "manager/HythonManager/Services/OperationHistory.cs"
        )
        app = self.text("manager/HythonManager/App.xaml.cs")
        xaml = self.text("manager/HythonManager/MainWindow.xaml")
        for marker in (
            "ObservableCollection<OperationItem>", "Enqueue", "OverallProgressChanged",
            "OperationState.RebootRequired", "TryRepairAsync",
        ):
            self.assertIn(marker, queue)
        for marker in ("ManualResetEventSlim", "Pause()", "Resume()"):
            self.assertIn(marker, operation)
        for marker in (
            "RangeHeaderValue", 'string partial = path + ".part"',
            "attempt <= 4", "/qn /norestart", "/fa ",
        ):
            self.assertIn(marker, catalog)
        self.assertNotIn("/passive", catalog)
        self.assertIn('"작업-{DateTime.Now:yyyy-MM}.jsonl"', history)
        self.assertIn("JsonSerializer.Serialize", history)
        self.assertIn("trayProgressItem", app)
        for marker in ("QueueList", "OverallProgress", "일시정지", "작업 기록 열기"):
            self.assertIn(marker, xaml)

    def test_manager_supports_persistent_dark_and_blue_light_themes(self):
        theme = self.text("manager/HythonManager/Services/ThemeService.cs")
        settings = self.text("manager/HythonManager/Services/ManagerSettings.cs")
        xaml = self.text("manager/HythonManager/MainWindow.xaml")
        app = self.text("manager/HythonManager/App.xaml")
        for marker in ("Dark", "Light", "#1677D2", "#F5F8FC", "#0D1119"):
            self.assertIn(marker, theme)
        self.assertIn('key.SetValue("Theme", Theme', settings)
        self.assertIn("ThemeRadio_Checked", xaml)
        self.assertIn("화이트 모드 · 파란색", xaml)
        self.assertIn("DynamicResource Accent", app)

    def test_manager_self_update_uses_verified_independent_helper(self):
        app = self.text("manager/HythonManager/App.xaml.cs")
        catalog = self.text(
            "manager/HythonManager/Services/ProductCatalogService.cs"
        )
        queue = self.text(
            "manager/HythonManager/Services/OperationQueueService.cs"
        )
        for marker in (
            "--apply-update", "RunUpdateHelperAndExitAsync",
            "RunManagerUpdateHelperAsync",
        ):
            self.assertIn(marker, app + catalog)
        for marker in (
            "File.Copy(currentExecutable, helperPath",
            "WaitForExitAsync(timeout.Token)",
            "firstLength != secondLength",
            "/qn /norestart",
        ):
            self.assertIn(marker, catalog)
        self.assertNotIn("timeout /t 2", catalog)
        self.assertLess(
            queue.index("다운로드 검증 완료"),
            queue.index("StartManagerUpgrade(path)"),
        )
        self.assertIn("Manager는 종료되지 않습니다.", queue)


if __name__ == "__main__":
    unittest.main()
