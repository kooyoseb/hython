using System.Diagnostics;
using System.Text;
using System.Text.Json;
using HythonStudio.Models;

namespace HythonStudio.Services;

public sealed class DebugSession : IAsyncDisposable
{
    private readonly Process process;
    private readonly SemaphoreSlim writeLock = new(1, 1);
    private readonly Task readerTask;

    public event Action<DebugEvent>? EventReceived;
    public bool IsRunning => !process.HasExited;

    public DebugSession(
        HythonEngine engine, string path, IEnumerable<int> breakpoints)
    {
        string arguments = "ide debug " + HythonProcessService.Quote(path) +
            string.Concat(breakpoints.Order().Select(
                line => " --breakpoint " + line));
        ProcessStartInfo start = new()
        {
            FileName = engine.Executable,
            Arguments = arguments,
            WorkingDirectory = Path.GetDirectoryName(path) ?? Environment.CurrentDirectory,
            UseShellExecute = false,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true,
            StandardInputEncoding = Encoding.UTF8,
            StandardOutputEncoding = Encoding.UTF8,
            StandardErrorEncoding = Encoding.UTF8
        };
        process = new Process { StartInfo = start, EnableRaisingEvents = true };
        process.Start();
        readerTask = ReadEventsAsync();
    }

    public Task ContinueAsync() => SendAsync("continue");
    public Task StepAsync() => SendAsync("step");
    public Task StopAsync() => SendAsync("stop");

    public async Task SetBreakpointsAsync(IEnumerable<int> lines)
    {
        await SendMessageAsync(new
        {
            command = "setBreakpoints",
            lines = lines.Order().ToArray()
        });
    }

    private Task SendAsync(string command) =>
        SendMessageAsync(new { command });

    private async Task SendMessageAsync(object message)
    {
        if (process.HasExited) return;
        string json = JsonSerializer.Serialize(message);
        await writeLock.WaitAsync();
        try
        {
            await process.StandardInput.WriteLineAsync(json);
            await process.StandardInput.FlushAsync();
        }
        finally { writeLock.Release(); }
    }

    private async Task ReadEventsAsync()
    {
        string? line;
        while ((line = await process.StandardOutput.ReadLineAsync()) is not null)
        {
            try
            {
                using JsonDocument document = JsonDocument.Parse(line);
                JsonElement root = document.RootElement;
                string name = Text(root, "event");
                List<DebugVariable> variables = [];
                if (root.TryGetProperty("variables", out JsonElement values))
                    foreach (JsonProperty item in values.EnumerateObject())
                        variables.Add(new DebugVariable(
                            item.Name, Text(item.Value, "type"),
                            Text(item.Value, "value")));
                EventReceived?.Invoke(new DebugEvent(
                    name, Number(root, "line"), Text(root, "function"),
                    Text(root, "message"), Text(root, "text"),
                    Number(root, "exitCode"), variables));
            }
            catch (JsonException)
            {
                EventReceived?.Invoke(new DebugEvent(
                    "output", 0, "", "", line + Environment.NewLine, 0, []));
            }
        }
        string error = await process.StandardError.ReadToEndAsync();
        if (!string.IsNullOrWhiteSpace(error))
            EventReceived?.Invoke(new DebugEvent(
                "output", 0, "", "", error, process.ExitCode, []));
    }

    private static string Text(JsonElement root, string name) =>
        root.TryGetProperty(name, out JsonElement value) &&
        value.ValueKind == JsonValueKind.String ? value.GetString() ?? "" : "";

    private static int Number(JsonElement root, string name) =>
        root.TryGetProperty(name, out JsonElement value) &&
        value.TryGetInt32(out int number) ? number : 0;

    public async ValueTask DisposeAsync()
    {
        if (!process.HasExited)
        {
            try { await StopAsync(); }
            catch { }
            if (!process.WaitForExit(1500))
                process.Kill(entireProcessTree: true);
        }
        try { await readerTask; }
        catch { }
        process.Dispose();
        writeLock.Dispose();
    }
}
