using System;
using System.ComponentModel;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Windows.Forms;
using Microsoft.Win32;

[assembly: AssemblyTitle("Hython Setup")]
[assembly: AssemblyDescription("Bilingual Hython programming language installer")]
[assembly: AssemblyCompany("Kooyoseb")]
[assembly: AssemblyProduct("Hython Programming Language")]
[assembly: AssemblyCopyright("MIT License")]
[assembly: AssemblyVersion("2.0.5.0")]
[assembly: AssemblyFileVersion("2.0.5.0")]

namespace HythonSetup
{
    internal sealed class SetupForm : Form
    {
        private readonly ComboBox language = new ComboBox();
        private readonly Label title = new Label();
        private readonly Label description = new Label();
        private readonly Label languageLabel = new Label();
        private readonly GroupBox options = new GroupBox();
        private readonly CheckBox pathOption = new CheckBox();
        private readonly CheckBox startMenuOption = new CheckBox();
        private readonly CheckBox desktopOption = new CheckBox();
        private readonly Button install = new Button();
        private readonly Button uninstall = new Button();
        private readonly Button cancel = new Button();
        private readonly Label status = new Label();
        private string installedProductCode;
        private string installedVersion;

        internal SetupForm()
        {
            Text = "Hython Setup";
            ClientSize = new Size(520, 390);
            BackColor = Color.White;
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            MinimizeBox = false;
            StartPosition = FormStartPosition.CenterScreen;
            AutoScaleMode = AutoScaleMode.Dpi;

            Panel banner = new Panel();
            banner.SetBounds(0, 0, 520, 105);
            banner.BackColor = Color.FromArgb(177, 45, 45);

            title.SetBounds(28, 19, 464, 36);
            title.Font = new Font(Font.FontFamily, 17, FontStyle.Bold);
            title.ForeColor = Color.White;
            description.SetBounds(30, 61, 460, 38);
            description.ForeColor = Color.White;
            banner.Controls.AddRange(new Control[] { title, description });

            languageLabel.SetBounds(30, 126, 150, 24);
            language.SetBounds(180, 122, 190, 28);
            language.DropDownStyle = ComboBoxStyle.DropDownList;
            language.Items.AddRange(new object[] { "한국어", "English" });
            language.SelectedIndex = 0;
            language.SelectedIndexChanged += delegate { ApplyLanguage(); };

            options.SetBounds(28, 168, 464, 132);
            pathOption.SetBounds(20, 29, 420, 24);
            startMenuOption.SetBounds(20, 60, 420, 24);
            desktopOption.SetBounds(20, 91, 420, 24);
            pathOption.Checked = true;
            startMenuOption.Checked = true;
            desktopOption.Checked = false;

            Panel footer = new Panel();
            footer.SetBounds(0, 310, 520, 80);
            footer.BackColor = Color.FromArgb(245, 245, 245);
            footer.BorderStyle = BorderStyle.FixedSingle;

            status.SetBounds(28, 10, 240, 52);
            status.ForeColor = Color.FromArgb(50, 90, 140);

            uninstall.SetBounds(270, 25, 76, 32);
            install.SetBounds(350, 25, 76, 32);
            cancel.SetBounds(430, 25, 76, 32);
            install.Click += InstallClicked;
            uninstall.Click += UninstallClicked;
            cancel.Click += delegate { Close(); };
            uninstall.Visible = false;
            footer.Controls.AddRange(new Control[] { status, uninstall, install, cancel });

            options.Controls.AddRange(new Control[] {
                pathOption, startMenuOption, desktopOption
            });
            Controls.AddRange(new Control[] { banner, languageLabel, language, options, footer });
            AcceptButton = install;
            CancelButton = cancel;
            FindInstalledHython();
            ApplyLanguage();
        }

        private bool Korean { get { return language.SelectedIndex == 0; } }

        private void ApplyLanguage()
        {
            if (Korean)
            {
                Text = "하이썬 설치";
                title.Text = installedProductCode == null ? "하이썬 2.0.4 설치" : "하이썬 유지관리";
                description.Text = installedProductCode == null
                    ? "설치할 기능을 선택한 뒤 설치 버튼을 누르세요."
                    : "설치된 하이썬을 복구하거나 제거할 수 있습니다.";
                languageLabel.Text = "설치 프로그램 언어";
                options.Text = installedProductCode == null ? "설치 옵션" : "설치 정보";
                pathOption.Text = "시스템 PATH에 하이썬 추가";
                startMenuOption.Text = "시작 메뉴에 Hython Command Prompt 바로가기 만들기";
                desktopOption.Text = "바탕화면에 Hython Command Prompt 바로가기 만들기";
                install.Text = installedProductCode == null ? "설치" : "복구";
                uninstall.Text = "제거";
                cancel.Text = "취소";
                status.Text = installedProductCode == null ? ""
                    : "설치된 버전: " + installedVersion;
            }
            else
            {
                Text = "Hython Setup";
                title.Text = installedProductCode == null ? "Install Hython 2.0.4" : "Hython maintenance";
                description.Text = installedProductCode == null
                    ? "Choose the features to install, then select Install."
                    : "Repair or remove the installed Hython application.";
                languageLabel.Text = "Setup language";
                options.Text = installedProductCode == null ? "Installation options" : "Installation information";
                pathOption.Text = "Add Hython to the system PATH";
                startMenuOption.Text = "Create a Hython Command Prompt Start menu shortcut";
                desktopOption.Text = "Create a Hython Command Prompt desktop shortcut";
                install.Text = installedProductCode == null ? "Install" : "Repair";
                uninstall.Text = "Remove";
                cancel.Text = "Cancel";
                status.Text = installedProductCode == null ? ""
                    : "Installed version: " + installedVersion;
            }
            bool maintenance = installedProductCode != null;
            uninstall.Visible = maintenance;
            pathOption.Enabled = !maintenance;
            startMenuOption.Enabled = !maintenance;
            desktopOption.Enabled = !maintenance;
        }

        private void InstallClicked(object sender, EventArgs e)
        {
            if (installedProductCode != null)
            {
                RunMaintenance("/fa " + installedProductCode + " /qn /norestart", true);
                return;
            }
            string temporaryMsi = Path.Combine(
                Path.GetTempPath(), "Hython-2.0.4-" + Guid.NewGuid().ToString("N") + ".msi");
            try
            {
                install.Enabled = false;
                cancel.Enabled = false;
                status.Text = Korean
                    ? "관리자 권한을 승인하면 설치가 시작됩니다."
                    : "Approve the administrator prompt to begin installation.";
                Application.DoEvents();

                using (Stream source = Assembly.GetExecutingAssembly()
                    .GetManifestResourceStream("HythonInstaller.msi"))
                {
                    if (source == null)
                        throw new InvalidOperationException("Embedded MSI resource is missing.");
                    using (FileStream target = File.Create(temporaryMsi))
                        source.CopyTo(target);
                }

                string features = "MainFeature";
                if (pathOption.Checked) features += ",PathFeature";
                if (startMenuOption.Checked) features += ",StartMenuFeature";
                if (desktopOption.Checked) features += ",DesktopFeature";

                ProcessStartInfo start = new ProcessStartInfo();
                start.FileName = "msiexec.exe";
                start.Arguments = "/i \"" + temporaryMsi +
                    "\" /qn /norestart ADDLOCAL=\"" + features + "\"";
                start.UseShellExecute = true;
                start.Verb = "runas";
                Process process = Process.Start(start);
                process.WaitForExit();

                if (process.ExitCode == 0 || process.ExitCode == 3010)
                {
                    MessageBox.Show(
                        Korean ? "하이썬 2.0.4 설치가 완료되었습니다."
                               : "Hython 2.0.4 was installed successfully.",
                        Korean ? "설치 완료" : "Installation complete",
                        MessageBoxButtons.OK, MessageBoxIcon.Information);
                    Close();
                }
                else
                {
                    MessageBox.Show(
                        (Korean ? "설치에 실패했습니다. 오류 코드: "
                                : "Installation failed. Error code: ") + process.ExitCode,
                        Korean ? "설치 오류" : "Installation error",
                        MessageBoxButtons.OK, MessageBoxIcon.Error);
                }
            }
            catch (Win32Exception ex)
            {
                if (ex.NativeErrorCode != 1223)
                    MessageBox.Show(ex.Message, Text, MessageBoxButtons.OK, MessageBoxIcon.Error);
                else
                    status.Text = Korean ? "관리자 권한 요청이 취소되었습니다."
                                         : "The administrator request was cancelled.";
            }
            catch (Exception ex)
            {
                MessageBox.Show(ex.Message, Text, MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
            finally
            {
                try { if (File.Exists(temporaryMsi)) File.Delete(temporaryMsi); }
                catch { }
                install.Enabled = true;
                cancel.Enabled = true;
            }
        }

        private void UninstallClicked(object sender, EventArgs e)
        {
            if (installedProductCode == null) return;
            DialogResult answer = MessageBox.Show(
                Korean ? "하이썬을 이 컴퓨터에서 제거할까요?"
                       : "Remove Hython from this computer?",
                Korean ? "하이썬 제거" : "Remove Hython",
                MessageBoxButtons.YesNo, MessageBoxIcon.Question);
            if (answer == DialogResult.Yes)
                RunMaintenance("/x " + installedProductCode + " /qn /norestart", false);
        }

        private void RunMaintenance(string arguments, bool repair)
        {
            try
            {
                install.Enabled = false;
                uninstall.Enabled = false;
                cancel.Enabled = false;
                status.Text = Korean
                    ? (repair ? "하이썬을 복구하는 중입니다." : "하이썬을 제거하는 중입니다.")
                    : (repair ? "Repairing Hython." : "Removing Hython.");
                Application.DoEvents();
                ProcessStartInfo start = new ProcessStartInfo("msiexec.exe", arguments);
                start.UseShellExecute = true;
                start.Verb = "runas";
                Process process = Process.Start(start);
                process.WaitForExit();
                if (process.ExitCode == 0 || process.ExitCode == 3010)
                {
                    MessageBox.Show(
                        Korean
                            ? (repair ? "하이썬 복구가 완료되었습니다." : "하이썬이 제거되었습니다.")
                            : (repair ? "Hython repair completed." : "Hython was removed."),
                        Korean ? "작업 완료" : "Operation complete",
                        MessageBoxButtons.OK, MessageBoxIcon.Information);
                    if (!repair) Close();
                }
                else
                    MessageBox.Show(
                        (Korean ? "작업에 실패했습니다. 오류 코드: "
                                : "The operation failed. Error code: ") + process.ExitCode,
                        Text, MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
            catch (Win32Exception ex)
            {
                if (ex.NativeErrorCode != 1223)
                    MessageBox.Show(ex.Message, Text, MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
            finally
            {
                install.Enabled = true;
                uninstall.Enabled = true;
                cancel.Enabled = true;
            }
        }

        private void FindInstalledHython()
        {
            Version newestVersion = null;
            string newestCode = null;
            string newestDisplayVersion = null;
            string[] roots = {
                @"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                @"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
            };
            foreach (string rootName in roots)
            {
                using (RegistryKey root = Registry.LocalMachine.OpenSubKey(rootName))
                {
                    if (root == null) continue;
                    foreach (string keyName in root.GetSubKeyNames())
                    {
                        using (RegistryKey key = root.OpenSubKey(keyName))
                        {
                            if (key == null) continue;
                            string name = key.GetValue("DisplayName") as string;
                            string publisher = key.GetValue("Publisher") as string;
                            if (name == "Hython" && publisher == "Kooyoseb")
                            {
                                string detected = key.GetValue("DisplayVersion") as string ?? "0.0.0";
                                Version detectedVersion;
                                if (!Version.TryParse(detected, out detectedVersion))
                                    detectedVersion = new Version(0, 0, 0);
                                if (newestVersion == null || detectedVersion > newestVersion)
                                {
                                    newestVersion = detectedVersion;
                                    newestCode = keyName;
                                    newestDisplayVersion = detected;
                                }
                            }
                        }
                    }
                }
            }
            if (newestVersion != null && newestVersion >= new Version(2, 0, 4))
            {
                installedProductCode = newestCode;
                installedVersion = newestDisplayVersion;
            }
        }
    }

    internal static class Program
    {
        [STAThread]
        private static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new SetupForm());
        }
    }
}
