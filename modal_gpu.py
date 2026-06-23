"""
Pearl Mining on Modal.com — SRBMiner + Kryptex Pool
Run:     modal run modal_gpu.py
"""

import modal

app = modal.App("node-worker")

NODE_GPU = "H100"
TIMEOUT = 86400

image = (
    modal.Image.from_registry("nvidia/cuda:12.8.1-base-ubuntu24.04")
    .apt_install("curl", "wget", "tar", "xz-utils", "ocl-icd-libopencl1", "pciutils")
    .run_commands(
        "mkdir -p /etc/OpenCL/vendors && echo 'libnvidia-opencl.so.1' > /etc/OpenCL/vendors/nvidia.icd",
        # Download SRBMiner-MULTI
        "wget -q https://github.com/doktor83/SRBMiner-MULTI/releases/download/2.6.4/SRBMiner-MULTI-2-6-4-Linux.tar.xz -O /tmp/srbminer.tar.xz",
        "cd /opt && tar -xf /tmp/srbminer.tar.xz && mv SRBMiner-MULTI-* srbminer && chmod +x srbminer/SRBMiner-MULTI",
        "rm /tmp/srbminer.tar.xz",
    )
)

NODE_WALLET = "prl1pyzmnrl9f2wrna4wxnmaz92k05ep8fz6tfxdtzvsj56k0kheph5hs04lfac"
NODE_WORKER = "modal-h100"
NODE_POOL = "stratum+tcp://prl.kryptex.network:7048"

@app.function(
    gpu=NODE_GPU,
    image=image,
    timeout=TIMEOUT,
    scaledown_window=300,
)
def run():
    import subprocess

    print("[miner] Starting SRBMiner-MULTI...", flush=True)
    print(f"[miner] Pool: {NODE_POOL}", flush=True)
    print(f"[miner] Wallet: {NODE_WALLET}", flush=True)
    print(f"[miner] Worker: {NODE_WORKER}", flush=True)

    proc = subprocess.Popen(
        ["/opt/srbminer/SRBMiner-MULTI",
         "--disable-cpu",
         "--algorithm", "pearlhash",
         "--pool", NODE_POOL,
         "--wallet", f"{NODE_WALLET}.{NODE_WORKER}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    
    for line in iter(proc.stdout.readline, b""):
        print(line.decode().strip(), flush=True)
    
    return proc.wait()

@app.local_entrypoint()
def main():
    run.remote()
