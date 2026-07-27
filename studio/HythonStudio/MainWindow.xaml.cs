using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Diagnostics;
using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Shell;
using System.Xml;
using HythonStudio.Models;
using HythonStudio.Services;
using HythonStudio.Editor;
using ICSharpCode.AvalonEdit;
using ICSharpCode.AvalonEdit.CodeCompletion;
using ICSharpCode.AvalonEdit.Document;
using ICSharpCode.AvalonEdit.Folding;
using ICSharpCode.AvalonEdit.Highlighting;
using ICSharpCode.AvalonEdit.Highlighting.Xshd;
using Microsoft.Win32;

namespace HythonStudio;

public partial class MainWindow : Window
{
    private readonly ObservableCollection<ExplorerNode> roots = [];
    private readonly Dictionary<TabItem, string> openFiles = [];
    private readonly Dictionary<TextEditor, FoldingManager> foldingManagers = [];
    private readonly HashSet<TabItem> dirtyTabs = [];
    private HythonEngine? engine;
    private string? projectDirectory;
    private readonly IHighlightingDefinition? hythonHighlighting;
    private CancellationTokenSource? analysisCancellation;
    private readonly TerminalService terminal = new();
    private CancellationTokenSource? terminalCancellation;
    private bool packageOperationRunning;
    private DebugSession? debugSession;
    private readonly HashSet<int> breakpoints = [];
    private CancellationTokenSource? searchCancellation;

    public MainWindow(string? startupPath = null, string? startupAction = null)
    {
        InitializeComponent();
        hythonHighlighting = LoadHythonHighlighting();
        ProjectTree.ItemsSource = roots;
        RefreshRecentProjects();
        RefreshEngine();
        UpdateTerminalPrompt();
        CommandBindings.Add(new CommandBinding(
            ApplicationCommands.Save, (_, _) => SaveCurrentFile()));
        if (!string.IsNullOrWhiteSpace(startupPath))
            Loaded += async (_, _) => await HandleStartupPathAsync(
                startupPath, startupAction);
    }

    private async Task HandleStartupPathAsync(string path, string? action)
    {
        try { path = Path.GetFullPath(path); }
        catch { return; }
        if (Directory.Exists(path))
        {
            LoadProject(path);
            return;
        }
        if (!File.Exists(path)) return;
        LoadProject(Path.GetDirectoryName(path)!);
        string extension = Path.GetExtension(path);
        if (action == "--build-hbc" &&
            extension.Equals(".hbc", StringComparison.OrdinalIgnoreCase))
        {
            await ConfigureHbcBuildPathAsync(path);
            return;
        }
        if (action == "--convert-python" &&
            extension.Equals(".py", StringComparison.OrdinalIgnoreCase))
        {
            OpenFile(path);
            ConvertPython_Click(this, new RoutedEventArgs());
            return;
        }
        if (!extension.Equals(".hbc", StringComparison.OrdinalIgnoreCase))
            OpenFile(path);
        else
            await ConfigureHbcBuildPathAsync(path);
    }

    protected override void OnClosed(EventArgs e)
    {
        if (debugSession is not null)
        {
            debugSession.EventReceived -= DebugSession_EventReceived;
            debugSession.DisposeAsync().AsTask().GetAwaiter().GetResult();
            debugSession = null;
        }
        terminalCancellation?.Cancel();
        searchCancellation?.Cancel();
        base.OnClosed(e);
    }

    protected override void OnClosing(CancelEventArgs e)
    {
        if (dirtyTabs.Count > 0)
        {
            MessageBoxResult result = MessageBox.Show(
                this, $"저장하지 않은 파일이 {dirtyTabs.Count}개 있습니다.\n모두 저장할까요?",
                "Hython Studio 종료", MessageBoxButton.YesNoCancel,
                MessageBoxImage.Warning);
            if (result == MessageBoxResult.Cancel)
            {
                e.Cancel = true;
                return;
            }
            if (result == MessageBoxResult.Yes &&
                dirtyTabs.ToArray().Any(tab => !SaveTab(tab)))
            {
                e.Cancel = true;
                return;
            }
        }
        base.OnClosing(e);
    }

    private void ShowExplorer_Click(object sender, RoutedEventArgs e)
    {
        ExplorerPanel.Visibility = Visibility.Visible;
        SearchPanel.Visibility = Visibility.Collapsed;
        ExplorerActivityButton.Background =
            new SolidColorBrush(Color.FromRgb(44, 48, 55));
        SearchActivityButton.Background = Brushes.Transparent;
    }

    private void ShowSearch_Click(object sender, RoutedEventArgs e)
    {
        ExplorerPanel.Visibility = Visibility.Collapsed;
        SearchPanel.Visibility = Visibility.Visible;
        ExplorerActivityButton.Background = Brushes.Transparent;
        SearchActivityButton.Background =
            new SolidColorBrush(Color.FromRgb(44, 48, 55));
        SearchInput.Focus();
    }

    private async void SearchInput_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key != Key.Enter) return;
        e.Handled = true;
        await SearchProjectAsync();
    }

    private async void SearchProject_Click(object sender, RoutedEventArgs e) =>
        await SearchProjectAsync();

    private async Task SearchProjectAsync()
    {
        string query = SearchInput.Text;
        if (projectDirectory is null || !Directory.Exists(projectDirectory))
        {
            SearchStatus.Text = "프로젝트를 먼저 여세요.";
            return;
        }
        if (string.IsNullOrEmpty(query))
        {
            SearchStatus.Text = "검색어를 입력하세요.";
            SearchResultsList.ItemsSource = null;
            return;
        }
        searchCancellation?.Cancel();
        searchCancellation?.Dispose();
        searchCancellation = new CancellationTokenSource();
        SearchStatus.Text = "검색 중…";
        try
        {
            IReadOnlyList<SearchResult> results =
                await ProjectSearchService.SearchAsync(
                    projectDirectory, query, SearchMatchCase.IsChecked == true,
                    searchCancellation.Token);
            SearchResultsList.ItemsSource = results;
            SearchStatus.Text = results.Count >= 2000
                ? "결과 2,000개 이상 · 일부만 표시"
                : $"결과 {results.Count:N0}개";
        }
        catch (OperationCanceledException) { }
        catch (Exception ex)
        {
            SearchStatus.Text = "검색 오류: " + ex.Message;
        }
    }

    private void SearchResults_DoubleClick(object sender, MouseButtonEventArgs e)
    {
        if (SearchResultsList.SelectedItem is not SearchResult result)
            return;
        OpenFile(result.File);
        if (CurrentEditor is not TextEditor editor) return;
        int line = Math.Clamp(result.Line, 1, editor.Document.LineCount);
        DocumentLine documentLine = editor.Document.GetLineByNumber(line);
        int offset = Math.Min(
            documentLine.Offset + Math.Max(0, result.Column - 1),
            documentLine.EndOffset);
        editor.Select(offset, Math.Min(
            SearchInput.Text.Length, editor.Document.TextLength - offset));
        editor.ScrollTo(line, result.Column);
        editor.Focus();
    }

    private static IHighlightingDefinition? LoadHythonHighlighting()
    {
        try
        {
            using Stream? stream = typeof(MainWindow).Assembly.GetManifestResourceStream(
                "HythonStudio.Resources.Hython.xshd");
            if (stream is null) return null;
            using XmlReader reader = XmlReader.Create(stream);
            return HighlightingLoader.Load(reader, HighlightingManager.Instance);
        }
        catch
        {
            // A broken optional color theme must never prevent the IDE from starting.
            return null;
        }
    }

    private void RefreshEngine()
    {
        engine = HythonLocator.Find();
        EngineStatus.Text = engine is null
            ? "Hython 엔진 없음"
            : $"엔진: {engine.Source} · {Path.GetFileName(engine.Executable)}";
    }

    private void OpenProject_Click(object sender, RoutedEventArgs e)
    {
        OpenFolderDialog dialog = new()
        {
            Title = "하이썬 프로젝트 폴더 선택",
            Multiselect = false
        };
        if (dialog.ShowDialog(this) != true)
            return;
        LoadProject(dialog.FolderName);
    }

    private void LoadProject(string folder)
    {
        projectDirectory = folder;
        roots.Clear();
        roots.Add(BuildNode(folder, 0));
        ProjectStatus.Text = folder;
        Title = $"Hython Studio — {new DirectoryInfo(folder).Name}";
        ProjectService.AddRecent(folder);
        terminal.SetDirectory(folder);
        UpdateTerminalPrompt();
        RefreshRecentProjects();
        AppendOutput($"프로젝트 열기: {folder}");
    }

    private void RefreshRecentProjects() =>
        RecentProjectsList.ItemsSource = ProjectService.LoadRecent();

    private static ExplorerNode BuildNode(string path, int depth)
    {
        bool directory = Directory.Exists(path);
        ExplorerNode node = new()
        {
            Name = directory ? new DirectoryInfo(path).Name : Path.GetFileName(path),
            FullPath = path,
            IsDirectory = directory
        };
        if (!directory || depth > 12)
            return node;
        try
        {
            HashSet<string> skipped =
                [".git", ".vs", ".compiler-audit", ".wheel-audit", "bin", "obj",
                 "__pycache__", "build", "dist"];
            foreach (string child in Directory.EnumerateDirectories(path)
                         .Where(p => !skipped.Contains(Path.GetFileName(p)))
                         .OrderBy(p => p, StringComparer.CurrentCultureIgnoreCase))
                node.Children.Add(BuildNode(child, depth + 1));
            foreach (string child in Directory.EnumerateFiles(path)
                         .OrderBy(p => p, StringComparer.CurrentCultureIgnoreCase))
                node.Children.Add(BuildNode(child, depth + 1));
        }
        catch (UnauthorizedAccessException) { }
        catch (IOException) { }
        return node;
    }

    private void ProjectTree_DoubleClick(object sender, MouseButtonEventArgs e)
    {
        if (ProjectTree.SelectedItem is ExplorerNode { IsDirectory: false } node)
        {
            string extension = Path.GetExtension(node.FullPath);
            if (extension.Equals(".hbc", StringComparison.OrdinalIgnoreCase))
            {
                AppendOutput("HBC는 바이너리 파일입니다. 우클릭 → HBC → 독립 EXE를 사용하세요.");
                BottomTabs.SelectedIndex = 1;
                return;
            }
            OpenFile(node.FullPath);
        }
    }

    private void OpenSelectedFile_Click(object sender, RoutedEventArgs e)
    {
        if (ProjectTree.SelectedItem is not ExplorerNode { IsDirectory: false } node)
            return;
        if (Path.GetExtension(node.FullPath)
            .Equals(".hbc", StringComparison.OrdinalIgnoreCase))
        {
            AppendOutput("HBC 바이너리는 편집기로 열 수 없습니다.");
            BottomTabs.SelectedIndex = 1;
            return;
        }
        OpenFile(node.FullPath);
    }

    private void OpenFile(string path)
    {
        TabItem? existing = openFiles.FirstOrDefault(pair =>
            string.Equals(pair.Value, path, StringComparison.OrdinalIgnoreCase)).Key;
        if (existing is not null)
        {
            EditorTabs.SelectedItem = existing;
            return;
        }
        string text;
        try { text = File.ReadAllText(path, Encoding.UTF8); }
        catch (Exception ex)
        {
            AppendOutput("파일 열기 실패: " + ex.Message);
            return;
        }
        TextEditor editor = new()
        {
            Text = text,
            FontFamily = new FontFamily("Cascadia Mono,Consolas"),
            FontSize = 14,
            Background = new SolidColorBrush(Color.FromRgb(24, 26, 31)),
            Foreground = new SolidColorBrush(Color.FromRgb(225, 228, 234)),
            LineNumbersForeground = new SolidColorBrush(Color.FromRgb(100, 106, 116)),
            ShowLineNumbers = true,
            SyntaxHighlighting = string.Equals(Path.GetExtension(path), ".hy",
                StringComparison.OrdinalIgnoreCase) ? hythonHighlighting : null,
            HorizontalScrollBarVisibility = ScrollBarVisibility.Auto,
            VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
            Options =
            {
                ConvertTabsToSpaces = true,
                IndentationSize = 4,
                EnableHyperlinks = false,
                EnableEmailHyperlinks = false,
                HighlightCurrentLine = true
            }
        };
        editor.TextArea.TextView.CurrentLineBackground =
            new SolidColorBrush(Color.FromArgb(45, 95, 102, 114));
        editor.TextArea.TextView.CurrentLineBorder = new Pen(
            new SolidColorBrush(Color.FromArgb(70, 110, 118, 132)), 1);
        editor.TextArea.TextView.BackgroundRenderers.Add(
            new BracketHighlightRenderer(editor));
        TabItem tab = new() { Content = editor };
        tab.Header = CreateTabHeader(tab, path);
        editor.TextChanged += (_, _) =>
        {
            dirtyTabs.Add(tab);
            UpdateTabHeader(tab);
            if (foldingManagers.TryGetValue(editor, out FoldingManager? manager))
                HythonFoldingStrategy.Update(manager, editor.Document);
            ScheduleAnalysis(editor, path);
        };
        editor.TextArea.PreviewKeyDown += async (_, args) =>
        {
            if (args.Key == Key.Space && Keyboard.Modifiers.HasFlag(ModifierKeys.Control))
            {
                args.Handled = true;
                await ShowCompletionsAsync(editor, path);
            }
        };
        openFiles[tab] = path;
        FoldingManager foldingManager = FoldingManager.Install(editor.TextArea);
        foldingManagers[editor] = foldingManager;
        HythonFoldingStrategy.Update(foldingManager, editor.Document);
        EditorTabs.Items.Add(tab);
        EditorTabs.SelectedItem = tab;
        CurrentFileText.Text = path;
        _ = AnalyzeCurrentAsync();
    }

    private string? CurrentPath =>
        EditorTabs.SelectedItem is TabItem tab && openFiles.TryGetValue(tab, out string? path)
            ? path : null;

    private TextEditor? CurrentEditor =>
        (EditorTabs.SelectedItem as TabItem)?.Content as TextEditor;

    private void Save_Click(object sender, RoutedEventArgs e) => SaveCurrentFile();

    private void SaveAll_Click(object sender, RoutedEventArgs e)
    {
        int saved = dirtyTabs.ToArray().Count(SaveTab);
        ProjectStatus.Text = $"모두 저장 완료 · {saved}개 파일";
    }

    private bool SaveCurrentFile()
    {
        return EditorTabs.SelectedItem is TabItem tab && SaveTab(tab);
    }

    private bool SaveTab(TabItem tab)
    {
        if (!openFiles.TryGetValue(tab, out string? path) ||
            tab.Content is not TextEditor editor)
            return false;
        try
        {
            File.WriteAllText(path, editor.Text, new UTF8Encoding(false));
            dirtyTabs.Remove(tab);
            UpdateTabHeader(tab);
            ProjectStatus.Text = "저장됨: " + Path.GetFileName(path);
            if (ReferenceEquals(EditorTabs.SelectedItem, tab))
                _ = AnalyzeCurrentAsync();
            return true;
        }
        catch (Exception ex)
        {
            AppendOutput("저장 실패: " + ex.Message);
            return false;
        }
    }

    private object CreateTabHeader(TabItem tab, string path)
    {
        TextBlock title = new()
        {
            Text = Path.GetFileName(path),
            VerticalAlignment = VerticalAlignment.Center,
            Tag = "title"
        };
        Button close = new()
        {
            Content = "×", Width = 22, Height = 22,
            Padding = new Thickness(0), Margin = new Thickness(9, 0, -5, 0),
            Background = Brushes.Transparent, BorderThickness = new Thickness(0),
            ToolTip = "탭 닫기", Tag = tab
        };
        close.Click += CloseEditorTab_Click;
        StackPanel panel = new() { Orientation = Orientation.Horizontal };
        panel.Children.Add(title);
        panel.Children.Add(close);
        return panel;
    }

    private void UpdateTabHeader(TabItem tab)
    {
        if (tab.Header is not StackPanel panel ||
            panel.Children.OfType<TextBlock>().FirstOrDefault() is not TextBlock title ||
            !openFiles.TryGetValue(tab, out string? path))
            return;
        title.Text = Path.GetFileName(path) + (dirtyTabs.Contains(tab) ? " ●" : "");
        title.Foreground = dirtyTabs.Contains(tab)
            ? new SolidColorBrush(Color.FromRgb(234, 91, 91))
            : new SolidColorBrush(Color.FromRgb(231, 233, 237));
    }

    private void CloseEditorTab_Click(object sender, RoutedEventArgs e)
    {
        e.Handled = true;
        if (sender is Button { Tag: TabItem tab })
            CloseEditorTab(tab);
    }

    private bool CloseEditorTab(TabItem tab)
    {
        if (dirtyTabs.Contains(tab))
        {
            string name = openFiles.TryGetValue(tab, out string? path)
                ? Path.GetFileName(path) : "파일";
            MessageBoxResult result = MessageBox.Show(
                this, $"{name}의 변경 내용을 저장할까요?", "탭 닫기",
                MessageBoxButton.YesNoCancel, MessageBoxImage.Warning);
            if (result == MessageBoxResult.Cancel) return false;
            if (result == MessageBoxResult.Yes && !SaveTab(tab)) return false;
        }
        if (tab.Content is TextEditor editor &&
            foldingManagers.Remove(editor, out FoldingManager? manager))
            FoldingManager.Uninstall(manager);
        dirtyTabs.Remove(tab);
        openFiles.Remove(tab);
        EditorTabs.Items.Remove(tab);
        return true;
    }

    private async void Run_Click(object sender, RoutedEventArgs e) =>
        await RunHythonAsync("run", "실행");

    private async void Compile_Click(object sender, RoutedEventArgs e) =>
        await RunHythonAsync("compile", "HBC 컴파일");

    private async void BuildExe_Click(object sender, RoutedEventArgs e) =>
        await RunHythonAsync("exe", "EXE 빌드");

    private async void ConvertPython_Click(object sender, RoutedEventArgs e)
    {
        string? source = SelectedFileWithExtension(".py") ??
            (Path.GetExtension(CurrentPath ?? "")
                .Equals(".py", StringComparison.OrdinalIgnoreCase) ? CurrentPath : null);
        if (!CanRunFileTool(source, ".py", "변환할 Python 파일을 선택하세요."))
            return;
        string output = Path.ChangeExtension(source!, ".hy");
        if (!ConfirmOverwrite(output, "하이썬 변환"))
            return;
        await RunFileToolAsync(
            $"Python → 완전 하이썬: {Path.GetFileName(source)}",
            () => ConversionService.PythonToHythonAsync(engine!, source!, output),
            output, openOutput: true);
    }

    private async void BuildSelectedHbc_Click(object sender, RoutedEventArgs e)
    {
        string? source = SelectedFileWithExtension(".hbc") ??
            (Path.GetExtension(CurrentPath ?? "")
                .Equals(".hbc", StringComparison.OrdinalIgnoreCase) ? CurrentPath : null);
        if (!CanRunFileTool(source, ".hbc", "빌드할 HBC 파일을 선택하세요."))
            return;
        string output = Path.ChangeExtension(source!, ".exe");
        if (!ConfirmOverwrite(output, "독립 EXE 빌드"))
            return;
        await RunFileToolAsync(
            $"HBC → EXE: {Path.GetFileName(source)}",
            () => ConversionService.HbcToExeAsync(engine!, source!, output),
            output, openOutput: false);
    }

    private async void ConfigureHbcBuild_Click(object sender, RoutedEventArgs e)
    {
        string? source = SelectedFileWithExtension(".hbc") ??
            (Path.GetExtension(CurrentPath ?? "")
                .Equals(".hbc", StringComparison.OrdinalIgnoreCase) ? CurrentPath : null);
        if (!CanRunFileTool(source, ".hbc", "설정할 HBC 파일을 선택하세요."))
            return;
        await ConfigureHbcBuildPathAsync(source!);
    }

    private async Task ConfigureHbcBuildPathAsync(string source)
    {
        if (engine is null || !File.Exists(source))
            return;
        HbcBuildDialog dialog = new(engine!, source!) { Owner = this };
        if (dialog.ShowDialog() != true)
            return;
        HbcBuildOptions options = dialog.Options;
        if (!ConfirmOverwrite(options.Output, "HBC EXE 빌드"))
            return;
        await RunFileToolAsync(
            $"메타데이터 EXE 빌드: {Path.GetFileName(source)}",
            () => ConversionService.HbcToExeAsync(engine!, source!, options),
            options.Output, openOutput: false);
    }

    private string? SelectedFileWithExtension(string extension) =>
        ProjectTree.SelectedItem is ExplorerNode { IsDirectory: false } node &&
        Path.GetExtension(node.FullPath).Equals(
            extension, StringComparison.OrdinalIgnoreCase)
            ? node.FullPath : null;

    private bool CanRunFileTool(string? path, string extension, string message)
    {
        if (engine is null)
        {
            AppendOutput("Hython 엔진을 찾을 수 없습니다.");
            BottomTabs.SelectedIndex = 1;
            return false;
        }
        if (path is not null && File.Exists(path) &&
            Path.GetExtension(path).Equals(extension, StringComparison.OrdinalIgnoreCase))
            return true;
        AppendOutput(message);
        BottomTabs.SelectedIndex = 1;
        return false;
    }

    private bool ConfirmOverwrite(string output, string title) =>
        !File.Exists(output) ||
        MessageBox.Show(
            this, $"이미 존재하는 파일을 덮어쓸까요?\n{output}", title,
            MessageBoxButton.YesNo, MessageBoxImage.Warning) == MessageBoxResult.Yes;

    private async Task RunFileToolAsync(
        string label, Func<Task<(int ExitCode, string Output)>> operation,
        string output, bool openOutput)
    {
        AppendOutput($"> {label}");
        BottomTabs.SelectedIndex = 1;
        ProjectStatus.Text = label + " 작업 중…";
        try
        {
            var result = await operation();
            if (!string.IsNullOrWhiteSpace(result.Output))
                AppendOutput(result.Output.Trim());
            if (result.ExitCode != 0)
            {
                AppendOutput($"[실패 · 종료 코드 {result.ExitCode}]");
                ProjectStatus.Text = label + " 실패";
                return;
            }
            AppendOutput($"[완료] {output}");
            ProjectStatus.Text = label + " 완료";
            RefreshProjectTree();
            if (openOutput && File.Exists(output))
                OpenFile(output);
        }
        catch (Exception ex)
        {
            AppendOutput("[오류] " + ex.Message);
            ProjectStatus.Text = label + " 오류";
        }
    }

    private async Task RunHythonAsync(string command, string label)
    {
        if (engine is null)
        {
            AppendOutput("Hython 엔진을 찾을 수 없습니다.");
            return;
        }
        string? path = CurrentPath;
        if (path is null)
        {
            AppendOutput(label + ": 먼저 .hy 또는 .hbc 파일을 여세요.");
            return;
        }
        SaveCurrentFile();
        AppendOutput($"> {engine.Executable} {command} \"{path}\"");
        try
        {
            var result = await HythonProcessService.RunAsync(
                engine, command + " " + HythonProcessService.Quote(path),
                Path.GetDirectoryName(path));
            AppendOutput(result.Output);
            AppendOutput($"[{label} 종료 코드: {result.ExitCode}]");
        }
        catch (Exception ex) { AppendOutput(label + " 실패: " + ex.Message); }
    }

    private void Debug_Click(object sender, RoutedEventArgs e)
    {
        BottomTabs.SelectedItem = DebugTab;
        if (debugSession is null)
            DebugStart_Click(sender, e);
    }

    private void ToggleBreakpoint_Click(object sender, RoutedEventArgs e)
    {
        if (CurrentEditor is not TextEditor editor || CurrentPath is null ||
            !Path.GetExtension(CurrentPath).Equals(".hy", StringComparison.OrdinalIgnoreCase))
            return;
        int line = editor.TextArea.Caret.Line;
        if (!breakpoints.Add(line)) breakpoints.Remove(line);
        BreakpointsList.ItemsSource = breakpoints.Order().Select(item => $"●  줄 {item}");
        DebugStatus.Text = breakpoints.Contains(line)
            ? $"줄 {line}에 중단점 설정" : $"줄 {line} 중단점 해제";
        if (debugSession is not null)
            _ = debugSession.SetBreakpointsAsync(breakpoints);
    }

    private async void DebugStart_Click(object sender, RoutedEventArgs e)
    {
        if (engine is null || CurrentPath is null || CurrentEditor is null ||
            !Path.GetExtension(CurrentPath).Equals(".hy", StringComparison.OrdinalIgnoreCase))
        {
            DebugStatus.Text = ".hy 파일을 먼저 여세요.";
            BottomTabs.SelectedItem = DebugTab;
            return;
        }
        SaveCurrentFile();
        if (debugSession is not null)
            await EndDebugSessionAsync();
        DebugOutput.Clear();
        DebugVariables.ItemsSource = null;
        debugSession = new DebugSession(engine, CurrentPath, breakpoints);
        debugSession.EventReceived += DebugSession_EventReceived;
        SetDebugControls(running: true, paused: false);
        DebugStatus.Text = "디버거 시작 중…";
        BottomTabs.SelectedItem = DebugTab;
    }

    private void DebugSession_EventReceived(DebugEvent item) =>
        Dispatcher.InvokeAsync(async () =>
        {
            switch (item.Event)
            {
                case "initialized":
                    DebugStatus.Text = "실행 준비 완료";
                    await debugSession!.ContinueAsync();
                    break;
                case "stopped":
                    DebugStatus.Text = $"줄 {item.Line}에서 일시정지 · {item.Function}";
                    DebugVariables.ItemsSource = item.Variables;
                    SetDebugControls(running: true, paused: true);
                    NavigateToDebugLine(item.Line);
                    break;
                case "output":
                    DebugOutput.AppendText(item.Output);
                    DebugOutput.ScrollToEnd();
                    break;
                case "exception":
                    DebugStatus.Text = "예외: " + item.Message;
                    DebugOutput.AppendText(
                        $"{Environment.NewLine}[{item.Message}]{Environment.NewLine}");
                    break;
                case "terminated":
                    DebugStatus.Text = item.ExitCode == 0
                        ? "디버그 종료" : $"오류로 종료 · 코드 {item.ExitCode}";
                    SetDebugControls(running: false, paused: false);
                    break;
                case "error":
                    DebugStatus.Text = item.Message;
                    break;
            }
        });

    private void NavigateToDebugLine(int line)
    {
        if (CurrentEditor is not TextEditor editor) return;
        line = Math.Clamp(line, 1, editor.Document.LineCount);
        editor.ScrollTo(line, 1);
        editor.TextArea.Caret.Line = line;
        editor.TextArea.Caret.Column = 1;
        editor.Focus();
    }

    private async void DebugContinue_Click(object sender, RoutedEventArgs e)
    {
        if (debugSession is null) return;
        SetDebugControls(running: true, paused: false);
        DebugStatus.Text = "실행 중…";
        await debugSession.ContinueAsync();
    }

    private async void DebugStep_Click(object sender, RoutedEventArgs e)
    {
        if (debugSession is null) return;
        SetDebugControls(running: true, paused: false);
        DebugStatus.Text = "한 단계 실행 중…";
        await debugSession.StepAsync();
    }

    private async void DebugStop_Click(object sender, RoutedEventArgs e) =>
        await EndDebugSessionAsync();

    private async Task EndDebugSessionAsync()
    {
        if (debugSession is null) return;
        DebugSession session = debugSession;
        debugSession = null;
        session.EventReceived -= DebugSession_EventReceived;
        await session.DisposeAsync();
        SetDebugControls(running: false, paused: false);
        DebugStatus.Text = "사용자가 디버그를 중지했습니다.";
    }

    private void SetDebugControls(bool running, bool paused)
    {
        DebugStartButton.IsEnabled = !running;
        DebugContinueButton.IsEnabled = running && paused;
        DebugStepButton.IsEnabled = running && paused;
        DebugStopButton.IsEnabled = running;
    }

    private void Packages_Click(object sender, RoutedEventArgs e)
    {
        BottomTabs.SelectedItem = PackagesTab;
        PackageSpecInput.Focus();
    }

    private async void PackageInstall_Click(object sender, RoutedEventArgs e) =>
        await RunPackageOperationAsync(upgrade: false);

    private async void PackageUpdate_Click(object sender, RoutedEventArgs e) =>
        await RunPackageOperationAsync(upgrade: true);

    private async Task RunPackageOperationAsync(bool upgrade)
    {
        string package = PackageSpecInput.Text.Trim();
        if (!ValidatePackageInput(package, "설치할 패키지 이름을 입력하세요."))
            return;
        await ExecutePackageAsync(() => PackageService.InstallAsync(
            engine!, package, PackageModuleInput.Text, upgrade, projectDirectory));
    }

    private async void PackageRemove_Click(object sender, RoutedEventArgs e)
    {
        string package = PackageSpecInput.Text.Trim();
        if (!ValidatePackageInput(package, "제거할 패키지 이름을 입력하세요."))
            return;
        if (MessageBox.Show(
                this, $"'{package}' 패키지와 생성된 한글 발음 사전을 제거할까요?",
                "패키지 제거", MessageBoxButton.YesNo, MessageBoxImage.Warning)
            != MessageBoxResult.Yes)
            return;
        await ExecutePackageAsync(() => PackageService.UninstallAsync(
            engine!, package, PackageModuleInput.Text, projectDirectory));
    }

    private async void PackageScan_Click(object sender, RoutedEventArgs e)
    {
        string module = PackageModuleInput.Text.Trim();
        if (string.IsNullOrWhiteSpace(module))
            module = PackageSpecInput.Text.Trim();
        if (!ValidatePackageInput(module, "분석할 모듈 이름을 입력하세요."))
            return;
        await ExecutePackageAsync(() => PackageService.ScanAsync(
            engine!, module, PackageStaticScan.IsChecked == true, projectDirectory));
    }

    private bool ValidatePackageInput(string value, string message)
    {
        if (packageOperationRunning)
            return false;
        if (engine is null)
        {
            PackageStatus.Text = "Hython 엔진을 찾을 수 없습니다.";
            AppendPackageLog("[오류] Hython 엔진을 먼저 설치하거나 다시 찾아주세요.");
            return false;
        }
        if (!string.IsNullOrWhiteSpace(value))
            return true;
        PackageStatus.Text = message;
        PackageSpecInput.Focus();
        return false;
    }

    private async Task ExecutePackageAsync(
        Func<Task<PackageOperationResult>> operation)
    {
        packageOperationRunning = true;
        SetPackageButtons(false);
        PackageProgress.Visibility = Visibility.Visible;
        PackageStatus.Text = "작업 중… 패키지 API 수에 따라 시간이 걸릴 수 있습니다.";
        AppendPackageLog($"[{DateTime.Now:HH:mm:ss}] 작업 시작");
        try
        {
            PackageOperationResult result = await operation();
            if (!string.IsNullOrWhiteSpace(result.Output))
                AppendPackageLog(result.Output);
            PackageStatus.Text = result.Success
                ? $"{result.Label} 완료 · 자동완성과 한글 문법에 반영됨"
                : $"{result.Label} 실패 · 종료 코드 {result.ExitCode}";
            AppendPackageLog(result.Success
                ? $"[완료] {result.Label}"
                : $"[실패] {result.Label} (종료 코드 {result.ExitCode})");
            if (result.Success)
                await AnalyzeCurrentAsync();
        }
        catch (Exception ex)
        {
            PackageStatus.Text = "패키지 작업 중 오류가 발생했습니다.";
            AppendPackageLog("[오류] " + ex.Message);
        }
        finally
        {
            PackageProgress.Visibility = Visibility.Collapsed;
            SetPackageButtons(true);
            packageOperationRunning = false;
        }
    }

    private void SetPackageButtons(bool enabled)
    {
        PackageInstallButton.IsEnabled = enabled;
        PackageUpdateButton.IsEnabled = enabled;
        PackageRemoveButton.IsEnabled = enabled;
        PackageScanButton.IsEnabled = enabled;
    }

    private void AppendPackageLog(string text)
    {
        PackageLog.AppendText(
            (PackageLog.Text.Length == 0 ? "" : Environment.NewLine) + text);
        PackageLog.ScrollToEnd();
    }

    private void ClearPackageLog_Click(object sender, RoutedEventArgs e) =>
        PackageLog.Clear();

    private void RefreshEngine_Click(object sender, RoutedEventArgs e)
    {
        RefreshEngine();
        AppendOutput(EngineStatus.Text);
    }

    private void ManageEngine_Click(object sender, RoutedEventArgs e)
    {
        EngineManagerDialog dialog = new() { Owner = this };
        dialog.ShowDialog();
        if (dialog.EngineChanged)
        {
            RefreshEngine();
            AppendOutput("Hython 엔진 변경 감지: " + EngineStatus.Text);
        }
    }

    private void EditorTabs_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        CurrentFileText.Text = CurrentPath ?? "선택되지 않음";
    }

    private void ProblemsList_DoubleClick(object sender, MouseButtonEventArgs e)
    {
        if (ProblemsList.SelectedItem is not EditorDiagnostic diagnostic ||
            CurrentEditor is not TextEditor editor)
            return;
        int line = Math.Clamp(diagnostic.Line, 1, editor.Document.LineCount);
        DocumentLine documentLine = editor.Document.GetLineByNumber(line);
        int offset = Math.Min(
            documentLine.Offset + Math.Max(0, diagnostic.Column),
            documentLine.EndOffset);
        editor.Select(offset, Math.Min(1, editor.Document.TextLength - offset));
        editor.ScrollTo(line, diagnostic.Column + 1);
        editor.Focus();
    }

    private void AppendOutput(string text)
    {
        OutputBox.AppendText((OutputBox.Text.Length == 0 ? "" : Environment.NewLine) + text);
        OutputBox.ScrollToEnd();
    }

    private async void TerminalInput_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key != Key.Enter || terminalCancellation is not null)
            return;
        e.Handled = true;
        string command = TerminalInput.Text;
        TerminalInput.Clear();
        if (string.IsNullOrWhiteSpace(command)) return;
        if (command.Trim().Equals("cls", StringComparison.OrdinalIgnoreCase) ||
            command.Trim().Equals("클리어", StringComparison.OrdinalIgnoreCase))
        {
            TerminalOutput.Clear();
            return;
        }
        AppendTerminal($"{terminal.CurrentDirectory}> {command}");
        terminalCancellation = new CancellationTokenSource();
        TerminalInput.IsEnabled = false;
        try
        {
            var result = await terminal.ExecuteAsync(command, terminalCancellation.Token);
            if (!string.IsNullOrWhiteSpace(result.Output))
                AppendTerminal(result.Output.TrimEnd());
            if (result.ExitCode != 0)
                AppendTerminal($"[종료 코드 {result.ExitCode}]");
        }
        catch (OperationCanceledException)
        {
            AppendTerminal("[사용자가 명령을 중단했습니다.]");
        }
        catch (Exception ex)
        {
            AppendTerminal("[터미널 오류] " + ex.Message);
        }
        finally
        {
            terminalCancellation.Dispose();
            terminalCancellation = null;
            TerminalInput.IsEnabled = true;
            UpdateTerminalPrompt();
            TerminalInput.Focus();
        }
    }

    private void AppendTerminal(string text)
    {
        TerminalOutput.AppendText(
            (TerminalOutput.Text.Length == 0 ? "" : Environment.NewLine) + text);
        TerminalOutput.ScrollToEnd();
    }

    private void UpdateTerminalPrompt() =>
        TerminalPrompt.ToolTip = terminal.CurrentDirectory;

    private void ClearTerminal_Click(object sender, RoutedEventArgs e) =>
        TerminalOutput.Clear();

    private void StopTerminal_Click(object sender, RoutedEventArgs e) =>
        terminalCancellation?.Cancel();

    private async Task AnalyzeCurrentAsync()
    {
        string? path = CurrentPath;
        TextEditor? editor = CurrentEditor;
        if (engine is null || path is null || editor is null ||
            !string.Equals(Path.GetExtension(path), ".hy", StringComparison.OrdinalIgnoreCase))
            return;
        int line = editor.TextArea.Caret.Line;
        int column = Math.Max(0, editor.TextArea.Caret.Column - 1);
        try
        {
            AnalysisResult? result = await HythonAnalysisService.AnalyzeAsync(
                engine, path, editor.Text, line, column);
            if (result is null) return;
            ProblemsList.ItemsSource = result.Diagnostics;
            SymbolsList.ItemsSource = result.Symbols;
            ProjectStatus.Text = result.Diagnostics.Count == 0
                ? $"분석 완료 · Hython {result.HythonVersion}"
                : $"문제 {result.Diagnostics.Count}개";
        }
        catch (Exception ex)
        {
            AppendOutput("코드 분석 실패: " + ex.Message);
        }
    }

    private void ScheduleAnalysis(TextEditor editor, string path)
    {
        analysisCancellation?.Cancel();
        CancellationTokenSource cancellation = new();
        analysisCancellation = cancellation;
        _ = AnalyzeAfterDelayAsync(editor, path, cancellation.Token);
    }

    private async Task AnalyzeAfterDelayAsync(
        TextEditor editor, string path, CancellationToken cancellation)
    {
        try
        {
            await Task.Delay(550, cancellation);
            if (cancellation.IsCancellationRequested ||
                EditorTabs.SelectedItem is not TabItem selected ||
                selected.Content != editor)
                return;
            await AnalyzeCurrentAsync();
        }
        catch (OperationCanceledException) { }
    }

    private async Task ShowCompletionsAsync(TextEditor editor, string path)
    {
        if (engine is null)
            return;
        int line = editor.TextArea.Caret.Line;
        int column = Math.Max(0, editor.TextArea.Caret.Column - 1);
        try
        {
            AnalysisResult? result = await HythonAnalysisService.AnalyzeAsync(
                engine, path, editor.Text, line, column);
            if (result is null || result.Completions.Items.Count == 0)
                return;
            string prefix = result.Completions.Prefix;
            CompletionWindow suggestions = new(editor.TextArea)
            {
                StartOffset = Math.Max(0, editor.CaretOffset - prefix.Length)
            };
            foreach (CompletionItem item in result.Completions.Items.Take(40))
                suggestions.CompletionList.CompletionData.Add(
                    new HythonCompletionData(item));
            suggestions.Show();
        }
        catch (Exception ex)
        {
            AppendOutput("자동완성 실패: " + ex.Message);
        }
    }

    private void About_Click(object sender, RoutedEventArgs e) =>
        MessageBox.Show(this,
            "Hython Studio 0.2.0\n\nHython 분석 기반 문법 강조·자동완성 IDE",
            "Hython Studio 정보", MessageBoxButton.OK, MessageBoxImage.Information);

    private void Exit_Click(object sender, RoutedEventArgs e) => Close();

    private void NewProject_Click(object sender, RoutedEventArgs e)
    {
        NewProjectDialog dialog = new() { Owner = this };
        if (dialog.ShowDialog() != true) return;
        try
        {
            string root = ProjectService.Create(
                dialog.Location, dialog.ProjectName, dialog.EntryFile);
            LoadProject(root);
            OpenFile(Path.Combine(root,
                dialog.EntryFile.EndsWith(".hy", StringComparison.OrdinalIgnoreCase)
                    ? dialog.EntryFile : dialog.EntryFile + ".hy"));
        }
        catch (Exception ex)
        {
            MessageBox.Show(this, ex.Message, "프로젝트 생성 실패",
                MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void RecentProjects_DoubleClick(object sender, MouseButtonEventArgs e)
    {
        if (RecentProjectsList.SelectedItem is string path && Directory.Exists(path))
            LoadProject(path);
    }

    private string SelectedDirectory()
    {
        if (ProjectTree.SelectedItem is ExplorerNode node)
            return node.IsDirectory ? node.FullPath :
                Path.GetDirectoryName(node.FullPath) ?? projectDirectory ?? "";
        return projectDirectory ?? "";
    }

    private void NewFile_Click(object sender, RoutedEventArgs e)
    {
        string directory = SelectedDirectory();
        if (!Directory.Exists(directory)) return;
        string? name = PromptForName("새 Hython 파일", "파일 이름", "새파일.hy");
        if (string.IsNullOrWhiteSpace(name)) return;
        if (!name.EndsWith(".hy", StringComparison.OrdinalIgnoreCase)) name += ".hy";
        try
        {
            string path = Path.Combine(directory, name);
            if (File.Exists(path)) throw new IOException("같은 이름의 파일이 이미 있습니다.");
            File.WriteAllText(path, "", new UTF8Encoding(false));
            RefreshProject_Click(sender, e);
            OpenFile(path);
        }
        catch (Exception ex) { AppendOutput("파일 생성 실패: " + ex.Message); }
    }

    private void NewFolder_Click(object sender, RoutedEventArgs e)
    {
        string directory = SelectedDirectory();
        if (!Directory.Exists(directory)) return;
        string? name = PromptForName("새 폴더", "폴더 이름", "새폴더");
        if (string.IsNullOrWhiteSpace(name)) return;
        try
        {
            string path = Path.Combine(directory, name);
            if (Directory.Exists(path)) throw new IOException("같은 이름의 폴더가 이미 있습니다.");
            Directory.CreateDirectory(path);
            RefreshProject_Click(sender, e);
        }
        catch (Exception ex) { AppendOutput("폴더 생성 실패: " + ex.Message); }
    }

    private void RenameSelected_Click(object sender, RoutedEventArgs e)
    {
        if (ProjectTree.SelectedItem is not ExplorerNode node ||
            projectDirectory is null ||
            string.Equals(node.FullPath, projectDirectory,
                StringComparison.OrdinalIgnoreCase))
            return;
        string? name = PromptForName(
            "이름 바꾸기", "새 이름", Path.GetFileName(node.FullPath));
        if (string.IsNullOrWhiteSpace(name) ||
            name.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0)
            return;
        string parent = Path.GetDirectoryName(node.FullPath)!;
        string destination = Path.Combine(parent, name);
        if (!IsInsideProject(destination))
        {
            AppendOutput("프로젝트 밖으로 이동할 수 없습니다.");
            return;
        }
        try
        {
            if (File.Exists(destination) || Directory.Exists(destination))
                throw new IOException("같은 이름의 항목이 이미 있습니다.");
            string old = node.FullPath;
            if (node.IsDirectory)
                Directory.Move(old, destination);
            else
                File.Move(old, destination);
            foreach (var pair in openFiles.ToArray())
            {
                if (!pair.Value.Equals(old, StringComparison.OrdinalIgnoreCase) &&
                    !(node.IsDirectory && pair.Value.StartsWith(
                        old + Path.DirectorySeparatorChar,
                        StringComparison.OrdinalIgnoreCase)))
                    continue;
                string updated = destination + pair.Value[old.Length..];
                openFiles[pair.Key] = updated;
                UpdateTabHeader(pair.Key);
            }
            RefreshProjectTree();
            AppendOutput($"이름 변경: {old} → {destination}");
        }
        catch (Exception ex) { AppendOutput("이름 변경 실패: " + ex.Message); }
    }

    private void DeleteSelected_Click(object sender, RoutedEventArgs e)
    {
        if (ProjectTree.SelectedItem is not ExplorerNode node ||
            projectDirectory is null ||
            string.Equals(node.FullPath, projectDirectory,
                StringComparison.OrdinalIgnoreCase) ||
            !IsInsideProject(node.FullPath))
            return;
        if (MessageBox.Show(
                this, $"다음 항목을 완전히 삭제할까요?\n{node.FullPath}",
                "프로젝트 항목 삭제", MessageBoxButton.YesNo,
                MessageBoxImage.Warning) != MessageBoxResult.Yes)
            return;
        TabItem[] affected = openFiles
            .Where(pair => pair.Value.Equals(
                    node.FullPath, StringComparison.OrdinalIgnoreCase) ||
                (node.IsDirectory && pair.Value.StartsWith(
                    node.FullPath + Path.DirectorySeparatorChar,
                    StringComparison.OrdinalIgnoreCase)))
            .Select(pair => pair.Key).ToArray();
        if (affected.Any(tab => !CloseEditorTab(tab)))
            return;
        try
        {
            if (node.IsDirectory)
                Directory.Delete(node.FullPath, recursive: true);
            else
                File.Delete(node.FullPath);
            RefreshProjectTree();
            AppendOutput("삭제 완료: " + node.FullPath);
        }
        catch (Exception ex) { AppendOutput("삭제 실패: " + ex.Message); }
    }

    private bool IsInsideProject(string path)
    {
        if (projectDirectory is null) return false;
        string root = Path.GetFullPath(projectDirectory)
            .TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
        string candidate = Path.GetFullPath(path);
        return candidate.StartsWith(root, StringComparison.OrdinalIgnoreCase);
    }

    private void RefreshProject_Click(object sender, RoutedEventArgs e)
    {
        RefreshProjectTree();
        ProjectStatus.Text = "프로젝트 새로고침 완료";
    }

    private void RefreshProjectTree()
    {
        if (projectDirectory is null || !Directory.Exists(projectDirectory)) return;
        roots.Clear();
        roots.Add(BuildNode(projectDirectory, 0));
    }

    private string? PromptForName(string title, string label, string initial)
    {
        Window dialog = new()
        {
            Owner = this, Title = title, Width = 410, Height = 190,
            ResizeMode = ResizeMode.NoResize, WindowStartupLocation = WindowStartupLocation.CenterOwner,
            Background = new SolidColorBrush(Color.FromRgb(32, 35, 41)),
            Foreground = Brushes.White
        };
        TextBox input = new()
        {
            Text = initial, Margin = new Thickness(0, 6, 0, 14),
            Padding = new Thickness(7), Background = new SolidColorBrush(Color.FromRgb(24, 26, 31)),
            Foreground = Brushes.White, BorderBrush = new SolidColorBrush(Color.FromRgb(64, 69, 79))
        };
        Button accept = new() { Content = "만들기", Width = 85, IsDefault = true };
        Button cancel = new() { Content = "취소", Width = 75, IsCancel = true };
        accept.Click += (_, _) => dialog.DialogResult = true;
        StackPanel buttons = new()
        {
            Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right
        };
        buttons.Children.Add(cancel); buttons.Children.Add(accept);
        StackPanel content = new() { Margin = new Thickness(22) };
        content.Children.Add(new TextBlock { Text = label, Foreground = new SolidColorBrush(Color.FromRgb(170, 176, 186)) });
        content.Children.Add(input); content.Children.Add(buttons);
        dialog.Content = content;
        dialog.Loaded += (_, _) => { input.Focus(); input.SelectAll(); };
        return dialog.ShowDialog() == true ? input.Text.Trim() : null;
    }

    private void TitleBar_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (e.ClickCount == 2)
            ToggleMaximize();
        else
            DragMove();
    }

    private void Minimize_Click(object sender, RoutedEventArgs e) =>
        WindowState = WindowState.Minimized;

    private void Maximize_Click(object sender, RoutedEventArgs e) => ToggleMaximize();

    private void ToggleMaximize() =>
        WindowState = WindowState == WindowState.Maximized
            ? WindowState.Normal : WindowState.Maximized;

    private void Close_Click(object sender, RoutedEventArgs e) => Close();

    private void Window_PreviewKeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.F5)
        {
            e.Handled = true;
            Run_Click(sender, new RoutedEventArgs());
        }
        else if (e.Key == Key.F6)
        {
            e.Handled = true;
            Compile_Click(sender, new RoutedEventArgs());
        }
        else if (e.Key == Key.S &&
                 Keyboard.Modifiers == (ModifierKeys.Control | ModifierKeys.Shift))
        {
            e.Handled = true;
            SaveAll_Click(sender, new RoutedEventArgs());
        }
        else if (e.Key == Key.W &&
                 Keyboard.Modifiers == ModifierKeys.Control &&
                 EditorTabs.SelectedItem is TabItem tab &&
                 openFiles.ContainsKey(tab))
        {
            e.Handled = true;
            CloseEditorTab(tab);
        }
    }
}
