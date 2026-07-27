using System.Diagnostics;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.Win32;

namespace HythonStudio.Services;

public sealed record EngineEnvironment(
    bool PythonAvailable, string PythonVersion,
    bool PipHythonInstalled, string PipHythonVersion,
    bool WingetAvailable, bool WindowsHythonInstalled);

public enum EngineInstallSource { Pip, GitHub, Winget }

public static class EngineManagementService
{
    private const string Repository = "kooyoseb/hython";
    private const string WingetId = "Kooyoseb.Hython";

    public static async Task<EngineEnvironment> DetectAsync()
    {
        var python = await RunAsync("py", "--version");
        (int ExitCode, string Output) pip = python.ExitCode == 0
            ? await RunAsync("py", "-m pip show hython")
            : (ExitCode: -1, Output: "");
        var winget = await RunAsync("winget", "--version");
        HythonEngine? engine = HythonLocator.Find();
        string pipVersion = pip.Output.Split('\n')
            .FirstOrDefault(line => line.StartsWith(
                "Version:", StringComparison.OrdinalIgnoreCase))
            ?.Split(':', 2)[1].Trim() ?? "";
        return new EngineEnvironment(
            python.ExitCode == 0, python.Output.Trim(),
            pip.ExitCode == 0, pipVersion,
            winget.ExitCode == 0,
            engine?.Source == "Windows 설치본");
    }

    public static async Task<(int ExitCode, string Output)> InstallOrUpdateAsync(
        EngineInstallSource source, bool update, bool skipWingetPageCheck,
        IProgress<string>? progress = null)
    {
        return source switch
        {
            EngineInstallSource.Pip => await RunPipAsync(progress),
            EngineInstallSource.Winget => await RunWingetAsync(
                update, skipWingetPageCheck, progress),
            _ => await RunGitHubAsync(progress),
        };
    }

    public static async Task<(int ExitCode, string Output)> UninstallAsync(
        EngineInstallSource source, IProgress<string>? progress = null)
    {
        switch (source)
        {
            case EngineInstallSource.Pip:
                progress?.Report("PyPI Hython 패키지를 제거하는 중…");
                return await RunAsync("py", "-m pip uninstall -y hython");
            case EngineInstallSource.Winget:
                progress?.Report("Winget으로 Hython을 제거하는 중…");
                return await RunAsync(
                    "winget", $"uninstall --id {WingetId} -e --silent");
            default:
                progress?.Report("Windows Hython MSI 설치 정보를 찾는 중…");
                return await UninstallWindowsMsiAsync(progress);
        }
    }

    private static async Task<(int ExitCode, string Output)> UninstallWindowsMsiAsync(
        IProgress<string>? progress)
    {
        string? uninstall = FindUninstallCommand();
        if (string.IsNullOrWhiteSpace(uninstall))
            return (-1, "설치된 Hython MSI 정보를 찾을 수 없습니다.");
        string arguments = uninstall;
        int executableEnd = uninstall.IndexOf(".exe", StringComparison.OrdinalIgnoreCase);
        if (executableEnd >= 0)
            arguments = uninstall[(executableEnd + 4)..].Trim();
        arguments = arguments.Replace("/I", "/X", StringComparison.OrdinalIgnoreCase);
        if (!arguments.Contains("/X", StringComparison.OrdinalIgnoreCase))
            arguments = "/X " + arguments;
        progress?.Report("Windows 제거 프로그램을 시작합니다…");
        ProcessStartInfo start = new()
        {
            FileName = "msiexec.exe",
            Arguments = arguments,
            UseShellExecute = true,
            Verb = "runas"
        };
        using Process process = Process.Start(start)!;
        await process.WaitForExitAsync();
        return (process.ExitCode, process.ExitCode == 0
            ? "Windows Hython 제거가 완료되었습니다."
            : $"Windows 제거 종료 코드: {process.ExitCode}");
    }

    private static string? FindUninstallCommand()
    {
        (RegistryHive Hive, RegistryView View)[] locations =
        [
            (RegistryHive.LocalMachine, RegistryView.Registry64),
            (RegistryHive.LocalMachine, RegistryView.Registry32),
            (RegistryHive.CurrentUser, RegistryView.Registry64),
            (RegistryHive.CurrentUser, RegistryView.Registry32),
        ];
        foreach (var location in locations)
        {
            using RegistryKey root = RegistryKey.OpenBaseKey(
                location.Hive, location.View);
            using RegistryKey? uninstall = root.OpenSubKey(
                @"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall");
            if (uninstall is null) continue;
            foreach (string name in uninstall.GetSubKeyNames())
            {
                using RegistryKey? item = uninstall.OpenSubKey(name);
                string display = Convert.ToString(item?.GetValue("DisplayName")) ?? "";
                if (!display.Equals("Hython", StringComparison.OrdinalIgnoreCase))
                    continue;
                return Convert.ToString(item?.GetValue("UninstallString"));
            }
        }
        return null;
    }

    private static async Task<(int, string)> RunPipAsync(IProgress<string>? progress)
    {
        progress?.Report("PyPI에서 Hython을 설치·업데이트하는 중…");
        return await RunAsync("py", "-m pip install --upgrade hython");
    }

    private static async Task<(int, string)> RunWingetAsync(
        bool update, bool skipCheck, IProgress<string>? progress)
    {
        if (!skipCheck)
        {
            progress?.Report("winstall.app에서 Winget 패키지 등록을 확인하는 중…");
            using HttpClient client = Client();
            using HttpResponseMessage response = await client.GetAsync(
                $"https://winstall.app/apps/{WingetId}");
            if (!response.IsSuccessStatusCode)
                return (-1, "Winget 패키지 페이지를 확인할 수 없습니다. " +
                    "설정에서 페이지 확인 건너뛰기를 선택할 수 있습니다.");
        }
        progress?.Report(update ? "Winget으로 Hython을 업데이트하는 중…"
                                : "Winget으로 Hython을 설치하는 중…");
        string verb = update ? "upgrade" : "install";
        return await RunAsync("winget",
            $"{verb} --id {WingetId} -e --accept-package-agreements " +
            "--accept-source-agreements");
    }

    private static async Task<(int, string)> RunGitHubAsync(
        IProgress<string>? progress)
    {
        progress?.Report("GitHub 최신 릴리스를 확인하는 중…");
        using HttpClient client = Client();
        string json = await client.GetStringAsync(
            $"https://api.github.com/repos/{Repository}/releases/latest");
        using JsonDocument document = JsonDocument.Parse(json);
        JsonElement asset = document.RootElement.GetProperty("assets")
            .EnumerateArray()
            .FirstOrDefault(item =>
                item.GetProperty("name").GetString()?.EndsWith(
                    ".msi", StringComparison.OrdinalIgnoreCase) == true);
        if (asset.ValueKind == JsonValueKind.Undefined)
            return (-1, "최신 GitHub 릴리스에서 MSI 파일을 찾을 수 없습니다.");
        string name = asset.GetProperty("name").GetString()!;
        string url = asset.GetProperty("browser_download_url").GetString()!;
        string path = Path.Combine(Path.GetTempPath(), name);
        progress?.Report($"{name} 다운로드 중…");
        byte[] payload = await client.GetByteArrayAsync(url);
        string? digest = asset.TryGetProperty("digest", out JsonElement value)
            ? value.GetString() : null;
        if (digest?.StartsWith("sha256:", StringComparison.OrdinalIgnoreCase) == true)
        {
            string actual = Convert.ToHexString(SHA256.HashData(payload));
            if (!actual.Equals(digest[7..], StringComparison.OrdinalIgnoreCase))
                return (-1, "다운로드한 MSI의 SHA-256 검증이 실패했습니다.");
        }
        await File.WriteAllBytesAsync(path, payload);
        progress?.Report("Windows 설치 프로그램을 시작합니다…");
        ProcessStartInfo start = new()
        {
            FileName = "msiexec.exe",
            Arguments = "/i " + HythonProcessService.Quote(path),
            UseShellExecute = true,
            Verb = "runas"
        };
        using Process process = Process.Start(start)!;
        await process.WaitForExitAsync();
        return (process.ExitCode,
            process.ExitCode == 0 ? "GitHub MSI 설치가 완료되었습니다."
                                  : $"MSI 설치 종료 코드: {process.ExitCode}");
    }

    private static HttpClient Client()
    {
        HttpClient client = new() { Timeout = TimeSpan.FromMinutes(5) };
        client.DefaultRequestHeaders.UserAgent.ParseAdd("HythonStudio/0.2");
        return client;
    }

    private static async Task<(int ExitCode, string Output)> RunAsync(
        string file, string arguments)
    {
        try
        {
            ProcessStartInfo start = new()
            {
                FileName = file, Arguments = arguments,
                UseShellExecute = false, CreateNoWindow = true,
                RedirectStandardOutput = true, RedirectStandardError = true,
                StandardOutputEncoding = Encoding.UTF8,
                StandardErrorEncoding = Encoding.UTF8
            };
            using Process process = Process.Start(start)!;
            Task<string> output = process.StandardOutput.ReadToEndAsync();
            Task<string> error = process.StandardError.ReadToEndAsync();
            await process.WaitForExitAsync();
            return (process.ExitCode, (await output) + (await error));
        }
        catch (Exception ex) { return (-1, ex.Message); }
    }
}
