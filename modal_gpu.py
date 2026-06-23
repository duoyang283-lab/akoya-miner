"""
Pearl Mining on Modal.com — Test mine function
Run:     modal run modal_gpu.py
"""

import modal

app = modal.App("node-worker")

NODE_GPU = "H100"
TIMEOUT = 86400

image = (
    modal.Image.from_registry("nvidia/cuda:12.8.1-devel-ubuntu24.04", add_python="3.12")
    .apt_install("git", "curl", "wget", "build-essential", "pkg-config", "libssl-dev")
    .run_commands(
        "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y",
    )
    .env({"PATH": "/root/.cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"})
    .run_commands(
        "pip install maturin",
        "git clone --depth 1 https://github.com/pearl-research-labs/pearl /opt/pearl",
        "cd /opt/pearl/py-pearl-mining && maturin build --release",
    )
    .run_commands(
        "cd /opt/pearl/py-pearl-mining && pip install target/wheels/*.whl",
    )
)

@app.function(
    gpu=NODE_GPU,
    image=image,
    timeout=TIMEOUT,
    scaledown_window=300,
)
def run():
    import sys
    sys.stdout.flush()
    
    print("[debug] Starting...", flush=True)
    
    import subprocess
    nvidia_smi = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,compute_cap,memory.total", "--format=csv,noheader"],
        capture_output=True, text=True, timeout=10
    )
    print(f"[debug] GPU: {nvidia_smi.stdout.strip()}", flush=True)
    
    print("[debug] Importing pearl_mining...", flush=True)
    import pearl_mining as pm
    print(f"[debug] pearl_mining version: {pm.__version__}", flush=True)
    
    print("[debug] Creating block header...", flush=True)
    header = pm.IncompleteBlockHeader(
        version=1,
        prev_block=bytes(32),
        merkle_root=bytes(32),
        timestamp=0,
        nbits=0x207FFFFF,
    )
    print("[debug] Header created", flush=True)
    
    print("[debug] Creating mining config...", flush=True)
    k = 1024
    rank = 32
    rows_pattern = pm.PeriodicPattern.from_list([0, 1, 2, 3])
    cols_pattern = pm.PeriodicPattern.from_list([0, 1, 2, 3])
    mining_config = pm.MiningConfiguration(
        common_dim=k,
        rank=rank,
        mma_type=pm.MMAType.Int7xInt7ToInt32,
        rows_pattern=rows_pattern,
        cols_pattern=cols_pattern,
        moe=None,
    )
    print("[debug] Config created", flush=True)
    
    print("[debug] Starting mine()...", flush=True)
    m, n = 128, 128
    import time
    start = time.time()
    
    try:
        proof = pm.mine(m, n, k, header, mining_config)
        elapsed = time.time() - start
        print(f"[debug] Mining done in {elapsed:.2f}s", flush=True)
        print(f"[debug] Proof: {proof}", flush=True)
    except Exception as e:
        print(f"[debug] Error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return 1
    
    print("[debug] Done!", flush=True)
    return 0

@app.local_entrypoint()
def main():
    run.remote()
