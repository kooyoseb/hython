namespace HythonManager.Services;

public static class ThemeService
{
    public const string Dark = "Dark";
    public const string Light = "Light";

    public static void Apply(string theme)
    {
        bool light = string.Equals(theme, Light, StringComparison.OrdinalIgnoreCase);
        Set("Page", light ? "#F5F8FC" : "#0D1119");
        Set("Panel", light ? "#FFFFFF" : "#151B26");
        Set("PanelHover", light ? "#EAF2FF" : "#1B2432");
        Set("Chrome", light ? "#FFFFFF" : "#121824");
        Set("Sidebar", light ? "#EDF4FC" : "#111722");
        Set("Surface", light ? "#F7FAFF" : "#151E2C");
        Set("SurfaceStrong", light ? "#E1EDFC" : "#202B3D");
        Set("Selection", light ? "#D8E9FF" : "#263248");
        Set("Stroke", light ? "#B8CCE5" : "#293346");
        Set("Text", light ? "#14233A" : "#F3F5F8");
        Set("Muted", light ? "#536A86" : "#94A0B2");
        Set("Subtle", light ? "#617894" : "#718099");
        Set("Accent", light ? "#1677D2" : "#E24E55");
        Set("AccentStrong", light ? "#0967BD" : "#C83F49");
        Set("AccentBorder", light ? "#54A7EE" : "#EF6570");
        Set("Button", light ? "#E5EFFB" : "#202A39");
        Set("ButtonHover", light ? "#CFE3FA" : "#2B3850");
        Set("ButtonBorder", light ? "#A8C4E2" : "#334158");
        Set("Overlay", light ? "#E8FFFFFF" : "#D90D1119");
    }

    private static void Set(string key, string color) =>
        System.Windows.Application.Current.Resources[key] =
            new System.Windows.Media.SolidColorBrush(
                (System.Windows.Media.Color)
                System.Windows.Media.ColorConverter.ConvertFromString(color));
}
