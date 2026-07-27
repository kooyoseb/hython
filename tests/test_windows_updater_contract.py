import re
import unittest
from pathlib import Path

import hython


class WindowsUpdaterContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.source = (cls.root / "installer" / "hython_updater.cs").read_text(
            encoding="utf-8"
        )
        cls.wix = (cls.root / "installer" / "hython.wxs").read_text(encoding="utf-8")

    def test_updater_version_matches_release(self):
        self.assertIn(
            f'AssemblyFileVersion("{hython.__version__}.0")', self.source
        )

    def test_updater_only_uses_official_repository(self):
        self.assertIn(
            "https://api.github.com/repos/kooyoseb/hython/releases?per_page=100",
            self.source,
        )
        self.assertNotRegex(self.source, r"http://")
        self.assertIn("client.Encoding = Encoding.UTF8", self.source)

    def test_non_core_releases_are_ignored(self):
        self.assertIn(
            r'Regex.IsMatch(tag, @"^[vV]\d+\.\d+\.\d+(?:\.\d+)?$")',
            self.source,
        )
        self.assertIn('"Hython-" + version + "-x64.msi"', self.source)
        self.assertIn('IsTrue(root, "draft")', self.source)
        self.assertIn('IsTrue(root, "prerelease")', self.source)

    def test_download_is_sha256_verified_before_install(self):
        verify_at = self.source.index("SHA256.Create()")
        install_at = self.source.index("public static int Install")
        self.assertLess(verify_at, install_at)
        self.assertIn("MSI SHA-256 검증 정보를 찾을 수 없습니다.", self.source)

    def test_installed_version_comes_from_windows_uninstall_registry(self):
        self.assertIn(
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", self.source
        )
        self.assertIn('child.GetValue("DisplayVersion")', self.source)

    def test_msi_contains_updater_and_login_startup(self):
        self.assertIn('File Id="HythonUpdaterExe"', self.wix)
        self.assertIn(r"Microsoft\Windows\CurrentVersion\Run", self.wix)
        self.assertIn('Name="Hython Updater"', self.wix)
        self.assertIn('ComponentRef Id="HythonUpdaterComponent"', self.wix)

    def test_language_selection_is_persisted_per_user(self):
        self.assertIn(r"Software\Kooyoseb\Hython Updater", self.source)
        self.assertIn('key.SetValue("Language", korean ? "ko" : "en"', self.source)
        self.assertIn('new ToolStripMenuItem("한국어")', self.source)
        self.assertIn('new ToolStripMenuItem("English")', self.source)


if __name__ == "__main__":
    unittest.main()
