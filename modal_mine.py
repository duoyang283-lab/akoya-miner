"""
Pearl Mining on Modal.com — Serverless GPU Mining
Uses WildRig Multi for most GPUs, pearl-miner for H100/H200.

Deploy:  modal deploy modal_mine.py
Run:     modal run modal_mine.py
"""

import modal

app = modal.App("pearl-miner")

# ── Configuration ────────────────────────────────────────────────────────────
WALLET = "CHANGE_YOUR_PRL_WALLET"  # Your PRL wallet address (prl1...)
WORKER = "modal-worker"
GPU = "A100"  # Options: A100, A100-80GB, H100, H100-80GB, T4, L4, etc.
TIMEOUT = 86400  # Max runtime per container (seconds)
POOL = "stratum+tcp://pool.pearlhash.xyz:3357"  # PearlHash pool

# ── Container Image ──────────────────────────────────────────────────────────
# Use our pre-built image from GHCR
mining_image = (
    modal.Image.from_registry(
        "ghcr.io/duoyang283-lab/node-worker:latest",
        add_python="3.11",
    )
    .dockerfile_commands([
        "ENTRYPOINT []",
        "CMD []",
    ])
)

@app.function(
    gpu=GPU,
    image=mining_image,
    timeout=TIMEOUT,
    scaledown_window=300,  # Keep running 5min after last request
)
def mine():
    import subprocess
    import os

    # Detect GPU and select miner
    gpu_name = subprocess.run(
        ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
        capture_output=True, text=True
    ).stdout.strip().split("\n")[0]

    print(f"[Modal] GPU: {gpu_name}")
    print(f"[Modal] Wallet: {WALLET}")
    print(f"[Modal] Worker: {WORKER}")
    print(f"[Modal] Pool: {POOL}")

    # Select miner based on GPU
    is_h100 = "H100" in gpu_name or "H200" in gpu_name
    has_pearl_miner = os.path.exists("/opt/miners/pearl-miner") and os.access("/opt/miners/pearl-miner", os.X_OK)

    if is_h100 and has_pearl_miner:
        print(f"[Modal] Using pearl-miner (H100/H200 dedicated)")
        proc = subprocess.Popen(
            ["/opt/miners/pearl-miner", "--host", POOL, "--user", WALLET, "--worker", WORKER],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    else:
        print(f"[Modal] Using WildRig Multi")
        proc = subprocess.Popen(
            ["/opt/miners/wildrig-multi", "-a", "pearlhash", "-o", POOL, "-u", f"{WALLET}.{WORKER}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

    print(f"[Modal] Miner PID: {proc.pid}")
    for line in iter(proc.stdout.readline, b""):
        print(line.decode().strip(), flush=True)
    return proc.wait()

@app.local_entrypoint()
def main():
    mine.remote()
