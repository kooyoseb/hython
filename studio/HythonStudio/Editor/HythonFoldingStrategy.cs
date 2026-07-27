using ICSharpCode.AvalonEdit.Document;
using ICSharpCode.AvalonEdit.Folding;

namespace HythonStudio.Editor;

public static class HythonFoldingStrategy
{
    public static IEnumerable<NewFolding> Create(TextDocument document)
    {
        List<(int Indent, int Start, string Name)> stack = [];
        foreach (DocumentLine line in document.Lines)
        {
            string text = document.GetText(line);
            if (string.IsNullOrWhiteSpace(text) || text.TrimStart().StartsWith("#"))
                continue;
            int indent = text.Length - text.TrimStart().Length;
            while (stack.Count > 0 && indent <= stack[^1].Indent)
            {
                var block = stack[^1];
                stack.RemoveAt(stack.Count - 1);
                if (line.PreviousLine is not null &&
                    line.PreviousLine.EndOffset > block.Start)
                    yield return new NewFolding(block.Start, line.PreviousLine.EndOffset)
                    { Name = block.Name };
            }
            string trimmed = text.Trim();
            if (trimmed.EndsWith(":"))
            {
                string name = trimmed.Length > 42 ? trimmed[..42] + "…" : trimmed;
                stack.Add((indent, line.EndOffset, name));
            }
        }
        while (stack.Count > 0)
        {
            var block = stack[^1];
            stack.RemoveAt(stack.Count - 1);
            if (document.TextLength > block.Start)
                yield return new NewFolding(block.Start, document.TextLength)
                { Name = block.Name };
        }
    }

    public static void Update(FoldingManager manager, TextDocument document) =>
        manager.UpdateFoldings(Create(document).OrderBy(f => f.StartOffset), -1);
}
