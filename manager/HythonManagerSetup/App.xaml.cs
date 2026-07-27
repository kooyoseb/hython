using System.Windows;
using Microsoft.Win32;
using System.Diagnostics;
using System.IO;
using System.Reflection;

namespace HythonManagerSetup;

public partial class App : Application
{
    protected override async void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        if (e.Args.Contains("--install-silent", StringComparer.OrdinalIgnoreCase))
        {
            Shutdown(await InstallEmbeddedAsync());
            return;
        }
        if (e.Args.Contains("--uninstall-silent", StringComparer.OrdinalIgnoreCase))
        {
            Shutdown(await UninstallAsync());
            return;
        }
        MainWindow window = new();
        MainWindow = window;
        window.Show();
    }

    private static async Task<int> InstallEmbeddedAsync()
    {
        string temporary = Path.Combine(Path.GetTempPath(),
            "HythonManagerSetupTest-" + Guid.NewGuid().ToString("N") + ".msi");
        try
        {
            using Stream source = Assembly.GetExecutingAssembly()
                .GetManifestResourceStream("HythonManagerInstaller.msi")
                ?? throw new InvalidOperationException("Embedded Manager MSI is missing.");
            await using (FileStream target = File.Create(temporary))
                await source.CopyToAsync(target);
            return await RunMsiAsync($"/i \"{temporary}\" /qn /norestart");
        }
        catch { return 1; }
        finally { try { File.Delete(temporary); } catch { } }
    }

    private static async Task<int> UninstallAsync()
    {
        string? code = FindProductCode();
        return code is null ? 0 : await RunMsiAsync($"/x {code} /qn /norestart");
    }

    private static string? FindProductCode()
    {
        foreach (RegistryHive hive in new[] { RegistryHive.CurrentUser, RegistryHive.LocalMachine })
        foreach (RegistryView view in new[] { RegistryView.Registry64, RegistryView.Registry32 })
        using (RegistryKey baseKey = RegistryKey.OpenBaseKey(hive, view))
        using (RegistryKey? root = baseKey.OpenSubKey(
            @"Software\Microsoft\Windows\CurrentVersion\Uninstall"))
        {
            if (root is null) continue;
            foreach (string name in root.GetSubKeyNames())
            using (RegistryKey? child = root.OpenSubKey(name))
                if (Convert.ToString(child?.GetValue("DisplayName")) == "Hython Manager")
                    return name;
        }
        return null;
    }

    private static async Task<int> RunMsiAsync(string arguments)
    {
        using Process process = Process.Start(new ProcessStartInfo(
            "msiexec.exe", arguments)
        {
            UseShellExecute = false, CreateNoWindow = true
        }) ?? throw new InvalidOperationException("Windows Installer could not start.");
        await process.WaitForExitAsync();
        return process.ExitCode;
    }
}
