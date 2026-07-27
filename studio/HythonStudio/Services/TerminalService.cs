using System.Diagnostics;
using System.Text;

namespace HythonStudio.Services;

public sealed class TerminalService
{
    public string CurrentDirectory { get; private set; }

    public TerminalService(string? initialDirectory = null)
    {
        CurrentDirectory = Directory.Exists(initialDirectory)
            ? Path.GetFullPath(initialDirectory)
            : Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
    }

    public void SetDirectory(string directory)
    {
        if (Directory.Exists(directory))
            CurrentDirectory = Path.GetFullPath(directory);
    }

    public async Task<(int ExitCode, string Output)> ExecuteAsync(
        string command, CancellationToken cancellationToken)
    {
        command = command.Trim();
        if (string.IsNullOrEmpty(command))
            return (0, "");
        if (TryChangeDirectory(command, out string? message))
            return (message is null ? 0 : 1, message ?? "");

        string shell = FindShell();
        ProcessStartInfo start = new()
        {
            FileName = shell,
            WorkingDirectory = CurrentDirectory,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            StandardOutputEncoding = Encoding.UTF8,
            StandardErrorEncoding = Encoding.UTF8
        };
        start.ArgumentList.Add("-NoLogo");
        start.ArgumentList.Add("-NoProfile");
        start.ArgumentList.Add("-NonInteractive");
        start.ArgumentList.Add("-Command");
        start.ArgumentList.Add(
            "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false);" +
            "$OutputEncoding=[Console]::OutputEncoding;" + command);
        using Process process = new() { StartInfo = start };
        process.Start();
        Task<string> stdout = process.StandardOutput.ReadToEndAsync(cancellationToken);
        Task<string> stderr = process.StandardError.ReadToEndAsync(cancellationToken);
        try
        {
            await process.WaitForExitAsync(cancellationToken);
        }
        catch (OperationCanceledException)
        {
            try { if (!process.HasExited) process.Kill(true); } catch { }
            throw;
        }
        return (process.ExitCode, (await stdout) + (await stderr));
    }

    private bool TryChangeDirectory(string command, out string? message)
    {
        message = null;
        if (!command.Equals("cd", StringComparison.OrdinalIgnoreCase) &&
            !command.StartsWith("cd ", StringComparison.OrdinalIgnoreCase) &&
            !command.StartsWith("셋-로케이션 ", StringComparison.OrdinalIgnoreCase))
            return false;
        string target = command.Equals("cd", StringComparison.OrdinalIgnoreCase)
            ? Environment.GetFolderPath(Environment.SpecialFolder.UserProfile)
            : command[(command.IndexOf(' ') + 1)..].Trim().Trim('"');
        string resolved = Path.IsPathRooted(target)
            ? target : Path.GetFullPath(Path.Combine(CurrentDirectory, target));
        if (!Directory.Exists(resolved))
        {
            message = "폴더를 찾을 수 없습니다: " + resolved;
            return true;
        }
        CurrentDirectory = resolved;
        return true;
    }

    private static string FindShell()
    {
        string? path = Environment.GetEnvironmentVariable("PATH");
        foreach (string folder in (path ?? "").Split(
                     Path.PathSeparator, StringSplitOptions.RemoveEmptyEntries))
        {
            string candidate = Path.Combine(folder.Trim('"'), "pwsh.exe");
            if (File.Exists(candidate)) return candidate;
        }
        return "powershell.exe";
    }
}
