using Microsoft.Win32;

namespace HythonManager.Services;

public sealed class ManagerSettings
{
    private const string SettingsKey = @"Software\Kooyoseb\Hython Manager";
    private const string RunKey =
        @"Software\Microsoft\Windows\CurrentVersion\Run";

    public bool StartWithWindows { get; set; } = true;
    public bool BackgroundChecks { get; set; } = true;
    public int CheckIntervalHours { get; set; } = 6;

    public static ManagerSettings Load()
    {
        using RegistryKey? key = Registry.CurrentUser.OpenSubKey(SettingsKey);
        return new ManagerSettings
        {
            StartWithWindows = ReadBool(key, "StartWithWindows", true),
            BackgroundChecks = ReadBool(key, "BackgroundChecks", true),
            CheckIntervalHours = Math.Clamp(
                Convert.ToInt32(key?.GetValue("CheckIntervalHours", 6)), 1, 168)
        };
    }

    public void Save()
    {
        using (RegistryKey key = Registry.CurrentUser.CreateSubKey(SettingsKey))
        {
            key.SetValue("StartWithWindows", StartWithWindows ? 1 : 0,
                         RegistryValueKind.DWord);
            key.SetValue("BackgroundChecks", BackgroundChecks ? 1 : 0,
                         RegistryValueKind.DWord);
            key.SetValue("CheckIntervalHours", CheckIntervalHours,
                         RegistryValueKind.DWord);
        }
        using RegistryKey run = Registry.CurrentUser.CreateSubKey(RunKey);
        if (StartWithWindows)
            run.SetValue("Hython Manager", $"\"{Environment.ProcessPath}\" --tray",
                         RegistryValueKind.String);
        else
            run.DeleteValue("Hython Manager", false);
    }

    private static bool ReadBool(RegistryKey? key, string name, bool fallback) =>
        Convert.ToInt32(key?.GetValue(name, fallback ? 1 : 0)) != 0;
}
