"""The two records the page system takes as input — agreed with the page-system session 2026-11-14.

    hypothesis.json   one big swing for a 50/50 test (`briefs.py page --hypothesis <file>`: a variant page brief and a
                      draft test, gated on the owner's dated approval). Up to three per page per teardown, each with
                      rank 1–3, value_usd_month and its basis: swings/swing-N/hypothesis.json; the run's hypothesis.json
                      is the owner's pick (rank 1 until he picks).
    fixes.json        the team's fix list for one page (page-change: a page brief with job "new-control" builds vN
                      against the control named here; it goes live on a compliance pass and an approver's dated click,
                      then becomes the control; refused while the page has a test draft or live, once the control has
                      moved, or for an archived page).

`build` / `build_fixes` assemble them, `check` / `check_fixes` refuse a record that breaks its contract. Every yes
happens at the approval card, never here: `status` is always "draft" when written.
"""
import re

ID_RE = re.compile(r"^[a-z0-9-]+_[a-z0-9-]+_[a-z0-9-]+$")
VERSION_RE = re.compile(r"^v[1-9][0-9]*$")
TYPES = ("design", "offer")
SOURCES = ("all", "ads", "email", "creator", "bio")
DEVICES = ("all", "mobile", "desktop")
STOP_KEYS = ("min_days", "max_days", "min_visitors_per_group", "max_visitors_per_group", "min_orders_per_group",
             "decide", "early_stop", "at_cap")


def clips_of(written_clips, links=None):
    links = links or {}
    out = []
    for c in (written_clips or [])[:3]:
        clip = {"recording_id": c["recording_id"], "at_s": int(c.get("at_s") or 0), "note": c.get("note", "")}
        link = links.get((c["recording_id"], clip["at_s"]))
        if link:
            clip["replay"] = link
        out.append(clip)
    return out


def evidence(leak, picked, patterns, clips, window="", source="all", device="all", clarity=None):
    """The evidence block both records carry."""
    return {
        "leak": {"step": leak["step"], "visitors": leak["visitors"], "reached_next": leak["reached_next"],
                 "revenue_per_visitor": leak["revenue_per_visitor"], "window": window,
                 "source": source, "device": device},
        "recordings": {"left": len(picked["left"]), "converted": len(picked["converted"])},
        "patterns": [{"pattern": p["pattern"], "left": int(p["left"]), "converted": int(p["converted"])}
                     for p in patterns],
        "clips": clips,
        "clarity": clarity,
    }


def build(hyp_id, page, leak, picked, patterns, written, stop, by, clarity=None, links=None,
          source="all", device="all", window="", rank=1, value_usd_month=0.0, basis=""):
    ctl = page["control"]
    return {
        "id": hyp_id, "kind": "hypothesis", "page_id": page["page_id"], "type": written["type"],
        "control": {"version": ctl["version"], "path": ctl["path"], "offer": ctl.get("offer", "")},
        "variant_offer": written.get("variant_offer") or ctl.get("offer", ""),
        "hypothesis": written["hypothesis"], "change": written["change"],
        "primary_metric": "checkout_reached", "confirm_metric": "purchase",
        "rank": rank, "value_usd_month": round(float(value_usd_month or 0), 2), "basis": basis,
        "stop": dict(stop),
        "evidence": evidence(leak, picked, patterns, clips_of(written.get("clips"), links), window, source, device,
                             clarity),
        "by": by,
        "status": "draft",
    }


def check(rec):
    """Every way a record can break the contract, as plain sentences. Empty list = it passes."""
    bad = []
    for k in ("id", "kind", "page_id", "type", "control", "variant_offer", "hypothesis", "change", "primary_metric",
              "confirm_metric", "stop", "evidence", "by", "status"):
        if k not in rec:
            bad.append("missing " + k)
    if bad:
        return bad
    if rec["kind"] != "hypothesis":
        bad.append("kind must be hypothesis")
    if not ID_RE.match(rec["page_id"]):
        bad.append("page_id is not <brand>_<place>_<page>")
    if rec["type"] not in TYPES:
        bad.append("type must be design or offer")
    if not VERSION_RE.match(rec["control"].get("version", "")):
        bad.append("control version must be vN")
    same = str(rec["variant_offer"]) == str(rec["control"].get("offer", ""))
    if rec["type"] == "design" and not same:
        bad.append("a design test keeps the control's offer")
    if rec["type"] == "offer" and same:
        bad.append("an offer test changes the offer")
    for k in ("hypothesis", "change"):
        if len(str(rec[k]).strip()) < 12:
            bad.append(k + " is empty or too short")
    if rec["primary_metric"] != "checkout_reached" or rec["confirm_metric"] != "purchase":
        bad.append("metrics must be checkout_reached / purchase")
    if rec.get("rank") not in (1, 2, 3):
        bad.append("rank must be 1, 2 or 3 (at most three big swings per page per teardown)")
    if not isinstance(rec.get("value_usd_month"), (int, float)) or rec["value_usd_month"] < 0:
        bad.append("value_usd_month must be a number, 0 or more")
    if len(str(rec.get("basis") or "").strip()) < 12:
        bad.append("basis must say how the dollar figure was worked out")
    for k in STOP_KEYS:
        if k not in rec["stop"]:
            bad.append("stop is missing " + k)
    bad += check_evidence(rec["evidence"])
    if rec["status"] != "draft":
        bad.append("status is written as draft; the yes happens at the approval card")
    return bad


def check_evidence(ev):
    bad = []
    n_left, n_conv = ev["recordings"]["left"], ev["recordings"]["converted"]
    if ev["leak"]["source"] not in SOURCES or ev["leak"]["device"] not in DEVICES:
        bad.append("leak source/device not a known value")
    if not ev["patterns"]:
        bad.append("no patterns: a record needs evidence")
    for p in ev["patterns"]:
        if not (0 <= p["left"] <= n_left and 0 <= p["converted"] <= n_conv):
            bad.append("pattern counts exceed the recordings read: " + p["pattern"][:40])
    if len(ev["clips"]) > 3:
        bad.append("at most 3 clips")
    return bad


# ---------------------------------------------------------------- the fix list (the team's half)
FIX_TYPES = ("copy", "design", "bug", "speed")
EFFORTS = ("s", "m", "l")
FIX_ID_RE = re.compile(r"^[a-z0-9-]+_[a-z0-9-]+_[a-z0-9-]+_fix-[0-9]{8}-[1-9][0-9]*$")


def build_fixes(list_id, page, ev, fixes, by):
    """fixes: [{what, section, section_job, selector?, pattern, left, converted, clips, value_usd_month, basis, type,
    effort}] → the fix list record, f1… in the order given (the most money first)."""
    rows = []
    for i, f in enumerate(fixes, 1):
        where = {"section_job": f.get("section_job") or "", "section": f.get("section") or ""}
        if f.get("selector"):
            where["selector"] = f["selector"]
        rows.append({"id": "f%d" % i, "what": f.get("what", ""), "where": where,
                     "why": {"pattern": f.get("pattern", ""), "left": int(f.get("left") or 0),
                             "converted": int(f.get("converted") or 0), "clips": f.get("clips") or []},
                     "value_usd_month": round(float(f.get("value_usd_month") or 0), 2), "basis": f.get("basis", ""),
                     "type": f.get("type", ""), "effort": f.get("effort", "")})
    return {"id": list_id, "kind": "fix-list", "page_id": page["page_id"],
            "control": {"version": page["control"]["version"]}, "fixes": rows, "evidence": ev, "by": by,
            "status": "draft"}


def check_fixes(rec):
    bad = []
    for k in ("id", "kind", "page_id", "control", "fixes", "evidence", "by", "status"):
        if k not in rec:
            bad.append("fix list missing " + k)
    if bad:
        return bad
    if rec["kind"] != "fix-list":
        bad.append("kind must be fix-list")
    if not ID_RE.match(rec["page_id"]):
        bad.append("page_id is not <brand>_<place>_<page>")
    if not FIX_ID_RE.match(rec["id"]) or not rec["id"].startswith(rec["page_id"] + "_fix-"):
        bad.append("id must be <page_id>_fix-<YYYYMMDD>-<n>")
    if not VERSION_RE.match(rec["control"].get("version", "")):
        bad.append("control version must be vN")
    if rec["status"] != "draft":
        bad.append("fix list is written as draft; the yes happens at the approval card")
    n_left, n_conv = rec["evidence"]["recordings"]["left"], rec["evidence"]["recordings"]["converted"]
    for f in rec["fixes"]:
        if f["type"] not in FIX_TYPES:
            bad.append("%s: type must be one of %s" % (f["id"], ", ".join(FIX_TYPES)))
        if f["effort"] not in EFFORTS:
            bad.append("%s: effort must be s, m or l" % f["id"])
        if len(str(f["what"]).strip()) < 8 or len(str(f["why"]["pattern"]).strip()) < 8:
            bad.append("%s: what or why is empty" % f["id"])
        if not (0 <= f["why"]["left"] <= n_left and 0 <= f["why"]["converted"] <= n_conv):
            bad.append("%s: counts exceed the recordings read" % f["id"])
        if len(str(f["basis"]).strip()) < 12:
            bad.append("%s: basis must say how the dollar figure was worked out" % f["id"])
    return bad
