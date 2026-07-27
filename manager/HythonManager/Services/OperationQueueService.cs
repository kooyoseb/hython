using HythonManager.Models;
using System.Collections.ObjectModel;

namespace HythonManager.Services;

public sealed class OperationQueueService
{
    private readonly ProductCatalogService catalog;
    private readonly Queue<OperationItem> pending = new();
    private readonly object sync = new();
    private bool running;

    public ObservableCollection<OperationItem> Items { get; } = new();
    public event Action<double, string>? OverallProgressChanged;
    public event Action<OperationItem>? OperationFinished;

    public OperationQueueService(ProductCatalogService catalog) => this.catalog = catalog;

    public OperationItem Enqueue(ProductInfo product)
    {
        lock (sync)
        {
            OperationItem? existing = Items.FirstOrDefault(item =>
                item.Product.Id == product.Id &&
                item.State is OperationState.Waiting or OperationState.Downloading
                    or OperationState.Paused or OperationState.Installing);
            if (existing is not null) return existing;
            var item = new OperationItem { Id = Guid.NewGuid(), Product = product };
            Items.Add(item);
            pending.Enqueue(item);
            if (!running) _ = RunAsync();
            UpdateOverall();
            return item;
        }
    }

    private async Task RunAsync()
    {
        running = true;
        while (true)
        {
            OperationItem? item;
            lock (sync) item = pending.Count > 0 ? pending.Dequeue() : null;
            if (item is null) break;
            await ExecuteAsync(item);
            OperationFinished?.Invoke(item);
            UpdateOverall();
        }
        running = false;
        OverallProgressChanged?.Invoke(100, "모든 작업 완료");
    }

    private async Task ExecuteAsync(OperationItem item)
    {
        ProductInfo product = item.Product;
        try
        {
            await OperationHistory.WriteAsync(product.Name, "설치/업데이트",
                "시작", $"{product.InstalledVersion ?? new Version(0, 0)} → {product.LatestVersion}");
            int code;
            if (product.Id == "vscode")
            {
                item.State = OperationState.Installing;
                item.Detail = "code 명령으로 확장을 설치하고 있습니다.";
                item.Progress = 75;
                code = await ProductCatalogService.InstallAsync(product, null);
            }
            else
            {
                item.State = OperationState.Downloading;
                item.CanPause = true;
                item.Detail = "다운로드를 준비하고 있습니다.";
                string path = await catalog.DownloadVerifiedAsync(product,
                    new Progress<double>(value =>
                    {
                        item.Progress = value * 70;
                        item.Detail = $"다운로드 {value:P0}";
                        UpdateOverall();
                    }), item);
                item.CanPause = false;
                item.State = OperationState.Installing;
                item.Detail = "무창 설치를 진행하고 있습니다.";
                item.Progress = 78;
                if (product.Id == "manager")
                {
                    ProductCatalogService.StartManagerUpgrade(path);
                    item.Progress = 100;
                    item.State = OperationState.Completed;
                    App.ExitForUpgrade();
                    return;
                }
                code = await ProductCatalogService.InstallAsync(product, path);
            }
            if (code is 3010 or 1641)
            {
                item.Progress = 100;
                item.State = OperationState.RebootRequired;
                item.Detail = "설치 완료 · Windows 재부팅이 필요합니다.";
                await OperationHistory.WriteAsync(product.Name, "설치/업데이트",
                    "재부팅 필요", $"Windows Installer 코드 {code}");
            }
            else if (code == 0)
            {
                item.Progress = 100;
                item.State = OperationState.Completed;
                item.Detail = "정상적으로 완료되었습니다.";
                await OperationHistory.WriteAsync(product.Name, "설치/업데이트",
                    "완료", "정상 완료");
            }
            else throw new InvalidOperationException($"Windows Installer 오류 코드: {code}");
        }
        catch (Exception ex)
        {
            item.CanPause = false;
            item.State = OperationState.Repairing;
            item.Detail = "실패하여 이전 설치를 자동 복구하고 있습니다.";
            bool restored = product.InstalledVersion is not null &&
                            await ProductCatalogService.TryRepairAsync(product);
            item.State = OperationState.Failed;
            item.Detail = restored
                ? "작업 실패 · 이전 설치 자동 복구 완료"
                : "작업 실패 · 자동 복구 불가. 작업 기록을 확인하세요.";
            await OperationHistory.WriteAsync(product.Name, "설치/업데이트",
                restored ? "실패 후 복구" : "실패", item.Detail, ex);
        }
    }

    public void PauseOrResume(OperationItem item)
    {
        if (item.IsPaused) item.Resume(); else item.Pause();
        UpdateOverall();
    }

    private void UpdateOverall()
    {
        OperationItem[] active = Items.Where(item =>
            item.State is not OperationState.Completed and not OperationState.Failed
                and not OperationState.RebootRequired).ToArray();
        double value = Items.Count == 0 ? 0 : Items.Average(item => item.Progress);
        string text = active.Length == 0 ? "대기 중"
            : $"{active[0].ProductName} · {active[0].StateText} · 전체 {value:F0}%";
        OverallProgressChanged?.Invoke(value, text);
    }
}
