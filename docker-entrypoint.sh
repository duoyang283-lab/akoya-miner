#!/bin/bash
set -e

# ── Cloudflare WARP ─────────────────────────────────────────────────────────
# Start warp-svc daemon, register, connect. All outbound traffic goes through WARP.
warp-svc >/tmp/warp-svc.log 2>&1 &>/dev/null & || true
sleep 2
warp-cli --accept-tos register || true
warp-cli --accept-tos connect || true

# Wait for WARP connection (best-effort, max ~60s)
for i in $(seq 1 60); do
  if warp-cli --accept-tos status 2>&1 | grep -qiE 'connected|hasIPv4'; then
    break
  fi
  sleep 1
done

# ── GEMM library selection ──────────────────────────────────────────────────
LIB_DIR="/app/lib"
TARGET="$LIB_DIR/libgemm.so"

variant_exists() {
  [[ -f "$LIB_DIR/libgemm_$1.so" ]]
}

select_for_cc() {
  local cc="$1" major="${cc%%.*}" minor="${cc#*.}"
  if [[ "$major" -eq 7 ]] && [[ "$minor" -eq 0 ]] && variant_exists volta; then echo "volta"
  elif [[ "$major" -eq 7 ]] && [[ "$minor" -eq 5 ]] && variant_exists turing; then echo "turing"
  elif [[ "$major" -eq 10 ]] && variant_exists b200; then echo "b200"
  elif [[ "$major" -eq 12 ]] && variant_exists blackwell; then echo "blackwell"
  elif [[ "$major" -eq 9 ]] && variant_exists h100; then echo "h100"
  elif [[ "$major" -eq 8 ]] && [[ "$minor" -eq 9 ]] && variant_exists ada; then echo "ada"
  elif [[ "$major" -eq 8 ]] && variant_exists ampere; then echo "ampere"
  else echo "portable"
  fi
}

select_for_name() {
  local name="$1"
  case "$name" in
    *H100*|*H200*)           if variant_exists h100; then echo "h100"; return; fi ;;
    *B200*|*B100*|*GB200*)   if variant_exists b200; then echo "b200"; return; fi ;;
    *RTX*50[0-9][0-9]*)      if variant_exists blackwell; then echo "blackwell"; return; fi ;;
    *RTX*40[0-9][0-9]*|*L40*|*L4*|*"6000 Ada"*) if variant_exists ada; then echo "ada"; return; fi ;;
    *RTX*30[0-9][0-9]*|*A100*|*A40*|*A6000*)    if variant_exists ampere; then echo "ampere"; return; fi ;;
  esac
  echo "portable"
}

select_gemm_lib() {
  local forced="${NW_GEMM_VARIANT:-auto}"
  case "$forced" in
    auto|"") ;;
    h100|volta|turing|portable|ampere|ada|blackwell|b200)
      if ! variant_exists "$forced"; then
        echo "[entrypoint] NW_GEMM_VARIANT=$forced requested, but libgemm_${forced}.so is missing" >&2
        exit 64
      fi
      echo "$forced"; return ;;
    *)
      echo "[entrypoint] invalid NW_GEMM_VARIANT=$forced" >&2; exit 64 ;;
  esac

  local cc
  cc=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d '[:space:]') || true
  if [[ -z "$cc" ]]; then
    local name
    name=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1) || true
    if [[ -n "$name" ]]; then
      select_for_name "$name"; return
    fi
    echo "portable"; return
  fi
  select_for_cc "$cc"
}

if [[ "${NW_GEMM_LIB:-$TARGET}" == "$TARGET" ]]; then
  variant=$(select_gemm_lib | tail -1)
  ln -sf "$LIB_DIR/libgemm_${variant}.so" "$TARGET"
  echo "[entrypoint] NW_GEMM_LIB=$TARGET -> libgemm_${variant}.so" >&2
fi

# ── Launch miner ────────────────────────────────────────────────────────────
exec /app/node-worker "$@"
