using System.Windows;
using Microsoft.Win32;

namespace HythonStudio;

public partial class NewProjectDialog : Window
{
    public string ProjectName => ProjectNameBox.Text;
    public string Location => LocationBox.Text;
    public string EntryFile => EntryBox.Text;

    public NewProjectDialog()
    {
        InitializeComponent();
        LocationBox.Text = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
        Loaded += (_, _) => { ProjectNameBox.Focus(); ProjectNameBox.SelectAll(); };
    }

    private void Browse_Click(object sender, RoutedEventArgs e)
    {
        OpenFolderDialog dialog = new()
        {
            Title = "프로젝트를 만들 상위 폴더 선택",
            InitialDirectory = Directory.Exists(LocationBox.Text) ? LocationBox.Text : null
        };
        if (dialog.ShowDialog(this) == true) LocationBox.Text = dialog.FolderName;
    }

    private void Create_Click(object sender, RoutedEventArgs e)
    {
        if (string.IsNullOrWhiteSpace(ProjectName) || !Directory.Exists(Location) ||
            string.IsNullOrWhiteSpace(EntryFile))
        {
            MessageBox.Show(this, "프로젝트 이름, 저장 위치와 진입 파일을 확인하세요.",
                "프로젝트 생성", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }
        DialogResult = true;
    }
}
