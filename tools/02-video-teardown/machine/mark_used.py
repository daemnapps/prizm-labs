#!/usr/bin/env python3
"""5u · MARK USED — the customer language this asset used, recorded.

Damon, 2026-09-28: "anytime any of that language is used, we clearly mark it
as used in X asset, right? We can index and search between things that have
been used and things that have not been used, and then we can get
performance metrics on what has been used."

Runs after the brief, on every chain. Two ways a row counts as used:

  cited    a stage handed language rows ends with `LANGUAGE USED:` and names
           the row's id (injection, hooks, expansion)
  matched  the row's words appear verbatim in the brief (rows of four words
           or more; shorter rows only count when cited)

Writes ONE file per asset per avatar into the language folder's used lane —
brands/<brand>/core-avatars/<avatar>/language/used/<run slug>.json, shaped as
brands/language-schema.md "The used lane" says. A bank row is never edited.
No model.

    python3 mark_used.py <run dir>        (re-mark a finished run by hand)
"""
import json, re, sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain as C  # noqa: E402

# stage key -> where it shows in the record (the board's display id)
WHERE = [("stage3", "3"), ("stage3v", "3v"), ("stage4b", "4b"), ("stage4c", "4d"),
         ("stage4d", "4e"), ("stage4g", "4g"), ("stage5", "5")]
BLOCK = re.compile(r"^LANGUAGE USED:[ \t]*(.*?)(?=^\S[^\n]*:\s*$|^## |\Z)", re.M | re.S)
LINE = re.compile(r"^\s*[-*]\s*\[?([A-Za-z0-9][\w.\-]*)\]?\s*(?:\|\s*(.*))?$", re.M)
MIN_WORDS = 4
STOP = set("a an the is it its this that to of in on for and or but so you your i me my he his she her we they them be was are with at as by do did just".split())


def _norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[\"“”‘’'`*_]", "", (s or "").lower())).strip()


def _clean(s):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s']", " ", (s or "").lower())).strip()


def cited(text):
    """[(row_id, words)] from a stage output's LANGUAGE USED block(s)."""
    out = []
    for m in BLOCK.finditer(text or ""):
        body = m.group(1)
        if body.strip().lower().startswith("none"):
            continue
        for lm in LINE.finditer(body):
            out.append((lm.group(1), (lm.group(2) or "").strip()))
    return out


def picked_lines(hooks_text, pick):
    return _norm(C.hook_lines(hooks_text, pick))


def collect(d, st, rows_by_id):
    """-> {row_id: record} for run folder d."""
    outs = {}
    for key, where in WHERE:
        rec = st.get("stages", {}).get(key) or {}
        if rec.get("status") in ("done", "held") and rec.get("out") and (Path(d) / rec["out"]).is_file():
            outs[key] = (where, (Path(d) / rec["out"]).read_text())
    pick = str(st.get("hook_pick") or "").upper()
    used = {}
    for key, (where, text) in outs.items():
        for rid, words in cited(text):
            row = rows_by_id.get(rid)
            if not row:
                continue                                  # an id the bank does not hold
            if key == "stage4b" and pick:
                # a leaf writes one hook through: only that hook's rows are this asset's
                mine = picked_lines(text, pick)
                probe = _norm(words) or _norm(row.get("text"))
                if probe and probe not in mine:
                    continue
            used.setdefault(rid, dict(row_id=rid, text=row.get("text"), avatar=row.get("avatar"),
                                      where=where, how="cited", results=None))
    # The hook this asset opens on: its fills often come from the room's short
    # comment rows (two or three words and an emoji) that the brief match below
    # is too strict for. The picked hook's own LINE and CARD are matched against
    # the bank at two words and up (Damon, 2026-09-28: "give me the sources").
    hooks_text = outs.get("stage4b", (None, ""))[1]
    if hooks_text:
        lines = re.findall(r"^(?:LINE|CARD) " + re.escape(pick or "V0") + r":[ \t]*(.+)$", hooks_text, re.M)
        mine = " " + _clean(" ".join(lines)) + " "
        if mine.strip():
            for rid, row in rows_by_id.items():
                if rid in used:
                    continue
                words = _clean(row.get("text")).split()
                # a run of three or more of the row's own words, in order, in the hook
                if len(words) >= 3 and any(" " + " ".join(words[i:i + 3]) + " " in mine
                                           and sum(w not in STOP for w in words[i:i + 3]) >= 2
                                           for i in range(len(words) - 2)):
                    used[rid] = dict(row_id=rid, text=row.get("text"), avatar=row.get("avatar"),
                                     where="4b", how="matched", results=None)
    brief = outs.get("stage5", (None, ""))[1]
    nb = _norm(brief)
    if nb:
        for rid, row in rows_by_id.items():
            if rid in used:
                continue
            t = _norm(row.get("text"))
            if len(t.split()) >= MIN_WORDS and len(t) <= 400 and t in nb:
                used[rid] = dict(row_id=rid, text=row.get("text"), avatar=row.get("avatar"),
                                 where="5", how="matched", results=None)
    return used


def chain_of(st):
    lane = (st.get("triage_lane") or "").upper()
    return {"VARIATION": "variation-video", "FRAMEWORK": "framework"}.get(lane, "new-video")


def run(d, st, out=None):
    import language as L                                  # the language layer, via this machine's shim
    brand = st["brand"]
    rows = L.load(brand)
    by_id = {r["id"]: r for r in rows if r.get("id")}
    used = collect(d, st, by_id)
    base = L.bank_dir(L.brand_dir(brand))
    written = []
    by_av = {}
    for u in used.values():
        by_av.setdefault(u.get("avatar") or "_unattributed", []).append(u)
    run_rel = str(Path(d).resolve().relative_to(C.WS)) if str(Path(d).resolve()).startswith(str(C.WS)) else str(d)
    for av, items in sorted(by_av.items()):
        home = base / av / "language" / "used"
        if not (base / av).is_dir():
            continue                                      # never create an avatar folder
        home.mkdir(parents=True, exist_ok=True)
        f = home / f"{st['slug']}.json"
        f.write_text(json.dumps(dict(
            schema=1, kind="language-used", asset=st.get("ad_name") or st["slug"], run=run_rel,
            chain=chain_of(st), leaf=st.get("variation_leaf"), written=date.today().isoformat(),
            state="drafted",
            used=[{k: v for k, v in u.items() if k != "avatar"} for u in
                  sorted(items, key=lambda x: (x["where"], x["row_id"]))]),
            indent=1, ensure_ascii=False) + "\n")
        written.append(str(f.relative_to(C.WS)))
    n_c = sum(1 for u in used.values() if u["how"] == "cited")
    n_m = len(used) - n_c
    st["used_lane"] = dict(rows=len(used), cited=n_c, matched=n_m, files=written)
    if out:
        lines = [f"# 5 u · Mark used", "",
                 f"**{len(used)} language rows** marked used in this asset — {n_c} cited by a stage, "
                 f"{n_m} matched verbatim in the brief.", ""]
        for f in written:
            lines.append(f"- `{f}`")
        lines += ["", "| Row | Where | How | Words |", "|---|---|---|---|"]
        for u in sorted(used.values(), key=lambda x: (x["where"], x["row_id"])):
            lines.append(f"| `{u['row_id']}` | {u['where']} | {u['how']} | "
                         f"{(u.get('text') or '').replace('|', '/').strip()[:140]} |")
        if not used:
            lines.append("| — | — | — | nothing from the bank was used |")
        Path(out).write_text("\n".join(lines) + "\n")
    return "none (mark_used.py)"


if __name__ == "__main__":
    d = Path(sys.argv[1]).resolve()
    st = json.loads((d / "run.json").read_text())
    run(d, st, None)
    print(json.dumps(st.get("used_lane"), indent=1))
