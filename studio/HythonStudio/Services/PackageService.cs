namespace HythonStudio.Services;

public sealed record PackageOperationResult(
    string Label, int ExitCode, string Output)
{
    public bool Success => ExitCode == 0;
}

public static class PackageService
{
    public static Task<PackageOperationResult> InstallAsync(
        HythonEngine engine, string package, string? module, bool upgrade,
        string? workingDirectory = null)
    {
        string arguments = "package install " + HythonProcessService.Quote(package);
        if (!string.IsNullOrWhiteSpace(module))
            arguments += " --module " + HythonProcessService.Quote(module.Trim());
        if (upgrade)
            arguments += " --upgrade";
        return RunAsync(engine, upgrade ? "업데이트" : "설치", arguments, workingDirectory);
    }

    public static Task<PackageOperationResult> UninstallAsync(
        HythonEngine engine, string package, string? module,
        string? workingDirectory = null)
    {
        string arguments = "package uninstall " + HythonProcessService.Quote(package);
        if (!string.IsNullOrWhiteSpace(module))
            arguments += " --module " + HythonProcessService.Quote(module.Trim());
        return RunAsync(engine, "제거", arguments, workingDirectory);
    }

    public static Task<PackageOperationResult> ScanAsync(
        HythonEngine engine, string module, bool staticOnly,
        string? workingDirectory = null)
    {
        string arguments = "package scan " + HythonProcessService.Quote(module);
        if (staticOnly)
            arguments += " --static";
        return RunAsync(engine, "문법 분석", arguments, workingDirectory);
    }

    private static async Task<PackageOperationResult> RunAsync(
        HythonEngine engine, string label, string arguments, string? workingDirectory)
    {
        var result = await HythonProcessService.RunAsync(
            engine, arguments, workingDirectory);
        return new PackageOperationResult(label, result.ExitCode, result.Output.Trim());
    }
}
