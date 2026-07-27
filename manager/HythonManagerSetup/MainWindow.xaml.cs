using Microsoft.Win32;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Media.Animation;

namespace HythonManagerSetup;

public partial class MainWindow : Window
{
    private string? productCode;
    private string? installedVersion;
    private bool Busy;
    private bool Korean => LanguageSelector.SelectedIndex != 1;

    public MainWindow()
    {
        InitializeComponent();
        Loaded += (_, _) =>
        {
            FindInstalled();
            ApplyLanguage();
            BeginAnimation(OpacityProperty,
                new DoubleAnimation(0, 1, TimeSpan.FromMilliseconds(360)));
            ContentTranslate.BeginAnimation(
                System.Windows.Media.TranslateTransform.XProperty,
                new DoubleAnimation(28, 0, TimeSpan.FromMilliseconds(430))
                { EasingFunction = new CubicEase { EasingMode = EasingMode.EaseOut } });
        };
    }

    private void FindInstalled()
    {
        foreach (RegistryHive hive in new[] { RegistryHive.CurrentUser, RegistryHive.LocalMachine })
        foreach (RegistryView view in new[] { RegistryView.Registry64, RegistryView.Registry32 })
        using (RegistryKey baseKey = RegistryKey.OpenBaseKey(hive, view))
        using (RegistryKey? root = baseKey.OpenSubKey(
            @"Software\Microsoft\Windows\CurrentVersion\Uninstall"))
        {
            if (root is null) continue;
            foreach (string childName in root.GetSubKeyNames())
            using (RegistryKey? child = root.OpenSubKey(childName))
            {
                if (Convert.ToString(child?.GetValue("DisplayName")) != "Hython Manager")
                    continue;
                productCode = childName;
                installedVersion = Convert.ToString(child?.GetValue("DisplayVersion"));
                return;
            }
        }
    }

    private void ApplyLanguage()
    {
        bool maintenance = productCode is not null;
        if (Korean)
        {
            Heading.Text = maintenance ? "Hython Manager 유지관리" : "Hython Manager 설치";
            Description.Text = maintenance
                ? $"설치된 버전 {installedVersion}을 복구하거나 제거할 수 있습니다."
                : "제품 설치와 업데이트를 관리하는 트레이 앱을 설치합니다.";
            SideDescription.Text = "하이썬 생태계 전체를\n한곳에서 관리하세요.";
            LocationLabel.Text = "설치 위치";
            DesktopOption.Content = "바탕화면 바로가기 만들기";
            InstallNote.Text = "시작 메뉴와 Windows 자동 시작이 기본 구성됩니다.";
            MainButton.Content = maintenance ? "복구" : "설치";
            RemoveButton.Content = "제거";
        }
        else
        {
            Heading.Text = maintenance ? "Maintain Hython Manager" : "Install Hython Manager";
            Description.Text = maintenance
                ? $"Repair or remove installed version {installedVersion}."
                : "Install the tray app that manages every Hython product.";
            SideDescription.Text = "Manage the entire Hython\necosystem in one place.";
            LocationLabel.Text = "Install location";
            DesktopOption.Content = "Create a desktop shortcut";
            InstallNote.Text = "Start menu and Windows startup are configured automatically.";
            MainButton.Content = maintenance ? "Repair" : "Install";
            RemoveButton.Content = "Remove";
        }
        RemoveButton.Visibility = maintenance ? Visibility.Visible : Visibility.Collapsed;
        DesktopOption.IsEnabled = !maintenance;
    }

    private async void Main_Click(object sender, RoutedEventArgs e)
    {
        if (Busy) return;
        if (productCode is not null)
        {
            await RunMsiAsync($"/fa {productCode} /qn /norestart");
            return;
        }
        string temporary = Path.Combine(Path.GetTempPath(),
            "HythonManager-" + Guid.NewGuid().ToString("N") + ".msi");
        try
        {
            using Stream source = Assembly.GetExecutingAssembly()
                .GetManifestResourceStream("HythonManagerInstaller.msi")
                ?? throw new InvalidOperationException("Embedded Manager MSI is missing.");
            await using FileStream target = File.Create(temporary);
            await source.CopyToAsync(target);
            await target.FlushAsync();
            target.Close();
            string features = "ManagerFeature";
            if (DesktopOption.IsChecked == true)
                features += ",ManagerDesktopFeature";
            await RunMsiAsync($"/i \"{temporary}\" /qn /norestart ADDLOCAL=\"{features}\"");
        }
        finally
        {
            try { File.Delete(temporary); } catch { }
        }
    }

    private async void Remove_Click(object sender, RoutedEventArgs e)
    {
        if (Busy || productCode is null) return;
        MessageBoxResult answer = MessageBox.Show(this,
            Korean ? "Hython Manager를 제거할까요?" : "Remove Hython Manager?",
            "Hython Manager", MessageBoxButton.YesNo, MessageBoxImage.Question);
        if (answer == MessageBoxResult.Yes)
            await RunMsiAsync($"/x {productCode} /qn /norestart");
    }

    private async Task RunMsiAsync(string arguments)
    {
        Busy = true;
        MainButton.IsEnabled = RemoveButton.IsEnabled = false;
        Progress.Visibility = Visibility.Visible;
        Status.Text = Korean ? "Windows Installer 작업을 진행하고 있습니다…"
                             : "Windows Installer is working…";
        try
        {
            using Process process = Process.Start(new ProcessStartInfo(
                "msiexec.exe", arguments)
            {
                UseShellExecute = false, CreateNoWindow = true
            }) ?? throw new InvalidOperationException("Windows Installer could not start.");
            await process.WaitForExitAsync();
            if (process.ExitCode is not (0 or 3010 or 1641))
                throw new InvalidOperationException(
                    (Korean ? "설치 프로그램 오류 코드: " : "Installer error code: ") +
                    process.ExitCode);
            MessageBox.Show(this,
                Korean ? "작업이 완료되었습니다." : "The operation completed successfully.",
                "Hython Manager", MessageBoxButton.OK, MessageBoxImage.Information);
            Close();
        }
        catch (Exception ex)
        {
            Status.Text = ex.Message;
            MessageBox.Show(this, ex.Message, "Hython Manager",
                MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally
        {
            Busy = false;
            MainButton.IsEnabled = RemoveButton.IsEnabled = true;
            Progress.Visibility = Visibility.Collapsed;
        }
    }

    private void Language_Changed(object sender, System.Windows.Controls.SelectionChangedEventArgs e)
    {
        if (IsLoaded) ApplyLanguage();
    }
    private void Close_Click(object sender, RoutedEventArgs e)
    {
        if (!Busy) Close();
    }
}
