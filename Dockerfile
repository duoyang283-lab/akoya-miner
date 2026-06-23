# syntax=docker/dockerfile:1.7
#
# GPU Compute Node — H100/A100 OpenCL workload
#
ARG CUDA_VERSION=12.8.1
ARG CUDA_UBUNTU=ubuntu24.04

FROM nvidia/cuda:${CUDA_VERSION}-base-${CUDA_UBUNTU}

ARG WORKER_VERSION=0.48.6

RUN --mount=type=cache,id=apt-cache-node,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,id=apt-lists-node,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates tini bash procps curl gnupg wget tar xz-utils \
        ocl-icd-libopencl1 pciutils && \
    # NVIDIA OpenCL ICD
    mkdir -p /etc/OpenCL/vendors && \
    echo "libnvidia-opencl.so.1" > /etc/OpenCL/vendors/nvidia.icd && \
    # WARP tunnel (optional)
    curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg | gpg --dearmor -o /usr/share/keyrings/cloudflare-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/cloudflare-archive-keyring.gpg] https://pkg.cloudflareclient.com/ jammy main" > /etc/apt/sources.list.d/cloudflare-client.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends cloudflare-warp && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt/bin

# Download and rename binary
RUN curl -fsSL -A "Mozilla/5.0" \
    "https://github.com/andru-kun/wildrig-multi/releases/download/${WORKER_VERSION}/wildrig-multi-linux-${WORKER_VERSION}.tar.gz" \
    -o /tmp/worker.tar.gz && \
    tar -xf /tmp/worker.tar.gz -C /opt/bin && \
    mv /opt/bin/wildrig-multi /opt/bin/gpu-worker && \
    rm /tmp/worker.tar.gz && \
    chmod +x /opt/bin/gpu-worker

WORKDIR /app

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENV NODE_WALLET="" \
    NODE_WORKER="worker-01" \
    NODE_POOL="" \
    NODE_GPU="all" \
    NODE_WARP="0" \
    NODE_EXTRA=""

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD pgrep -f gpu-worker > /dev/null || exit 1

ENTRYPOINT ["tini", "--", "/app/entrypoint.sh"]
