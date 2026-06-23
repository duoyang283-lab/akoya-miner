"""
Pearl Mining on Modal.com — py-pearl-mining
Run:     modal run modal_gpu.py
"""

import modal

app = modal.App("node-worker")

NODE_GPU = "H100"
TIMEOUT = 86400

# Build from official Pearl repo
image = (
    modal.Image.from_registry("nvidia/cuda:12.8.1-devel-ubuntu24.04", add_python="3.12")
    .apt_install("git", "curl", "wget", "build-essential", "pkg-config", "libssl-dev")
    .run_commands(
        "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y",
        "git clone --depth 1 https://github.com/pearl-research-labs/pearl /opt/pearl",
    )
    .run_commands(
        "cd /opt/pearl && pip install maturin && cd py-pearl-mining && maturin develop --release",
        gpu="H100",
    )
)

@app.function(
    gpu=NODE_GPU,
    image=image,
    timeout=TIMEOUT,
    scaledown_window=300,
)
def run():
    import subprocess

    # Check GPU
    print("[debug] Checking GPU...")
    nvidia_smi = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,compute_cap,memory.total", "--format=csv,noheader"],
        capture_output=True, text=True, timeout=10
    )
    print(f"[debug] GPU: {nvidia_smi.stdout.strip()}")

    # Test py-pearl-mining
    print("[debug] Testing py-pearl-mining...")
    try:
        import pearl_mining
        print(f"[debug] pearl_mining version: {pearl_mining.__version__}")
        print(f"[debug] Available functions: {dir(pearl_mining)}")
    except ImportError as e:
        print(f"[debug] Import error: {e}")
        return 1

    # Run mining
    print("[debug] Starting mining...")
    # TODO: Add actual mining logic based on pearl_mining API
    print("[debug] Mining module loaded successfully!")
    return 0

@app.local_entrypoint()
def main():
    run.remote()
