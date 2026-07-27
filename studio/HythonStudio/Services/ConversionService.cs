namespace HythonStudio.Services;

public sealed record HbcBuildOptions(
    string Output, string ProductName, string Version, string Company,
    string Description, string Copyright, string Icon, bool Windowed, bool OneDir);

public static class ConversionService
{
    public static Task<(int ExitCode, string Output)> PythonToHythonAsync(
        HythonEngine engine, string source, string output, bool complete = true)
    {
        string arguments =
            "translate " + HythonProcessService.Quote(source) +
            " --reverse" +
            (complete ? " --complete" : "") +
            " -o " + HythonProcessService.Quote(output);
        return HythonProcessService.RunAsync(
            engine, arguments, Path.GetDirectoryName(source));
    }

    public static Task<(int ExitCode, string Output)> HbcToExeAsync(
        HythonEngine engine, string source, string output)
    {
        string arguments =
            "exe " + HythonProcessService.Quote(source) +
            " -o " + HythonProcessService.Quote(output);
        return HythonProcessService.RunAsync(
            engine, arguments, Path.GetDirectoryName(source));
    }

    public static Task<(int ExitCode, string Output)> HbcToExeAsync(
        HythonEngine engine, string source, HbcBuildOptions options)
    {
        string arguments =
            "exe " + HythonProcessService.Quote(source) +
            " -o " + HythonProcessService.Quote(options.Output) +
            " --file-version " + HythonProcessService.Quote(options.Version);
        arguments = AddOption(arguments, "--product-name", options.ProductName);
        arguments = AddOption(arguments, "--company", options.Company);
        arguments = AddOption(arguments, "--description", options.Description);
        arguments = AddOption(arguments, "--copyright", options.Copyright);
        arguments = AddOption(arguments, "--icon", options.Icon);
        if (options.Windowed) arguments += " --windowed";
        if (options.OneDir) arguments += " --onedir";
        return HythonProcessService.RunAsync(
            engine, arguments, Path.GetDirectoryName(source));
    }

    private static string AddOption(string arguments, string option, string value) =>
        string.IsNullOrWhiteSpace(value)
            ? arguments
            : arguments + " " + option + " " + HythonProcessService.Quote(value);
}
