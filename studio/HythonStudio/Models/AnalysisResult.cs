using System.Text.Json.Serialization;

namespace HythonStudio.Models;

public sealed class AnalysisResult
{
    [JsonPropertyName("protocolVersion")]
    public int ProtocolVersion { get; set; }
    [JsonPropertyName("hythonVersion")]
    public string HythonVersion { get; set; } = "";
    [JsonPropertyName("diagnostics")]
    public List<EditorDiagnostic> Diagnostics { get; set; } = [];
    [JsonPropertyName("symbols")]
    public List<EditorSymbol> Symbols { get; set; } = [];
    [JsonPropertyName("completions")]
    public CompletionResult Completions { get; set; } = new();
}

public sealed class EditorDiagnostic
{
    [JsonPropertyName("severity")]
    public string Severity { get; set; } = "";
    [JsonPropertyName("message")]
    public string Message { get; set; } = "";
    [JsonPropertyName("line")]
    public int Line { get; set; }
    [JsonPropertyName("column")]
    public int Column { get; set; }
    public override string ToString() => $"{Line}:{Column + 1}  {Message}";
}

public sealed class EditorSymbol
{
    [JsonPropertyName("name")]
    public string Name { get; set; } = "";
    [JsonPropertyName("kind")]
    public string Kind { get; set; } = "";
    [JsonPropertyName("line")]
    public int Line { get; set; }
    public override string ToString() => $"{Kind}  {Name}  (줄 {Line})";
}

public sealed class CompletionResult
{
    [JsonPropertyName("prefix")]
    public string Prefix { get; set; } = "";
    [JsonPropertyName("items")]
    public List<CompletionItem> Items { get; set; } = [];
}

public sealed class CompletionItem
{
    [JsonPropertyName("label")]
    public string Label { get; set; } = "";
    [JsonPropertyName("kind")]
    public string Kind { get; set; } = "";
    [JsonPropertyName("insertText")]
    public string InsertText { get; set; } = "";
}
