using System.Diagnostics;
using System.Text;

namespace HythonStudio.Services;

public static class HythonProcessService
{
    public static async Task<(int ExitCode, string Output)> RunAsync(
        HythonEngine engine, string arguments, string? workingDirectory = null,
        string? standardInput = null)
    {
        ProcessStartInfo start = new()
        {
            FileName = engine.Executable,
            Arguments = arguments,
            WorkingDirectory = workingDirectory ?? Environment.CurrentDirectory,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            RedirectStandardInput = standardInput is not null,
            CreateNoWindow = true,
            StandardOutputEncoding = Encoding.UTF8,
            StandardErrorEncoding = Encoding.UTF8
        };
        if (standardInput is not null)
            start.StandardInputEncoding = Encoding.UTF8;
        using Process process = new() { StartInfo = start };
        process.Start();
        if (standardInput is not null)
        {
            await process.StandardInput.WriteAsync(standardInput);
            process.StandardInput.Close();
        }
        Task<string> stdout = process.StandardOutput.ReadToEndAsync();
        Task<string> stderr = process.StandardError.ReadToEndAsync();
        await process.WaitForExitAsync();
        return (process.ExitCode, (await stdout) + (await stderr));
    }

    public static string Quote(string value) => "\"" + value.Replace("\"", "\\\"") + "\"";
}
