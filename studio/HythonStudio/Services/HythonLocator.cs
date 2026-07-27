using Microsoft.Win32;

namespace HythonStudio.Services;

public sealed record HythonEngine(string Executable, string Source);

public static class HythonLocator
{
    public static HythonEngine? Find()
    {
        string? installed = FindInstalledPath();
        if (IsHython(installed))
            return new HythonEngine(installed!, "Windows 설치본");

        string? path = FindOnPath("hython.exe");
        if (IsHython(path))
            return new HythonEngine(path!, "PATH");

        DirectoryInfo? current = new(AppContext.BaseDirectory);
        while (current is not null)
        {
            string candidate = Path.Combine(current.FullName, "release", "hython.exe");
            if (IsHython(candidate))
                return new HythonEngine(candidate, "저장소 독립 실행본");
            current = current.Parent;
        }
        return null;
    }

    private static string? FindInstalledPath()
    {
        using RegistryKey? key = Registry.LocalMachine.OpenSubKey(
            @"SOFTWARE\Kooyoseb\Hython");
        string? installFolder = Convert.ToString(key?.GetValue("InstallLocation"));
        if (!string.IsNullOrWhiteSpace(installFolder))
            return Path.Combine(installFolder, "hython.exe");

        string programFiles = Environment.GetFolderPath(
            Environment.SpecialFolder.ProgramFiles);
        return Path.Combine(programFiles, "Hython", "hython.exe");
    }

    private static string? FindOnPath(string name)
    {
        foreach (string folder in (Environment.GetEnvironmentVariable("PATH") ?? "")
                     .Split(Path.PathSeparator, StringSplitOptions.RemoveEmptyEntries))
        {
            try
            {
                string candidate = Path.Combine(folder.Trim('"'), name);
                if (File.Exists(candidate))
                    return candidate;
            }
            catch { }
        }
        return null;
    }

    private static bool IsHython(string? path) =>
        !string.IsNullOrWhiteSpace(path) && File.Exists(path);
}
