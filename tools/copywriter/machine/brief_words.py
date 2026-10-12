#!/usr/bin/env python3
"""brief_words — the ad's words (primary text, headlines, descriptions) for one brief.

    brief_words.py --brand brand-b --brief brief-0001 --product gadget            write them
    brief_words.py --brand brand-b --brief brief-0001 --product gadget --dry-run  what would run, spends nothing
    brief_words.py --brand brand-a --brief brief-0137 --source <file.md>        from a named source

Every lane's writing step ends in a spoken script, a sequence brief or a plate —
none of which is the text Meta shows beside the ad. The copywriter already writes
that text: its stage 8 render (`**BODY A**…` under each `**FORMAT: …**`, then
**HEADLINES** and **DESCRIPTIONS**), the one source the approval card reads its
words from (components/meta-upload/card_words.py). This file routes a brief
through that same chain — `copy.py`, its own prompts, unchanged — and nothing
else. It writes no prompt wording of its own.

The SOURCE the copywriter reads, first that exists:
  1. --source, when named;
  2. the finished ad itself — the transcript of a delivered master
     (runs/audio-teardown/<brand>/*/<unit>/transcript.md, made by
     components/audio-teardown), with the brief's own header lines on top;
  3. the brief's writing run — the video-writing brief (deliverable/7-final-brief.md,
     5-brief.md), an image/sequence teardown record (out/01-teardown.md), or a
     production run's own brief (its run.json `source_brief`).

The run files as `runs/copywriter/<brand>/<product>-<brief>-words/` — the brief's
number in the label is how the card writer finds it. Formats default to
short-form and caption (the two a feed ad carries); `--formats` names others
from bank/formats.json.

Hooked in (2 Oct 2026): the video chain's last step (tools/video-teardown/
machine/run.py, every route that wrote a brief) and the image chain's AI sequence
briefs (tools/image-teardown/chain.py). Off for one run: NO_AD_WORDS=1.
"""
import argparse, json, os, re, subprocess, sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
COPY = HERE.parent
WS = next(d for d in HERE.parents if (d / "components").is_dir() and (d / "brands").is_dir())
if str(WS / "components/naming") not in sys.path:
    sys.path.append(str(WS / "components/naming"))
import names as N  # noqa: E402

DEFAULT_FORMATS = "short-form,caption"
AUDIO_RUNS = WS / "runs" / "audio-teardown"


def off():
    return os.environ.get("NO_AD_WORDS") == "1"


def label_for(product, brief):
    return f"{N.slug(product) if product else 'none'}-{N.brief_id(brief)}-words"


def product_path(brand, product):
    """The product file the copywriter reads, workspace-relative (a file or a product folder)."""
    base = WS / "brands" / N.slug(brand) / "products"
    for cand in (base / f"{product}.md", base / product / "product.md", base / product):
        if cand.exists():
            return str(cand.relative_to(WS))
    return None


def brief_facts(brand, brief, product=None):
    """(header, register record) for the brief — either may be None."""
    hit = N.find_brief(brand, brief, product)
    if not hit:
        return None, None
    reg = hit.get("register")
    return hit.get("header"), ({k: v for k, v in reg.items() if k not in ("key", "_table")} if reg else None)


def transcript_for(brand, product, brief):
    """The newest delivered-master transcript for this brief, or None."""
    unit_pat = f"{N.slug(brand)}_{N.slug(product)}_{N.brief_id(brief)}_"
    hits = sorted((p for p in (AUDIO_RUNS / N.slug(brand)).glob(f"*/{unit_pat}*/transcript.md")),
                  key=lambda p: p.stat().st_mtime) if (AUDIO_RUNS / N.slug(brand)).is_dir() else []
    return hits[-1] if hits else None


def run_source(run, brand):
    """The writing a brief's run left behind, best first."""
    if not run:
        return None
    r = Path(str(run))
    roots = [WS / r] if "/" in str(run) else [
        WS / "runs/video-writing" / brand / str(run), WS / "runs/video-teardown" / brand / str(run),
        WS / "runs/image-teardown" / brand / str(run), WS / "tools/image-teardown/runs" / str(run)]
    for d in roots:
        for f in ("deliverable/7-final-brief.md", "deliverable/5-brief.md", "stages/7-final-brief.md",
                  "stages/5-brief.md", "brief.md", "out/01-teardown.md"):
            if (d / f).is_file():
                return d / f
        rj = d / "run.json"
        if rj.is_file():
            try:
                sb = json.loads(rj.read_text()).get("source_brief")
            except ValueError:
                sb = None
            if sb and (d / sb).is_file():
                return d / sb
    return None


def header_lines(brand, brief, header, reg):
    """The brief's own facts, as plain lines on top of a transcript source."""
    h = {**(reg or {}), **(header or {})}
    out = [f"# {h.get('title') or brief} — {N.slug(brand).upper()} {N.brief_id(brief)} (our finished ad)", ""]
    for k in ("product", "avatar", "problem", "angle", "concept", "format", "type"):
        if h.get(k):
            out.append(f"- {k}: {h[k]}")
    out += ["", "This is the finished ad as delivered — every spoken word, from its audio.", ""]
    return "\n".join(out)


def source_for(brand, brief, product=None, source=None):
    """(path to the source the copywriter reads, what it is). Writes a small
    composed file beside a transcript (its header + the transcript)."""
    if source:
        return Path(source), "named"
    header, reg = brief_facts(brand, brief, product)
    product = product or (header or {}).get("product") or (reg or {}).get("product")
    t = transcript_for(brand, product, brief) if product else None
    if t:
        comp = t.parent / "copy-source.md"
        text = header_lines(brand, brief, header, reg) + t.read_text()
        if not comp.is_file() or comp.read_text() != text:
            comp.write_text(text)
        return comp, f"the delivered ad's transcript ({t.parent.name})"
    s = run_source((reg or {}).get("run") or (header or {}).get("run"), N.slug(brand))
    if s:
        return s, f"the brief's writing run ({s.relative_to(WS)})"
    return None, "no source: no delivered transcript and no writing run on the brief"


def command(brand, brief, product, src, formats=DEFAULT_FORMATS, avatar=None, label=None, dry_run=False):
    prod = product_path(brand, product)
    if not prod:
        raise FileNotFoundError(f"no product file for {brand} {product}")
    cmd = [sys.executable, str(HERE / "copy.py"), str(src), "--brand", N.slug(brand), "--product", prod,
           "--write-as", formats, "--label", label or label_for(product, brief),
           "--source-reference", f"{N.slug(brand)} {N.brief_id(brief)} ({product})"]
    if avatar:
        cmd += ["--avatar", avatar]
    if dry_run:
        cmd.append("--dry-run")
    return cmd


def write(brand, brief, product=None, *, source=None, formats=DEFAULT_FORMATS, dry_run=False,
          label=None, quiet=False):
    """Run the copywriter for one brief. Returns {"run", "label", "source", "rc", "words"}."""
    brand = N.slug(brand)
    header, reg = brief_facts(brand, brief, product)
    if header is None and reg is None and not source:
        raise KeyError(f"{brand} {brief}: no such brief")
    product = product or (header or {}).get("product") or (reg or {}).get("product")
    src, what = source_for(brand, brief, product, source)
    if not src:
        return {"run": None, "label": None, "source": what, "rc": None, "words": None}
    avatar = (header or {}).get("avatar") or (reg or {}).get("avatar")
    avatar = avatar if avatar and N.SLUG.match(str(avatar)) else None
    label = label or label_for(product, brief)
    cmd = command(brand, brief, product, src, formats, avatar, label, dry_run)
    r = subprocess.run(cmd, cwd=str(COPY), capture_output=quiet, text=True)
    run = WS / "runs" / "copywriter" / brand / label
    words = None
    if not dry_run and (run / "stage8--render.md").is_file():
        sys.path.insert(0, str(WS / "components/meta-upload"))
        import card_words as W
        words = W.from_runs([run])
    return {"run": run, "label": label, "source": f"{what}: {src}", "rc": r.returncode, "words": words}


def auto(brand, brief, product=None, *, source=None, say=print):
    """The hooks' door: write the words unless NO_AD_WORDS=1 or a run already
    holds them. Never raises — a lane's run is whole without its words."""
    try:
        if off():
            say(f"      ad words: off (NO_AD_WORDS=1) for {brief}")
            return None
        label = label_for(product, brief)
        if (WS / "runs/copywriter" / N.slug(brand) / label / "stage8--render.md").is_file():
            say(f"      ad words: already written ({label})")
            return None
        res = write(brand, brief, product, source=source, quiet=True)
        if res["rc"] is None:
            say(f"      ad words: SKIPPED — {res['source']}")
        else:
            w = res["words"] or {}
            say(f"      ad words: {len(w.get('primary') or [])} primary, {len(w.get('headlines') or [])} headlines, "
                f"{len(w.get('descriptions') or [])} descriptions → runs/copywriter/{N.slug(brand)}/{res['label']}"
                + ("" if res["rc"] == 0 else f" (copywriter stopped, rc {res['rc']})"))
        return res
    except Exception as e:                      # noqa: BLE001
        say(f"      ad words: SKIPPED — {str(e)[:160]}")
        return None


def for_writing_run(d, brand, product=None, say=print):
    """The video chain's hook: a run that wrote a brief gets its ad words, labelled
    by the run (the brief number is issued later; card_words also finds a copy
    run by the folder its source sits in)."""
    if off():
        return None
    d = Path(d)
    src = next((d / f for f in ("deliverable/7-final-brief.md", "stages/7-final-brief.md", "7-final-brief.md",
                                "deliverable/5-brief.md", "stages/5-brief.md") if (d / f).is_file()), None)
    if not src or not product:
        return None
    label = f"{N.slug(d.name)}-words"
    if (WS / "runs/copywriter" / N.slug(brand) / label / "stage8--render.md").is_file():
        return None
    try:
        cmd = command(brand, d.name, product, src, label=label)
    except (FileNotFoundError, ValueError) as e:
        say(f"      ad words: SKIPPED — {e}")
        return None
    r = subprocess.run(cmd, cwd=str(COPY), capture_output=True, text=True)
    say(f"      ad words: {'written' if r.returncode == 0 else 'stopped (rc ' + str(r.returncode) + ')'} → runs/copywriter/{N.slug(brand)}/{label}")
    return r.returncode


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--brief", required=True, nargs="+")
    ap.add_argument("--product")
    ap.add_argument("--source", help="the source file to write from (default: found from the brief)")
    ap.add_argument("--formats", default=DEFAULT_FORMATS, help=f"copywriter formats (default {DEFAULT_FORMATS})")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    for b in a.brief:
        try:
            res = write(a.brand, b, a.product, source=a.source, formats=a.formats, dry_run=a.dry_run)
        except (KeyError, FileNotFoundError, N.AmbiguousBrief) as e:
            print(f"{b}: {e}")
            continue
        print(f"{b}: source — {res['source']}")
        if res["words"]:
            w = res["words"]
            print(f"   {len(w['primary'])} primary · {len(w['headlines'])} headlines · {len(w['descriptions'])} descriptions"
                  f" → {res['run'].relative_to(WS)}")


if __name__ == "__main__":
    main()
