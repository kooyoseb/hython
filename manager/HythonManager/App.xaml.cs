using System.Threading;
using System.Windows;
using System.Windows.Threading;
using HythonManager.Services;
using Forms = System.Windows.Forms;

namespace HythonManager;

public partial class App : System.Windows.Application
{
    public static void Notify(string title, string message)
    {
        if (Current is App app && app.tray is not null)
        {
            app.tray.BalloonTipTitle = title;
            app.tray.BalloonTipText = message;
            app.tray.ShowBalloonTip(4500);
        }
    }

    public static void UpdateTrayProgress(double progress, string text)
    {
        if (Current is not App app || app.tray is null) return;
        string tooltip = progress > 0 && progress < 100
            ? $"하이썬 매니저 · {progress:F0}% · {text}" : "하이썬 매니저";
        app.tray.Text = tooltip.Length > 63 ? tooltip[..63] : tooltip;
        if (app.trayProgressItem is not null)
            app.trayProgressItem.Text = progress > 0 && progress < 100
                ? $"전체 진행률 {progress:F0}% · {text}" : "진행 중인 작업 없음";
    }

    private Mutex? mutex;
    private Forms.NotifyIcon? tray;
    private Forms.ToolStripMenuItem? trayProgressItem;
    private MainWindow? window;
    private DispatcherTimer? updateTimer;
    private ManagerSettings settings = null!;

    protected override void OnStartup(StartupEventArgs e)
    {
        mutex = new Mutex(true, @"Global\Kooyoseb.Hython.Manager", out bool created);
        if (!created)
        {
            Shutdown();
            return;
        }
        base.OnStartup(e);
        settings = ManagerSettings.Load();
        settings.Save();
        window = new MainWindow(settings);
        MainWindow = window;
        CreateTray();
        ConfigureTimer();
        if (!e.Args.Contains("--tray", StringComparer.OrdinalIgnoreCase))
            window.Show();
    }

    private void CreateTray()
    {
        var menu = new Forms.ContextMenuStrip();
        trayProgressItem = new Forms.ToolStripMenuItem("진행 중인 작업 없음")
            { Enabled = false };
        menu.Items.Add(trayProgressItem);
        menu.Items.Add(new Forms.ToolStripSeparator());
        menu.Items.Add("하이썬 매니저 열기", null, (_, _) => ShowManager());
        menu.Items.Add("제품 업데이트 확인", null, async (_, _) =>
            await window!.RefreshProductsAsync(true));
        menu.Items.Add("모두 설치 및 업데이트", null, async (_, _) =>
        {
            ShowManager();
            await window!.InstallOrUpdateAllAsync();
        });
        menu.Items.Add(new Forms.ToolStripSeparator());
        menu.Items.Add("종료", null, (_, _) => ExitManager());
        tray = new Forms.NotifyIcon
        {
            Text = "하이썬 매니저",
            Icon = System.Drawing.Icon.ExtractAssociatedIcon(Environment.ProcessPath!),
            ContextMenuStrip = menu,
            Visible = true
        };
        tray.DoubleClick += (_, _) => ShowManager();
    }

    private void ConfigureTimer()
    {
        updateTimer = new DispatcherTimer
        {
            Interval = TimeSpan.FromHours(settings.CheckIntervalHours)
        };
        updateTimer.Tick += async (_, _) =>
        {
            if (settings.BackgroundChecks)
                await window!.RefreshProductsAsync(true, false);
        };
        if (settings.BackgroundChecks) updateTimer.Start();
    }

    private void ShowManager()
    {
        window!.Show();
        if (window.WindowState == WindowState.Minimized)
            window.WindowState = WindowState.Normal;
        window.Activate();
    }

    private void ExitManager()
    {
        tray!.Visible = false;
        tray.Dispose();
        window!.AllowClose = true;
        window.Close();
        Shutdown();
    }

    public static void ExitForUpgrade()
    {
        if (Current is not App app) return;
        app.tray!.Visible = false;
        app.tray.Dispose();
        app.window!.AllowClose = true;
        app.window.Close();
        app.Shutdown();
    }

    protected override void OnExit(ExitEventArgs e)
    {
        tray?.Dispose();
        updateTimer?.Stop();
        mutex?.Dispose();
        base.OnExit(e);
    }
}
