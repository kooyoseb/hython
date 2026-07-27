using System.Collections.ObjectModel;

namespace HythonStudio.Models;

public sealed class ExplorerNode
{
    public required string Name { get; init; }
    public required string FullPath { get; init; }
    public bool IsDirectory { get; init; }
    public string Icon => IsDirectory ? "▸" : Path.GetExtension(Name).ToLowerInvariant() switch
    {
        ".hy" => "ㅎ",
        ".hbc" => "◆",
        ".py" => "Py",
        _ => "·"
    };
    public ObservableCollection<ExplorerNode> Children { get; } = [];
}
