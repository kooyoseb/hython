using System.Windows;
using HythonStudio.Services;
using Microsoft.Win32;

namespace HythonStudio;

public partial class HbcBuildDialog : Window
{
    private readonly HythonEngine engine;
    private readonly string source;

    public HbcBuildOptions Options => new(
        OutputBox.Text.Trim(), ProductBox.Text.Trim(), VersionBox.Text.Trim(),
        CompanyBox.Text.Trim(), DescriptionBox.Text.Trim(),
        CopyrightBox.Text.Trim(), IconBox.Text.Trim(),
        WindowedBox.IsChecked == true, OneDirBox.IsChecked == true);

    public HbcBuildDialog(HythonEngine engine, string source)
    {
        InitializeComponent();
        this.engine = engine;
        this.source = source;
        SourceText.Text = source;
        ProductBox.Text = Path.GetFileNameWithoutExtension(source);
        DescriptionBox.Text = ProductBox.Text + " — Hython 애플리케이션";
        OutputBox.Text = Path.ChangeExtension(source, ".exe");
        Loaded += async (_, _) => await AnalyzeAsync();
    }

    private async Task AnalyzeAsync()
    {
        try
        {
            var result = await HythonProcessService.RunAsync(
                engine, "disassemble " + HythonProcessService.Quote(source),
                Path.GetDirectoryName(source));
            string[] lines = result.Output.Split(
                ['\r', '\n'], StringSplitOptions.RemoveEmptyEntries);
            FileInfo file = new(source);
            AnalysisSummary.Text = result.ExitCode == 0
                ? $"명령 {lines.Length:N0}개 · {file.Length:N0}바이트 · {file.LastWriteTime:g}"
                : "HBC 분석 실패";
            DisassemblyBox.Text = string.Join(Environment.NewLine, lines.Take(500));
        }
        catch (Exception ex)
        {
            AnalysisSummary.Text = "분석 오류: " + ex.Message;
        }
    }

    private void BrowseOutput_Click(object sender, RoutedEventArgs e)
    {
        if (OneDirBox.IsChecked == true)
        {
            OpenFolderDialog dialog = new()
            {
                Title = "폴더 배포 출력 위치",
                InitialDirectory = Path.GetDirectoryName(source)
            };
            if (dialog.ShowDialog(this) == true)
                OutputBox.Text = Path.Combine(
                    dialog.FolderName, Path.GetFileNameWithoutExtension(source) + "-dist");
            return;
        }
        SaveFileDialog save = new()
        {
            Title = "EXE 출력 위치",
            Filter = "Windows 실행 파일 (*.exe)|*.exe",
            FileName = Path.GetFileNameWithoutExtension(source) + ".exe",
            InitialDirectory = Path.GetDirectoryName(source)
        };
        if (save.ShowDialog(this) == true) OutputBox.Text = save.FileName;
    }

    private void BrowseIcon_Click(object sender, RoutedEventArgs e)
    {
        OpenFileDialog open = new()
        {
            Title = "Windows 아이콘 선택",
            Filter = "Windows 아이콘 (*.ico)|*.ico"
        };
        if (open.ShowDialog(this) == true) IconBox.Text = open.FileName;
    }

    private void OneDirBox_Changed(object sender, RoutedEventArgs e)
    {
        if (string.IsNullOrWhiteSpace(OutputBox.Text)) return;
        OutputBox.Text = OneDirBox.IsChecked == true
            ? Path.Combine(Path.GetDirectoryName(source) ?? "",
                Path.GetFileNameWithoutExtension(source) + "-dist")
            : Path.ChangeExtension(source, ".exe");
    }

    private void Build_Click(object sender, RoutedEventArgs e)
    {
        HbcBuildOptions options = Options;
        if (string.IsNullOrWhiteSpace(options.Output))
        {
            ValidationText.Text = "출력 위치를 입력하세요.";
            return;
        }
        if (!Version.TryParse(options.Version, out _))
        {
            ValidationText.Text = "파일 버전은 1.0.0.0 형식으로 입력하세요.";
            return;
        }
        if (!string.IsNullOrWhiteSpace(options.Icon) && !File.Exists(options.Icon))
        {
            ValidationText.Text = "선택한 아이콘 파일을 찾을 수 없습니다.";
            return;
        }
        DialogResult = true;
    }
}
