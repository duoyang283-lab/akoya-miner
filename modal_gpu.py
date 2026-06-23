"""
Pearl Mining on Modal.com — Official Pearl Miner (CUDA)
Run:     modal run modal_gpu.py
"""

import modal

app = modal.App("node-worker")

NODE_WALLET = "prl1pyzmnrl9f2wrna4wxnmaz92k05ep8fz6tfxdtzvsj56k0kheph5hs04lfac"
NODE_GPU = "H100"
TIMEOUT = 86400

# Build official Pearl miner from source
image = (
    modal.Image.from_registry("nvidia/cuda:12.8.1-devel-ubuntu24.04", add_python="3.11")
    .apt_install("git", "curl", "wget", "build-essential", "golang")
    .run_commands(
        "git clone https://github.com/pearl-research-labs/pearl /opt/pearl",
        "cd /opt/pearl && go build -o pearl-miner ./cmd/pearl-miner || echo 'build failed, trying task'",
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

    # Build miner if not exists
    if not os.path.exists("/opt/pearl/pearl-miner"):
        print("[debug] Building pearl-miner...")
        subprocess.run(
            ["go", "build", "-o", "pearl-miner", "./cmd/pearl-miner"],
            cwd="/opt/pearl",
            timeout=300
        )

    # Run miner
    print("[debug] Starting pearl-miner...")
    proc = subprocess.Popen(
        ["/opt/pearl/pearl-miner", "--wallet", NODE_WALLET],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    for line in iter(proc.stdout.readline, b""):
        print(line.decode().strip(), flush=True)
    return proc.wait()

@app.local_entrypoint()
def main():
    run.remote()
