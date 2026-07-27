using System.Windows;
using System.Windows.Media;
using ICSharpCode.AvalonEdit;
using ICSharpCode.AvalonEdit.Document;
using ICSharpCode.AvalonEdit.Rendering;

namespace HythonStudio.Editor;

public sealed class BracketHighlightRenderer : IBackgroundRenderer
{
    private readonly TextEditor editor;
    private readonly Brush fill = new SolidColorBrush(Color.FromArgb(72, 212, 76, 76));
    private readonly Pen border = new(new SolidColorBrush(Color.FromRgb(229, 101, 101)), 1);

    public BracketHighlightRenderer(TextEditor editor)
    {
        this.editor = editor;
        fill.Freeze();
        border.Freeze();
        editor.TextArea.Caret.PositionChanged += (_, _) =>
            editor.TextArea.TextView.InvalidateLayer(Layer);
    }

    public KnownLayer Layer => KnownLayer.Selection;

    public void Draw(TextView textView, DrawingContext drawingContext)
    {
        if (!textView.VisualLinesValid)
            return;
        (int First, int Second)? pair = FindPair();
        if (pair is null)
            return;
        DrawOffset(textView, drawingContext, pair.Value.First);
        DrawOffset(textView, drawingContext, pair.Value.Second);
    }

    private void DrawOffset(TextView view, DrawingContext context, int offset)
    {
        foreach (Rect rect in BackgroundGeometryBuilder.GetRectsForSegment(
                     view, new TextSegment { StartOffset = offset, Length = 1 }))
            context.DrawRoundedRectangle(fill, border, rect, 2, 2);
    }

    private (int, int)? FindPair()
    {
        string text = editor.Text;
        if (text.Length == 0)
            return null;
        int caret = editor.CaretOffset;
        int position = caret > 0 && IsBracket(text[caret - 1]) ? caret - 1 :
            caret < text.Length && IsBracket(text[caret]) ? caret : -1;
        if (position < 0)
            return null;
        const string opens = "([{";
        const string closes = ")]}";
        char current = text[position];
        int openIndex = opens.IndexOf(current);
        bool forward = openIndex >= 0;
        int kind = forward ? openIndex : closes.IndexOf(current);
        char open = opens[kind];
        char close = closes[kind];
        int depth = 0;
        if (forward)
        {
            for (int index = position; index < text.Length; index++)
            {
                if (text[index] == open) depth++;
                else if (text[index] == close && --depth == 0) return (position, index);
            }
        }
        else
        {
            for (int index = position; index >= 0; index--)
            {
                if (text[index] == close) depth++;
                else if (text[index] == open && --depth == 0) return (index, position);
            }
        }
        return null;
    }

    private static bool IsBracket(char value) => "()[]{}".Contains(value);
}
