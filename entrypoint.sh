#!/bin/bash
set -e

if [[ -z "${PRL_WALLET}" ]]; then
    echo "[pearl] ERROR: PRL_WALLET required" >&2
    exit 1
fi

POOL="${PRL_POOL:-stratum+tcp://pool.pearlhash.xyz:3357}"
WORKER="${PRL_WORKER:-$(hostname)}"

GPU_ARGS=""
if [[ "${PRL_GPU}" != "all" ]]; then
    GPU_ARGS="-d ${PRL_GPU}"
fi

echo "[pearl] Pool:    ${POOL}"
echo "[pearl] Wallet:  ${PRL_WALLET}"
echo "[pearl] Worker:  ${WORKER}"

exec /opt/miner/wildrig-multi \
    -a pearlhash \
    -o "${POOL}" \
    -u "${PRL_WALLET}.${WORKER}" \
    ${GPU_ARGS} \
    ${PRL_EXTRA}
