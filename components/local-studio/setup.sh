#!/usr/bin/env bash
# setup.sh — check, and build from scratch, local-studio's whole install on an Apple-silicon Mac.
#
#     bash components/local-studio/setup.sh [--check]   one line per piece: present|fallback|missing <path>; exit 1 if any missing
#     bash components/local-studio/setup.sh --install   tools (git, uv, ffmpeg via Homebrew), the two venvs from the pinned
#                                                       requirements-*.txt, the LTX-2 MLX port, RIFE + Real-ESRGAN binaries
#     bash components/local-studio/setup.sh --fetch     every model weight (~16 GB here, + ~15.5 GB for 3D)
#     add --no-3d to leave out components/3d (TRELLIS.2, which has its own setup.sh and is run from here otherwise)
#
# Everything installs inside this component, git-ignored: .venv (PyTorch jobs), .venv-mlx (MLX jobs),
# src/ltx-2-mlx, models/ (binaries + weights). BiRefNet (and the 3D weights) go to the per-user Hugging Face
# cache (${HF_HUB_CACHE:-${HF_HOME:-~/.cache/huggingface}/hub}), which the matte and 3d jobs read. Every
# download is an official upstream release, pinned (version, commit, or Hugging Face revision) and, where a
# checksum is known, verified. Idempotent: what is already there is skipped; an incomplete venv is completed.
# LOCAL_STUDIO_FALLBACK may name an older tools folder (laid out av/, local/, 3d/); a piece missing here but
# present there is reported "fallback", used by local.py, and not downloaded. A fallback, never the default.
# The LTX-2.5 image-to-video weights (~29 GB) are not fetched (README.md, "Not local").
# macOS bash 3.2: no associative arrays.
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

# LD-52 (venvs outside repo), extended to models: weights live outside the repo first
# ($UPRIGHT_MODELS, default ~/.upright/models, then local-studio/ — run-kit paths.models), so a
# mini run in a fresh worktree finds them; this component's models/ when that folder is not there —
# the same rule as local.py's MODELS, so --check and the jobs always look in one place.
SHARED_MODELS="${UPRIGHT_MODELS:-$HOME/.upright/models}/local-studio"
if [ -d "$SHARED_MODELS" ]; then
    MODELS="$SHARED_MODELS"
else
    MODELS="$ROOT/models"
fi
FALLBACK="${LOCAL_STUDIO_FALLBACK:-}"
HF_SHARED="${HF_HUB_CACHE:-${HF_HOME:-$HOME/.cache/huggingface}/hub}"
SETUP_3D="$REPO/components/3d/setup.sh"

# ---- upstream sources, pinned to what the measured build ran (2026-09-26/27) ----
RIFE_DIR=rife-ncnn-vulkan-20221029-macos
RIFE_URL=https://github.com/nihui/rife-ncnn-vulkan/releases/download/20221029/rife-ncnn-vulkan-20221029-macos.zip  # MIT, 437 MB
RIFE_SHA=d11429c72f0cddfb170fd131ee9373dc5329a5729c4382c0acfd40092e5ed19a   # of the rife-ncnn-vulkan binary inside
ESRGAN_URL=https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-macos.zip  # BSD-3, 52 MB
ESRGAN_SHA=c1c35d92079085de96b9d547fd7e4464bc8a2e9ccf28d7b8c712d72ade91b7cc  # of the realesrgan-ncnn-vulkan binary inside
LTX_URL=https://github.com/dgrauet/ltx-2-mlx.git
LTX_REV=b89155bc8b2d28503000ebdc967da749e0c56849
# <dest under models/> <url> <sha256>
FILES="sam2/sam2.1_hiera_small.pt https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_small.pt 6d1aa6f30de5c92224f8172114de081d104bbd23dd9dc5c58996f0cad5dc4d38
depth-pro/depth_pro.pt https://ml-site.cdn-apple.com/models/depth-pro/depth_pro.pt 3eb35ca68168ad3d14cb150f8947a4edf85589941661fdb2686259c80685c0ce
torch/hub/checkpoints/f7e0c4bc-ba3fe64a.th https://dl.fbaipublicfiles.com/demucs/hybrid_transformer/f7e0c4bc-ba3fe64a.th ba3fe64ae8ef66ac9a4857222ce48efbdc5eb3ad375cb79dd13debee5aaa4066
torch/hub/checkpoints/d12395a8-e57c48e6.th https://dl.fbaipublicfiles.com/demucs/hybrid_transformer/d12395a8-e57c48e6.th e57c48e6b0e38af4f7118d7bd08c49f0a0c0edf7d09143bdd902ea0d237303e6
torch/hub/checkpoints/92cfc3b6-ef3bcb9c.th https://dl.fbaipublicfiles.com/demucs/hybrid_transformer/92cfc3b6-ef3bcb9c.th ef3bcb9c8b40d14ae5d51b6db2587339cc12c6b77c0be151ce6d69002e087bf2
torch/hub/checkpoints/04573f0d-f3cf25b2.th https://dl.fbaipublicfiles.com/demucs/hybrid_transformer/04573f0d-f3cf25b2.th f3cf25b222c4eed7cd49dd8b2c9597d50c18bd154090f7b919cfa5f93cf22c49"
# where each FILES entry sits in the fallback's layout (same order)
FILES_OLD="av/models/sam2/sam2.1_hiera_small.pt
av/models/depth-pro/depth_pro.pt
local/models/torch/hub/checkpoints/f7e0c4bc-ba3fe64a.th
local/models/torch/hub/checkpoints/d12395a8-e57c48e6.th
local/models/torch/hub/checkpoints/92cfc3b6-ef3bcb9c.th
local/models/torch/hub/checkpoints/04573f0d-f3cf25b2.th"
# Hugging Face, as local.py names them: <repo> <revision> [allow-pattern]
HF_MLX_MODELS="mflux-community/flux2-klein-4b-mflux-q4 794cd159538149ad9830848508c31f0ea7088e58
mlx-community/whisper-large-v3-turbo a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb
mlx-community/Kokoro-82M-bf16 a71e4d38b236d968966a2002c4c895dbd12b1c3c
prince-canuma/Kokoro-82M e02c9eada7ce7416798af36b190a8a2dd2ecd566 voices/*"
HF_SHARED_MODELS="ZhengPeng7/BiRefNet e2bf8e4460fc8fa32bba5ea4d94b3233d367b0e4
ZhengPeng7/BiRefNet_lite aa62cd87eafb9cc43056d08ef3615a14628b831d"
SEEDVR2_REPO=numz/SeedVR2_comfyUI
SEEDVR2_REV=09ced71023636e9bc8cdf9cdecfb2625d1e691e8
SEEDVR2_FILES="seedvr2_ema_3b_fp16.safetensors ema_vae_fp16.safetensors"

TORCH_MODULES="torch torchvision transformers timm kornia einops demucs sam2 depth_pro soundfile cv2 PIL"
MLX_MODULES="mflux mlx mlx_whisper mlx_audio misaki spacy en_core_web_sm huggingface_hub"

usage() { sed -n '2,9p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

rel() {
    case "$1" in
        "$REPO"/*) printf '%s' "${1#"$REPO"/}" ;;
        "$HOME"/*) printf '~/%s' "${1#"$HOME"/}" ;;
        *) printf '%s' "$1" ;;
    esac
}

MISSING=0
say() { echo "$1 $(rel "$2")${3:+ $3}"; [ "$1" = missing ] && MISSING=$((MISSING + 1)); return 0; }

where() {   # where <own> <old-rel> [probe] — the same rule as local.py found(): own, else fallback, else own
    local probe="${3:-}"
    if [ -e "$1${probe:+/$probe}" ] || [ -z "$FALLBACK" ]; then echo "$1"; return; fi
    if [ -e "$FALLBACK/$2${probe:+/$probe}" ]; then echo "$FALLBACK/$2"; else echo "$1"; fi
}

state_of() {   # state_of <own> <found> [probe] -> present|fallback|missing
    if [ ! -e "$2${3:+/$3}" ]; then echo missing
    elif [ "$1" = "$2" ]; then echo present
    else echo fallback; fi
}

piece() {   # piece <own> <old-rel> [probe]
    local f; f="$(where "$1" "$2" "${3:-}")"
    say "$(state_of "$1" "$f" "${3:-}")" "$f"
}

missing_modules() {   # missing_modules <python> <modules...> — the modules the venv cannot find (find_spec: no import, fast)
    local py="$1"; shift
    "$py" -c 'import importlib.util as u, sys; print(" ".join(m for m in sys.argv[1:] if u.find_spec(m) is None))' "$@" 2>/dev/null \
        || echo "$*"
}

venv_piece() {   # venv_piece <own venv> <old-rel> <modules>
    local f st miss; f="$(where "$1" "$2" bin/python)"; st="$(state_of "$1" "$f" bin/python)"
    if [ "$st" = missing ]; then say missing "$1"; return; fi
    # shellcheck disable=SC2086
    miss="$(missing_modules "$f/bin/python" $3)"
    if [ -n "$miss" ]; then say missing "$f" "(incomplete: $miss)"; else say "$st" "$f"; fi
}

hf_have() { [ -f "$1/models--$(echo "$2" | sed 's#/#--#g')/refs/main" ]; }

hf_mlx_home() { where "$MODELS/hf" local/models/hf hub/models--mflux-community--flux2-klein-4b-mflux-q4; }

esrgan() {  # Real-ESRGAN is found, never one fixed path — local.py esrgan_places(), same order
    local d w old="${FALLBACK:+$FALLBACK/av/bin/realesrgan}"
    for d in "${REALESRGAN_DIR:-}" "$MODELS/realesrgan" "$old"; do
        if [ -n "$d" ] && [ -e "$d" ]; then
            if [ "$d" = "$old" ]; then say fallback "$d"; else say present "$d"; fi
            return
        fi
    done
    w="$(command -v realesrgan-ncnn-vulkan 2>/dev/null || true)"
    if [ -n "$w" ]; then say present "$w"; return; fi
    say missing "$MODELS/realesrgan" "(or REALESRGAN_DIR, or realesrgan-ncnn-vulkan on PATH)"
}

tool() {   # tool <command> <how to get it>
    local w; w="$(command -v "$1" 2>/dev/null || true)"
    if [ -n "$w" ]; then say present "$w"; else say missing "$1" "($2)"; fi
}

check() {
    MISSING=0
    local i dest old repo hf line
    tool git "xcode-select --install"
    tool uv "brew install uv"
    tool ffmpeg "brew install ffmpeg"
    venv_piece "$ROOT/.venv" av/.venv "$TORCH_MODULES"
    venv_piece "$ROOT/.venv-mlx" local/.venv-mlx "$MLX_MODULES"
    piece "$ROOT/src/ltx-2-mlx" local/src/ltx-2-mlx .venv/bin/ltx-2-mlx
    piece "$MODELS/$RIFE_DIR" "av/bin/$RIFE_DIR" rife-ncnn-vulkan
    esrgan
    i=0
    for dest in $(echo "$FILES" | awk '{print $1}'); do
        i=$((i + 1)); old="$(echo "$FILES_OLD" | sed -n "${i}p")"
        piece "$MODELS/$dest" "$old"
    done
    piece "$MODELS/seedvr2-3b" local/models/seedvr2-3b seedvr2_ema_3b_fp16.safetensors
    hf="$(hf_mlx_home)"
    for repo in $(echo "$HF_MLX_MODELS" | awk '{print $1}'); do
        if hf_have "$hf/hub" "$repo"; then say "$([ "$hf" = "$MODELS/hf" ] && echo present || echo fallback)" "$hf/hub/$repo"
        else say missing "$hf/hub/$repo"; fi
    done
    for repo in $(echo "$HF_SHARED_MODELS" | awk '{print $1}'); do
        if hf_have "$HF_SHARED" "$repo"; then say present "$HF_SHARED/$repo"; else say missing "$HF_SHARED/$repo"; fi
    done
    if [ "$NO_3D" = 0 ]; then
        if [ -f "$SETUP_3D" ]; then
            bash "$SETUP_3D" --check | sed '/^[0-9]* missing (3d)/d' > "${TMPDIR:-/tmp}/ls-3d.$$"
            while read -r line; do
                echo "$line"
                case "$line" in missing*) MISSING=$((MISSING + 1)) ;; esac
            done < "${TMPDIR:-/tmp}/ls-3d.$$"
            rm -f "${TMPDIR:-/tmp}/ls-3d.$$"
        else
            say missing "$SETUP_3D"
        fi
    fi
    echo "not installed by design: LTX-2.5 image-to-video weights (~29 GB, $(rel "$MODELS")/ltx-2.5-mlx-q4) — README.md, 'Not local'."
    if [ "$MISSING" -gt 0 ]; then
        echo "$MISSING missing. bash components/local-studio/setup.sh --install --fetch installs them."
        return 1
    fi
    return 0
}

# ---------------------------------------------------------------- install
brew_get() {   # brew_get <command> <formula>
    command -v "$1" >/dev/null 2>&1 && return 0
    if command -v brew >/dev/null 2>&1; then brew install "$2" && return 0; fi
    echo "setup.sh: needs $1 — install Homebrew (https://brew.sh), then run this again" >&2
    return 1
}

sha_ok() { [ "$(shasum -a 256 "$1" | awk '{print $1}')" = "$2" ]; }

download() {   # download <url> <dest> [sha256] — resumable, atomic, verified
    mkdir -p "$(dirname "$2")"
    echo "  downloading $(basename "$2") from $1"
    curl -fL --retry 3 -C - --progress-bar -o "$2.part" "$1" || { echo "  download failed: $1" >&2; return 1; }
    if [ -n "${3:-}" ] && ! sha_ok "$2.part" "$3"; then
        echo "  checksum mismatch: $2.part (expected $3) — left in place for inspection" >&2
        return 1
    fi
    mv "$2.part" "$2"
}

unzip_tool() {   # unzip_tool <url> <binary-name> <sha256> <dest dir> — release zip -> the folder holding the binary
    local tmp found
    [ -x "$4/$2" ] && { echo "  $(rel "$4") already there"; return 0; }
    tmp="$MODELS/.dl/$2"; rm -rf "$tmp"; mkdir -p "$tmp"
    download "$1" "$tmp.zip" || return 1
    unzip -q -o "$tmp.zip" -d "$tmp" || return 1
    found="$(find "$tmp" -type f -name "$2" | head -1)"
    [ -n "$found" ] || { echo "  $2 not in $(basename "$1")" >&2; return 1; }
    sha_ok "$found" "$3" || { echo "  $2 checksum mismatch" >&2; return 1; }
    rm -rf "$4"; mv "$(dirname "$found")" "$4"; chmod +x "$4/$2"
    rm -rf "$tmp" "$tmp.zip"
}

clone_at() {   # clone_at <url> <dir> <rev> — exactly that commit, shallow
    if [ -d "$2/.git" ]; then echo "  $(rel "$2") already cloned"; return 0; fi
    echo "  cloning $1 @ ${3:0:12}"
    mkdir -p "$2" && git -C "$2" init -q && git -C "$2" remote add origin "$1" \
        && git -C "$2" fetch -q --depth 1 origin "$3" && git -C "$2" checkout -q FETCH_HEAD
}

build_venv() {   # build_venv <venv> <old-rel> <python version> <requirements> <modules>
    local f miss
    f="$(where "$1" "$2" bin/python)"
    if [ "$f" != "$1" ]; then echo "  $(rel "$1"): using the fallback $(rel "$f")"; return 0; fi
    if [ ! -x "$1/bin/python" ]; then
        echo "  creating $(rel "$1") (Python $3)"
        uv venv -q --python "$3" "$1" || return 1
    fi
    # shellcheck disable=SC2086
    miss="$(missing_modules "$1/bin/python" $5)"
    if [ -z "$miss" ]; then echo "  $(rel "$1") complete"; return 0; fi
    echo "  installing $(basename "$4") into $(rel "$1") (missing: $miss)"
    SAM2_BUILD_CUDA=0 uv pip install --python "$1/bin/python" -r "$4"
}

install() {
    [ "$(uname -m)" = arm64 ] || echo "warning: the MLX jobs need Apple silicon (M1 or later)"
    brew_get git git || return 1
    brew_get uv uv || return 1
    brew_get ffmpeg ffmpeg || return 1
    build_venv "$ROOT/.venv" av/.venv 3.12 "$ROOT/requirements-torch.txt" "$TORCH_MODULES" || return 1
    build_venv "$ROOT/.venv-mlx" local/.venv-mlx 3.12 "$ROOT/requirements-mlx.txt" "$MLX_MODULES" || return 1
    if [ "$(where "$ROOT/src/ltx-2-mlx" local/src/ltx-2-mlx .venv/bin/ltx-2-mlx)" = "$ROOT/src/ltx-2-mlx" ]; then
        clone_at "$LTX_URL" "$ROOT/src/ltx-2-mlx" "$LTX_REV" || return 1
        [ -x "$ROOT/src/ltx-2-mlx/.venv/bin/ltx-2-mlx" ] || (cd "$ROOT/src/ltx-2-mlx" && uv sync -q --frozen) || return 1
    fi
    mkdir -p "$MODELS"
    if [ "$(where "$MODELS/$RIFE_DIR" "av/bin/$RIFE_DIR" rife-ncnn-vulkan)" = "$MODELS/$RIFE_DIR" ]; then
        unzip_tool "$RIFE_URL" rife-ncnn-vulkan "$RIFE_SHA" "$MODELS/$RIFE_DIR" || return 1
    fi
    if [ -z "$(esrgan | grep -v '^missing')" ]; then
        unzip_tool "$ESRGAN_URL" realesrgan-ncnn-vulkan "$ESRGAN_SHA" "$MODELS/realesrgan" || return 1
    fi
    rm -rf "$MODELS/.dl"
    if [ "$NO_3D" = 0 ]; then bash "$SETUP_3D" --install || return 1; fi
}

# ---------------------------------------------------------------- fetch
hf_get() {   # hf_get <python> <cache> <repo> <revision> [pattern] — one pinned snapshot, then refs/main -> it (offline runs find it)
    HF_HUB_OFFLINE=0 "$1" - "$2" "$3" "$4" "${5:-}" <<'PY'
import sys
from pathlib import Path
from huggingface_hub import snapshot_download
cache, repo, rev, pat = sys.argv[1:5]
snapshot_download(repo, revision=rev, cache_dir=cache, allow_patterns=[pat] if pat else None)
ref = Path(cache) / ("models--" + repo.replace("/", "--")) / "refs" / "main"
ref.parent.mkdir(parents=True, exist_ok=True)
if not ref.exists():
    ref.write_text(rev)
PY
}

hf_models() {   # hf_models <python> <cache> <list>
    local repo rev pat rc=0
    while read -r repo rev pat; do
        [ -n "$repo" ] || continue
        if hf_have "$2" "$repo"; then echo "  $repo already in $(rel "$2")"; continue; fi
        echo "  fetching $repo @ ${rev:0:12}${pat:+ ($pat)}"
        hf_get "$1" "$2" "$repo" "$rev" "$pat" || { echo "  fetch failed: $repo" >&2; rc=1; }
    done <<EOF
$3
EOF
    return $rc
}

fetch() {
    local py dest url sha i=0 old f rc=0 hf
    py="$(where "$ROOT/.venv-mlx" local/.venv-mlx bin/python)/bin/python"
    [ -x "$py" ] || py="$(where "$ROOT/.venv" av/.venv bin/python)/bin/python"
    [ -x "$py" ] || { echo "setup.sh: no venv with huggingface_hub yet; run --install first" >&2; return 1; }
    while read -r dest url sha; do
        i=$((i + 1)); old="$(echo "$FILES_OLD" | sed -n "${i}p")"
        f="$(where "$MODELS/$dest" "$old")"
        if [ -e "$f" ]; then echo "  $(rel "$f") already there"; continue; fi
        download "$url" "$MODELS/$dest" "$sha" || rc=1
    done <<EOF
$FILES
EOF
    hf="$(hf_mlx_home)"
    hf_models "$py" "$hf/hub" "$HF_MLX_MODELS" || rc=1
    hf_models "$py" "$HF_SHARED" "$HF_SHARED_MODELS" || rc=1
    if [ "$(where "$MODELS/seedvr2-3b" local/models/seedvr2-3b seedvr2_ema_3b_fp16.safetensors)" = "$MODELS/seedvr2-3b" ] \
       && [ ! -f "$MODELS/seedvr2-3b/seedvr2_ema_3b_fp16.safetensors" ]; then
        echo "  fetching $SEEDVR2_REPO @ ${SEEDVR2_REV:0:12} ($SEEDVR2_FILES) -> $(rel "$MODELS")/seedvr2-3b"
        # shellcheck disable=SC2086
        HF_HUB_OFFLINE=0 "$py" -c 'import sys
from huggingface_hub import hf_hub_download
repo, rev, dest, *files = sys.argv[1:]
for f in files:
    hf_hub_download(repo, f, revision=rev, local_dir=dest)' "$SEEDVR2_REPO" "$SEEDVR2_REV" "$MODELS/seedvr2-3b" $SEEDVR2_FILES \
            && touch "$MODELS/seedvr2-3b/config.json" || rc=1
    fi
    if [ "$NO_3D" = 0 ]; then bash "$SETUP_3D" --fetch || rc=1; fi
    return $rc
}

DO_CHECK=0 DO_INSTALL=0 DO_FETCH=0 NO_3D=0
for arg in "$@"; do
    case "$arg" in
        --check) DO_CHECK=1 ;;
        --install) DO_INSTALL=1 ;;
        --fetch) DO_FETCH=1 ;;
        --no-3d) NO_3D=1 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "setup.sh: unknown argument: $arg" >&2; usage >&2; exit 2 ;;
    esac
done

if [ "$DO_INSTALL" = 0 ] && [ "$DO_FETCH" = 0 ]; then
    check
    exit $?
fi

RC=0
if [ "$DO_INSTALL" = 1 ]; then
    echo "== install"
    install || exit 1
fi
if [ "$DO_FETCH" = 1 ]; then
    echo "== fetch"
    fetch || RC=1
fi
echo
echo "== check"
check || true
exit $RC
