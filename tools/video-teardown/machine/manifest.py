"""THE BRIEF MANIFEST — the last page of every brief (2026-09-24).

the owner: "There needs to be a manifest at the end of every brief to make sure
teardown record, and final brief has the core elements that literally make
this ad work before we can go into ai production — i do not have time to
babysit this anymore."

One table, written onto the end of the brief, answering every question that
has cost a run so far:

    the swipe's core elements   every ELEMENT of the replication spec (E1…) and
                                every LOAD-BEARING item (L1…), each pointed at
                                the brief scene that carries it — a judge reads
                                the spec and the brief, quoting the brief
    the swipe's structure       the swipe-match stamp (places, people, camera,
                                order — swipe_match.py)
    the cast and elements       every person, look, voice, place, product and
                                prop the brief names, banked or not
                                (video-production's elements check)
    every price and figure      each $ figure in a line, card or screen is found
                                in the brand's own files, or it is flagged

The last line says `MANIFEST: COMPLETE` or `MANIFEST: MISSING — …`, tied to the
brief's fingerprint. video-production's `run.py start` refuses a brief whose
manifest is not COMPLETE for this exact brief. A missing core element can only
pass on the owner's number (`--approve-structure E6`), never quietly.

The judge's answer is kept in `manifest.json` beside the run, keyed to the
brief's fingerprint, so a re-check never re-asks and never renumbers.
Brand-agnostic: it reads the run's own spec, its brief and `brands/<brand>/`.

    python3 manifest.py <teardown run dir> [--approve-structure E6,L2]
"""
import argparse, importlib.util, json, os, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]
# the writing station's prompts live in the copywriter since 2026-09-30
PROMPTS = next((d for d in (HERE.parents[1] / "copywriter" / "prompts" / "video" / "stage-5n-manifest",
                           HERE.parent / "prompts" / "stage-5n-manifest") if d.is_dir()),
               HERE.parents[1] / "copywriter" / "prompts" / "video" / "stage-5n-manifest")
MODEL = "gemini-3.1-pro-preview"
BLOCK = re.compile(r"\n?<!-- manifest -->.*?<!-- /manifest -->\n?", re.S)
LINE = re.compile(r"^MANIFEST: (COMPLETE|MISSING)[^\n]*· ([0-9a-f]{16})$", re.M)


def _load(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return m


SM = _load("swipe_match", HERE / "swipe_match.py")


def strip(text):
    return BLOCK.sub("\n", text).rstrip() + "\n"


def prompt_file():
    files = sorted(PROMPTS.glob("manifest-v*-damon.md"),
                   key=lambda p: int(re.search(r"-v(\d+)-", p.name).group(1)))
    return files[-1]


def spec_part(spec):
    """The element inventory and the load-bearing list — what makes the swipe work."""
    out = []
    for head in ("ELEMENT INVENTORY", "LOAD-BEARING"):
        m = re.search(r"(\*\*\d+\.\s*(?:THE\s+)?" + head + r".*?)(?=\n\*\*\d+\.|\Z)", spec, re.S | re.I)
        if m:
            out.append(m.group(1).strip())
    return "\n\n".join(out) or spec


def ask_judge(spec, brief):
    g = SM._gemini_tools()
    k = g.key()
    text = prompt_file().read_text().replace("{spec}", spec_part(spec)).replace("{brief}", brief)
    last = ""
    for _ in range(3):
        try:
            r = g.req(f"{g.BASE}/v1beta/models/{MODEL}:generateContent?key={k}",
                      data=json.dumps({"contents": [{"parts": [{"text": text}]}],
                                       "generationConfig": {"responseMimeType": "application/json",
                                                            "temperature": 0, "seed": 7}}).encode(),
                      headers={"Content-Type": "application/json"})
            raw = "".join(p.get("text", "") for p in r["candidates"][0]["content"]["parts"])
            return json.loads(re.search(r"\{.*\}", raw, re.S).group(0))
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:300]}"
    raise RuntimeError(f"the manifest judge could not answer — {last}")


def elements_rows(brief, brand):
    ec = _load("elements_check", WS / "tools" / "video-production" / "machine" / "elements_check.py")
    try:
        sh = ec.sheet(brief, brand)
    except Exception as e:
        return [{"what": "the elements check", "ok": False, "note": f"could not run: {e}"}]
    rows = []
    for it in sh.get("items", []):
        ok = it.get("status") == "banked" and not it.get("missing")
        rows.append({"what": f"{it.get('kind')} · {it.get('id')}", "ok": ok,
                     "note": (it.get("folder") or it.get("bank_id") or "banked") if ok else ("; ".join(it.get("missing") or []) or "to make")})
    for g_ in sh.get("brief_gaps") or []:
        rows.append({"what": "brief", "ok": False, "note": str(g_)})
    return rows


def price_rows(brief, brand):
    """Every $ figure the viewer hears or reads must be in the brand's own files."""
    doc = SM.json.loads(re.findall(r"```json\s*\n(.*?)\n```", brief, re.S)[-1]) if "```json" in brief else {}
    said = []
    for s in doc.get("scenes") or []:
        bits = [s.get("voice") or "", json.dumps(s.get("screen") or {}), json.dumps(s.get("endcard") or {}),
                " ".join(s.get("lines") or []), s.get("on_screen") if isinstance(s.get("on_screen"), str) else ""]
        for f in re.findall(r"\$\s?\d[\d,]*(?:\.\d+)?", " ".join(bits)):
            said.append((s["id"], f.replace(" ", "")))
    home = WS / "brands" / brand
    corpus = "\n".join(p.read_text(errors="ignore") for p in home.rglob("*.md"))
    rows, seen = [], set()
    for sid, f in said:
        if f in seen:
            continue
        seen.add(f)
        rows.append({"what": f"{f} ({sid})", "ok": f in corpus,
                     "note": "in the brand's files" if f in corpus else "NOT in any brands/" + brand + " file — invented or stale"})
    return rows


def hole_rows(brief):
    """A blank left in anything the viewer hears or reads is missing, never
    carried (2026-09-24: a receipt with an [UNFILLED] price passed as 'the price
    redefinition'). The funnel link is the one exception — it is set at the
    edit, so it is listed, not held."""
    blocks = re.findall(r"```json\s*\n(.*?)\n```", brief, re.S)
    doc = json.loads(blocks[-1]) if blocks else {}
    rows = []
    for s in doc.get("scenes") or []:
        parts = {"voice": s.get("voice") or "", "on_screen": s.get("on_screen") if isinstance(s.get("on_screen"), str) else "",
                 "lines": " ".join(s.get("lines") or []), "screen": json.dumps((s.get("screen") or {}).get("lines") or []),
                 "offer": json.dumps({k: (s.get("endcard") or {}).get(k) for k in ("offer_lines", "guarantee")})}
        for where, txt in parts.items():
            for m in re.findall(r"\[(?:UNFILLED|SLOT)[^\]]*\]", txt or ""):
                rows.append({"what": f"{s['id']} {where}: {m}", "ok": False, "note": "a blank the viewer would hear or read"})
        cta = (s.get("endcard") or {}).get("cta") or ""
        if "[UNFILLED" in cta:
            rows.append({"what": f"{s['id']} link: {cta}", "ok": True, "note": "fill before the edit — the link is set as text at the edit, not in any frame"})
    return rows


def check(run_dir, brand=None, brief_name="5-brief.md"):
    d = Path(run_dir)
    brief_p = d / "stages" / brief_name
    spec_p = SM.teardown_stage(d, "2-spec.md")
    st = json.loads((d / "run.json").read_text()) if (d / "run.json").exists() else {}
    brand = brand or st.get("brand")
    text = strip(brief_p.read_text())
    h = SM.brief_hash(text)
    rec_p = d / "manifest.json"
    rec = json.loads(rec_p.read_text()) if rec_p.exists() else {}
    if rec.get("brief_hash") != h:
        if not spec_p.exists():
            raise RuntimeError("no replication spec in the run — the manifest has nothing to hold the brief to")
        rec = {"brief_hash": h, "prompt": prompt_file().name, "model": MODEL,
               "judge": ask_judge(spec_p.read_text(), SM.unstamped(text))}
    ok = SM.approved()
    core = []
    for e in rec["judge"].get("elements", []) + rec["judge"].get("load_bearing", []):
        fine = bool(e.get("carried")) or ok == "all" or e.get("id") in ok
        core.append({**e, "ok": fine, "approved": (not e.get("carried")) and fine})
    stamp = SM.stamp_of(text)
    els = elements_rows(text, brand)
    prices = price_rows(text, brand)
    holes = hole_rows(text)
    missing = ([r["what"] for r in holes if not r["ok"]] + [e["id"] for e in core if not e["ok"]]
               + (["swipe match"] if stamp != "PASSED" else [])
               + [r["what"] for r in els if not r["ok"]]
               + [r["what"] for r in prices if not r["ok"]])
    rec.update({"passed": not missing, "missing": missing,
                "to_make": [r["what"] for r in els if not r["ok"]],
                "core_missing": [e["id"] for e in core if not e["ok"]] + [r["what"] for r in prices if not r["ok"]] + [r["what"] for r in holes if not r["ok"]]
                                + (["swipe match"] if stamp != "PASSED" else [])})
    rec_p.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")

    tick = lambda b: "✅" if b else "❌"
    md = ["<!-- manifest -->", "", "## MANIFEST — what makes this ad work, checked before production", "",
          "### The swipe's core elements (replication spec) → where the brief carries them", "",
          "| # | Element | Carried | Where | How |", "|---|---|---|---|---|"]
    for e in core:
        name = e.get("element") or e.get("item") or ""
        mark = tick(e["ok"]) + (" (approved by the owner)" if e["approved"] else "")
        md.append(f"| {e.get('id')} | {name} | {mark} | {', '.join(e.get('where') or [])} | {str(e.get('how') or '').replace('|', '/')} |")
    md += ["", "### The swipe's structure", "", f"- {tick(stamp == 'PASSED')} swipe match: {stamp or 'never checked'} (places, people, camera, order)",
           "", "### Cast and elements", "", "| | Element | Banked as |", "|---|---|---|"]
    md += [f"| {tick(r['ok'])} | {r['what']} | {r['note']} |" for r in els]
    md += ["", "### Every price and figure", ""]
    md += [f"- {tick(r['ok'])} {r['what']} — {r['note']}" for r in prices] or ["- (no figures in the brief)"]
    md += ["", "### Blanks", ""]
    md += [f"- {tick(r['ok'])} {r['what']} — {r['note']}" for r in holes] or ["- ✅ none — every line is filled"]
    status = "COMPLETE" if not missing else "MISSING — " + ", ".join(missing)
    md += ["", f"MANIFEST: {status} · {h}", "", "<!-- /manifest -->", ""]
    brief_p.write_text(text.rstrip() + "\n\n" + "\n".join(md))
    return not missing, missing


def status_of(brief_text):
    """What production reads: 'COMPLETE', 'MISSING', 'STALE' or None."""
    m = LINE.search(brief_text)
    if not m:
        return None
    return m.group(1) if m.group(2) == SM.brief_hash(strip(brief_text)) else "STALE"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run_dir")
    ap.add_argument("--brand")
    ap.add_argument("--brief", default="5-brief.md")
    ap.add_argument("--approve-structure", default="")
    a = ap.parse_args()
    if a.approve_structure:
        os.environ["DAEMN_STRUCTURE_APPROVALS"] = a.approve_structure
    passed, missing = check(a.run_dir, a.brand, a.brief)
    print("MANIFEST:", "COMPLETE" if passed else "MISSING — " + ", ".join(missing))
    sys.exit(0 if passed else 1)
