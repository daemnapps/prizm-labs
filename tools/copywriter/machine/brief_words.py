#!/usr/bin/env python3
"""brief_words — the ad's words (primary text, headlines, descriptions) for one brief.

    brief_words.py --brand brand-a --brief brief-0001 --product crush            write them
    brief_words.py --brand brand-a --brief brief-0001 --product crush --dry-run  what would run, spends nothing
    brief_words.py --brand brand-b --brief brief-0137 --source <file.md>        from a named source

Every lane's writing step ends in a spoken script, a sequence brief or a plate —
none of which is the text Meta shows beside the ad. The copywriter already writes
that text: its stage 8 render (`**BODY A**…` under each `**FORMAT: …**`, then
**HEADLINES** and **DESCRIPTIONS**), the one source the approval card reads its
words from (components/meta-upload/card_words.py). This file routes a brief
through that same chain — `copy_writer.py`, its own prompts, unchanged — and nothing
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
    for name in _product_names(brand, product):
        for cand in (base / f"{name}.md", base / name / "product.md", base / name):
            if cand.exists():
                return str(cand.relative_to(WS))
    return None


def _product_names(brand, product):
    """The product as asked, then its catalog id and every alias (names.product_id / product_aliases): the product
    file can sit under the short name while the brief and the card carry the catalog id (2026-10-28: "nova" vs
    "nova-face-brush" left a card with no words)."""
    out = [str(product)]
    try:
        cid = N.product_id(brand, product)
        out += [cid] + list(N.product_aliases(brand, cid) or []) if cid else []
    except Exception:                                          # noqa: BLE001  the lookup is a help, never a stop
        pass
    return list(dict.fromkeys(x for x in out if x))


def _ordered_as_promo(brand, reg):
    """The brief's own order (its teardown run's vars/ask.md → ask.json) names a seasonal moment: a sale ad, so its
    words come from the promo formats (2026-10-28: a Black Friday clearance ad came back as "Meet the new NOVA lineup")."""
    run = (reg or {}).get("run")
    if not run:
        return False
    try:
        ap = (WS / "runs" / "image-teardown" / N.slug(brand) / run / "vars" / "ask.md").read_text().strip()
        ask = json.loads((WS / ap).read_text()) if ap else {}
    except (OSError, ValueError):
        return False
    return bool(ask.get("moment"))


def ordered_offer(brand, reg):
    """The offer lines the brief's order names (ask.json offer.lines), or None."""
    run = (reg or {}).get("run")
    if not run:
        return None
    try:
        ap = (WS / "runs" / "image-teardown" / N.slug(brand) / run / "vars" / "ask.md").read_text().strip()
        ask = json.loads((WS / ap).read_text()) if ap else {}
    except (OSError, ValueError):
        return None
    return list((ask.get("offer") or {}).get("lines") or []) or None


def ordered_moment(brand, reg):
    """The moment the brief's order names (its key, e.g. "black-friday"), or None."""
    run = (reg or {}).get("run")
    if not run:
        return None
    try:
        ap = (WS / "runs" / "image-teardown" / N.slug(brand) / run / "vars" / "ask.md").read_text().strip()
        ask = json.loads((WS / ap).read_text()) if ap else {}
    except (OSError, ValueError):
        return None
    m = ask.get("moment")
    return (m.get("key") if isinstance(m, dict) else m) or None


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


def awareness_for(brand, brief, product=None, header=None, reg=None):
    """The ad's awareness level as its run recorded it (the owner 2026-10-12: words written at the ad's level) — the
    brief's header first, then the production/teardown run it points at. None when nothing recorded one."""
    import copy_set as CS
    if header is None and reg is None:
        header, reg = brief_facts(brand, brief, product)
    h = {**(reg or {}), **(header or {})}
    if h.get("awareness") in CS.awareness_levels():
        return h["awareness"]
    return CS.awareness_from_run(h.get("run"))


def command(brand, brief, product, src, formats=DEFAULT_FORMATS, avatar=None, label=None, dry_run=False,
            awareness=None, promo=None):
    prod = product_path(brand, product)
    if not prod:
        raise FileNotFoundError(f"no product file for {brand} {product}")
    cmd = [sys.executable, str(HERE / "copy_writer.py"), str(src), "--brand", N.slug(brand), "--product", prod,
           "--write-as", formats, "--label", label or label_for(product, brief),
           "--source-reference", f"{N.slug(brand)} {N.brief_id(brief)} ({product})"]
    if avatar:
        cmd += ["--avatar", avatar]
    if awareness:
        cmd += ["--awareness", awareness]
    if promo:
        cmd.append("--promo")
    if dry_run:
        cmd.append("--dry-run")
    return cmd


def write(brand, brief, product=None, *, source=None, formats=DEFAULT_FORMATS, dry_run=False,
          label=None, quiet=False, awareness=None, promo=None):
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
    awareness = awareness or awareness_for(brand, brief, product, header, reg)
    if promo is None:
        import copy_set as CS
        angle = (header or {}).get("angle") or (reg or {}).get("angle")
        promo = str(angle or "").lower() == "promo" or CS.is_promo(brand, angle) or _ordered_as_promo(brand, reg)
    # Our own winning formats first (the owner, 2026-10-27: "we keep writing brand new ad copy over and over ... it's not
    # in a proven format"): a brand with a format bank (real_formats.py) gets its words by filling those formats;
    # the stage chain below runs only for a brand with no bank, for other formats asked by name, or COPY_FREEFORM=1.
    if formats == DEFAULT_FORMATS and os.environ.get("COPY_FREEFORM") != "1":
        import format_copy as FC
        res = FC.write(brand, brief, product, src, awareness=awareness, promo=bool(promo), avatar=avatar,
                       topics=(header or {}).get("problem") or (reg or {}).get("problem"), label=label,
                       dry_run=dry_run, say=(lambda *_: None) if quiet else print,
                       moment=(ordered_moment(brand, reg) or "").replace("-", " ") or None,
                       offer_lines=ordered_offer(brand, reg))
        if res is not None:
            return {"run": res["run"], "label": label, "source": f"{what}: {src}", "rc": res["rc"],
                    "words": res["words"], "formats": True}
    cmd = command(brand, brief, product, src, formats, avatar, label, dry_run, awareness, promo)
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
        # One copy set per product + angle (copy_set.py, the owner 2 Oct 2026): a brief on an
        # angle that already has a set writes nothing; a new angle writes one draft set.
        head = brief_facts(brand, brief, product)[0] or {}
        reg0 = brief_facts(brand, brief, product)[1] or {}
        # the angle is the brief's field: header, else the register entry angle_pick.py wrote (naming ANGLE.md)
        prod, angle = head.get("product") or reg0.get("product") or product, head.get("angle") or reg0.get("angle")
        if prod and angle:
            import copy_set as CS
            s = CS.load(brand, prod, angle)
            if s:
                say(f"      ad words: copy set {s['id']} v{s['version']} ({s['status']}) — nothing new written")
                return None
            reg = brief_facts(brand, brief, product)[1] or {}
            s = CS.write(brand, prod, angle, avatar=head.get("avatar"), topics=head.get("problem"),
                         awareness=awareness_for(brand, brief, product, head, reg),
                         ad_format=head.get("format") or reg.get("format"))
            say(f"      ad words: NEW ANGLE — wrote draft copy set {s['id']}, waiting on the owner's yes")
            return s
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
    ap.add_argument("--awareness", help="the ad's awareness level (doctrine id); default: what the brief's run recorded")
    ap.add_argument("--promo", action="store_true", default=None, help="a promotion / value ad (default: the angle row)")
    a = ap.parse_args()
    for b in a.brief:
        try:
            res = write(a.brand, b, a.product, source=a.source, formats=a.formats, dry_run=a.dry_run,
                        awareness=a.awareness, promo=a.promo)
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
