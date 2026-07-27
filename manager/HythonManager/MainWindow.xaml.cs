using HythonManager.Models;
using HythonManager.Services;
using System.ComponentModel;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media.Animation;
using System.Diagnostics;
using System.IO;

namespace HythonManager;

public partial class MainWindow : Window
{
    private readonly ProductCatalogService catalog = new();
    private readonly OperationQueueService queue;
    private readonly ManagerSettings settings;
    private readonly SemaphoreSlim operationLock = new(1, 1);
    private IReadOnlyList<ProductInfo> currentProducts = Array.Empty<ProductInfo>();
    private bool settingsLoaded;
    public bool AllowClose { get; set; }

    public MainWindow(ManagerSettings settings)
    {
        this.settings = settings;
        queue = new OperationQueueService(catalog);
        InitializeComponent();
        QueueList.ItemsSource = queue.Items;
        queue.OverallProgressChanged += (value, text) => Dispatcher.Invoke(() =>
        {
            OverallProgress.Value = value;
            StatusText.Text = text;
            App.UpdateTrayProgress(value, text);
        });
        queue.OperationFinished += item => Dispatcher.Invoke(() =>
        {
            App.Notify(item.State == OperationState.RebootRequired
                    ? "재부팅 필요" : item.State == OperationState.Completed
                        ? "작업 완료" : "작업 실패",
                $"{item.ProductName}: {item.Detail}");
        });
        StartWithWindowsCheck.IsChecked = settings.StartWithWindows;
        BackgroundChecksCheck.IsChecked = settings.BackgroundChecks;
        settingsLoaded = true;
        Loaded += async (_, _) =>
        {
            StartLoadingAnimation();
            await RefreshProductsAsync(false);
        };
    }

    public async Task RefreshProductsAsync(bool notify, bool showErrors = true)
    {
        if (!await operationLock.WaitAsync(0)) return;
        LoadingOverlay.Visibility = Visibility.Visible;
        LoadingText.Text = "GitHub 태그와 설치 상태를 분석하는 중…";
        StatusText.Text = "제품 카탈로그 동기화 중";
        try
        {
            IReadOnlyList<ProductInfo> products = await catalog.LoadAsync();
            currentProducts = products;
            ProductsList.ItemsSource = products;
            int installed = products.Count(p => p.InstalledVersion is not null);
            int updates = products.Count(p => p.State == ProductState.UpdateAvailable);
            SummaryText.Text = $"{products.Count}개 제품 발견 · {installed}개 설치됨" +
                (updates > 0 ? $" · {updates}개 업데이트 가능" : " · 모두 최신");
            LastCheckedText.Text = DateTime.Now.ToString("HH:mm에 확인");
            StatusText.Text = "제품 상태 최신";
            if (notify)
                ShowTrayBalloon("확인 완료", updates > 0
                    ? $"{updates}개의 업데이트가 있습니다."
                    : "설치된 Hython 제품이 모두 최신입니다.");
        }
        catch (Exception ex)
        {
            SummaryText.Text = "제품 정보를 불러오지 못했습니다.";
            StatusText.Text = "동기화 실패";
            if (showErrors)
                System.Windows.MessageBox.Show(this, ex.Message, "Hython Manager",
                    MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally
        {
            LoadingOverlay.Visibility = Visibility.Collapsed;
            operationLock.Release();
        }
    }

    private async void Install_Click(object sender, RoutedEventArgs e)
    {
        if ((sender as FrameworkElement)?.Tag is not ProductInfo product) return;
        queue.Enqueue(product);
        StatusText.Text = $"{product.Name} 작업을 대기열에 추가했습니다.";
    }

    public async Task InstallOrUpdateAllAsync()
    {
        ProductInfo[] targets = currentProducts
            .Where(product => product.State != ProductState.Installed).ToArray();
        if (targets.Length == 0)
        {
            App.Notify("Hython Manager", "설치하거나 업데이트할 제품이 없습니다.");
            return;
        }
        if (IsVisible && System.Windows.MessageBox.Show(this,
                $"{targets.Length}개 제품을 차례로 설치하거나 업데이트할까요?",
                "Hython Manager", MessageBoxButton.YesNo,
                MessageBoxImage.Question) != MessageBoxResult.Yes) return;
        foreach (ProductInfo product in targets) queue.Enqueue(product);
        StatusText.Text = $"{targets.Length}개 작업을 대기열에 추가했습니다.";
    }

    private async Task<bool> InstallProductCoreAsync(ProductInfo product)
    {
        LoadingOverlay.Visibility = Visibility.Visible;
        LoadingText.Text = $"{product.Name} 준비 중…";
        try
        {
            if (product.Id == "vscode")
            {
                int vscodeCode = await ProductCatalogService.InstallAsync(product, null);
                if (vscodeCode != 0) throw new InvalidOperationException(
                    $"VS Code 확장 설치 오류 코드: {vscodeCode}");
            }
            else
            {
                var progress = new Progress<double>(value =>
                    LoadingText.Text = $"{product.Name} 다운로드 중 · {value:P0}");
                string path = await catalog.DownloadVerifiedAsync(product, progress);
                if (product.Id == "manager")
                {
                    ProductCatalogService.StartManagerUpgrade(path);
                    App.ExitForUpgrade();
                    return true;
                }
                int code = await ProductCatalogService.InstallAsync(product, path);
                if (code is not (0 or 3010 or 1641))
                    throw new InvalidOperationException($"설치 프로그램 오류 코드: {code}");
            }
            return true;
        }
        catch (Exception ex)
        {
            System.Windows.MessageBox.Show(this, ex.Message, product.Name,
                MessageBoxButton.OK, MessageBoxImage.Error);
            return false;
        }
        finally { LoadingOverlay.Visibility = Visibility.Collapsed; }
    }

    private async void Uninstall_Click(object sender, RoutedEventArgs e)
    {
        if ((sender as FrameworkElement)?.Tag is not ProductInfo product ||
            product.InstalledVersion is null) return;
        if (System.Windows.MessageBox.Show(this, $"{product.Name}을(를) 제거할까요?",
                "Hython Manager", MessageBoxButton.YesNo,
                MessageBoxImage.Question) != MessageBoxResult.Yes) return;
        await RunProductActionAsync(product, async () =>
        {
            StatusText.Text = $"{product.Name} 제거 중";
            int code = await ProductCatalogService.UninstallAsync(product);
            if (code is not (0 or 3010 or 1641))
                throw new InvalidOperationException($"제거 프로그램 오류 코드: {code}");
        });
    }

    private async void Repair_Click(object sender, RoutedEventArgs e)
    {
        if ((sender as FrameworkElement)?.Tag is not ProductInfo product) return;
        StatusText.Text = $"{product.Name} 복구 중";
        bool repaired = await ProductCatalogService.TryRepairAsync(product);
        await OperationHistory.WriteAsync(product.Name, "복구",
            repaired ? "완료" : "실패",
            repaired ? "Windows Installer 복구 완료" : "복구를 완료하지 못했습니다.");
        App.Notify(repaired ? "복구 완료" : "복구 실패",
            $"{product.Name}: {(repaired ? "설치가 복구되었습니다." : "작업 기록을 확인하세요.")}");
        await RefreshProductsAsync(false);
    }

    private void PauseResume_Click(object sender, RoutedEventArgs e)
    {
        if ((sender as FrameworkElement)?.Tag is OperationItem item)
            queue.PauseOrResume(item);
    }

    private void OpenHistory_Click(object sender, RoutedEventArgs e)
    {
        Directory.CreateDirectory(OperationHistory.LogDirectory);
        Process.Start(new ProcessStartInfo("explorer.exe", OperationHistory.LogDirectory)
            { UseShellExecute = true });
    }

    private async Task RunProductActionAsync(ProductInfo product, Func<Task> action)
    {
        LoadingOverlay.Visibility = Visibility.Visible;
        LoadingText.Text = $"{product.Name} 준비 중…";
        try
        {
            await action();
            if (product.Id == "manager") return;
            await RefreshProductsAsync(false);
            ShowTrayBalloon("작업 완료", $"{product.Name} 관리 작업이 완료되었습니다.");
        }
        catch (Exception ex)
        {
            LoadingOverlay.Visibility = Visibility.Collapsed;
            StatusText.Text = "작업 실패";
            System.Windows.MessageBox.Show(this, ex.Message, product.Name,
                MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void StartLoadingAnimation()
    {
        var animation = new DoubleAnimation(0, 360,
            TimeSpan.FromSeconds(1.1)) { RepeatBehavior = RepeatBehavior.Forever };
        LoadingRotation.BeginAnimation(System.Windows.Media.RotateTransform.AngleProperty,
                                       animation);
    }

    private static void ShowTrayBalloon(string title, string message)
    {
        App.Notify(title, message);
    }

    private async void Refresh_Click(object sender, RoutedEventArgs e) =>
        await RefreshProductsAsync(false);
    private async void InstallAll_Click(object sender, RoutedEventArgs e) =>
        await InstallOrUpdateAllAsync();
    private void Setting_Changed(object sender, RoutedEventArgs e)
    {
        if (!settingsLoaded) return;
        StatusText.Text = "저장되지 않은 설정";
    }
    private void SaveSettings_Click(object sender, RoutedEventArgs e)
    {
        settings.StartWithWindows = StartWithWindowsCheck.IsChecked == true;
        settings.BackgroundChecks = BackgroundChecksCheck.IsChecked == true;
        settings.Save();
        StatusText.Text = "설정 저장 완료";
        App.Notify("설정 저장 완료", "새 설정은 즉시 적용되며 다음 실행에도 유지됩니다.");
    }
    private void Minimize_Click(object sender, RoutedEventArgs e) =>
        WindowState = WindowState.Minimized;
    private void Close_Click(object sender, RoutedEventArgs e) => Hide();
    private void TitleBar_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (e.ClickCount == 2)
            WindowState = WindowState == WindowState.Maximized
                ? WindowState.Normal : WindowState.Maximized;
        else DragMove();
    }
    protected override void OnClosing(CancelEventArgs e)
    {
        if (!AllowClose)
        {
            e.Cancel = true;
            Hide();
        }
        base.OnClosing(e);
    }
}
