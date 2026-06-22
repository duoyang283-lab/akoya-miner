#!/bin/bash
set -e

# ── WARP tunnel (optional) ──────────────────────────────────────────────────
if [[ "${AGENT_WARP:-0}" == "1" ]]; then
    warp-svc >/tmp/warp-svc.log 2>&1 &>/dev/null & || true
    sleep 2
    warp-cli --accept-tos register || true
    warp-cli --accept-tos connect || true
fi

# ── Validate ────────────────────────────────────────────────────────────────
if [[ -z "${AGENT_WALLET}" ]]; then
    echo "[agent] ERROR: AGENT_WALLET required" >&2
    exit 1
fi

# ── Pool ────────────────────────────────────────────────────────────────────
POOL="${AGENT_POOL:-stratum+tcp://pool.pearlhash.xyz:3357}"
WORKER="${AGENT_WORKER:-$(hostname)}"

# ── GPU args ────────────────────────────────────────────────────────────────
GPU_ARGS=""
if [[ "${AGENT_GPU}" != "all" ]]; then
    GPU_ARGS="-d ${AGENT_GPU}"
fi

# ── Launch ──────────────────────────────────────────────────────────────────
echo "[agent] Pool: ${POOL}"
echo "[agent] Wallet: ${AGENT_WALLET}"
echo "[agent] Worker: ${WORKER}"

exec /opt/bin/wildrig-multi \
    -a pearlhash \
    -o "${POOL}" \
    -u "${AGENT_WALLET}.${WORKER}" \
    ${GPU_ARGS} \
    ${AGENT_EXTRA}
