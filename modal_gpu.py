"""
Pearl Mining on Modal.com — py-pearl-mining
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
        "git clone --depth 1 https://github.com/pearl-research-labs/pearl /opt/pearl",
        "cd /opt/pearl/py-pearl-mining && python -m venv .venv && . .venv/bin/activate && pip install maturin && maturin develop --release",
    )
)

@app.function(
    gpu=NODE_GPU,
    image=image,
    timeout=TIMEOUT,
    scaledown_window=300,
)
def run():
    import subprocess, os, sys

    # Check GPU
    print("[debug] Checking GPU...")
    nvidia_smi = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,compute_cap,memory.total", "--format=csv,noheader"],
        capture_output=True, text=True, timeout=10
    )
    print(f"[debug] GPU: {nvidia_smi.stdout.strip()}")

    # Add venv to path
    venv_path = "/opt/pearl/py-pearl-mining/.venv/lib/python3.12/site-packages"
    if venv_path not in sys.path:
        sys.path.insert(0, venv_path)

    # Try import
    try:
        import pearl_mining
        print(f"[debug] pearl_mining imported successfully!")
        print(f"[debug] dir: {dir(pearl_mining)}")
    except ImportError as e:
        print(f"[debug] Import failed: {e}")
        return 1

    return 0

@app.local_entrypoint()
def main():
    run.remote()
