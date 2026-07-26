using Microsoft.Win32;
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.Net;
using System.Security.Cryptography;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;

[assembly: System.Reflection.AssemblyTitle("Hython Updater")]
[assembly: System.Reflection.AssemblyCompany("Kooyoseb")]
[assembly: System.Reflection.AssemblyProduct("Hython Updater")]
[assembly: System.Reflection.AssemblyVersion("2.0.4.0")]
[assembly: System.Reflection.AssemblyFileVersion("2.0.4.0")]

namespace HythonUpdater
{
    internal sealed class ReleaseAsset
    {
        public string Name;
        public string Url;
        public string Digest;
    }

    internal sealed class ReleaseInfo
    {
        public Version Version;
        public string Tag;
        public ReleaseAsset Msi;
        public ReleaseAsset Checksum;
    }

    internal static class UpdateEngine
    {
        private const string ReleasesApi =
            "https://api.github.com/repos/kooyoseb/hython/releases/latest";

        public static Version InstalledVersion()
        {
            Version best = new Version(0, 0, 0);
            string[] roots = {
                @"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                @"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
            };
            foreach (string rootPath in roots)
            {
                using (RegistryKey root = Registry.LocalMachine.OpenSubKey(rootPath))
                {
                    if (root == null) continue;
                    foreach (string childName in root.GetSubKeyNames())
                    {
                        using (RegistryKey child = root.OpenSubKey(childName))
                        {
                            if (child == null) continue;
                            string name = Convert.ToString(child.GetValue("DisplayName"));
                            string publisher = Convert.ToString(child.GetValue("Publisher"));
                            if (!String.Equals(name, "Hython", StringComparison.OrdinalIgnoreCase) &&
                                !(name.IndexOf("Hython", StringComparison.OrdinalIgnoreCase) >= 0 &&
                                  publisher.IndexOf("Kooyoseb", StringComparison.OrdinalIgnoreCase) >= 0))
                                continue;
                            Version parsed;
                            if (Version.TryParse(Convert.ToString(child.GetValue("DisplayVersion")), out parsed)
                                && parsed > best)
                                best = parsed;
                        }
                    }
                }
            }
            if (best == new Version(0, 0, 0))
                Version.TryParse(Application.ProductVersion, out best);
            return best ?? new Version(0, 0, 0);
        }

        public static ReleaseInfo LatestRelease()
        {
            ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
            using (WebClient client = NewClient())
            {
                string json = client.DownloadString(ReleasesApi);
                var root = new JavaScriptSerializer().DeserializeObject(json)
                    as Dictionary<string, object>;
                if (root == null) throw new InvalidDataException("릴리스 응답을 읽을 수 없습니다.");
                string tag = Convert.ToString(root["tag_name"]);
                Version version;
                if (!Version.TryParse(tag.TrimStart('v', 'V'), out version))
                    throw new InvalidDataException("릴리스 버전이 올바르지 않습니다: " + tag);
                var result = new ReleaseInfo { Version = version, Tag = tag };
                object[] assets = root["assets"] as object[];
                if (assets == null) throw new InvalidDataException("릴리스 파일 목록이 없습니다.");
                foreach (object item in assets)
                {
                    var asset = item as Dictionary<string, object>;
                    if (asset == null) continue;
                    var parsed = new ReleaseAsset {
                        Name = Convert.ToString(asset["name"]),
                        Url = Convert.ToString(asset["browser_download_url"]),
                        Digest = asset.ContainsKey("digest") ? Convert.ToString(asset["digest"]) : ""
                    };
                    if (parsed.Name.EndsWith("-x64.msi", StringComparison.OrdinalIgnoreCase))
                        result.Msi = parsed;
                    else if (parsed.Name.EndsWith("-x64.msi.sha256", StringComparison.OrdinalIgnoreCase))
                        result.Checksum = parsed;
                }
                if (result.Msi == null)
                    throw new InvalidDataException("최신 릴리스에 x64 MSI 파일이 없습니다.");
                return result;
            }
        }

        public static string DownloadAndVerify(ReleaseInfo release)
        {
            string directory = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData),
                "Hython", "Updates", release.Tag);
            Directory.CreateDirectory(directory);
            string msiPath = Path.Combine(directory, release.Msi.Name);
            using (WebClient client = NewClient())
                client.DownloadFile(release.Msi.Url, msiPath);

            string expected = "";
            if (!String.IsNullOrWhiteSpace(release.Msi.Digest) &&
                release.Msi.Digest.StartsWith("sha256:", StringComparison.OrdinalIgnoreCase))
                expected = release.Msi.Digest.Substring(7).Trim();
            if (String.IsNullOrWhiteSpace(expected) && release.Checksum != null)
            {
                using (WebClient client = NewClient())
                    expected = client.DownloadString(release.Checksum.Url)
                        .Split(new[] { ' ', '\t', '\r', '\n' },
                               StringSplitOptions.RemoveEmptyEntries)[0];
            }
            if (String.IsNullOrWhiteSpace(expected))
                throw new InvalidDataException("MSI SHA-256 검증 정보를 찾을 수 없습니다.");
            string actual;
            using (SHA256 sha = SHA256.Create())
            using (FileStream stream = File.OpenRead(msiPath))
                actual = BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "");
            if (!String.Equals(actual, expected, StringComparison.OrdinalIgnoreCase))
            {
                File.Delete(msiPath);
                throw new InvalidDataException("다운로드한 MSI의 SHA-256이 일치하지 않습니다.");
            }
            return msiPath;
        }

        public static int Install(string msiPath)
        {
            var info = new ProcessStartInfo {
                FileName = "msiexec.exe",
                Arguments = "/i \"" + msiPath + "\" /qn /norestart",
                UseShellExecute = true,
                Verb = "runas"
            };
            using (Process process = Process.Start(info))
            {
                process.WaitForExit();
                return process.ExitCode;
            }
        }

        private static WebClient NewClient()
        {
            var client = new WebClient();
            client.Headers[HttpRequestHeader.UserAgent] = "Hython-Updater/2.0.4";
            client.Headers[HttpRequestHeader.Accept] = "application/vnd.github+json";
            return client;
        }
    }

    internal sealed class TrayApplication : ApplicationContext
    {
        private readonly NotifyIcon icon;
        private readonly System.Windows.Forms.Timer timer;
        private readonly ContextMenuStrip menu;
        private readonly ToolStripMenuItem checkItem;
        private readonly ToolStripMenuItem versionItem;
        private readonly ToolStripMenuItem languageItem;
        private readonly ToolStripMenuItem koreanItem;
        private readonly ToolStripMenuItem englishItem;
        private readonly ToolStripMenuItem exitItem;
        private bool checking;
        private bool korean;

        public TrayApplication()
        {
            korean = LoadLanguage();
            menu = new ContextMenuStrip();
            checkItem = new ToolStripMenuItem();
            checkItem.Click += delegate { BeginCheck(true); };
            versionItem = new ToolStripMenuItem { Enabled = false };
            languageItem = new ToolStripMenuItem();
            koreanItem = new ToolStripMenuItem("한국어");
            englishItem = new ToolStripMenuItem("English");
            koreanItem.Click += delegate { SetLanguage(true); };
            englishItem.Click += delegate { SetLanguage(false); };
            languageItem.DropDownItems.AddRange(new ToolStripItem[] { koreanItem, englishItem });
            exitItem = new ToolStripMenuItem();
            exitItem.Click += delegate { ExitThread(); };
            menu.Items.Add(checkItem);
            menu.Items.Add(versionItem);
            menu.Items.Add(languageItem);
            menu.Items.Add(new ToolStripSeparator());
            menu.Items.Add(exitItem);
            icon = new NotifyIcon {
                Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath),
                ContextMenuStrip = menu,
                Visible = true
            };
            icon.DoubleClick += delegate { BeginCheck(true); };
            ApplyLanguage();
            timer = new System.Windows.Forms.Timer { Interval = 6 * 60 * 60 * 1000 };
            timer.Tick += delegate { BeginCheck(false); };
            timer.Start();
            BeginCheck(false);
        }

        private async void BeginCheck(bool manual)
        {
            if (checking) return;
            checking = true;
            try
            {
                Version installed = UpdateEngine.InstalledVersion();
                ReleaseInfo release = await Task.Run(() => UpdateEngine.LatestRelease());
                if (release.Version <= installed)
                {
                    if (manual) Notify(
                        T("업데이트 없음", "No updates"),
                        T("하이썬 " + installed + "이(가) 최신 버전입니다.",
                          "Hython " + installed + " is up to date."));
                    return;
                }
                Notify(
                    T("새 버전 발견", "New version found"),
                    T("하이썬 " + release.Version + "을(를) 내려받고 있습니다.",
                      "Downloading Hython " + release.Version + "."));
                string path = await Task.Run(() => UpdateEngine.DownloadAndVerify(release));
                Notify(
                    T("업데이트 설치", "Installing update"),
                    T("관리자 권한을 허용하면 하이썬 " + release.Version + "이(가) 설치됩니다.",
                      "Approve administrator access to install Hython " + release.Version + "."));
                int code = await Task.Run(() => UpdateEngine.Install(path));
                if (code == 0 || code == 3010 || code == 1641)
                {
                    Notify(
                        T("업데이트 완료", "Update complete"),
                        T("하이썬 " + release.Version + " 설치가 완료되었습니다.",
                          "Hython " + release.Version + " was installed successfully."));
                    timer.Stop();
                    await Task.Delay(5000);
                    ExitThread();
                }
                else Notify(
                    T("업데이트 실패", "Update failed"),
                    T("MSI 설치 오류 코드: " + code, "MSI error code: " + code));
            }
            catch (Exception ex)
            {
                if (manual) Notify(
                    T("업데이트 확인 실패", "Update check failed"), ex.Message);
            }
            finally { checking = false; }
        }

        private static bool LoadLanguage()
        {
            using (RegistryKey key = Registry.CurrentUser.OpenSubKey(
                @"Software\Kooyoseb\Hython Updater"))
            {
                string saved = key == null ? null : Convert.ToString(key.GetValue("Language"));
                if (saved == "ko") return true;
                if (saved == "en") return false;
            }
            return CultureInfo.CurrentUICulture.TwoLetterISOLanguageName == "ko";
        }

        private void SetLanguage(bool useKorean)
        {
            korean = useKorean;
            using (RegistryKey key = Registry.CurrentUser.CreateSubKey(
                @"Software\Kooyoseb\Hython Updater"))
                key.SetValue("Language", korean ? "ko" : "en", RegistryValueKind.String);
            ApplyLanguage();
            Notify(
                T("언어 변경 완료", "Language changed"),
                T("업데이터 언어가 한국어로 변경되었습니다.",
                  "The updater language has been changed to English."));
        }

        private void ApplyLanguage()
        {
            icon.Text = T("하이썬 업데이터", "Hython Updater");
            checkItem.Text = T("지금 업데이트 확인", "Check for updates now");
            versionItem.Text = T("설치된 버전: ", "Installed version: ") +
                UpdateEngine.InstalledVersion();
            languageItem.Text = T("언어", "Language");
            exitItem.Text = T("종료", "Exit");
            koreanItem.Checked = korean;
            englishItem.Checked = !korean;
        }

        private string T(string ko, string en)
        {
            return korean ? ko : en;
        }

        private void Notify(string title, string text)
        {
            icon.BalloonTipTitle = title;
            icon.BalloonTipText = text.Length > 240 ? text.Substring(0, 240) : text;
            icon.ShowBalloonTip(5000);
        }

        protected override void ExitThreadCore()
        {
            timer.Stop();
            icon.Visible = false;
            icon.Dispose();
            base.ExitThreadCore();
        }
    }

    internal static class Program
    {
        [STAThread]
        private static int Main(string[] args)
        {
            bool once = Array.IndexOf(args, "--check-once") >= 0;
            bool dryRun = Array.IndexOf(args, "--dry-run") >= 0;
            if (once)
            {
                try
                {
                    Version installed = UpdateEngine.InstalledVersion();
                    ReleaseInfo latest = UpdateEngine.LatestRelease();
                    Console.WriteLine("설치됨=" + installed);
                    Console.WriteLine("최신=" + latest.Version);
                    Console.WriteLine("업데이트=" + (latest.Version > installed));
                    if (!dryRun && latest.Version > installed)
                        return UpdateEngine.Install(UpdateEngine.DownloadAndVerify(latest));
                    return 0;
                }
                catch (Exception ex) { Console.Error.WriteLine(ex.Message); return 1; }
            }
            bool created;
            using (var mutex = new Mutex(true, @"Global\Kooyoseb.Hython.Updater", out created))
            {
                if (!created) return 0;
                Application.EnableVisualStyles();
                Application.SetCompatibleTextRenderingDefault(false);
                Application.Run(new TrayApplication());
            }
            return 0;
        }
    }
}
