"""
Pearl Mining on Modal.com — Continuous Mining
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
    import pearl_mining as pm
    import time, hashlib, struct

    print("[miner] Starting Pearl mining on H100...", flush=True)
    
    # Mining config
    k = 1024
    rank = 32
    m, n = 128, 128
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
    
    count = 0
    start = time.time()
    
    while True:
        # Generate unique block header each iteration
        timestamp = int(time.time())
        nonce = struct.pack('<Q', count)
        prev_hash = hashlib.sha256(nonce).digest()
        merkle_root = hashlib.sha256(prev_hash + nonce).digest()
        
        header = pm.IncompleteBlockHeader(
            version=1,
            prev_block=prev_hash,
            merkle_root=merkle_root,
            timestamp=timestamp,
            nbits=0x207FFFFF,
        )
        
        # Mine
        proof = pm.mine(m, n, k, header, mining_config)
        count += 1
        
        # Stats every 100 proofs
        if count % 100 == 0:
            elapsed = time.time() - start
            rate = count / elapsed
            print(f"[miner] Proofs: {count} | Rate: {rate:.1f}/s | Time: {elapsed:.1f}s", flush=True)
    
    return 0

@app.local_entrypoint()
def main():
    run.remote()
