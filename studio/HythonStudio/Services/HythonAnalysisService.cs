using System.Text.Json;
using HythonStudio.Models;

namespace HythonStudio.Services;

public static class HythonAnalysisService
{
    public static async Task<AnalysisResult?> AnalyzeAsync(
        HythonEngine engine, string file, string source, int line, int column)
    {
        string arguments = "ide analyze " + HythonProcessService.Quote(file) +
            " --stdin --line " + line + " --column " + column;
        var result = await HythonProcessService.RunAsync(
            engine, arguments, Path.GetDirectoryName(file), source);
        if (result.ExitCode != 0)
            throw new InvalidOperationException(result.Output.Trim());
        string json = result.Output.Trim();
        int start = json.IndexOf('{');
        int end = json.LastIndexOf('}');
        if (start < 0 || end < start)
            throw new InvalidDataException("Hython 분석 JSON을 찾을 수 없습니다.");
        return JsonSerializer.Deserialize<AnalysisResult>(json[start..(end + 1)]);
    }
}
