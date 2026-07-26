using System;
using System.ComponentModel;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Windows.Forms;

[assembly: AssemblyTitle("Hython Setup")]
[assembly: AssemblyDescription("Bilingual Hython programming language installer")]
[assembly: AssemblyCompany("Kooyoseb")]
[assembly: AssemblyProduct("Hython Programming Language")]
[assembly: AssemblyCopyright("MIT License")]
[assembly: AssemblyVersion("2.0.2.0")]
[assembly: AssemblyFileVersion("2.0.2.0")]

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
        private readonly Button cancel = new Button();
        private readonly Label status = new Label();

        internal SetupForm()
        {
            Text = "Hython Setup";
            ClientSize = new Size(520, 390);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            MinimizeBox = false;
            StartPosition = FormStartPosition.CenterScreen;
            AutoScaleMode = AutoScaleMode.Dpi;

            title.SetBounds(28, 24, 464, 36);
            title.Font = new Font(Font.FontFamily, 17, FontStyle.Bold);
            description.SetBounds(30, 67, 460, 44);

            languageLabel.SetBounds(30, 122, 150, 24);
            language.SetBounds(180, 118, 190, 28);
            language.DropDownStyle = ComboBoxStyle.DropDownList;
            language.Items.AddRange(new object[] { "한국어", "English" });
            language.SelectedIndex = 0;
            language.SelectedIndexChanged += delegate { ApplyLanguage(); };

            options.SetBounds(28, 165, 464, 132);
            pathOption.SetBounds(20, 29, 420, 24);
            startMenuOption.SetBounds(20, 60, 420, 24);
            desktopOption.SetBounds(20, 91, 420, 24);
            pathOption.Checked = true;
            startMenuOption.Checked = true;
            desktopOption.Checked = false;

            status.SetBounds(30, 308, 310, 45);
            status.ForeColor = Color.FromArgb(50, 90, 140);

            install.SetBounds(336, 330, 76, 32);
            cancel.SetBounds(416, 330, 76, 32);
            install.Click += InstallClicked;
            cancel.Click += delegate { Close(); };

            options.Controls.AddRange(new Control[] {
                pathOption, startMenuOption, desktopOption
            });
            Controls.AddRange(new Control[] {
                title, description, languageLabel, language, options,
                status, install, cancel
            });
            AcceptButton = install;
            CancelButton = cancel;
            ApplyLanguage();
        }

        private bool Korean { get { return language.SelectedIndex == 0; } }

        private void ApplyLanguage()
        {
            if (Korean)
            {
                Text = "하이썬 설치";
                title.Text = "하이썬 2.0.2 설치";
                description.Text = "설치할 기능을 선택한 뒤 설치 버튼을 누르세요.";
                languageLabel.Text = "설치 프로그램 언어";
                options.Text = "설치 옵션";
                pathOption.Text = "시스템 PATH에 하이썬 추가";
                startMenuOption.Text = "시작 메뉴에 Hython Command Prompt 바로가기 만들기";
                desktopOption.Text = "바탕화면에 Hython Command Prompt 바로가기 만들기";
                install.Text = "설치";
                cancel.Text = "취소";
                status.Text = "";
            }
            else
            {
                Text = "Hython Setup";
                title.Text = "Install Hython 2.0.2";
                description.Text = "Choose the features to install, then select Install.";
                languageLabel.Text = "Setup language";
                options.Text = "Installation options";
                pathOption.Text = "Add Hython to the system PATH";
                startMenuOption.Text = "Create a Hython Command Prompt Start menu shortcut";
                desktopOption.Text = "Create a Hython Command Prompt desktop shortcut";
                install.Text = "Install";
                cancel.Text = "Cancel";
                status.Text = "";
            }
        }

        private void InstallClicked(object sender, EventArgs e)
        {
            string temporaryMsi = Path.Combine(
                Path.GetTempPath(), "Hython-2.0.2-" + Guid.NewGuid().ToString("N") + ".msi");
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
                        Korean ? "하이썬 2.0.2 설치가 완료되었습니다."
                               : "Hython 2.0.2 was installed successfully.",
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
