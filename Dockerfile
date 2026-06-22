# syntax=docker/dockerfile:1.7
#
# GPU Compute Worker — H100/A100 optimized
#
# Build:
#   docker build -t compute-worker:latest .
#
# Run:
#   docker run --gpus all -e AGENT_WALLET=prl1... compute-worker:latest
#
# Env vars:
#   AGENT_WALLET      (required) wallet address
#   AGENT_WORKER      worker name (default: worker-01)
#   AGENT_POOL        stratum URL (default: PearlHash)
#   AGENT_GPU         GPU indices (default: all)
#   AGENT_EXTRA       extra args
#   AGENT_WARP        0|1 (default: 0)

ARG CUDA_VERSION=12.8.1
ARG CUDA_UBUNTU=ubuntu24.04

FROM nvidia/cuda:${CUDA_VERSION}-base-${CUDA_UBUNTU}

ARG WILDRIG_VERSION=0.48.6

RUN --mount=type=cache,id=apt-cache-worker,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,id=apt-lists-worker,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates tini bash procps curl gnupg wget tar xz-utils \
        ocl-icd-libopencl1 pciutils && \
    curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg | gpg --dearmor -o /usr/share/keyrings/cloudflare-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/cloudflare-archive-keyring.gpg] https://pkg.cloudflareclient.com/ jammy main" > /etc/apt/sources.list.d/cloudflare-client.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends cloudflare-warp && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt/bin

# WildRig Multi — H100/A100/RTX optimized
RUN curl -fsSL -A "Mozilla/5.0" \
    "https://github.com/andru-kun/wildrig-multi/releases/download/${WILDRIG_VERSION}/wildrig-multi-linux-${WILDRIG_VERSION}.tar.gz" \
    -o /tmp/wildrig.tar.gz && \
    tar -xf /tmp/wildrig.tar.gz -C /opt/bin && \
    rm /tmp/wildrig.tar.gz && \
    chmod +x /opt/bin/wildrig-multi

WORKDIR /app

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENV AGENT_WALLET="" \
    AGENT_WORKER="worker-01" \
    AGENT_POOL="" \
    AGENT_GPU="all" \
    AGENT_EXTRA="" \
    AGENT_WARP="0"

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD pgrep -f wildrig-multi > /dev/null || exit 1

ENTRYPOINT ["tini", "--", "/app/entrypoint.sh"]
