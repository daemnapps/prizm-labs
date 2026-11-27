#!/usr/bin/python3
"""The mini's door into local-studio's upscale job — a lab-run turns a request into this call.

    lab-run → lab_entry.py --input <file> --label L [--scale 2|4] [--dry_run yes|no]
            → local.py upscale <input> -o $OUT/<label>/<stem>-up<suffix> --scale N

Why it is hand-written (LD-7 (four more doors)): local.py's upscale (local.py:303-305)
takes `-o FILE`, no --brand and no --dry-run, none of which a lab_door.json
manifest expresses; the argument pairs and the in-checkout path check are
run-kit's shared door (run_kit/lab_door.py), reused here rather than copied.
local.py finds the Real-ESRGAN models itself (esrgan_places(), :58-69) — nothing
is passed for them. --dry_run yes prints the command and runs nothing.

Refuses (exit 2, named, before anything runs): a missing $OUT; --engine (the
job's default engine only) and every argument but the four above; a value
starting with `-`; an --input with a `..` part, outside this checkout, not
there or not a file; a --scale other than 2 or 4; a missing or malformed
--label; an existing $OUT/<label>/. $BRAND is not read — the job has no brand.
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent                # components/local-studio → repo root (local.py REPO, :38)
sys.path.append(str(REPO / "components" / "run-kit"))
from run_kit import lab_door as D        # noqa: E402  pairs, repo_path, refused_by, Refused, NAME

ACCEPTS = ("input", "label", "scale", "dry_run")
REFUSE = ("engine",)
SCALES = ("2", "4")


def upscale_argv(picture, dest, scale):
    return [sys.executable, str(HERE / "local.py"), "upscale", str(picture),
            "-o", str(dest / f"{picture.stem}-up{picture.suffix}"), "--scale", scale]


def main(argv=None, env=None, run=subprocess.call, repo=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    env = os.environ if env is None else env
    repo = Path(repo).resolve() if repo else REPO
    try:
        args = D.pairs(argv)
        for name in args:
            hit = D.refused_by(name, REFUSE)
            if hit:
                raise D.Refused(f"--{name} is refused by this door ({hit}) — upscale runs on its default engine")
        unknown = sorted(set(args) - set(ACCEPTS))
        if unknown:
            raise D.Refused(f"unknown argument(s) {', '.join('--' + u for u in unknown)}; "
                            "this door takes --input, --label, --scale and --dry_run")
        for name, value in args.items():
            if value.startswith("-"):
                raise D.Refused(f"--{name} {value!r} starts with '-' and would read as a flag")
        if not env.get("OUT"):
            raise D.Refused("$OUT not set — lab-run sets it; run local.py upscale directly by hand")
        out = Path(env["OUT"])
        label = args.get("label", "")
        if not D.NAME.fullmatch(label):
            raise D.Refused(f"--label {label!r}: a plain name is required — the result lands in $OUT/<label>/")
        if not args.get("input"):
            raise D.Refused("--input is required (a repo-relative file)")
        picture = D.repo_path(repo, "input", args["input"])
        if not picture.is_file():
            raise D.Refused(f"--input {args['input']} is not a file ({picture})")
        scale = args.get("scale", "2").strip()
        if scale not in SCALES:
            raise D.Refused(f"--scale {scale!r}: 2 or 4")
        dry = args.get("dry_run", "").strip().lower()
        if dry not in D.YES and dry not in D.NO:
            raise D.Refused(f"--dry_run {args['dry_run']!r}: say yes or no")
        dest = out / label
        if dest.exists():
            raise D.Refused(f"{dest} already exists — refusing to overwrite it")
    except D.Refused as e:
        print(f"lab_entry: {e}")
        return 2
    cmd = upscale_argv(picture, dest, scale)
    if dry in D.YES:
        print("dry run — would run: " + " ".join(cmd))
        return 0
    dest.mkdir(parents=True)
    print("running: " + " ".join(cmd))
    return run(cmd, env=dict(env))


if __name__ == "__main__":
    sys.exit(main())
