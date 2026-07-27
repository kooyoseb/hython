using System.Windows;
using System.Windows.Controls;
using HythonStudio.Services;

namespace HythonStudio;

public partial class EngineManagerDialog : Window
{
    public bool EngineChanged { get; private set; }

    public EngineManagerDialog()
    {
        InitializeComponent();
        Loaded += async (_, _) => await DetectAsync();
    }

    private async void Detect_Click(object sender, RoutedEventArgs e) =>
        await DetectAsync();

    private async Task DetectAsync()
    {
        SetBusy(true);
        try
        {
            EngineEnvironment state = await EngineManagementService.DetectAsync();
            PythonStatus.Text = state.PythonAvailable
                ? $"Python: {state.PythonVersion}" : "Python: 찾을 수 없음";
            PipStatus.Text = state.PipHythonInstalled
                ? $"PyPI Hython: {state.PipHythonVersion}" : "PyPI Hython: 설치되지 않음";
            WingetStatus.Text = state.WingetAvailable
                ? "Winget: 사용 가능" : "Winget: 찾을 수 없음";
            MsiStatus.Text = state.WindowsHythonInstalled
                ? "Windows Hython: 설치됨" : "Windows Hython: 설치되지 않음";
        }
        finally { SetBusy(false); }
    }

    private async void Install_Click(object sender, RoutedEventArgs e) =>
        await RunAsync(update: false);

    private async void Update_Click(object sender, RoutedEventArgs e) =>
        await RunAsync(update: true);

    private async void Remove_Click(object sender, RoutedEventArgs e)
    {
        EngineInstallSource source = SelectedSource();
        if (MessageBox.Show(
                this, $"선택한 방식({source})의 Hython을 제거할까요?",
                "Hython 제거", MessageBoxButton.YesNo,
                MessageBoxImage.Warning) != MessageBoxResult.Yes)
            return;
        SetBusy(true);
        LogBox.Clear();
        try
        {
            var result = await EngineManagementService.UninstallAsync(
                source, new Progress<string>(message =>
                {
                    LogBox.AppendText(message + Environment.NewLine);
                    LogBox.ScrollToEnd();
                }));
            LogBox.AppendText(result.Output);
            EngineChanged = result.ExitCode == 0;
            if (EngineChanged) await DetectAsync();
        }
        catch (Exception ex) { LogBox.AppendText("오류: " + ex.Message); }
        finally { SetBusy(false); }
    }

    private async Task RunAsync(bool update)
    {
        EngineInstallSource source = SelectedSource();
        SetBusy(true);
        LogBox.Clear();
        Progress<string> progress = new(message =>
        {
            LogBox.AppendText(message + Environment.NewLine);
            LogBox.ScrollToEnd();
        });
        try
        {
            var result = await EngineManagementService.InstallOrUpdateAsync(
                source, update, SkipWingetCheck.IsChecked == true, progress);
            LogBox.AppendText(result.Output);
            EngineChanged = result.ExitCode == 0;
            if (EngineChanged) await DetectAsync();
        }
        catch (Exception ex) { LogBox.AppendText("오류: " + ex.Message); }
        finally { SetBusy(false); }
    }

    private EngineInstallSource SelectedSource() =>
        Enum.Parse<EngineInstallSource>(
            Convert.ToString((SourceBox.SelectedItem as ComboBoxItem)?.Tag) ?? "Winget");

    private void SetBusy(bool busy)
    {
        InstallButton.IsEnabled = !busy;
        UpdateButton.IsEnabled = !busy;
        RemoveButton.IsEnabled = !busy;
        Progress.Visibility = busy ? Visibility.Visible : Visibility.Collapsed;
    }
}
