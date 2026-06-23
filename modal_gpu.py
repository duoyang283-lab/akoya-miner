"""
Pearl Mining on Modal.com — Debug Build
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
    )
)

@app.function(
    gpu=NODE_GPU,
    image=image,
    timeout=TIMEOUT,
    scaledown_window=300,
)
def run():
    import subprocess, os

    # Check GPU
    print("[debug] Checking GPU...")
    nvidia_smi = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,compute_cap,memory.total", "--format=csv,noheader"],
        capture_output=True, text=True, timeout=10
    )
    print(f"[debug] GPU: {nvidia_smi.stdout.strip()}")

    # Check if repo exists
    print("[debug] Checking /opt/pearl...")
    if os.path.exists("/opt/pearl"):
        print(f"[debug] /opt/pearl exists, contents: {os.listdir('/opt/pearl')[:10]}")
    else:
        print("[debug] /opt/pearl does not exist!")
        return 1

    # Check py-pearl-mining
    py_mining_path = "/opt/pearl/py-pearl-mining"
    if os.path.exists(py_mining_path):
        print(f"[debug] {py_mining_path} exists")
        print(f"[debug] Contents: {os.listdir(py_mining_path)}")
    else:
        print(f"[debug] {py_mining_path} does not exist!")
        return 1

    # Try to build
    print("[debug] Building py-pearl-mining...")
    result = subprocess.run(
        ["pip", "install", "maturin"],
        capture_output=True, text=True, timeout=60
    )
    print(f"[debug] maturin install: {result.returncode}")

    result = subprocess.run(
        ["maturin", "develop", "--release"],
        cwd=py_mining_path,
        capture_output=True, text=True, timeout=300
    )
    print(f"[debug] maturin build: {result.returncode}")
    if result.stdout:
        print(f"[debug] stdout: {result.stdout[:500]}")
    if result.stderr:
        print(f"[debug] stderr: {result.stderr[:500]}")

    # Try import
    try:
        import pearl_mining
        print(f"[debug] pearl_mining imported successfully!")
        print(f"[debug] dir: {dir(pearl_mining)}")
    except ImportError as e:
        print(f"[debug] Import failed: {e}")

    return 0

@app.local_entrypoint()
def main():
    run.remote()
