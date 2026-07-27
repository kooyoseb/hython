using System.Windows;
using System.Windows.Media;
using HythonStudio.Models;
using ICSharpCode.AvalonEdit.CodeCompletion;
using ICSharpCode.AvalonEdit.Document;
using ICSharpCode.AvalonEdit.Editing;

namespace HythonStudio.Editor;

public sealed class HythonCompletionData(CompletionItem item) : ICompletionData
{
    public ImageSource? Image => null;
    public string Text => item.InsertText;
    public object Content => item.Label;
    public object Description => item.Kind;
    public double Priority => item.Kind == "키워드" ? 2 : 1;

    public void Complete(TextArea textArea, ISegment completionSegment,
                         EventArgs insertionRequestEventArgs)
    {
        textArea.Document.Replace(completionSegment, Text);
    }
}
