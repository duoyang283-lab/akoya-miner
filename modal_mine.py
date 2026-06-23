"""
Pearl Miner on Modal.com — H100/A100
Deploy:  modal deploy modal_mine.py
Run:     modal run modal_mine.py
"""

import modal

app = modal.App("pearl-miner")

PRL_WALLET = "prl1pyzmnrl9f2wrna4wxnmaz92k05ep8fz6tfxdtzvsj56k0kheph5hs04lfac"
PRL_WORKER = "modal-h100"
PRL_GPU = "H100"
PRL_POOL = "stratum+tcp://pool.pearlhash.xyz:3357"
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
    gpu=PRL_GPU,
    image=image,
    timeout=TIMEOUT,
    scaledown_window=300,
)
def mine():
    import subprocess
    print(f"[pearl] GPU: {PRL_GPU}")
    print(f"[pearl] Wallet: {PRL_WALLET}")
    print(f"[pearl] Worker: {PRL_WORKER}")
    print(f"[pearl] Pool: {PRL_POOL}")

    proc = subprocess.Popen(
        ["/opt/miner/wildrig-multi", "-a", "pearlhash",
         "-o", PRL_POOL, "-u", f"{PRL_WALLET}.{PRL_WORKER}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    for line in iter(proc.stdout.readline, b""):
        print(line.decode().strip(), flush=True)
    return proc.wait()

@app.local_entrypoint()
def main():
    mine.remote()
