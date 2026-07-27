using HythonManager.Models;
using Microsoft.Win32;
using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace HythonManager.Services;

public sealed class ProductCatalogService
{
    private const string Api =
        "https://api.github.com/repos/kooyoseb/hython/releases?per_page=100";
    private readonly HttpClient client = new();

    public ProductCatalogService()
    {
        client.DefaultRequestHeaders.UserAgent.ParseAdd("Hython-Manager/1.1.1");
        client.DefaultRequestHeaders.Accept.ParseAdd("application/vnd.github+json");
    }

    public async Task<IReadOnlyList<ProductInfo>> LoadAsync()
    {
        string payload = await GetStringWithRetryAsync(Api);
        using JsonDocument json = JsonDocument.Parse(payload);
        var products = new Dictionary<string, ProductInfo>(StringComparer.OrdinalIgnoreCase);
        foreach (JsonElement release in json.RootElement.EnumerateArray())
        {
            if (release.GetProperty("draft").GetBoolean() ||
                release.GetProperty("prerelease").GetBoolean()) continue;
            string tag = release.GetProperty("tag_name").GetString() ?? "";
            ProductInfo? product = ParseRelease(tag, release);
            if (product is null) continue;
            if (!products.TryGetValue(product.Id, out ProductInfo? existing) ||
                product.LatestVersion > existing.LatestVersion)
                products[product.Id] = product;
        }
        await DetectInstalledAsync(products.Values);
        return products.Values
            .OrderBy(product => ProductOrder(product.Id))
            .ThenBy(product => product.Name)
            .ToArray();
    }

    private static ProductInfo? ParseRelease(string tag, JsonElement release)
    {
        string id;
        string name;
        string description;
        string pattern;
        Match versionMatch;
        if ((versionMatch = Regex.Match(tag, @"^v(?<v>\d+\.\d+\.\d+)$",
                                         RegexOptions.IgnoreCase)).Success)
        {
            id = "hython";
            name = "Hython";
            description = "한글 프로그래밍 언어 본체, HBC VM과 EXE 빌드 도구";
            pattern = @"^Hython-\d+\.\d+\.\d+-x64\.msi$";
        }
        else if ((versionMatch = Regex.Match(tag,
                     @"^studio-v(?<v>\d+\.\d+\.\d+)$",
                     RegexOptions.IgnoreCase)).Success)
        {
            id = "studio";
            name = "Hython Studio";
            description = "실행, 디버깅, HBC 컴파일과 프로젝트 관리를 위한 통합 개발 환경";
            pattern = @"^HythonStudio-\d+\.\d+\.\d+-x64\.msi$";
        }
        else if ((versionMatch = Regex.Match(tag,
                     @"^hython-development-v(?<v>\d+\.\d+\.\d+)$",
                     RegexOptions.IgnoreCase)).Success)
        {
            id = "vscode";
            name = "Hython Development";
            description = "VS Code용 문법 강조, 자동완성, 진단, 실행 및 빌드 확장";
            pattern = @"^hython-development-\d+\.\d+\.\d+\.vsix$";
        }
        else if ((versionMatch = Regex.Match(tag,
                     @"^manager-v(?<v>\d+\.\d+\.\d+)$",
                     RegexOptions.IgnoreCase)).Success)
        {
            id = "manager";
            name = "Hython Manager";
            description = "Hython 제품 설치, 업데이트와 상태를 통합 관리하는 트레이 앱";
            pattern = @"^HythonManager-\d+\.\d+\.\d+-x64\.msi$";
        }
        else
        {
            // 새 규격의 태그도 제품으로 인식: product-id-v1.2.3
            versionMatch = Regex.Match(tag,
                @"^(?<id>[a-z0-9][a-z0-9-]*)-v(?<v>\d+\.\d+\.\d+)$",
                RegexOptions.IgnoreCase);
            if (!versionMatch.Success) return null;
            id = versionMatch.Groups["id"].Value.ToLowerInvariant();
            name = Humanize(id);
            description = "GitHub 릴리스 태그에서 자동 발견된 Hython 제품";
            pattern = @"\.(msi|exe|vsix)$";
        }
        if (!Version.TryParse(versionMatch.Groups["v"].Value, out Version? version))
            return null;
        JsonElement? chosen = null;
        var assets = new List<JsonElement>();
        foreach (JsonElement asset in release.GetProperty("assets").EnumerateArray())
        {
            assets.Add(asset);
            string assetName = asset.GetProperty("name").GetString() ?? "";
            if (Regex.IsMatch(assetName, pattern, RegexOptions.IgnoreCase) && chosen is null)
                chosen = asset;
        }
        if (chosen is null) return null;
        JsonElement selected = chosen.Value;
        string selectedName = selected.GetProperty("name").GetString() ?? "";
        string? checksum = assets.FirstOrDefault(asset =>
                string.Equals(asset.GetProperty("name").GetString(),
                    selectedName + ".sha256", StringComparison.OrdinalIgnoreCase))
            .GetPropertyOrNull("browser_download_url");
        return new ProductInfo
        {
            Id = id, Name = name, Description = description, Tag = tag,
            LatestVersion = version,
            AssetName = selectedName,
            DownloadUrl = selected.GetProperty("browser_download_url").GetString(),
            AssetDigest = selected.TryGetProperty("digest", out JsonElement digest)
                ? digest.GetString() : null,
            ChecksumUrl = checksum
        };
    }

    private static async Task DetectInstalledAsync(IEnumerable<ProductInfo> products)
    {
        var registrations = ReadUninstallRegistry();
        foreach (ProductInfo product in products)
        {
            string expected = product.Id switch
            {
                "hython" => "Hython",
                "studio" => "Hython Studio",
                _ => product.Name
            };
            var match = registrations
                .Where(item => item.Name.Equals(expected, StringComparison.OrdinalIgnoreCase))
                .OrderByDescending(item => item.Version)
                .FirstOrDefault();
            if (match is not null)
            {
                product.InstalledVersion = match.Version;
                product.UninstallCommand = match.Uninstall;
                product.ProductCode = match.ProductCode;
                product.InstalledPath = match.InstalledPath;
                product.IsHealthy = CheckHealth(product);
            }
        }
        ProductInfo? vscode = products.FirstOrDefault(p => p.Id == "vscode");
        if (vscode is not null)
            vscode.InstalledVersion = await DetectVsCodeExtensionVersionAsync();
    }

    private static List<Registration> ReadUninstallRegistry()
    {
        var result = new List<Registration>();
        foreach (RegistryHive hive in new[] { RegistryHive.LocalMachine, RegistryHive.CurrentUser })
        foreach (RegistryView view in new[] { RegistryView.Registry64, RegistryView.Registry32 })
        using (RegistryKey baseKey = RegistryKey.OpenBaseKey(hive, view))
        using (RegistryKey? root = baseKey.OpenSubKey(
            @"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"))
        {
            if (root is null) continue;
            foreach (string childName in root.GetSubKeyNames())
            using (RegistryKey? child = root.OpenSubKey(childName))
            {
                string name = Convert.ToString(child?.GetValue("DisplayName")) ?? "";
                if (!name.Contains("Hython", StringComparison.OrdinalIgnoreCase)) continue;
                if (!Version.TryParse(Convert.ToString(child?.GetValue("DisplayVersion")),
                                      out Version? version)) continue;
                string? displayIcon = Convert.ToString(child?.GetValue("DisplayIcon"));
                string? installLocation = Convert.ToString(child?.GetValue("InstallLocation"));
                string? installedPath = !string.IsNullOrWhiteSpace(displayIcon)
                    ? displayIcon.Split(',')[0].Trim().Trim('"')
                    : installLocation;
                result.Add(new Registration(name, version,
                    Convert.ToString(child?.GetValue("UninstallString")),
                    childName, installedPath));
            }
        }
        return result;
    }

    public async Task<string> DownloadVerifiedAsync(
        ProductInfo product, IProgress<double>? progress = null,
        OperationItem? operation = null)
    {
        string directory = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "Hython", "Manager", "Downloads", product.Tag);
        Directory.CreateDirectory(directory);
        string path = Path.Combine(directory, product.AssetName!);
        string partial = path + ".part";
        if (File.Exists(path) && await VerifyAsync(product, path))
        {
            progress?.Report(1);
            return path;
        }
        if (File.Exists(path)) File.Delete(path);
        Exception? lastError = null;
        for (int attempt = 1; attempt <= 4; attempt++)
        {
            try
            {
                long existing = File.Exists(partial) ? new FileInfo(partial).Length : 0;
                using var request = new HttpRequestMessage(HttpMethod.Get, product.DownloadUrl);
                if (existing > 0) request.Headers.Range = new RangeHeaderValue(existing, null);
                using HttpResponseMessage response = await client.SendAsync(request,
                    HttpCompletionOption.ResponseHeadersRead,
                    operation?.Cancellation.Token ?? CancellationToken.None);
                if (existing > 0 && response.StatusCode == System.Net.HttpStatusCode.OK)
                {
                    File.Delete(partial);
                    existing = 0;
                }
                response.EnsureSuccessStatusCode();
                long total = existing + (response.Content.Headers.ContentLength ?? 0);
                await using Stream input = await response.Content.ReadAsStreamAsync(
                    operation?.Cancellation.Token ?? CancellationToken.None);
                await using FileStream output = new(partial, FileMode.Append,
                    FileAccess.Write, FileShare.Read);
                byte[] buffer = new byte[1024 * 128];
                long received = existing;
                int read;
                while ((read = await input.ReadAsync(buffer,
                           operation?.Cancellation.Token ?? CancellationToken.None)) > 0)
                {
                    operation?.PauseGate.Wait(operation.Cancellation.Token);
                    await output.WriteAsync(buffer.AsMemory(0, read),
                        operation?.Cancellation.Token ?? CancellationToken.None);
                    received += read;
                    if (total > 0) progress?.Report((double)received / total);
                }
                await output.FlushAsync();
                await output.DisposeAsync();
                await input.DisposeAsync();
                File.Move(partial, path, true);
                if (!await VerifyAsync(product, path))
                    throw new InvalidDataException(
                        "다운로드 파일의 SHA-256 검증에 실패했습니다.");
                return path;
            }
            catch (Exception ex) when (attempt < 4 &&
                                       ex is HttpRequestException or IOException
                                           or TaskCanceledException)
            {
                lastError = ex;
                if (operation is not null)
                    operation.Detail = $"네트워크 오류 · {attempt}/4회 재시도 대기 중";
                await Task.Delay(TimeSpan.FromSeconds(Math.Pow(2, attempt)));
            }
        }
        throw new IOException("다운로드를 4회 재시도했지만 완료하지 못했습니다.", lastError);
    }

    private async Task<bool> VerifyAsync(ProductInfo product, string path)
    {
        string? expected = product.AssetDigest?.StartsWith("sha256:") == true
            ? product.AssetDigest[7..] : null;
        if (expected is null && product.ChecksumUrl is not null)
            expected = (await client.GetStringAsync(product.ChecksumUrl))
                .Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries)[0];
        if (expected is not null)
        {
            string actual;
            await using (FileStream verification = File.OpenRead(path))
                actual = Convert.ToHexString(await SHA256.HashDataAsync(verification));
            if (!actual.Equals(expected, StringComparison.OrdinalIgnoreCase))
                return false;
        }
        return true;
    }

    public static async Task<int> InstallAsync(ProductInfo product, string? path)
    {
        if (product.Id == "vscode")
            return await RunCodeAsync(
                "--install-extension kooyoseb.hython-development --force");
        if (string.IsNullOrWhiteSpace(path))
            throw new InvalidOperationException("설치 파일 경로가 없습니다.");
        ProcessStartInfo start;
        if (Path.GetExtension(path).Equals(".msi", StringComparison.OrdinalIgnoreCase))
            start = new("msiexec.exe", $"/i \"{path}\" /qn /norestart")
                { UseShellExecute = true, Verb = "runas" };
        else
            start = new(path) { UseShellExecute = true, Verb = "runas" };
        using Process process = Process.Start(start)
            ?? throw new InvalidOperationException("설치 프로그램을 시작할 수 없습니다.");
        await process.WaitForExitAsync();
        return process.ExitCode;
    }

    public static async Task<int> UninstallAsync(ProductInfo product)
    {
        if (product.Id == "vscode")
            return await RunCodeAsync(
                "--uninstall-extension kooyoseb.hython-development");
        if (string.IsNullOrWhiteSpace(product.UninstallCommand))
            throw new InvalidOperationException("등록된 제거 명령을 찾을 수 없습니다.");
        string command = product.UninstallCommand;
        Match msi = Regex.Match(command, @"\{[0-9A-F-]{36}\}", RegexOptions.IgnoreCase);
        ProcessStartInfo start = msi.Success
            ? new("msiexec.exe", $"/x {msi.Value} /qn /norestart")
            : new("cmd.exe", "/d /c " + command);
        start.UseShellExecute = true;
        start.Verb = "runas";
        using Process process = Process.Start(start)
            ?? throw new InvalidOperationException("제거 프로그램을 시작할 수 없습니다.");
        await process.WaitForExitAsync();
        return process.ExitCode;
    }

    public static void StartManagerUpgrade(string msiPath)
    {
        if (!File.Exists(msiPath))
            throw new FileNotFoundException("Manager 업데이트 MSI를 찾을 수 없습니다.", msiPath);
        string command =
            $"timeout /t 2 /nobreak >nul & msiexec.exe /i \"{msiPath}\" /qn /norestart";
        var start = new ProcessStartInfo("cmd.exe")
        {
            UseShellExecute = false,
            CreateNoWindow = true
        };
        start.ArgumentList.Add("/d");
        start.ArgumentList.Add("/s");
        start.ArgumentList.Add("/c");
        start.ArgumentList.Add(command);
        Process.Start(start);
    }

    public static async Task<bool> TryRepairAsync(ProductInfo product)
    {
        if (string.IsNullOrWhiteSpace(product.ProductCode)) return false;
        var start = new ProcessStartInfo("msiexec.exe",
            $"/fa {product.ProductCode} /qn /norestart")
        {
            UseShellExecute = true,
            Verb = "runas"
        };
        try
        {
            using Process process = Process.Start(start)!;
            await process.WaitForExitAsync();
            return process.ExitCode is 0 or 3010 or 1641;
        }
        catch { return false; }
    }

    private async Task<string> GetStringWithRetryAsync(string url)
    {
        Exception? last = null;
        for (int attempt = 1; attempt <= 4; attempt++)
        {
            try
            {
                using HttpResponseMessage response = await client.GetAsync(url);
                if ((int)response.StatusCode == 403 &&
                    response.Headers.TryGetValues("X-RateLimit-Remaining", out var values) &&
                    values.FirstOrDefault() == "0")
                    throw new HttpRequestException(
                        "GitHub API 요청 한도에 도달했습니다. 잠시 뒤 자동으로 다시 시도합니다.");
                response.EnsureSuccessStatusCode();
                return await response.Content.ReadAsStringAsync();
            }
            catch (HttpRequestException ex) when (attempt < 4)
            {
                last = ex;
                await Task.Delay(TimeSpan.FromSeconds(Math.Pow(2, attempt)));
            }
        }
        throw new HttpRequestException(
            "GitHub에 연결할 수 없습니다. 네트워크를 확인한 뒤 다시 시도하세요.", last);
    }

    private static bool CheckHealth(ProductInfo product)
    {
        if (!string.IsNullOrWhiteSpace(product.InstalledPath) &&
            Path.HasExtension(product.InstalledPath))
            return File.Exists(product.InstalledPath);
        string? known = product.Id switch
        {
            "hython" => Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
                "Hython", "hython.exe"),
            "studio" => Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
                "Hython Studio", "HythonStudio.exe"),
            "manager" => Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "Hython Manager", "HythonManager.exe"),
            _ => null
        };
        return known is null || File.Exists(known);
    }

    private static int ProductOrder(string id) => id switch
        { "hython" => 0, "studio" => 1, "vscode" => 2, "manager" => 3, _ => 10 };
    private static string Humanize(string id) =>
        string.Join(" ", id.Split('-').Select(word =>
            char.ToUpperInvariant(word[0]) + word[1..]));

    private static async Task<Version?> DetectVsCodeExtensionVersionAsync()
    {
        ProcessResult result;
        try { result = await RunCodeCaptureAsync("--list-extensions --show-versions"); }
        catch { return null; }
        if (result.ExitCode != 0) return null;
        Version? best = null;
        foreach (string line in result.Output.Split(
                     new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries))
        {
            Match match = Regex.Match(line.Trim(),
                @"^kooyoseb\.hython-development@(?<v>\d+\.\d+\.\d+)$",
                RegexOptions.IgnoreCase);
            if (match.Success &&
                Version.TryParse(match.Groups["v"].Value, out Version? version) &&
                (best is null || version > best))
                best = version;
        }
        return best;
    }

    private static async Task<int> RunCodeAsync(string arguments) =>
        (await RunCodeCaptureAsync(arguments)).ExitCode;

    private static async Task<ProcessResult> RunCodeCaptureAsync(string arguments)
    {
        string command = FindCodeCommand();
        bool isCommandScript = command.EndsWith(".cmd", StringComparison.OrdinalIgnoreCase);
        var start = new ProcessStartInfo
        {
            FileName = isCommandScript ? "cmd.exe" : command,
            Arguments = isCommandScript
                ? $"/d /s /c \"\"{command}\" {arguments}\"" : arguments,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true
        };
        using Process process = Process.Start(start)
            ?? throw new InvalidOperationException("VS Code 명령을 시작할 수 없습니다.");
        string output = await process.StandardOutput.ReadToEndAsync();
        string error = await process.StandardError.ReadToEndAsync();
        await process.WaitForExitAsync();
        if (process.ExitCode != 0 && !string.IsNullOrWhiteSpace(error))
            throw new InvalidOperationException("VS Code 명령 실패: " + error.Trim());
        return new ProcessResult(process.ExitCode, output);
    }

    private static string FindCodeCommand()
    {
        string local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        string programFiles = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);
        string[] candidates =
        {
            Path.Combine(local, "Programs", "Microsoft VS Code", "bin", "code.cmd"),
            Path.Combine(programFiles, "Microsoft VS Code", "bin", "code.cmd")
        };
        foreach (string candidate in candidates)
            if (File.Exists(candidate)) return candidate;
        try
        {
            using Process probe = Process.Start(new ProcessStartInfo(
                "where.exe", "code")
            {
                UseShellExecute = false, RedirectStandardOutput = true,
                RedirectStandardError = true, CreateNoWindow = true
            })!;
            string output = probe.StandardOutput.ReadToEnd();
            probe.WaitForExit();
            string? discovered = output.Split(
                    new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries)
                .FirstOrDefault(path =>
                    path.EndsWith(".cmd", StringComparison.OrdinalIgnoreCase) ||
                    path.EndsWith(".exe", StringComparison.OrdinalIgnoreCase));
            if (probe.ExitCode == 0 && discovered is not null)
                return discovered.Trim();
        }
        catch { }
        throw new FileNotFoundException(
            "VS Code의 code 명령을 찾을 수 없습니다. VS Code를 다시 설치하거나 PATH에 추가하세요.");
    }

    private sealed record ProcessResult(int ExitCode, string Output);
    private sealed record Registration(string Name, Version Version, string? Uninstall,
        string ProductCode, string? InstalledPath);
}

internal static class JsonElementExtensions
{
    public static string? GetPropertyOrNull(this JsonElement element, string name) =>
        element.ValueKind == JsonValueKind.Object &&
        element.TryGetProperty(name, out JsonElement value) ? value.GetString() : null;
}
