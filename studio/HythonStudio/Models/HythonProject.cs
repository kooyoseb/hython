using System.Text.Json.Serialization;

namespace HythonStudio.Models;

public sealed class HythonProject
{
    [JsonPropertyName("name")]
    public string Name { get; set; } = "Hython 프로젝트";
    [JsonPropertyName("entry")]
    public string Entry { get; set; } = "main.hy";
    [JsonPropertyName("hythonVersion")]
    public string HythonVersion { get; set; } = "2.0.4";
    [JsonPropertyName("outputDirectory")]
    public string OutputDirectory { get; set; } = "dist";
}
