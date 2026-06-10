// Bind environment variables to MinerOptions, with deprecation warnings for
// any v1-era NW_* var that has no V2 effect.
//
// Single entry point: EnvVarBindings.Load(log). This is the *only* place
// env vars are read at startup. The rest of the miner takes MinerOptions
// through DI.

using System.Globalization;
using Microsoft.Extensions.Logging;

namespace Akoya.Miner.Config;

internal static class EnvVarBindings
{
    /// <summary>
    /// v1 vars that production configs may still set but which V2 ignores.
    /// Each gets a one-line "[deprecated] X ignored in v2" warning at startup
    /// if present in the env. None block startup.
    /// </summary>
    private static readonly (string Var, string Reason)[] DeprecatedVars =
    {
        ("NW_GATEWAY_HOST",                         "no solo/gateway mode in V2"),
        ("NW_GATEWAY_PORT",                         "no solo/gateway mode in V2"),
        ("NW_POOL_FIRST_JOB_TIMEOUT_SEC",           "gRPC server-push delivers job; no race"),
        ("NW_POOL_FIRST_JOB_GIVE_UP_AFTER",         "gRPC server-push delivers job; no race"),
        ("NW_POOL_RECONNECT_BASE_SEC",              "gRPC channel handles reconnect backoff"),
        ("NW_POOL_RECONNECT_CAP_SEC",               "gRPC channel handles reconnect backoff"),
        ("NW_POOL_RECONNECT_INITIAL_JITTER_SEC",    "gRPC channel handles reconnect backoff"),
        ("NW_POOL_RECONNECT_MAX_WAIT_SEC",          "use ReconnectHint.wait_seconds from server"),
        ("NW_POOL_RECONNECT_MIN_INTERVAL_SEC",      "server-side concern in V2"),
        ("NW_POOL_SHARE_STARVATION_SEC",            "v1 protocol workaround; not needed in V2"),
        ("NW_POOL_SHARE_STARVATION_COOLDOWN_SEC",   "v1 protocol workaround; not needed in V2"),
        ("NW_POOL_SHARE_STARVATION_DISABLE",        "v1 protocol workaround; not needed in V2"),
        ("NW_MINE_MAX_ITERS",                       "per-sigma iteration caps are disabled in V2"),
    };

    public static MinerOptions Load(ILogger log)
    {
        WarnOnDeprecated(log);

        // ---- Pool ---------------------------------------------------------
        // Default to the production V2 gateway. Operators can override via
        // NW_POOL_HOST (e.g. a self-hosted gateway). Port defaults to 443
        // when TLS is on (standard), 50052 plaintext otherwise (local dev).
        var host = Env("NW_POOL_HOST") ?? "pool-v2.nodepool.io";
        // NW_POOL_USE_TLS was used by the original packages and some
        // HiveOS flight sheets. Keep it as a compatibility alias while the
        // canonical current name remains NW_POOL_TLS.
        var tls = ParseBool(Env("NW_POOL_TLS") ?? Env("NW_POOL_USE_TLS"), defaultValue: true);
        int port = ParseInt(Env("NW_POOL_PORT"), defaultValue: tls ? 443 : 50052);

        var wallet = Env("NW_POOL_WALLET")
                     ?? throw new InvalidOperationException("NW_POOL_WALLET is required");
        var worker = Env("NW_POOL_WORKER") ?? Environment.MachineName;

        var pool = new PoolOptions(
            Host: host,
            Port: port,
            UseTls: tls,
            TlsInsecure: ParseBool(Env("NW_POOL_TLS_INSECURE"), defaultValue: false),
            WalletAddress: wallet,
            WorkerName: worker,
            PingIntervalSec:      ParseInt(Env("NW_POOL_PING_INTERVAL_SEC"), 15),
            HeartbeatIntervalSec: ParseInt(Env("NW_POOL_HEARTBEAT_INTERVAL_SEC"), 30),
            StreamWatchdogSec:    ParseInt(Env("NW_POOL_STREAM_WATCHDOG_SEC"), 90),
            KeepAlivePingSec:     Math.Max(1, ParseInt(Env("NW_POOL_KEEPALIVE_PING_SEC"), 10)),
            KeepAliveTimeoutSec:  Math.Max(1, ParseInt(Env("NW_POOL_KEEPALIVE_TIMEOUT_SEC"), 10)),
            PongTimeoutSec:       ParseInt(Env("NW_POOL_PONG_TIMEOUT_SEC"), 20),
            OutboundDepthTrip:    ParseInt(Env("NW_POOL_OUTBOUND_DEPTH_TRIP"), 16));

        // ---- Mining loop (defaults match v1 1:1) --------------------------
        //
        // NOTE: MatmulsPerPoll is no longer user-configurable. It's derived
        // at startup from the hashrate benchmark so the trigger-detection
        // latency is bounded to ~10ms regardless of GPU class
        // (see WorkerOrchestrator). We seed it here with a probe value
        // (10) which the benchmark uses internally and then overwrites.
        //
        // Similarly the benchmark is mandatory — there is no NW_BENCH_DISABLE.
        // The pool's vardiff depends on us reporting a real hashrate, and we
        // need iter_ms to size the batch.
        var mine = new MineOptions(
            M:                 ParseInt(Env("NW_MINE_M"), 8192),
            N:                 ParseInt(Env("NW_MINE_N"), 32768),
            K:                 ParseInt(Env("NW_MINE_K"), 2048),
            NoiseRank:         ParseInt(Env("NW_MINE_NOISE_RANK"), 128),
            MatmulsPerPoll:    10, // probe value; overwritten post-benchmark
            MaxBlocks:         ParseInt(Env("NW_MINE_MAX_BLOCKS"), 0),
            StatsIntervalSec:  ParseDouble(Env("NW_MINE_STATS_INTERVAL_SEC"), 5.0),
            WatchdogTimeoutSec:ParseInt(Env("NW_MINE_WATCHDOG_TIMEOUT_SEC"), 300),
            TriggerWatchdogSec:ParseInt(Env("NW_MINE_TRIGGER_WATCHDOG_SEC"), 300),
            FakeTarget:        Env("NW_FAKE_TARGET") == "1",
            BenchmarkDurationSec:ParseInt(Env("NW_BENCH_DURATION_SEC"), 10),
            // Emergency switch: force single-stream (V1-equivalent) mining
            // when set. Disables the Ping/Pong concurrent-stream double-buffer
            // so every batch runs sequentially on one CUDA stream. Use this
            // if you observe bursty `claimedHash > liveTarget` pre-submit
            // skips clustered in a single σ window — a symptom that points
            // to a concurrent-stream state hazard. Defaults off (full perf).
            DisablePong:       ParseBool(Env("NW_DISABLE_PONG"), defaultValue: false),
            ShapeOverridePresent: MineShapeOverridePresent(),
            CudaGraphIter:     ParseBool(Env("NW_CUDA_GRAPH_ITER"), defaultValue: false),
            CudaGraphRequired: ParseBool(Env("NW_CUDA_GRAPH_REQUIRED"), defaultValue: false));

        // ---- GPUs ---------------------------------------------------------
        var gpus = new GpuOptions(
            IndicesRaw: Env("NW_GPU_INDICES")
                        ?? Env("NW_GPU_INDEX")   // legacy single-GPU fallback
                        ?? "all");

        // ---- Observability ------------------------------------------------
        var obs = new ObservabilityOptions(
            LogLevel:        Env("NW_LOG_LEVEL") ?? "Information",
            LogJson:         ParseBool(Env("NW_LOG_JSON"), defaultValue: false),
            MetricsPort:     int.TryParse(Env("NW_METRICS_PORT"), NumberStyles.Integer, CultureInfo.InvariantCulture, out var mp) ? mp : null,
            HiveOsStatsPath: Env("NW_HIVEOS_STATS_PATH") ?? "/run/hive/node-worker-stats.json");

        // ---- Session ------------------------------------------------------
        var sess = new SessionOptions(
            FilePath: Env("NW_SESSION_FILE") ?? DefaultSessionPath());

        return new MinerOptions(pool, mine, gpus, obs, sess);
    }

    private static void WarnOnDeprecated(ILogger log)
    {
        foreach (var (name, reason) in DeprecatedVars)
        {
            if (!string.IsNullOrEmpty(Environment.GetEnvironmentVariable(name)))
            {
                log.LogWarning("[deprecated] {Var} ignored in v2 ({Reason})", name, reason);
            }
        }
    }

    private static string DefaultSessionPath()
    {
        // Prefer $HOME; fall back to /root in containers where HOME may be unset.
        var home = Environment.GetEnvironmentVariable("HOME");
        if (string.IsNullOrEmpty(home))
        {
            home = Environment.OSVersion.Platform == PlatformID.Win32NT
                ? Environment.GetFolderPath(Environment.SpecialFolder.UserProfile)
                : "/root";
        }
        return Path.Combine(home, ".nw", "session.json");
    }

    private static string? Env(string name)
    {
        var v = Environment.GetEnvironmentVariable(name);
        return string.IsNullOrEmpty(v) ? null : v;
    }

    private static bool MineShapeOverridePresent()
        => Env("NW_MINE_M") is not null
           || Env("NW_MINE_N") is not null
           || Env("NW_MINE_K") is not null
           || Env("NW_MINE_NOISE_RANK") is not null;

    private static int ParseInt(string? raw, int defaultValue)
        => int.TryParse(raw, NumberStyles.Integer, CultureInfo.InvariantCulture, out var v) ? v : defaultValue;

    private static double ParseDouble(string? raw, double defaultValue)
        => double.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out var v) ? v : defaultValue;

    private static bool ParseBool(string? raw, bool defaultValue) => raw switch
    {
        null      => defaultValue,
        "1"       => true,
        "0"       => false,
        var s when s.Equals("true",  StringComparison.OrdinalIgnoreCase) => true,
        var s when s.Equals("false", StringComparison.OrdinalIgnoreCase) => false,
        _         => defaultValue,
    };
}
