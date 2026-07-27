namespace HythonManager.Models;

public enum ProductState { NotInstalled, Installed, UpdateAvailable }

public sealed class ProductInfo
{
    public required string Id { get; init; }
    public required string Name { get; init; }
    public required string Description { get; init; }
    public required string Tag { get; init; }
    public required Version LatestVersion { get; init; }
    public Version? InstalledVersion { get; set; }
    public string? AssetName { get; init; }
    public string? DownloadUrl { get; init; }
    public string? AssetDigest { get; init; }
    public string? ChecksumUrl { get; init; }
    public string? UninstallCommand { get; set; }
    public ProductState State => InstalledVersion is null
        ? ProductState.NotInstalled
        : LatestVersion > InstalledVersion ? ProductState.UpdateAvailable : ProductState.Installed;
    public string StateText => State switch
    {
        ProductState.NotInstalled => "설치되지 않음",
        ProductState.UpdateAvailable => $"업데이트 가능 · {InstalledVersion}",
        _ => $"설치됨 · {InstalledVersion}"
    };
    public string ActionText => State switch
    {
        ProductState.NotInstalled => "설치",
        ProductState.UpdateAvailable => "업데이트",
        _ => "다시 설치"
    };
    public bool CanUninstall => InstalledVersion is not null;
}
