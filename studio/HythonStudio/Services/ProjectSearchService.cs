using HythonStudio.Models;

namespace HythonStudio.Services;

public static class ProjectSearchService
{
    private static readonly HashSet<string> Skipped =
        [".git", ".vs", "bin", "obj", "dist", "build", "__pycache__"];
    private static readonly HashSet<string> Extensions =
        [".hy", ".py", ".json", ".toml", ".md", ".txt"];

    public static Task<IReadOnlyList<SearchResult>> SearchAsync(
        string root, string query, bool matchCase,
        CancellationToken cancellationToken) =>
        Task.Run<IReadOnlyList<SearchResult>>(() =>
        {
            List<SearchResult> results = [];
            StringComparison comparison = matchCase
                ? StringComparison.Ordinal : StringComparison.OrdinalIgnoreCase;
            foreach (string file in EnumerateFiles(root))
            {
                cancellationToken.ThrowIfCancellationRequested();
                if (!Extensions.Contains(Path.GetExtension(file)))
                    continue;
                string[] lines;
                try { lines = File.ReadAllLines(file); }
                catch (Exception) { continue; }
                for (int index = 0; index < lines.Length; index++)
                {
                    int start = 0;
                    while ((start = lines[index].IndexOf(
                               query, start, comparison)) >= 0)
                    {
                        results.Add(new SearchResult(
                            file, index + 1, start + 1, lines[index].Trim()));
                        if (results.Count >= 2000)
                            return results;
                        start += Math.Max(1, query.Length);
                    }
                }
            }
            return results;
        }, cancellationToken);

    private static IEnumerable<string> EnumerateFiles(string root)
    {
        Stack<string> pending = new();
        pending.Push(root);
        while (pending.Count > 0)
        {
            string folder = pending.Pop();
            string[] files, directories;
            try
            {
                files = Directory.GetFiles(folder);
                directories = Directory.GetDirectories(folder);
            }
            catch (Exception) { continue; }
            foreach (string file in files) yield return file;
            foreach (string directory in directories)
                if (!Skipped.Contains(Path.GetFileName(directory)))
                    pending.Push(directory);
        }
    }
}
