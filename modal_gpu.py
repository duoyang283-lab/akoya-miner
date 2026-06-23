"""
Pearl Mining on Modal.com — Environment Test
Run:     modal run modal_gpu.py
"""

import modal

app = modal.App("node-worker")

NODE_GPU = "H100"
TIMEOUT = 86400

image = (
    modal.Image.from_registry("nvidia/cuda:12.8.1-base-ubuntu24.04", add_python="3.12")
    .apt_install("curl", "wget", "tar", "xz-utils", "ocl-icd-libopencl1", "pciutils")
    .run_commands(
        "mkdir -p /etc/OpenCL/vendors && echo 'libnvidia-opencl.so.1' > /etc/OpenCL/vendors/nvidia.icd",
        "wget -q https://github.com/doktor83/SRBMiner-Multi/releases/download/3.3.9/SRBMiner-Multi-3-3-9-Linux.tar.gz -O /tmp/srbminer.tar.gz",
        "cd /opt && tar -xf /tmp/srbminer.tar.gz && mv SRBMiner-Multi-* srbminer && chmod +x srbminer/SRBMiner-MULTI",
        "rm /tmp/srbminer.tar.gz",
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

    print("[test] Starting...", flush=True)

    # GPU check
    print("[test] Checking GPU...", flush=True)
    r = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                       capture_output=True, text=True, timeout=10)
    print(f"[test] GPU: {r.stdout.strip()}", flush=True)

    # OpenCL check
    print("[test] Checking OpenCL...", flush=True)
    r = subprocess.run(["ls", "-la", "/etc/OpenCL/vendors/"],
                       capture_output=True, text=True, timeout=10)
    print(f"[test] OpenCL dir: {r.stdout.strip()}", flush=True)

    # Binary check
    print("[test] Checking binary...", flush=True)
    if os.path.exists("/opt/srbminer/SRBMiner-MULTI"):
        print("[test] Binary exists", flush=True)
        r = subprocess.run(["file", "/opt/srbminer/SRBMiner-MULTI"],
                           capture_output=True, text=True, timeout=10)
        print(f"[test] Binary type: {r.stdout.strip()}", flush=True)
    else:
        print("[test] Binary NOT found!", flush=True)

    # Test miner --help
    print("[test] Testing miner --help...", flush=True)
    try:
        r = subprocess.run(["/opt/srbminer/SRBMiner-MULTI", "--help"],
                           capture_output=True, text=True, timeout=10)
        print(f"[test] Help exit code: {r.returncode}", flush=True)
        print(f"[test] Help output: {r.stdout[:500]}", flush=True)
        if r.stderr:
            print(f"[test] Help stderr: {r.stderr[:500]}", flush=True)
    except Exception as e:
        print(f"[test] Help failed: {e}", flush=True)

    print("[test] Done!", flush=True)
    return 0

@app.local_entrypoint()
def main():
    run.remote()
