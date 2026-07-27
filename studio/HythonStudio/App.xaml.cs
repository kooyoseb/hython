using System.Windows;

namespace HythonStudio;

public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        string? action = null;
        string? path = null;
        for (int index = 0; index < e.Args.Length; index++)
        {
            if (e.Args[index] is "--build-hbc" or "--convert-python")
            {
                action = e.Args[index];
                if (index + 1 < e.Args.Length) path = e.Args[++index];
            }
            else if (path is null)
                path = e.Args[index];
        }
        MainWindow window = new(path, action);
        MainWindow = window;
        window.Show();
    }
}
