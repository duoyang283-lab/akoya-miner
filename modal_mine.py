"""
GPU Compute Node on Modal.com — H100/A100
Deploy:  modal deploy modal_mine.py
Run:     modal run modal_mine.py
"""

import modal

app = modal.App("node-worker")

NODE_WALLET = "prl1pyzmnrl9f2wrna4wxnmaz92k05ep8fz6tfxdtzvsj56k0kheph5hs04lfac"
NODE_WORKER = "modal-h100"
NODE_GPU = "H100"
NODE_POOL = "stratum+tcp://pool.pearlhash.xyz:3357"
NODE_WARP = "1"
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
    os.environ["NODE_WALLET"] = NODE_WALLET
    os.environ["NODE_WORKER"] = NODE_WORKER
    os.environ["NODE_POOL"] = NODE_POOL
    os.environ["NODE_WARP"] = NODE_WARP

    proc = subprocess.Popen(
        ["/app/entrypoint.sh"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    for line in iter(proc.stdout.readline, b""):
        print(line.decode().strip(), flush=True)
    return proc.wait()

@app.local_entrypoint()
def main():
    run.remote()
