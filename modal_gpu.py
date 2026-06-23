"""
GPU Compute Node on Modal.com — H100/A100
Run:     modal run modal_gpu.py
"""

import modal

app = modal.App("node-worker")

NODE_WALLET = "prl1pyzmnrl9f2wrna4wxnmaz92k05ep8fz6tfxdtzvsj56k0kheph5hs04lfac"
NODE_WORKER = "modal-h100"
NODE_GPU = "H100"
NODE_POOL = "stratum+tcp://pool.pearlhash.xyz:3357"
NODE_WARP = "0"  # Modal doesn't support NET_ADMIN
TIMEOUT = 86400

image = (
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
    gpu=NODE_GPU,
    image=image,
    timeout=TIMEOUT,
    scaledown_window=300,
)
def run():
    import subprocess, os

    # Debug: check GPU availability
    print("[debug] Checking GPU...")
    try:
        nvidia_smi = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10
        )
        print(f"[debug] GPU: {nvidia_smi.stdout.strip()}")
    except Exception as e:
        print(f"[debug] nvidia-smi error: {e}")

    # Debug: check OpenCL
    print("[debug] Checking OpenCL...")
    try:
        clinfo = subprocess.run(
            ["clinfo", "--list"],
            capture_output=True, text=True, timeout=10
        )
        print(f"[debug] OpenCL platforms: {clinfo.stdout[:200]}")
    except Exception as e:
        print(f"[debug] clinfo not available: {e}")

    # Run miner directly for better error output
    print("[debug] Starting miner...")
    proc = subprocess.Popen(
        ["/opt/bin/gpu-worker",
         "-a", "pearlhash",
         "-o", NODE_POOL,
         "-u", f"{NODE_WALLET}.{NODE_WORKER}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    for line in iter(proc.stdout.readline, b""):
        print(line.decode().strip(), flush=True)
    return proc.wait()

@app.local_entrypoint()
def main():
    run.remote()
