#!/bin/bash
set -e

# ── Cloudflare WARP (optional) ──────────────────────────────────────────────
if [[ "${NW_WARP:-0}" == "1" ]]; then
    echo "[entrypoint] Starting Cloudflare WARP..."
    warp-svc >/tmp/warp-svc.log 2>&1 &>/dev/null & || true
    sleep 2
    warp-cli --accept-tos register || true
    warp-cli --accept-tos connect || true
    for i in $(seq 1 30); do
        if warp-cli --accept-tos status 2>&1 | grep -qiE 'connected|hasIPv4'; then
            echo "[entrypoint] WARP connected"
            break
        fi
        sleep 1
    done
fi

# ── Validate wallet ─────────────────────────────────────────────────────────
if [[ -z "${NW_WALLET}" ]]; then
    echo "[entrypoint] ERROR: NW_WALLET is required. Set it to your PRL wallet address." >&2
    exit 1
fi

# ── Pool selection ──────────────────────────────────────────────────────────
# PearlHash endpoints: auto-select by region, or use NW_POOL override
if [[ -n "${NW_POOL}" ]]; then
    POOL_URL="${NW_POOL}"
else
    # Default PearlHash stratum (Americas/Europe)
    POOL_URL="stratum+tcp://pool.pearlhash.xyz:3357"
fi

# ── Miner selection ─────────────────────────────────────────────────────────
select_miner() {
    local forced="${NW_MINER:-auto}"
    case "$forced" in
        wildrig) echo "wildrig"; return ;;
        pearl)   echo "pearl"; return ;;
        auto)    ;;
        *)       echo "[entrypoint] Invalid NW_MINER=$forced" >&2; exit 64 ;;
    esac

    # Auto-detect: use pearl-miner for H100/H200, wildrig for everything else
    local gpu_name
    gpu_name=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1) || true
    if [[ "$gpu_name" == *H100* ]] || [[ "$gpu_name" == *H200* ]]; then
        echo "pearl"
    else
        echo "wildrig"
    fi
}

MINER=$(select_miner)

# ── GPU list ────────────────────────────────────────────────────────────────
GPU_ARGS=""
if [[ "${NW_GPU_INDICES}" != "all" ]]; then
    GPU_ARGS="-d ${NW_GPU_INDICES}"
fi

# ── Launch miner ────────────────────────────────────────────────────────────
WORKER="${NW_WORKER:-$(hostname)}"

if [[ "$MINER" == "pearl" ]]; then
    echo "[entrypoint] Using pearl-miner (H100/H200 dedicated)"
    echo "[entrypoint] Pool: ${POOL_URL}"
    echo "[entrypoint] Wallet: ${NW_WALLET}"
    echo "[entrypoint] Worker: ${WORKER}"
    exec /opt/miners/pearl-miner \
        --host "${POOL_URL}" \
        --user "${NW_WALLET}" \
        --worker "${WORKER}" \
        ${NW_EXTRA_ARGS}
else
    echo "[entrypoint] Using WildRig Multi"
    echo "[entrypoint] Pool: ${POOL_URL}"
    echo "[entrypoint] Wallet: ${NW_WALLET}"
    echo "[entrypoint] Worker: ${WORKER}"
    echo "[entrypoint] Algo: ${NW_ALGO:-pearlhash}"
    exec /opt/miners/wildrig-multi \
        -a "${NW_ALGO:-pearlhash}" \
        -o "${POOL_URL}" \
        -u "${NW_WALLET}.${WORKER}" \
        ${GPU_ARGS} \
        ${NW_EXTRA_ARGS}
fi
