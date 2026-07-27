using System.Text;
using System.Text.Json;
using HythonStudio.Models;

namespace HythonStudio.Services;

public static class ProjectService
{
    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true };
    private static string SettingsDirectory => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "Hython", "Studio");
    private static string RecentFile => Path.Combine(SettingsDirectory, "recent-projects.json");

    public static string Create(string parent, string name, string entry)
    {
        string safeName = string.Concat(name.Trim().Select(character =>
            Path.GetInvalidFileNameChars().Contains(character) ? '_' : character));
        if (string.IsNullOrWhiteSpace(safeName))
            throw new ArgumentException("프로젝트 이름이 필요합니다.");
        string root = Path.Combine(parent, safeName);
        if (Directory.Exists(root) && Directory.EnumerateFileSystemEntries(root).Any())
            throw new IOException("같은 이름의 비어 있지 않은 폴더가 이미 있습니다.");
        Directory.CreateDirectory(root);
        Directory.CreateDirectory(Path.Combine(root, "dist"));
        string entryName = entry.Trim();
        if (!entryName.EndsWith(".hy", StringComparison.OrdinalIgnoreCase))
            entryName += ".hy";
        HythonProject project = new() { Name = name.Trim(), Entry = entryName };
        File.WriteAllText(Path.Combine(root, "hython.project.json"),
            JsonSerializer.Serialize(project, JsonOptions), new UTF8Encoding(false));
        File.WriteAllText(Path.Combine(root, entryName),
            "데프 메인():\n    프린트(\"안녕, 하이썬!\")\n\n\n이프 __네임__ == \"__메인__\":\n    메인()\n",
            new UTF8Encoding(false));
        File.WriteAllText(Path.Combine(root, ".gitignore"),
            "dist/\n*.hbc\n*.exe\n", new UTF8Encoding(false));
        AddRecent(root);
        return root;
    }

    public static IReadOnlyList<string> LoadRecent()
    {
        try
        {
            if (!File.Exists(RecentFile)) return [];
            return (JsonSerializer.Deserialize<List<string>>(
                        File.ReadAllText(RecentFile, Encoding.UTF8)) ?? [])
                .Where(Directory.Exists).Distinct(StringComparer.OrdinalIgnoreCase)
                .Take(10).ToList();
        }
        catch { return []; }
    }

    public static void AddRecent(string path)
    {
        Directory.CreateDirectory(SettingsDirectory);
        List<string> recent = LoadRecent()
            .Where(item => !string.Equals(item, path, StringComparison.OrdinalIgnoreCase))
            .Prepend(path).Take(10).ToList();
        File.WriteAllText(RecentFile, JsonSerializer.Serialize(recent, JsonOptions),
            new UTF8Encoding(false));
    }
}
