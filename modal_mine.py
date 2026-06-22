"""
GPU Compute Worker on Modal.com — H100/A100
Deploy:  modal deploy modal_mine.py
Run:     modal run modal_mine.py
"""

import modal

app = modal.App("gpu-worker")

WALLET = "prl1pyzmnrl9f2wrna4wxnmaz92k05ep8fz6tfxdtzvsj56k0kheph5hs04lfac"
WORKER = "modal-h100"
GPU = "H100"
TIMEOUT = 86400
POOL = "stratum+tcp://pool.pearlhash.xyz:3357"

worker_image = (
    modal.Image.from_registry(
        "ghcr.io/duoyang283-lab/compute-worker:latest",
        add_python="3.11",
    )
    .dockerfile_commands([
        "ENTRYPOINT []",
        "CMD []",
    ])
)

@app.function(
    gpu=GPU,
    image=worker_image,
    timeout=TIMEOUT,
    scaledown_window=300,
)
def run():
    import subprocess
    print(f"[worker] GPU: {GPU}")
    print(f"[worker] Wallet: {WALLET}")
    print(f"[worker] Worker: {WORKER}")
    print(f"[worker] Pool: {POOL}")

    proc = subprocess.Popen(
        ["/opt/bin/wildrig-multi", "-a", "pearlhash",
         "-o", POOL, "-u", f"{WALLET}.{WORKER}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    for line in iter(proc.stdout.readline, b""):
        print(line.decode().strip(), flush=True)
    return proc.wait()

@app.local_entrypoint()
def main():
    run.remote()
