# syntax=docker/dockerfile:1.7
#
# Pearl Miner — WildRig Multi on CUDA base (H100/A100)
#
# Build:  docker build -t pearl-miner:latest .
# Run:    docker run --gpus all -e PRL_WALLET=prl1... pearl-miner:latest
#
# Env:
#   PRL_WALLET   (required) PRL wallet address
#   PRL_WORKER   worker name (default: worker-01)
#   PRL_POOL     stratum URL (default: PearlHash)
#   PRL_GPU      GPU indices (default: all)
#   PRL_EXTRA    extra args for wildrig

ARG CUDA_VERSION=12.8.1
ARG CUDA_UBUNTU=ubuntu24.04

FROM nvidia/cuda:${CUDA_VERSION}-base-${CUDA_UBUNTU}

ARG WILDRIG_VERSION=0.48.6

RUN --mount=type=cache,id=apt-cache-prl,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,id=apt-lists-prl,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates tini bash procps curl gnupg wget tar xz-utils \
        ocl-icd-libopencl1 pciutils && \
    # Create NVIDIA OpenCL ICD file manually
    mkdir -p /etc/OpenCL/vendors && \
    echo "libnvidia-opencl.so.1" > /etc/OpenCL/vendors/nvidia.icd && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt/miner

# WildRig Multi 0.48.6 — Pearl hash, 0% dev-fee, H100/A100/RTX optimized
RUN curl -fsSL -A "Mozilla/5.0" \
    "https://github.com/andru-kun/wildrig-multi/releases/download/${WILDRIG_VERSION}/wildrig-multi-linux-${WILDRIG_VERSION}.tar.gz" \
    -o /tmp/wildrig.tar.gz && \
    tar -xf /tmp/wildrig.tar.gz -C /opt/miner && \
    rm /tmp/wildrig.tar.gz && \
    chmod +x /opt/miner/wildrig-multi

WORKDIR /app

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENV PRL_WALLET="" \
    PRL_WORKER="worker-01" \
    PRL_POOL="" \
    PRL_GPU="all" \
    PRL_EXTRA=""

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD pgrep -f wildrig-multi > /dev/null || exit 1

ENTRYPOINT ["tini", "--", "/app/entrypoint.sh"]
