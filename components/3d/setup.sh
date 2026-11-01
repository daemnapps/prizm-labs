#!/usr/bin/env bash
# setup.sh — check, and build, make3d's own install on an Apple-silicon Mac (TRELLIS.2 image-to-3D).
#
#     bash components/3d/setup.sh [--check]     one line per piece: present|fallback|missing <path>; exit 1 if any missing
#     bash components/3d/setup.sh --install     clone trellis-mac + TRELLIS.2 + deps at pinned commits, build the
#                                               Python 3.11 venv from requirements-trellis.txt, apply the MPS patches
#     bash components/3d/setup.sh --fetch       download the weights (~15.5 GB) into the shared Hugging Face cache
#
# Everything lands in components/3d/trellis-mac (git-ignored) and the per-user Hugging Face cache
# (${HF_HUB_CACHE:-${HF_HOME:-~/.cache/huggingface}/hub}). Nothing is committed. Idempotent: pieces already
# there are skipped. LOCAL_STUDIO_FALLBACK may name an older tools folder (laid out av/, local/, 3d/) whose
# 3d/trellis-mac is used when this component has none — a fallback only, never the default.
# Needs: git, uv (brew install uv), Blender (brew install --cask blender). Set MAKE3D_METAL=1 to also try the
# optional Metal texture backends (need full Xcode + its Metal toolchain; without them the slower fallback runs).
# macOS bash 3.2: no associative arrays.
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$HERE"
while [ "$REPO" != "/" ] && ! { [ -d "$REPO/components" ] && [ -d "$REPO/brands" ]; }; do
    REPO="$(dirname "$REPO")"
done
[ "$REPO" = "/" ] && REPO="$HERE"

TRELLIS="$HERE/trellis-mac"
FALLBACK="${LOCAL_STUDIO_FALLBACK:-}"
HF_CACHE="${HF_HUB_CACHE:-${HF_HOME:-$HOME/.cache/huggingface}/hub}"

# upstream sources, pinned to the commits the working build used (2026-09-26)
TRELLIS_MAC_URL=https://github.com/shivampkumar/trellis-mac.git
TRELLIS_MAC_REV=d58628f4f5b9c3de8274cb110074154f4b31cef2
TRELLIS2_URL=https://github.com/microsoft/TRELLIS.2.git
TRELLIS2_REV=75fbf0183001ed9876c8dbb35de6b68552ee08bd
# deps/<name> <url> <rev>
DEPS="utils3d https://github.com/EasternJournalist/utils3d.git 9a4eb15e4021b67b12c460c7057d642626897ec8
mtlbvh https://github.com/pedronaugusto/mtlbvh.git 6b2a0f63b476ad8225695d092902104beafd7f58
mtldiffrast https://github.com/pedronaugusto/mtldiffrast.git c9499ba2e4ed6849e95ce5da7aae5bf61addb528
mtlmesh https://github.com/pedronaugusto/mtlmesh.git 7de3864f783407201486bf6c900a4bd76a4018a3
mtlgemm https://github.com/pedronaugusto/mtlgemm.git 566c133781ce4992de3f77c3a97dd6feaae9d013
trellis2-apple https://github.com/pedronaugusto/trellis2-apple.git 17347247c91c36c8cdc1896234983e878a457bba"
# Hugging Face weights: <repo> <revision> [allow-pattern]   (all ungated; DINOv3 + RMBG are swapped for ungated mirrors in make3d.py)
WEIGHTS="microsoft/TRELLIS.2-4B af44b45f2e35a493886929c6d786e563ec68364d
microsoft/TRELLIS-image-large 25e0d31ffbebe4b5a97464dd851910efc3002d96 ckpts/ss_dec_conv3d_16l8_fp16.*
camenduru/dinov3-vitl16-pretrain-lvd1689m 3c276edd87d6f6e569ff0c4400e086807d0f3881
ZhengPeng7/BiRefNet e2bf8e4460fc8fa32bba5ea4d94b3233d367b0e4"
VENV_MODULES="torch torchvision transformers accelerate trimesh xatlas fast_simplification utils3d kornia timm easydict cv2 imageio"

usage() { sed -n '2,8p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

rel() {
    case "$1" in
        "$REPO"/*) printf '%s' "${1#"$REPO"/}" ;;
        "$HOME"/*) printf '~/%s' "${1#"$HOME"/}" ;;
        *) printf '%s' "$1" ;;
    esac
}

MISSING=0
say() { echo "$1 $(rel "$2")${3:+ $3}"; [ "$1" = missing ] && MISSING=$((MISSING + 1)); return 0; }

trellis_dir() {   # the trellis-mac make3d will use: ours, else the fallback's, else ours (to be installed)
    if [ -x "$TRELLIS/.venv/bin/python" ]; then echo "$TRELLIS"
    elif [ -n "$FALLBACK" ] && [ -x "$FALLBACK/3d/trellis-mac/.venv/bin/python" ]; then echo "$FALLBACK/3d/trellis-mac"
    else echo "$TRELLIS"; fi
}

missing_modules() {   # missing_modules <python> — modules of VENV_MODULES the venv cannot find (no import, fast)
    "$1" -c 'import importlib.util as u, sys; print(" ".join(m for m in sys.argv[1:] if u.find_spec(m) is None))' $VENV_MODULES 2>/dev/null \
        || echo "$VENV_MODULES"
}

hf_have() {   # hf_have <cache> <repo>
    [ -f "$1/models--$(echo "$2" | sed 's#/#--#g')/refs/main" ]
}

check() {
    MISSING=0
    local t state py miss repo
    t="$(trellis_dir)"
    state=present; [ "$t" != "$TRELLIS" ] && state=fallback
    if [ -f "$t/TRELLIS.2/trellis2/pipelines/trellis2_image_to_3d.py" ]; then say "$state" "$t/TRELLIS.2"
    else say missing "$TRELLIS/TRELLIS.2"; fi
    py="$t/.venv/bin/python"
    if [ -x "$py" ]; then
        miss="$(missing_modules "$py")"
        if [ -z "$miss" ]; then say "$state" "$t/.venv"
        else say missing "$t/.venv" "(incomplete: $miss)"; fi
    else
        say missing "$TRELLIS/.venv"
    fi
    if command -v blender >/dev/null 2>&1; then say present "$(command -v blender)"
    else say missing "blender" "(Blender on PATH: brew install --cask blender)"; fi
    for repo in $(echo "$WEIGHTS" | awk '{print $1}'); do
        if hf_have "$HF_CACHE" "$repo"; then say present "$HF_CACHE/$repo"
        else say missing "$HF_CACHE/$repo"; fi
    done
    if [ "$MISSING" -gt 0 ]; then
        echo "$MISSING missing (3d). bash components/3d/setup.sh --install --fetch installs them."
        return 1
    fi
    return 0
}

clone_at() {   # clone_at <url> <dir> <rev> — exactly that commit, shallow
    if [ -d "$2/.git" ]; then echo "  $(rel "$2") already cloned"; return 0; fi
    echo "  cloning $1 @ ${3:0:12} -> $(rel "$2")"
    mkdir -p "$2" && git -C "$2" init -q && git -C "$2" remote add origin "$1" \
        && git -C "$2" fetch -q --depth 1 origin "$3" && git -C "$2" checkout -q FETCH_HEAD
}

need_uv() {
    command -v uv >/dev/null 2>&1 && return 0
    if command -v brew >/dev/null 2>&1; then brew install uv && return 0; fi
    echo "setup.sh (3d): needs uv — install Homebrew (https://brew.sh), then run this again" >&2
    return 1
}

install() {
    local name url rev miss
    [ "$(uname -m)" = arm64 ] || echo "warning: TRELLIS.2 on Mac needs Apple silicon (M1 or later)"
    if [ "$(trellis_dir)" != "$TRELLIS" ]; then
        echo "3d: using the fallback install at $(trellis_dir) (LOCAL_STUDIO_FALLBACK) — nothing to install"
        return 0
    fi
    command -v git >/dev/null 2>&1 || { echo "setup.sh (3d): needs git (xcode-select --install)" >&2; return 1; }
    need_uv || return 1
    if ! command -v blender >/dev/null 2>&1 && command -v brew >/dev/null 2>&1; then
        brew install --cask blender || echo "  Blender install failed — make3d's finish pass needs it on PATH"
    fi
    clone_at "$TRELLIS_MAC_URL" "$TRELLIS" "$TRELLIS_MAC_REV" || return 1
    clone_at "$TRELLIS2_URL" "$TRELLIS/TRELLIS.2" "$TRELLIS2_REV" || return 1
    echo "$DEPS" | while read -r name url rev; do
        clone_at "$url" "$TRELLIS/deps/$name" "$rev" || exit 1
    done || return 1
    if [ ! -x "$TRELLIS/.venv/bin/python" ]; then
        echo "  creating $(rel "$TRELLIS/.venv") (Python 3.11)"
        uv venv -q --python 3.11 "$TRELLIS/.venv" || return 1
    fi
    miss="$(missing_modules "$TRELLIS/.venv/bin/python")"
    if [ -n "$miss" ]; then
        uv pip install --python "$TRELLIS/.venv/bin/python" -r "$HERE/requirements-trellis.txt" || return 1
    fi
    if [ "${MAKE3D_METAL:-0}" = 1 ]; then
        echo "  trying the optional Metal backends (need Xcode's Metal toolchain)"
        for name in mtlbvh mtldiffrast mtlmesh mtlgemm trellis2-apple/o-voxel; do
            MACOSX_DEPLOYMENT_TARGET="${MACOSX_DEPLOYMENT_TARGET:-12.0}" \
                uv pip install --python "$TRELLIS/.venv/bin/python" --no-build-isolation "$TRELLIS/deps/$name" \
                || echo "  $name failed — make3d falls back to pure PyTorch"
        done
    fi
    if [ ! -f "$TRELLIS/.make3d-patched" ]; then
        echo "  applying trellis-mac's MPS patches to TRELLIS.2"
        (cd "$TRELLIS" && .venv/bin/python patches/mps_compat.py) || return 1
        date > "$TRELLIS/.make3d-patched"
    fi
}

hf_get() {   # hf_get <python> <cache> <repo> <revision> [pattern] — one pinned snapshot, then refs/main -> it (offline runs find it)
    "$1" - "$2" "$3" "$4" "${5:-}" <<'PY'
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

fetch() {
    local py repo rev pat rc=0
    py="$(trellis_dir)/.venv/bin/python"
    [ -x "$py" ] || { echo "setup.sh (3d): no venv yet; run --install first" >&2; return 1; }
    echo "$WEIGHTS" | { while read -r repo rev pat; do
        if hf_have "$HF_CACHE" "$repo"; then echo "  $repo already in $(rel "$HF_CACHE")"; continue; fi
        echo "  fetching $repo @ ${rev:0:12}${pat:+ ($pat)}"
        HF_HUB_OFFLINE=0 hf_get "$py" "$HF_CACHE" "$repo" "$rev" "$pat" || { echo "  fetch failed: $repo" >&2; rc=1; }
    done; exit $rc; }
}

DO_CHECK=0 DO_INSTALL=0 DO_FETCH=0
for arg in "$@"; do
    case "$arg" in
        --check) DO_CHECK=1 ;;
        --install) DO_INSTALL=1 ;;
        --fetch) DO_FETCH=1 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "setup.sh (3d): unknown argument: $arg" >&2; usage >&2; exit 2 ;;
    esac
done
if [ "$DO_INSTALL" = 0 ] && [ "$DO_FETCH" = 0 ]; then
    check
    exit $?
fi
RC=0
if [ "$DO_INSTALL" = 1 ]; then install || exit 1; fi
if [ "$DO_FETCH" = 1 ]; then fetch || RC=1; fi
echo
check || true
exit $RC
