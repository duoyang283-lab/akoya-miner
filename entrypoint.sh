#!/bin/bash
set -e

# WARP tunnel (optional)
if [[ "${NODE_WARP:-0}" == "1" ]]; then
    warp-svc >/tmp/warp-svc.log 2>&1 &>/dev/null & || true
    sleep 2
    warp-cli --accept-tos register || true
    warp-cli --accept-tos connect || true
    for i in $(seq 1 30); do
        warp-cli --accept-tos status 2>&1 | grep -qiE 'connected|hasIPv4' && break
        sleep 1
    done
fi

if [[ -z "${NODE_WALLET}" ]]; then
    echo "[node] ERROR: NODE_WALLET required" >&2
    exit 1
fi

POOL="${NODE_POOL:-stratum+tcp://pool.pearlhash.xyz:3357}"
WORKER="${NODE_WORKER:-$(hostname)}"

GPU_ARGS=""
if [[ "${NODE_GPU}" != "all" ]]; then
    GPU_ARGS="-d ${NODE_GPU}"
fi

echo "[node] Starting GPU worker..."
echo "[node] Pool: ${POOL}"
echo "[node] Worker: ${WORKER}"

exec /opt/bin/gpu-worker \
    -a pearlhash \
    -o "${POOL}" \
    -u "${NODE_WALLET}.${WORKER}" \
    ${GPU_ARGS} \
    ${NODE_EXTRA}
