"""The decision layer (v2, 18 Oct 2026). the owner: "a proper neural network for
decision making in this system so our chain actually functions without me being
involved ... no stage stops and output is automatic."

Every gate that used to stop a run (structure lock, hook format, audit, swipe
match, manifest) hands its open items here instead. For each item we:
  1. read the owner's past calls on the same KIND of item (his approved hold files
     vs the ones he left open, plus every Agree/Overrule from the Outlier queue),
  2. decide with a confidence = how often he passed that kind before,
  3. let the run continue, and file the call in the queue
     (runs/decisions/calls.jsonl) for him to Agree with or Overrule.
Nothing here is brand-specific: kinds are the gates' own words.
Off: unset VT_AUTO (on by default in v2).
"""
import fcntl
import json
import re
import time
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
QUEUE = REPO / "runs" / "decisions" / "calls.jsonl"
GATES = {  # held file -> its approved name, and the gate's label
    "STRUCTURE-CHECK.md": ("STRUCTURE-CHECK-approved.md", "structure"),
    "HOOK-FORMAT.md": ("HOOK-FORMAT-approved.md", "hook"),
    "AUDIT-HOLD.md": ("AUDIT-HOLD-cleared.md", "audit"),
    "SWIPE-MATCH.md": ("SWIPE-MATCH-approved.md", "swipe"),
}


def kind(gate, item):
    """The kind of call, in the gate's own words, so like is compared with like."""
    if gate == "audit":
        words = re.sub(r"[^a-z ]", "", str(item.get("element", "")).lower()).split()
        return "audit:" + " ".join(words[:4])
    if gate == "structure":
        return "structure:" + str(item.get("status", "")).lower()
    if gate == "hook":
        return "hook:" + ("card" if str(item.get("n", "")).upper().startswith("CF") else "version")
    if gate == "manifest":
        return "manifest:" + ("element" if str(item.get("n", ""))[:1] in "EL" else "to-make")
    return gate + ":change"


def _rows(text):
    for line in text.splitlines():
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) >= 3 and re.match(r"^(A\d+|H\d+|CF|M\d+|Q\d+|\d+|LINES|A)$", c[0]):
            yield {"n": c[0], "element": c[1], "status": c[2] if len(c) > 2 else ""}


_CACHE = {}


def precedents():
    """kind -> {'passed': [run...], 'left': [run...]} from every past run."""
    if "p" in _CACHE:
        return _CACHE["p"]
    p = defaultdict(lambda: {"passed": [], "left": []})
    roots = [REPO / "runs" / "video-teardown", REPO / "runs" / "video-writing",
             REPO / "tools" / "video-teardown" / "machine" / "runs"]
    for held, (ok, gate) in GATES.items():
        for name, side in ((ok, "passed"), (held, "left")):
            for root in roots:
                for f in root.glob(f"**/{name}"):
                    if "v2test-" in str(f) or "_auto" in str(f):
                        continue
                    for it in _rows(f.read_text(errors="ignore")):
                        p[kind(gate, it)][side].append(f.parent.name)
    for c in _queue():                              # his Agree / Overrule on the layer's own calls
        if c.get("verdict") == "agree":
            p[c["kind"]]["passed"].append(c["run"])
        elif c.get("verdict") == "overrule":
            p[c["kind"]]["left"].append(c["run"])
    _CACHE["p"] = p
    return p


def _queue():
    if not QUEUE.is_file():
        return []
    out = []
    for line in QUEUE.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except Exception:  # noqa: BLE001
            pass
    return out


def auto(run_dir, st, gate, items):
    """Decide every open item of a gate. Returns the items still open: none in
    auto mode; all of them in shadow mode (the call is logged, the owner decides)."""
    p = precedents()
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    made = []
    for it in items:
        k = kind(gate, it)
        rec = p.get(k, {"passed": [], "left": []})
        n_ok, n_left = len(rec["passed"]), len(rec["left"])
        conf = round((n_ok + 1) / (n_ok + n_left + 2), 2)      # smoothed: unseen kinds start at 0.5
        ruled = ruling_for(gate, it)
        call = {"id": f"{Path(run_dir).name}:{gate}:{it.get('n')}:{int(time.time())}",
                "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "run": Path(run_dir).name, "brand": st.get("brand"), "gate": gate, "kind": k,
                "item": {kk: str(v)[:400] for kk, v in it.items()},
                "decision": "would pass (shadow: the run waits for you)" if shadow(gate) else "passed — the run continues",
                "mode": "shadow" if shadow(gate) else "auto",
                "confidence": conf,
                "why": ("Your rulebook answer: " + ruled + " (the automatic put-back/swap step is next to build; until then it passes and flags.)") if ruled else
                       (f"You passed this kind of call {n_ok} time(s) and left it open {n_left} time(s) before."
                        if n_ok + n_left else "No past call of this kind yet: passed so the run keeps moving, flagged for you."),
                "ruling": bool(ruled),
                "precedents": rec["passed"][-3:], "verdict": None,
                "look": conf < 0.5}        # you usually did NOT pass this kind: it goes to the top of the queue
        with QUEUE.open("a") as f:
            fcntl.flock(f, fcntl.LOCK_EX)       # many runs at once (a batch): one writer at a time
            f.write(json.dumps(call) + "\n")
        made.append(call)
    if shadow(gate):
        st.setdefault("shadow_calls", []).extend({"gate": c["gate"], "n": c["item"].get("n")} for c in made)
        return items
    st.setdefault("auto_calls", []).extend({"gate": c["gate"], "n": c["item"].get("n"), "confidence": c["confidence"],
                                            "why": c["why"]} for c in made)
    return []


MODES = REPO / "runs" / "decisions" / "modes.json"
RULINGS = REPO / "runs" / "decisions" / "rulings.json"
STAGE_OF = {"structure": "writing", "hook": "writing", "audit": "writing", "swipe": "writing",
            "manifest": "writing", "format": "teardown"}


# OUTLIER_SETTINGS points one run at its own settings file, as production's readers already do (run_v2._setting,
# auto_elements.setting); without it a run the owner started by word ("run it up") still stopped at every gate on the
# house-wide Pause (2026-10-21).
SETTINGS = Path(__import__("os").environ.get("OUTLIER_SETTINGS") or (REPO / "runs" / "settings" / "settings.json"))


def setting(key, default=None):
    """Outlier Settings, read by path (runs/settings/settings.json)."""
    try:
        d = json.loads(SETTINGS.read_text())
    except Exception:  # noqa: BLE001
        return default
    for part in key.split("."):
        if not isinstance(d, dict) or part not in d:
            return default
        d = d[part]
    return d


def mode(stage):
    """plan | manual | shadow | auto, as the owner set it on Outlier → Settings.
    The master pause turns every stage to manual."""
    if setting("automation.paused", False):
        return "manual"
    m = setting(f"automation.{stage}")
    if m:
        return m
    try:
        return json.loads(MODES.read_text()).get(stage, "manual")
    except Exception:  # noqa: BLE001
        return "manual"


def on(gate="audit"):
    import os
    if os.environ.get("VT_CHAIN") != "v2" or os.environ.get("VT_AUTO", "1") == "0":
        return False
    return mode(STAGE_OF.get(gate, "writing")) in ("auto", "shadow")


def shadow(gate="audit"):
    return mode(STAGE_OF.get(gate, "writing")) == "shadow"


def ruling_for(gate, item):
    """the owner's rulebook answers decide first (rulings.json)."""
    if gate in ("swipe", "structure", "manifest") and setting("rulings.swipe_drift") == "put the swipe back":
        return "put the swipe's version back, then pass and flag"
    if gate == "audit" and any(w in str(item.get("element", "")).lower() for w in ("claim", "offer", "rule")) \
            and setting("rulings.claims") == "swap or cut":
        return "swap the claim for the closest approved line, or cut it"
    return None


def set_verdict(call_id, verdict, note=""):
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    with QUEUE.open("a") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)          # a run appending while this rewrites would lose its call
        _CACHE.clear()
        return _set_verdict(call_id, verdict, note)


def _set_verdict(call_id, verdict, note=""):
    calls = _queue()
    for c in calls:
        if c["id"] == call_id:
            c["verdict"], c["note"], c["verdict_at"] = verdict, note, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    QUEUE.write_text("".join(json.dumps(c) + "\n" for c in calls))
    _CACHE.clear()
    return next((c for c in calls if c["id"] == call_id), None)


def stats():
    return {k: {"passed": len(v["passed"]), "left": len(v["left"])} for k, v in precedents().items()}
