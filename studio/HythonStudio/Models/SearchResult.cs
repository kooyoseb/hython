namespace HythonStudio.Models;

public sealed record SearchResult(
    string File, int Line, int Column, string Preview)
{
    public string Location => $"{Path.GetFileName(File)}:{Line}:{Column}";
}
