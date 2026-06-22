# syntax=docker/dockerfile:1.7
#
# Pearl Mining Container — WildRig Multi + pearl-miner (H100/H200)
# Replaces the old Akoya GEMM-based miner with the new pearlhash algorithm.
#
# Build:
#   docker build -t node-worker:latest .
#
# Run:
#   docker run --gpus all -e NW_WALLET=prl1... node-worker:latest
#
# Supported env vars (all optional except NW_WALLET):
#   NW_WALLET        (required) PRL wallet address
#   NW_WORKER        worker name (default: docker)
#   NW_POOL          pool stratum URL (default: auto-select PearlHash endpoint)
#   NW_MINER         force miner: wildrig | pearl (default: auto-detect GPU)
#   NW_ALGO          algorithm (default: pearlhash)
#   NW_GPU_INDICES   GPU indices to use (default: all)
#   NW_EXTRA_ARGS    extra args passed to the miner
#   NW_WARP          enable Cloudflare WARP tunnel (default: 0)

ARG CUDA_VERSION=12.8.1
ARG CUDA_UBUNTU=ubuntu24.04

FROM nvidia/cuda:${CUDA_VERSION}-base-${CUDA_UBUNTU} AS final

ARG WILDRIG_VERSION=0.48.6

RUN --mount=type=cache,id=apt-cache-pearl-final,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,id=apt-lists-pearl-final,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates tini bash procps curl gnupg wget tar xz-utils && \
    # Cloudflare WARP (optional, activated by NW_WARP=1)
    # Use "jammy" as Cloudflare doesn't publish noble packages; jammy works on noble.
    curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg | gpg --dearmor -o /usr/share/keyrings/cloudflare-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/cloudflare-archive-keyring.gpg] https://pkg.cloudflareclient.com/ jammy main" > /etc/apt/sources.list.d/cloudflare-client.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends cloudflare-warp && \
    rm -rf /var/lib/apt/lists/*

# Install WildRig Multi
WORKDIR /opt/miners
RUN wget -q "https://github.com/andru-kun/wildrig-multi/releases/download/${WILDRIG_VERSION}/wildrig-multi-linux-${WILDRIG_VERSION}.tar.gz" -O wildrig.tar.gz && \
    tar -xf wildrig.tar.gz && \
    rm wildrig.tar.gz && \
    chmod +x wildrig-multi

# Install pearl-miner (H100/H200 dedicated, from PearlHash)
# Use curl with user-agent to avoid Cloudflare blocks in CI
RUN curl -fsSL -A "Mozilla/5.0" "https://pearlhash.xyz/downloads/pearl-miner-v12" -o /opt/miners/pearl-miner && \
    chmod +x /opt/miners/pearl-miner

WORKDIR /app

COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

ENV LD_LIBRARY_PATH=/usr/local/cuda/targets/x86_64-linux/lib \
    DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1 \
    NW_WALLET="" \
    NW_WORKER="docker" \
    NW_POOL="" \
    NW_MINER="auto" \
    NW_ALGO="pearlhash" \
    NW_GPU_INDICES="all" \
    NW_EXTRA_ARGS="" \
    NW_WARP="0"

EXPOSE 9100

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD pgrep -f 'wildrig-multi\|pearl-miner' > /dev/null || exit 1

ENTRYPOINT ["tini", "--", "/app/docker-entrypoint.sh"]
