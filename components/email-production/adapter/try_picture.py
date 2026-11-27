"""Try a picture change first, add the one she picks — LD-83 (picture try first).

the team, 2026-10-22: "the team rarely just has one iteration … its better for the default prompt to be regenerating results
she can see faster (as opposed to wait to for it to update on the page). And then once complete she adds it", and
"lets already build in the ability for her to try different models as well". A picture change she asks for IN CLAUDE
makes numbered TRIES she sees at once, on any selectable house model, and nothing is committed; she ADDS the one she
picks. The page's own "change this picture" button keeps the apply path (adapter.py apply, sync.py).

    try_picture.py try <run> <P-code> "<change>" [--model M] [--count N] [--from-try K] [--brand B] [--by P]
        edits the picture from its record (picture_record.edit_inputs: the same references a remake uses) through
        tools/image-edit, into <run>/tries/<P>/: try-<n>.jpg per result, one line each in tries.json. Each try
        opens on her screen the moment it exists, before the judge answers; the verdict is advisory (never blocks,
        never deletes). design/email.json is not touched: no rebuild, no learning, no commit.
    try_picture.py add <run> <P-code> <n> [--alt "<words>"] [--no-drive] [--commit] [--brand B] [--by P]
        puts try-<n>.jpg in through own_picture.place (media/, Drive, the old picture kept in history, rebuilt and
        checked), writes its record (the try's references and model) and today's one picture learning
    try_picture.py clear <run> <P-code>      removes that picture's tries folder (her scratch; the only delete here)
    try_picture.py models                    what she may pick: the model house's choices for pictures.edit, each
                                             with the image-production row that makes it, or why it can't yet

<run> and <P-code> as own_picture.py takes them (P2, "oct-20 · P2", S addresses). --model is a registry id, or
<registry id>@<door>; left out, the model house's pictures.edit default. Every try prints, before it spends,
"N paid generation(s) on <model> — <the registry's price, or "price not on record">".

Model outcomes (card item 9): every try and every add writes one record onto platform/data/records/model-outcome/
(kind manifest platform/data/kinds/model-outcome.json), never into components/models/ or the model house. Tries and
their records are not committed by a try: tries/ is gitignored, and ask.py's add commit carries the records.

Exit: 0 ok · 1 failed · 2 refused (a model not in the choices, no door for it yet, a missing key).
"""
import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import own_picture as OP  # noqa: E402  this folder's own: find_run, pick, slots, place, as_jpeg, BAD_ALT
import sync  # noqa: E402  this folder's own: KIND, _learn; it appends email-production and design/ to sys.path
import picture_record as PR  # noqa: E402  design/picture_record.py: edit_inputs, keep_try, _store

REPO = OP.REPO
JOB = "pictures.edit"
OUTCOME_ROOT = REPO              # where model-outcome records land: <root>/platform/data/records/model-outcome/
OUTCOME_KIND = "model-outcome"
NO_DOOR = "%s: no door for it yet (the owner's follow-up) — pick %s"
_MH = []


class NoDoor(SystemExit):
    """A house model image-production has no door for yet: refused by name, nothing made (exit 2)."""


# --------------------------------------------------------------- the models she may pick

def _house():
    """components/generative-model-house/model_house.py, its public reader, loaded by path once (the folder has a
    hyphen), as image-production's route.py loads it."""
    if not _MH:
        spec = importlib.util.spec_from_file_location(
            "try_model_house", str(REPO / "components" / "generative-model-house" / "model_house.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _MH.append(mod)
    return _MH[0]


def _rows():
    """image-production's declared model rows (route.table(), its public surface): {row id: row}."""
    ip = str(REPO / "tools" / "image-production")
    if ip not in sys.path:
        sys.path.append(ip)
    from image_production import route
    return {k: v for k, v in (route.table().get("models") or {}).items() if isinstance(v, dict)}


def selectable(env=None):
    """The model house's choices for pictures.edit, each with "label" (<registry id>@<door>), "row" (the
    image-production row that makes it through image-edit, or None), "why" (None, or the no-door line) and
    "has_key" (its door key is in `env`, os.environ by default). Never a list of its own."""
    env = os.environ if env is None else env
    rows = _rows()
    out = []
    for c in _house().choices(JOB):
        hits = [rid for rid, row in rows.items()
                if row.get("provider") == c["door"] and row.get("vendor_model") == c["vendor_id"]]
        hits.sort(key=lambda rid: rows[rid].get("house_job") != JOB)          # the pictures.edit row first
        keys = c["key_env"] if isinstance(c["key_env"], list) else [c["key_env"]] if c["key_env"] else []
        out.append(dict(c, label="%s@%s" % (c["registry_id"], c["door"]), row=hits[0] if hits else None, why=None,
                        has_key=all(env.get(k) for k in keys)))
    ok = " · ".join(x["label"] for x in out if x["row"]) or "none"
    for x in out:
        if not x["row"]:
            x["why"] = NO_DOOR % (x["label"], ok)
    return out


def choose(model=None, env=None):
    """A person's pick, resolved: the house default when `model` is None, else model_house.pick (a model not in the
    choices, or a missing door key, is refused by name with its KeyError, never swapped). A model sold at one door
    image-edit can reach is that door; one with no door yet raises NoDoor. Returns the pick + label + row."""
    sel = selectable(env)
    if model:
        rid, _, door = str(model).partition("@")
        hits = [s for s in sel if s["registry_id"] == rid and (not door or s["door"] == door)]
        usable = [s for s in hits if s["row"]]
        if hits and not usable:
            raise NoDoor(hits[0]["why"])
        if not door and len(usable) == 1:
            model = usable[0]["label"]
    got = _house().pick(JOB, model, env)
    s = next(s for s in sel if (s["registry_id"], s["door"]) == (got["registry_id"], got["door"]))
    if not s["row"]:
        raise NoDoor(s["why"])
    return dict(got, label=s["label"], row=s["row"])


def _price(cost):
    if cost is None or cost == "":
        return None
    return cost if isinstance(cost, str) else json.dumps(cost, ensure_ascii=False)


def _cost(registry_id):
    """The registry's stated price for a model, or None (components/models/models.json, read through the house)."""
    for m in _house().registry().get("models", []):
        if isinstance(m, dict) and m.get("id") == registry_id:
            return m.get("cost")
    return None


# --------------------------------------------------------------- the tries folder

def _spec(run):
    return json.loads((Path(run) / "design" / "email.json").read_text())


def folder(run, code):
    """<run>/tries/<P>/ for a picture, and the P code."""
    n, _, _, _ = OP.pick(_spec(run), code)
    return Path(run) / "tries" / ("P%d" % n), "P%d" % n


def lines(where):
    f = Path(where) / "tries.json"
    try:
        got = json.loads(f.read_text())
    except (OSError, ValueError):
        return []
    return got if isinstance(got, list) else []


def _next_n(where):
    """The next try number for a picture: never reused while its tries folder exists."""
    seen = [t.get("n") for t in lines(where) if isinstance(t.get("n"), int)]
    seen += [int(m.group(1)) for m in (re.fullmatch(r"try-(\d+)\.jpg", f.name) for f in Path(where).glob("try-*.jpg")) if m]
    return max(seen or [0]) + 1


def _jpeg(src, dest):
    """The result as a JPEG: one already a JPEG is copied as made; anything else is saved through own_picture."""
    src = Path(src)
    with open(str(src), "rb") as fh:
        head = fh.read(3)
    if head[:2] == b"\xff\xd8":
        shutil.copy2(str(src), str(dest))
    else:
        OP.as_jpeg(src, dest)


def _verdict(row, cmp):
    """A try's verdict as the judges made it: image-production's on the picture, then image-edit's compare."""
    got = [v for v in (row.get("verdict"), (cmp or {}).get("verdict")) if v]
    if not got:
        return None
    why = list(row.get("fails") or []) + list((cmp or {}).get("fails") or [])
    return {"verdict": "pass" if all(v == "pass" for v in got) else next(v for v in got if v != "pass"), "why": why}


def _open(path):
    """Her screen: `open <file>` on macOS, the path printed elsewhere."""
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)], capture_output=True)
    print("   see: %s" % path)


def _real_judge():
    ip = str(REPO / "tools" / "image-production")
    if ip not in sys.path:
        sys.path.append(ip)
    from image_production import judge as J
    return J.google_caller


def _real_edit():
    ie = str(REPO / "tools" / "image-edit")
    if ie not in sys.path:
        sys.path.append(ie)
    import image_edit
    return image_edit.edit


# --------------------------------------------------------------- try, add, clear

def try_change(run, code, change, by, model=None, count=1, from_try=None, edit=None, opener=None, judge=None, env=None):
    """Make `count` tries of one picture change; returns the new tries.json lines. Nothing under the run changes
    but <run>/tries/<P>/: no design/email.json write, no rebuild, no learning, no git."""
    run = Path(run)
    change = (change or "").strip()
    if not change:
        raise SystemExit("a try needs the change, in words")
    count = int(count or 1)
    if count < 1:
        raise SystemExit("--count is 1 or more")
    n, _, _, picture = OP.pick(_spec(run), code)
    p_code = "P%d" % n
    where = run / "tries" / p_code
    brand = run.parent.name
    chosen = choose(model, env)                                 # refusals before anything is read or made
    inputs = PR.edit_inputs(brand, run, picture)                # CannotRemake: the "remake from the brief instead?" offer
    req = dict(inputs["request"])
    asked, base = change, None
    if from_try is not None:
        base = where / ("try-%d.jpg" % int(from_try))
        if not base.is_file():
            raise SystemExit("no try %d of %s to start from (%s)" % (int(from_try), p_code, ", ".join(
                "try %d" % t["n"] for t in lines(where)) or "no tries yet"))
        req["picture"] = str(base)
        prior = next((t for t in lines(where) if t.get("n") == int(from_try)), {})
        asked = "%s; then %s" % (prior["change"], change) if prior.get("change") else change
    where.mkdir(parents=True, exist_ok=True)
    req.update(change=change, count=count, model=chosen["row"], label="%s-%s-try" % (run.name, p_code),
               out=str(where / "edit"))
    print("%d paid generation(s) on %s — %s" % (count, chosen["label"], _price(chosen.get("cost")) or "price not on record"))

    shown = set()
    see = opener or _open

    def opening(prompt, img_path, entry, *a, **kw):
        """THE SEAM (card item 2): the engine's judge is handed the made file before any verdict exists; she sees it
        now, then the real judge answers."""
        if str(img_path) not in shown:
            shown.add(str(img_path))
            try:
                see(str(img_path))
            except Exception as e:  # noqa: BLE001 — not seeing it on screen never sinks the try; said
                print("   (couldn't open %s: %s)" % (img_path, e))
        return (judge or _real_judge())(prompt, img_path, entry, *a, **kw)

    r = (edit or _real_edit())(req, judge_caller=opening, mirror=False)      # tries stay local until one is added
    if r.get("refused"):
        raise RuntimeError("the try was refused before anything was made: %s" % r["refused"])
    compared = {x.get("from"): x for x in (r.get("delivered") or []) + (r.get("rejected") or []) if x.get("from")}
    made = []
    for row in (r.get("engine") or {}).get("pictures") or []:
        cmp = compared.get(row.get("file"))
        src = (cmp or {}).get("file") or row.get("file") or row.get("content")
        if not src or not Path(src).is_file():
            print("   a result had no file to keep (%s)" % (row.get("name") or "?"))
            continue
        k = _next_n(where)
        _jpeg(src, where / ("try-%d.jpg" % k))
        line = {"n": k, "change": asked, "model": chosen["label"], "registry_id": chosen["registry_id"],
                "door": chosen["door"], "from_try": None if from_try is None else int(from_try),
                "made": "tries/%s/try-%d.jpg" % (p_code, k),
                "at": dt.datetime.now().astimezone().isoformat(timespec="seconds"), "judge": _verdict(row, cmp)}
        (where / "tries.json").write_text(json.dumps(lines(where) + [line], indent=1, ensure_ascii=False) + "\n")
        j = line["judge"]
        print("   try %d: %s — %s" % (k, run / line["made"], "%s%s" % (j["verdict"], (": " + "; ".join(j["why"])[:200])
                                                                    if j["why"] else "") if j else "not judged"))
        outcome(by, run, p_code, line, False)
        made.append(line)
    return made


def add(run, code, n, by, alt=None, drive=True, place=None):
    """try-<n>.jpg goes into the email in place of the picture, through own_picture.place; its record and today's one
    picture learning are written. Returns place's dict + {"record", "try"}. No git here."""
    run = Path(run)
    n = int(n)
    spec = _spec(run)
    num, i, _, picture = OP.pick(spec, code)
    p_code = "P%d" % num
    where = run / "tries" / p_code
    src = where / ("try-%d.jpg" % n)
    line = next((t for t in lines(where) if t.get("n") == n), None)
    if line is None or not src.is_file():
        raise SystemExit("no try %d of %s to add (%s)" % (n, p_code, ", ".join("try %d" % t["n"] for t in lines(where))
                                                           or "no tries yet"))
    before = json.loads(json.dumps(picture))
    kind = sync.KIND.get(spec["sections"][i].get("s"), spec["sections"][i].get("s") or "")
    brand = run.parent.name
    inputs = PR.edit_inputs(brand, run, before)
    alt = (alt or "").strip() or "%s — %s" % ((before.get("alt") or "").strip(), line["change"])
    res = (place or OP.place)(run, code, str(src), alt, by, line["model"], "own", None, drive)
    spec = _spec(run)
    _, i2, _, now = OP.pick(spec, code)
    placed = now["photo"].split("run:", 1)[1]
    if now.get("drive_id"):
        file_ref = {"drive_id": now["drive_id"],
                    "label": "Shared Assets/runs/email-production/%s/%s/%s" % (brand, run.name, placed)}
    elif drive:
        file_ref, _ = PR._store(run, brand, run / placed)
    else:
        file_ref = None
    rel = PR.keep_try(brand, run, before, run / placed, file_ref, line["change"], i2,
                      {"id": line["registry_id"], "door": line["door"]}, line.get("judge"), inputs)
    now["record"] = rel
    (run / "design" / "email.json").write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n")
    import prepare
    if all(s.get("ok") for s in res.get("rebuilt") or []):
        prepare.stamp(run)                                      # the record is not built: the build stays current
    sync._learn(brand, "picture", "%s picture (%s): %s" % (kind, before.get("alt", "")[:120], line["change"]), by, run.name)
    outcome(by, run, p_code, line, True, tries_before_pick=len(lines(where)))
    res = dict(res, record=rel)
    res["try"] = n
    return res


def clear(run, code):
    """Removes <run>/tries/<P>/ — that picture's tries, her own scratch under runs/; returns the path removed."""
    where, _ = folder(run, code)
    if where.is_dir():
        shutil.rmtree(str(where))
    return where


# --------------------------------------------------------------- model outcomes (card item 9)

def outcome(person, run, code, entry, picked, tries_before_pick=None, root=None):
    """One model-outcome record per try or add, onto the records plane; returns its path. Never an edit of an
    earlier record, never written into components/models/ or the model house."""
    run = Path(run)
    num, _, _, picture = OP.pick(_spec(run), code)
    p_code = "P%d" % num
    rec_ = PR.read(run, picture.get("record")) or {}
    who = str(person or "unknown").lower()
    item = "%s-%s-try-%d" % (run.name, p_code, entry["n"])
    now = dt.datetime.now(dt.timezone.utc)
    j = entry.get("judge")
    verdict = {"model": entry["registry_id"], "door": entry["door"], "purpose": rec_.get("purpose"),
               "brand": run.parent.name,
               "judge": {"result": j["verdict"], "failing": list(j.get("why") or [])} if j else "not judged",
               "picked": bool(picked)}
    if picked:
        verdict["tries_before_pick"] = tries_before_pick
    verdict["cost"] = _price(_cost(entry["registry_id"])) or "not on record"
    out = Path(root or OUTCOME_ROOT) / "platform" / "data" / "records" / OUTCOME_KIND
    out.mkdir(parents=True, exist_ok=True)
    stem = "%s--%s--%s" % (now.strftime("%Y%m%dT%H%M%SZ"), who, item)
    f, k = out / (stem + ".json"), 2
    while f.exists():                                           # one record per event, never over an earlier one
        f, k = out / ("%s-%d.json" % (stem, k)), k + 1
    f.write_text(json.dumps({"schema": 1, "kind": OUTCOME_KIND, "reviewer": who, "item": item, "verdict": verdict,
                             "created": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
                             "via": "email-production/try_picture"}, indent=1, ensure_ascii=False) + "\n")
    return f


# --------------------------------------------------------------- the command

def _say(e):
    return e.args[0] if isinstance(e, KeyError) and e.args else str(e)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("try")
    t.add_argument("run")
    t.add_argument("code")
    t.add_argument("change")
    t.add_argument("--model")
    t.add_argument("--count", type=int, default=1)
    t.add_argument("--from-try", type=int)
    a = sub.add_parser("add")
    a.add_argument("run")
    a.add_argument("code")
    a.add_argument("n", type=int)
    a.add_argument("--alt", help="what the NEW picture shows (default: the old alt with the change)")
    a.add_argument("--no-drive", action="store_true", help="tests on a copy only: skip the Drive mirror")
    a.add_argument("--commit", action="store_true", help="commit and push the change (ask.py's share)")
    c = sub.add_parser("clear")
    c.add_argument("run")
    c.add_argument("code")
    sub.add_parser("models")
    for p in (t, a, c):
        p.add_argument("--brand")
    for p in (t, a):
        p.add_argument("--by", default="the team")
    x = ap.parse_args(argv)
    if x.cmd == "models":
        print(json.dumps(selectable(), indent=1, ensure_ascii=False))
        return 0
    run = OP.find_run(x.run, x.brand)
    try:
        if x.cmd == "try":
            out = {"tries": try_change(run, x.code, x.change, x.by, model=x.model, count=x.count, from_try=x.from_try)}
        elif x.cmd == "add":
            out = add(run, x.code, x.n, x.by, alt=x.alt, drive=not x.no_drive)
            if x.commit and all(s["ok"] for s in out["rebuilt"]):
                import ask
                rel = str(run.relative_to(REPO))
                out["git"] = ask.share([rel, "runs/learnings", "platform/data/records/" + OUTCOME_KIND],
                                       "%s added try %d: %s %s" % (x.by, x.n, rel.split("/")[-1], out["picture"]))
        else:
            out = {"removed": str(clear(run, x.code))}
    except (KeyError, NoDoor) as e:
        print(_say(e), file=sys.stderr)
        return 2
    except (Exception, SystemExit) as e:  # noqa: BLE001 — said, never hidden
        print(_say(e), file=sys.stderr)
        return 1
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0 if x.cmd != "add" or all(s.get("ok") for s in out.get("rebuilt") or []) else 1


if __name__ == "__main__":
    sys.exit(main())
