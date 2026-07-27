namespace HythonStudio.Models;

public sealed record DebugVariable(string Name, string Type, string Value);

public sealed record DebugEvent(
    string Event, int Line, string Function, string Message,
    string Output, int ExitCode, IReadOnlyList<DebugVariable> Variables);
