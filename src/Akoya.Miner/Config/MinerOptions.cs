// Strongly-typed V2 miner configuration.
//
// All values are derived from environment variables by EnvVarBindings.
// The record is immutable after construction; nothing in the runtime mutates
// MinerOptions, which is what lets us pass it to background threads without
// locking.
//
// V2 deliberately does NOT include any of the deprecated v1 vars
// (NW_POOL_RECONNECT_*, NW_POOL_FIRST_JOB_*, NW_POOL_SHARE_STARVATION_*,
// NW_GATEWAY_*). Those still parse from the environment but only produce
// a deprecation warning — see EnvVarBindings.WarnOnDeprecated.

namespace Akoya.Miner.Config;

/// <summary>Pool / gRPC connection parameters.</summary>
internal sealed record PoolOptions(
    string Host,
    int Port,
    bool UseTls,
    bool TlsInsecure,
    string WalletAddress,
    string WorkerName,
    int PingIntervalSec,
    int HeartbeatIntervalSec,
    int StreamWatchdogSec,
    int KeepAlivePingSec,
    int KeepAliveTimeoutSec,
    int PongTimeoutSec,
    int OutboundDepthTrip);

/// <summary>
/// GEMM / mining-loop parameters. Names + defaults match v1 1:1 — these are
/// the NW_MINE_* env vars that production HiveOS deployments set.
/// </summary>
internal sealed record MineOptions(
    int M,
    int N,
    int K,
    int NoiseRank,
    int MatmulsPerPoll,
    int MaxBlocks,
    double StatsIntervalSec,
    int WatchdogTimeoutSec,
    int TriggerWatchdogSec,
    bool FakeTarget,
    int BenchmarkDurationSec,
    bool DisablePong,
    bool ShapeOverridePresent = false,
    bool CudaGraphIter = false,
    bool CudaGraphRequired = false);

/// <summary>
/// GPU enumeration / selection. <c>IndicesRaw</c> is the raw value of
/// <c>NW_GPU_INDICES</c> (or legacy <c>NW_GPU_INDEX</c>): "all" or
/// comma-separated 0-based indices. Parsed into a concrete list by
/// WorkerOrchestrator once we know the device count.
/// </summary>
internal sealed record GpuOptions(string IndicesRaw);

/// <summary>Logging + observability.</summary>
internal sealed record ObservabilityOptions(
    string LogLevel,
    bool LogJson,
    int? MetricsPort,
    string HiveOsStatsPath);

/// <summary>
/// Session persistence. <c>FilePath</c> defaults to
/// <c>$HOME/.nw/session.json</c> (or
/// <c>/root/.nw/session.json</c> in container envs without $HOME).
/// </summary>
internal sealed record SessionOptions(string FilePath);

/// <summary>Aggregate root.</summary>
internal sealed record MinerOptions(
    PoolOptions Pool,
    MineOptions Mine,
    GpuOptions Gpus,
    ObservabilityOptions Observability,
    SessionOptions Session);
