using System.IO;
using System.Text.Json;

namespace HythonManager.Services;

public static class OperationHistory
{
    private static readonly SemaphoreSlim Gate = new(1, 1);
    public static string LogDirectory => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "Hython", "Manager", "Logs");
    public static string CurrentLog => Path.Combine(
        LogDirectory, $"작업-{DateTime.Now:yyyy-MM}.jsonl");

    public static async Task WriteAsync(string product, string action,
        string result, string message, Exception? exception = null)
    {
        Directory.CreateDirectory(LogDirectory);
        var entry = new
        {
            time = DateTimeOffset.Now,
            product, action, result, message,
            error = exception?.ToString()
        };
        string line = JsonSerializer.Serialize(entry,
            new JsonSerializerOptions { WriteIndented = false }) + Environment.NewLine;
        await Gate.WaitAsync();
        try { await File.AppendAllTextAsync(CurrentLog, line); }
        finally { Gate.Release(); }
    }
}
