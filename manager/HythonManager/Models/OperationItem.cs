using System.ComponentModel;
using System.Runtime.CompilerServices;

namespace HythonManager.Models;

public enum OperationState
{
    Waiting, Downloading, Paused, Installing, Repairing,
    Completed, Failed, RebootRequired
}

public sealed class OperationItem : INotifyPropertyChanged
{
    private double progress;
    private OperationState state = OperationState.Waiting;
    private string detail = "대기 중";
    private bool canPause;

    public required Guid Id { get; init; }
    public required ProductInfo Product { get; init; }
    public string ProductName => Product.Name;
    public double Progress { get => progress; set => Set(ref progress, value); }
    public OperationState State { get => state; set { Set(ref state, value); OnChanged(nameof(StateText)); } }
    public string Detail { get => detail; set => Set(ref detail, value); }
    public bool CanPause { get => canPause; set => Set(ref canPause, value); }
    public bool IsPaused => State == OperationState.Paused;
    public string StateText => State switch
    {
        OperationState.Waiting => "대기",
        OperationState.Downloading => "다운로드",
        OperationState.Paused => "일시정지",
        OperationState.Installing => "설치",
        OperationState.Repairing => "복구",
        OperationState.Completed => "완료",
        OperationState.Failed => "실패",
        OperationState.RebootRequired => "재부팅 필요",
        _ => State.ToString()
    };

    internal ManualResetEventSlim PauseGate { get; } = new(true);
    internal CancellationTokenSource Cancellation { get; } = new();
    public event PropertyChangedEventHandler? PropertyChanged;

    public void Pause()
    {
        if (!CanPause || IsPaused) return;
        PauseGate.Reset();
        State = OperationState.Paused;
        Detail = "사용자가 다운로드를 일시정지했습니다.";
    }

    public void Resume()
    {
        if (!IsPaused) return;
        PauseGate.Set();
        State = OperationState.Downloading;
        Detail = "다운로드를 재개했습니다.";
    }

    private void Set<T>(ref T field, T value, [CallerMemberName] string? name = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value)) return;
        field = value;
        OnChanged(name);
    }
    private void OnChanged([CallerMemberName] string? name = null) =>
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}
