#!/usr/bin/env bash
# setup.sh — check, and build, local-studio's own install on this Mac (SI-134 (local-studio setup)).
#
#     bash components/local-studio/setup.sh [--check]        one line per piece: present|missing <path>; exit 1 if any missing
#     bash components/local-studio/setup.sh --install        create .venv-mlx, pip-install mflux mlx-whisper mlx-audio,
#                                                            print their versions and the fetch command for each model
#     bash components/local-studio/setup.sh --install --fetch  …and run those fetch commands (weights into models/hf)
#
# The paths are the ones local.py names (ROOT/.venv-mlx, ROOT/models, ROOT/src/ltx-2-mlx,
# REPO/tools/av/bin, the SAM 2 checkpoint). tools/av is machine-local, outside this
# component and outside git: its pieces are reported, never installed.
# No network unless --install or --fetch. macOS bash 3.2: no associative arrays.
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

REPO="$ROOT"
while [ "$REPO" != "/" ] && ! { [ -d "$REPO/components" ] && [ -d "$REPO/brands" ]; }; do
    REPO="$(dirname "$REPO")"
done
if [ "$REPO" = "/" ]; then
    echo "setup.sh: no folder holding components/ and brands/ above $ROOT" >&2
    exit 2
fi

MODELS="$ROOT/models"
MLX="$ROOT/.venv-mlx"
AV="$REPO/tools/av"
SAM2_HERE="$MODELS/sam2/sam2.1_hiera_small.pt"
SAM2_AV="$AV/models/sam2/sam2.1_hiera_small.pt"

# model ids, as local.py names them (FLUX2_Q4, WHISPER, KOKORO)
MODEL_IDS="mflux-community/flux2-klein-4b-mflux-q4 mlx-community/whisper-large-v3-turbo mlx-community/Kokoro-82M-bf16"
PACKAGES="mflux mlx-whisper mlx-audio"

usage() {
    sed -n '2,7p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

rel() {
    case "$1" in
        "$REPO"/*) printf '%s' "${1#"$REPO"/}" ;;
        *) printf '%s' "$1" ;;
    esac
}

MISSING=0
piece() {   # piece <test-flag> <path>
    if [ "$1" "$2" ]; then
        echo "present $(rel "$2")"
    else
        echo "missing $(rel "$2")"
        MISSING=$((MISSING + 1))
    fi
}

esrgan() {  # Real-ESRGAN is found, never one fixed path — local.py esrgan_places(), same order
    for d in "${REALESRGAN_DIR:-}" "$MODELS/realesrgan" "$AV/bin/realesrgan"; do
        if [ -n "$d" ] && [ -e "$d" ]; then
            echo "present $(rel "$d")"
            return
        fi
    done
    w="$(command -v realesrgan-ncnn-vulkan 2>/dev/null || true)"
    if [ -n "$w" ]; then
        echo "present $w"
        return
    fi
    echo "missing $(rel "$AV/bin/realesrgan") (or $(rel "$MODELS/realesrgan"), REALESRGAN_DIR, or realesrgan-ncnn-vulkan on PATH)"
    MISSING=$((MISSING + 1))
}

check() {
    MISSING=0
    piece -x "$MLX/bin/python"
    piece -d "$MODELS"
    piece -d "$ROOT/src/ltx-2-mlx"
    piece -d "$AV/bin/rife-ncnn-vulkan-20221029-macos"
    esrgan
    if [ -f "$SAM2_HERE" ]; then
        echo "present $(rel "$SAM2_HERE")"
    elif [ -f "$SAM2_AV" ]; then
        echo "present $(rel "$SAM2_AV")"
    else
        echo "missing $(rel "$SAM2_HERE") (or $(rel "$SAM2_AV"))"
        MISSING=$((MISSING + 1))
    fi
    if [ "$MISSING" -gt 0 ]; then
        echo "$MISSING missing. tools/av pieces are machine-local and not installed by this script."
        return 1
    fi
    return 0
}

fetch_cmd() {   # the one command that fetches a model id into models/hf
    printf 'HF_HOME="%s" "%s" -c "from huggingface_hub import snapshot_download; snapshot_download('"'"'%s'"'"')"' "$MODELS/hf" "$MLX/bin/python" "$1"
}

install() {
    local py="${PYTHON:-python3}"
    if [ ! -x "$MLX/bin/python" ]; then
        echo "creating $(rel "$MLX") with $py ($("$py" --version 2>&1))"
        "$py" -m venv "$MLX" || { echo "setup.sh: venv failed" >&2; return 1; }
    fi
    # shellcheck disable=SC2086
    "$MLX/bin/python" -m pip install --upgrade $PACKAGES || { echo "setup.sh: pip install failed" >&2; return 1; }
    echo "installed (unpinned — current versions):"
    # shellcheck disable=SC2086
    "$MLX/bin/python" -m pip show $PACKAGES 2>/dev/null | awk '/^Name:/{n=$2} /^Version:/{print "  " n " " $2}'
    mkdir -p "$MODELS/hf"
}

fetch() {   # fetch <run: 0|1>
    local id rc=0
    echo "model fetch commands (weights into $(rel "$MODELS")/hf):"
    for id in $MODEL_IDS; do
        echo "  $(fetch_cmd "$id")"
        if [ "$1" = 1 ]; then
            HF_HOME="$MODELS/hf" "$MLX/bin/python" -c "from huggingface_hub import snapshot_download; snapshot_download('$id')" \
                || { echo "setup.sh: fetch failed: $id" >&2; rc=1; }
        fi
    done
    echo "not fetched here: SeedVR2 (numz/SeedVR2_comfyUI fp16 3B + VAE, into $(rel "$MODELS")/seedvr2-3b) and the LTX-2.5 pack ($(rel "$MODELS")/ltx-2.5-mlx-q4) — see README.md."
    return $rc
}

DO_CHECK=0 DO_INSTALL=0 DO_FETCH=0
for arg in "$@"; do
    case "$arg" in
        --check) DO_CHECK=1 ;;
        --install) DO_INSTALL=1 ;;
        --fetch) DO_FETCH=1 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "setup.sh: unknown argument: $arg" >&2; usage >&2; exit 2 ;;
    esac
done
[ "$DO_INSTALL" = 0 ] && [ "$DO_FETCH" = 0 ] && DO_CHECK=1

if [ "$DO_CHECK" = 1 ] && [ "$DO_INSTALL" = 0 ] && [ "$DO_FETCH" = 0 ]; then
    check
    exit $?
fi

RC=0
if [ "$DO_INSTALL" = 1 ]; then
    install || exit 1
fi
if [ ! -x "$MLX/bin/python" ]; then
    echo "setup.sh: $(rel "$MLX") is not installed; run --install first" >&2
    exit 1
fi
fetch "$DO_FETCH" || RC=1
echo
check || true
exit $RC
