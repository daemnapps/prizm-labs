#!/usr/bin/env python3
"""LD-83 (picture try first): a picture change asked in Claude makes numbered TRIES she sees at once (any selectable
house model, nothing committed) and ADDS the one she picks — proven offline, on a temp fixture run.

    python3 tools/email-production/adapter/test_ld83_try_add.py     (from the repo root: never with the working
                                                                          folder inside tools/email-production,
                                                                          whose email.py shadows the stdlib's)

Faked at the seams try_picture.py exposes: image-edit's edit() (it calls the judge_caller it is handed on each made
file, as image-production's judge does), the judge, the opener, own_picture.place, the model house's two files (the
REAL model_house.py reads a fixture house and registry), image-production's route rows, the Drive refs, the
learnings writer, the stamp file, and ask.share (it fails the test if a try reaches git). No network, no key, no
Chrome, no PIL needed. Every model-outcome record lands under a temp root, never the real plane.

  1  a try: try-1.jpg + tries.json; design/email.json byte-identical; no learning; no git; one model-outcome record
  2  the opener sees the made file BEFORE the judge returns; the paid line prints before the edit runs
  3  again -> try 2; --count 3 -> tries 3-5 (a rejected one is kept: the verdict is advice); --from-try 2 edits try 2
  4  model choice: the house default's edit row; a model sold at one reachable door; one not in the choices refused by
     name; a fal model refused with the no-door line (CLI exit 2); a missing key refused by name, nothing swapped
  5  add 3: the picture placed once (the old one in history), one rebuild, one picture learning, a record whose model
     is the registry id; a model-outcome with picked true and tries_before_pick
  6  clear removes that picture's tries folder only
  7  ask.py: "change this picture" -> try, "use try 2" -> add (committed with the model-outcome folder), a words line
     still through apply_one; "use try" with no number is asked back
  8  adapter.py try: picture -> a try; a word with no try, and an approval, refused exit 2
  9  nothing written under components/models/ or components/generative-model-house/; the kind manifest is whole
"""
import contextlib
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))      # this folder FIRST; never tools/email-production (its email.py)
import try_picture as TP           # noqa: E402
import own_picture as OP           # noqa: E402
import picture_record as PR        # noqa: E402  (try_picture put design/ on the path through sync)
import prepare                     # noqa: E402
import ask                         # noqa: E402
import adapter                     # noqa: E402

REPO = Path(OP.REPO)
BRAND = "zz-brand"
LABEL = "zz-brand-nov-99"
PIC = "pic.png"
OLD_REC = "media/records/zz-pic/record.json"
JPEG = b"\xff\xd8\xff\xe0"
ENV = {"OPENAI_API_KEY": "x", "GEMINI_API_KEY": "x", "FAL_KEY": "x"}
HOUSE = {"pictures": {"edit": {"registry": "gpt-image-2.5", "door": "openai", "capability": "image-edit"}}}
REGISTRY = {"models": [
    {"id": "gemini-3-pro-image", "status": "approved", "vendor": "google", "vendor_id": "gemini-3-pro-image",
     "key_env": "GEMINI_API_KEY", "capability": ["image-edit"], "cost": None},
    {"id": "gpt-image-2.5", "status": "draft", "capability": ["image-edit"], "cost": None,
     "doors": {"openai": {"vendor_id": "gpt-image-2.5-sunburst", "key_env": "OPENAI_API_KEY"},
               "fal": {"vendor_id": "openai/gpt-image-2.5/sunburst/edit", "key_env": "FAL_KEY"}}},
    {"id": "seedream-5-pro-edit", "status": "draft", "capability": ["image-edit"], "cost": None,
     "doors": {"fal": {"vendor_id": "bytedance/seedream/v5/pro/edit", "key_env": "FAL_KEY"}}},
    {"id": "some-voice", "status": "approved", "vendor": "x", "capability": ["voice"], "cost": None}]}
ROWS = {"gpt-image-person": {"provider": "openai", "vendor_model": "gpt-image-2.5-sunburst", "house_job": "pictures.generate"},
        "gpt-image-edit": {"provider": "openai", "vendor_model": "gpt-image-2.5-sunburst", "house_job": "pictures.edit"},
        "gemini-image-object": {"provider": "google", "vendor_model": "gemini-3-pro-image", "house_job": "pictures.object"}}
NO_DOOR_SEEDREAM = ("seedream-5-pro-edit@fal: no door for it yet (the owner's follow-up) — pick "
                    "gpt-image-2.5@openai · gemini-3-pro-image@google")


def snapshot(*tops):
    out = {}
    for top in tops:
        for f in Path(top).rglob("*"):
            if f.is_file() and "__pycache__" not in f.parts:
                out[str(f)] = hashlib.sha256(f.read_bytes()).hexdigest()
    return out


class Base(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.tmp = Path(os.path.realpath(t.name))
        self.runs = self.tmp / "runs" / "email-production"
        self.run = self.runs / BRAND / LABEL
        for d in ("design", "media/records/zz-pic", "media/records/zz-other", "klaviyo"):
            (self.run / d).mkdir(parents=True)
        (self.run / "media" / "records" / "zz-other" / "record.json").write_text(json.dumps(
            {"label": "zz-other", "file": "media/other.png", "purpose": "email-hero", "references": []}))
        (self.run / "media" / PIC).write_bytes(JPEG + b"the picture")
        (self.run / "media" / "other.png").write_bytes(JPEG + b"other")
        (self.run / "klaviyo" / "card.json").write_text("{}\n")
        (self.run / OLD_REC).write_text(json.dumps({
            "label": "zz-pic", "file": "media/" + PIC, "purpose": "email-story",
            "file_ref": {"drive_id": "id-pic", "label": "Shared Assets/runs/email-production/%s/%s/media/%s" % (BRAND, LABEL, PIC)},
            "references": [{"path": "tools/email-production/design/fonts.css",
                            "ref": "tools/email-production/design/fonts.css", "kind": "brand asset"},
                           {"path": "pin.jpg", "ref": {"drive_id": "id-pin", "label": "pin.jpg"}, "kind": "Pinterest pin (mood only)"}]}))
        self.spec = self.run / "design" / "email.json"
        self.spec.write_text(json.dumps({"brand": BRAND, "sections": [
            {"s": "band"},
            {"s": "hero_photo", "headline": "Hello", "picture": {"photo": "run:media/" + PIC, "alt": "a jar on a sink",
                                                                 "brief": "a jar", "record": OLD_REC}},
            {"s": "photo_card", "text": "card", "picture": {"photo": "run:media/other.png", "alt": "another jar",
                                                 "record": "media/records/zz-other/record.json"}}]}, indent=1))
        self.events, self.edits, self.learned, self.placed, self.rebuilds = [], [], [], [], 0
        self.out = io.StringIO()
        mh = TP._house()

        def local(ref):
            if isinstance(ref, str) and not os.path.isabs(ref):
                return REPO / ref
            raise AssertionError("asked the Drive for %r" % (ref,))
        fake_refs = types.SimpleNamespace(local=local, Unportable=type("Unportable", (Exception,), {}))

        def no_share(*a, **k):
            raise AssertionError("git was reached: %r" % (a,))
        for obj, name, value in ((mh, "house", lambda: HOUSE), (mh, "registry", lambda: REGISTRY),
                                 (TP, "_rows", lambda: dict(ROWS)), (TP, "OUTCOME_ROOT", self.tmp / "plane"),
                                 (PR, "_refs", lambda: fake_refs), (prepare, "STAMPS", self.tmp / "stamps.json"),
                                 (TP.sync, "_learn", lambda *a, **k: self.learned.append(a)),
                                 (ask, "share", no_share)):
            p = mock.patch.object(obj, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.verdicts = []          # compare verdicts the fake edit hands out, in order; "pass" when empty

    # ---- the fakes
    def opener(self, path):
        self.events.append(("open", path))

    def judge(self, prompt, img_path, entry, *a, **k):
        self.events.append(("judge-returns", img_path))
        return '{"results": []}'

    def edit(self, req, judge_caller=None, mirror=True):
        """image-edit's engine at its public seam: image-production makes each picture under out/engine/generated,
        hands the judge_caller the made file, then image-edit's compare files a kept or rejected copy."""
        self.edits.append(dict(req, _mirror=mirror, _out_at_call=self.out.getvalue()))
        out = Path(req["out"])
        rows, kept, rejected = [], [], []
        for i in range(1, req["count"] + 1):
            raw = out / "engine" / "generated" / ("%s-%02d.png" % (req["label"], i))
            raw.parent.mkdir(parents=True, exist_ok=True)
            raw.write_bytes(JPEG + ("%s|%s|%d" % (Path(req["picture"]).name, req["change"], i)).encode())
            judge_caller("the judge's prompt", str(raw), {"key": "GEMINI_API_KEY"})
            self.events.append(("judged", str(raw)))
            delivered = out / "engine" / raw.name
            shutil.copy2(str(raw), str(delivered))
            rows.append({"name": raw.name, "content": str(raw), "file": str(delivered), "verdict": "pass", "fails": []})
            v = self.verdicts.pop(0) if self.verdicts else "pass"
            if v == "pass":
                f = out / ("x--edit-v1-%02d.png" % i)
                shutil.copy2(str(delivered), str(f))
                kept.append({"from": str(delivered), "file": str(f), "verdict": "pass", "fails": []})
            else:
                f = out / "rejected" / ("x--edit-v1-%02d.png" % i)
                f.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(delivered), str(f))
                rejected.append({"from": str(delivered), "file": str(f), "verdict": "reject", "fails": ["NOTHING ELSE MOVED"]})
        return {"engine": {"pictures": rows}, "delivered": kept, "rejected": rejected, "refused": None,
                "instruction": "one change", "out": req["out"]}

    def place(self, run, code, src, alt, by, made_with, ratio, focus, drive):
        """own_picture.place at its seam: the file to media/, the picture replaced with the old one in history, one
        rebuild."""
        if OP.BAD_ALT.search(alt or ""):
            raise SystemExit("the alt text must describe the new picture in plain words (not a 'to make' prompt)")
        self.placed.append({"code": code, "src": src, "alt": alt, "by": by, "made_with": made_with, "ratio": ratio,
                            "focus": focus, "drive": drive})
        f = run / "design" / "email.json"
        spec = json.loads(f.read_text())
        n, i, j, p = OP.pick(spec, code)
        old = {k: v for k, v in p.items() if k != "history"}
        name = "own-p%d-test.jpg" % n
        shutil.copy2(src, str(run / "media" / name))
        new = {"photo": "run:media/" + name, "alt": alt, "source": "made", "made_with": made_with, "by": by,
               "drive_id": "id-placed", "history": (p.get("history") or []) + [{"was": old, "replaced_by": by}]}
        p.clear()
        p.update(new)
        f.write_text(json.dumps(spec, indent=1) + "\n")
        self.rebuilds += 1
        return {"picture": "P%d" % n, "section": i, "index": j, "file": str(run / "media" / name),
                "rebuilt": [{"step": "design/build.py", "ok": True}, {"step": "design/check.py", "ok": True}]}

    # ---- helpers
    def tri(self, code="P1", change="warmer light", **k):
        k.setdefault("env", ENV)
        with contextlib.redirect_stdout(self.out):
            return TP.try_change(self.run, code, change, "the team", edit=self.edit, opener=self.opener, judge=self.judge, **k)

    def tries(self, p="P1"):
        return json.loads((self.run / "tries" / p / "tries.json").read_text())

    def outcomes(self):
        d = self.tmp / "plane" / "platform" / "data" / "records" / "model-outcome"
        return [json.loads(f.read_text()) for f in sorted(d.glob("*.json"))] if d.is_dir() else []


class TestTry(Base):
    def test_1_a_try_writes_the_try_and_nothing_else(self):
        before = self.spec.read_bytes()
        got = self.tri()
        self.assertEqual([t["n"] for t in got], [1])
        f = self.run / "tries" / "P1" / "try-1.jpg"
        self.assertTrue(f.is_file())
        self.assertTrue(f.read_bytes().startswith(JPEG))
        line = self.tries()[0]
        self.assertEqual({k: line[k] for k in ("n", "change", "model", "registry_id", "door", "from_try", "made")},
                         {"n": 1, "change": "warmer light", "model": "gpt-image-2.5@openai", "registry_id": "gpt-image-2.5",
                          "door": "openai", "from_try": None, "made": "tries/P1/try-1.jpg"})
        self.assertEqual(line["judge"], {"verdict": "pass", "why": []})
        self.assertEqual(self.spec.read_bytes(), before)                       # the email is untouched
        self.assertEqual(self.learned, [])                                     # no learning
        self.assertEqual(self.rebuilds, 0)
        self.assertFalse(self.edits[0]["_mirror"])                             # a try stays local
        self.assertEqual(self.edits[0]["change"], "warmer light")
        self.assertEqual(self.edits[0]["model"], "gpt-image-edit")             # the house default's edit row
        self.assertEqual(Path(self.edits[0]["picture"]).name, PIC)
        self.assertEqual([Path(p).name for p in self.edits[0]["references"]], ["fonts.css"])   # no mood pin
        self.assertEqual(Path(self.edits[0]["out"]), self.run / "tries" / "P1" / "edit")
        recs = self.outcomes()
        self.assertEqual(len(recs), 1)
        r = recs[0]
        self.assertEqual((r["schema"], r["kind"], r["reviewer"], r["item"], r["via"]),
                         (1, "model-outcome", "designer", LABEL + "-P1-try-1", "email-production/try_picture"))
        self.assertEqual(r["verdict"], {"model": "gpt-image-2.5", "door": "openai", "purpose": "email-story",
                                        "brand": BRAND, "judge": {"result": "pass", "failing": []}, "picked": False,
                                        "cost": "not on record"})

    def test_2_she_sees_it_before_the_judge_returns_and_the_paid_line_comes_first(self):
        self.tri()
        made = self.edits and [e for e in self.events if e[0] == "open"]
        self.assertEqual(len(made), 1)
        self.assertEqual(self.events[:2], [("open", made[0][1]), ("judge-returns", made[0][1])])
        self.assertIn("/engine/generated/", made[0][1])
        self.assertIn("1 paid generation(s) on gpt-image-2.5@openai — price not on record", self.edits[0]["_out_at_call"])

    def test_3_again_options_and_from_try(self):
        self.tri()
        self.tri()                                                              # again
        self.assertEqual([t["n"] for t in self.tries()], [1, 2])
        self.verdicts = ["pass", "reject", "pass"]
        got = self.tri(change="warmer light", count=3)                          # give me 3 options
        self.assertEqual([t["n"] for t in got], [3, 4, 5])
        self.assertIn("3 paid generation(s) on gpt-image-2.5@openai — price not on record", self.out.getvalue())
        self.assertEqual(got[1]["judge"], {"verdict": "reject", "why": ["NOTHING ELSE MOVED"]})
        self.assertTrue((self.run / "tries" / "P1" / "try-4.jpg").is_file())  # advisory: a held try is kept
        got = self.tri(change="softer", from_try=2)                             # more like try 2 but softer
        self.assertEqual(Path(self.edits[-1]["picture"]), self.run / "tries" / "P1" / "try-2.jpg")
        self.assertEqual(self.edits[-1]["change"], "softer")
        self.assertEqual((got[0]["n"], got[0]["from_try"], got[0]["change"]), (6, 2, "warmer light; then softer"))
        self.assertTrue((self.run / "tries" / "P1" / "try-6.jpg").read_bytes().endswith(b"try-2.jpg|softer|1"))
        self.assertEqual(len(self.outcomes()), 6)
        with self.assertRaises(SystemExit) as c:
            self.tri(from_try=9)
        self.assertIn("no try 9 of P1", str(c.exception))

    def test_4_models(self):
        self.tri(model="gpt-image-2.5")                                       # one door it can reach: openai
        self.assertEqual(self.edits[-1]["model"], "gpt-image-edit")
        got = self.tri(model="gemini-3-pro-image")
        self.assertEqual(self.edits[-1]["model"], "gemini-image-object")
        self.assertEqual((got[0]["model"], got[0]["registry_id"]), ("gemini-3-pro-image@google", "gemini-3-pro-image"))
        n = len(self.edits)
        with self.assertRaises(KeyError) as c:                                 # not in the choices: by name
            self.tri(model="nano-banana")
        self.assertIn("'nano-banana' is not a choice", c.exception.args[0])
        with self.assertRaises(TP.NoDoor) as c:                                # a fal model: no door yet
            self.tri(model="seedream-5-pro-edit")
        self.assertEqual(str(c.exception), NO_DOOR_SEEDREAM)
        with self.assertRaises(TP.NoDoor):
            self.tri(model="gpt-image-2.5@fal")
        with self.assertRaises(KeyError) as c:                                 # her key file lacks it: by name, no swap
            self.tri(model="gemini-3-pro-image", env={"OPENAI_API_KEY": "x"})
        self.assertIn("gemini-3-pro-image@google needs GEMINI_API_KEY", c.exception.args[0])
        with self.assertRaises(KeyError) as c:
            self.tri(env={"GEMINI_API_KEY": "x"})
        self.assertIn("gpt-image-2.5@openai needs OPENAI_API_KEY", c.exception.args[0])
        self.assertEqual(len(self.edits), n)                                   # nothing made, nothing swapped
        self.assertEqual([t["n"] for t in self.tries()], [1, 2])
        sel = {s["label"]: s for s in TP.selectable(ENV)}
        self.assertEqual({k: v["row"] for k, v in sel.items()},
                         {"gpt-image-2.5@openai": "gpt-image-edit", "gemini-3-pro-image@google": "gemini-image-object",
                          "gpt-image-2.5@fal": None, "seedream-5-pro-edit@fal": None})
        self.assertEqual(sel["seedream-5-pro-edit@fal"]["why"], NO_DOOR_SEEDREAM)

    def test_4b_the_command_prints_the_no_door_line_and_exits_2(self):
        err = io.StringIO()
        with mock.patch.object(TP, "_real_edit", lambda: self.fail("an edit ran")), \
                contextlib.redirect_stderr(err), contextlib.redirect_stdout(self.out):
            code = TP.main(["try", str(self.run), "P1", "warmer light", "--model", "seedream-5-pro-edit"])
        self.assertEqual(code, 2)
        self.assertIn(NO_DOOR_SEEDREAM, err.getvalue())
        self.assertFalse((self.run / "tries").exists())


class TestAdd(Base):
    def test_5_add_places_once_records_the_model_and_learns_once(self):
        for _ in range(3):
            self.tri()
        before = json.loads(self.spec.read_text())["sections"][1]["picture"]
        with contextlib.redirect_stdout(self.out):
            res = TP.add(self.run, "P1", 3, "the team", place=self.place)
        self.assertEqual(len(self.placed), 1)
        self.assertEqual(self.rebuilds, 1)
        p = self.placed[0]
        self.assertEqual(Path(p["src"]), self.run / "tries" / "P1" / "try-3.jpg")
        self.assertEqual((p["alt"], p["made_with"], p["ratio"], p["focus"], p["drive"]),
                         ("a jar on a sink — warmer light", "gpt-image-2.5@openai", "own", None, True))
        whole = json.loads(self.spec.read_text())["sections"][1]
        self.assertEqual((whole["s"], whole["headline"]), ("hero_photo", "Hello"))   # only the picture changed
        sec = whole["picture"]
        self.assertEqual(sec["photo"], "run:media/own-p1-test.jpg")
        self.assertEqual(len(sec["history"]), 1)
        self.assertEqual(sec["history"][0]["was"]["photo"], before["photo"])
        self.assertEqual(sec["record"], res["record"])
        rec = json.loads((self.run / res["record"]).read_text())
        self.assertEqual(rec["model"], {"id": "gpt-image-2.5", "door": "openai"})
        self.assertEqual((rec["parent"], rec["edit_of"], rec["direction"], rec["state"], rec["file"], rec["purpose"]),
                         (OLD_REC, "media/" + PIC, "warmer light", "made", "media/own-p1-test.jpg", "email-story"))
        self.assertEqual(rec["file_ref"]["drive_id"], "id-placed")
        self.assertEqual(rec["references"][0]["kind"], "earlier version of this picture")
        self.assertEqual([r["path"] for r in rec["references"][1:]], ["tools/email-production/design/fonts.css"])
        self.assertEqual(res["record"], "media/records/zz-pic-v2/record.json")
        self.assertEqual(res["try"], 3)
        self.assertEqual(self.learned, [(BRAND, "picture", "Hero picture picture (a jar on a sink): warmer light", "the team", LABEL)])
        recs = self.outcomes()
        self.assertEqual(len(recs), 4)                                          # three tries, then the add
        self.assertEqual([r["verdict"]["picked"] for r in recs].count(True), 1)
        add = next(r for r in recs if r["verdict"]["picked"])
        self.assertEqual((add["item"], add["verdict"]["tries_before_pick"], add["verdict"]["model"]),
                         (LABEL + "-P1-try-3", 3, "gpt-image-2.5"))
        self.assertNotIn("tries_before_pick", recs[0]["verdict"])
        with self.assertRaises(SystemExit):
            TP.add(self.run, "P1", 9, "the team", place=self.place)
        self.assertEqual(len(self.placed), 1)

    def test_5b_a_to_make_alt_is_still_refused(self):
        self.tri()
        with self.assertRaises(SystemExit):
            TP.add(self.run, "P1", 1, "the team", alt="to make: a jar", place=self.place)
        self.assertEqual(self.learned, [])

    def test_6_clear_removes_that_pictures_tries_only(self):
        self.tri()
        self.tri(code="P2", change="brighter")
        gone = TP.clear(self.run, "P1")
        self.assertEqual(gone, self.run / "tries" / "P1")
        self.assertFalse(gone.exists())
        self.assertTrue((self.run / "tries" / "P2" / "try-1.jpg").is_file())
        self.assertTrue((self.run / "media" / PIC).is_file())
        self.assertEqual([t["n"] for t in self.tri()], [1])                    # the folder is gone: it counts again


class TestRouting(Base):
    def setUp(self):
        super().setUp()
        p = mock.patch.object(ask, "REPO", self.tmp)
        p.start()
        self.addCleanup(p.stop)
        self.calls = []

    def line(self, rest, who=""):
        return "Email request (x): nov-99 P1 [%s/%s, section 1, picture 0] · %s%s" % (BRAND, LABEL, rest, who)

    def ask(self, *rows):
        f = self.tmp / "asked.txt"
        f.write_text("\n".join(rows) + "\n")
        with contextlib.redirect_stdout(self.out):
            return ask.main([str(f)])

    def test_7_picture_words_go_to_try_use_try_goes_to_add(self):
        def try_change(run, code, change, by, **k):
            self.calls.append(("try", code, change, by))
            return [{"n": 1, "made": "tries/P1/try-1.jpg", "judge": {"verdict": "pass", "why": []}}]

        def add(run, code, n, by, **k):
            self.calls.append(("add", code, n, by))
            return {"picture": code, "rebuilt": [{"step": "design/build.py", "ok": True}]}

        def apply_one(k):
            self.calls.append(("apply", k["action"]))
            return True, "done"
        shared = []
        with mock.patch.object(TP, "try_change", try_change), mock.patch.object(TP, "add", add), \
                mock.patch.object(ask, "apply_one", apply_one):
            code = self.ask(self.line("change this picture: warmer light"))
            self.assertEqual(code, 0)
            self.assertEqual(self.calls, [("try", "P1", "warmer light", "graphic-designer")])   # no name given: the role
            self.assertIn("try 1 made: ", self.out.getvalue())
            self.assertIn("say 'use try 1' to add it", self.out.getvalue())
            with mock.patch.object(ask, "share", lambda paths, msg: shared.append(paths) or "shared"):
                code = self.ask(self.line("use try 2"),
                                self.line('change the words: [{"path": "text", "value": "new"}]', " (from the team)"))
        self.assertEqual(code, 0)
        self.assertEqual(self.calls[1:], [("add", "P1", 2, "graphic-designer"), ("apply", "words")])
        self.assertEqual(len(shared), 1)
        self.assertIn("platform/data/records/model-outcome", shared[0])
        self.assertIn("runs/email-production/%s/%s" % (BRAND, LABEL), shared[0])
        self.assertEqual(ask.run_paths([{"brand": BRAND, "label": LABEL, "action": "words"}]),
                         ["runs/email-production/%s/%s" % (BRAND, LABEL), "runs/learnings"])

    def test_7b_use_try_without_a_number_is_asked_back(self):
        got = ask.parse(self.line("use try"))
        self.assertEqual(got[0][0], None)
        self.assertIn("which try? say use try <n>", got[0][1])
        k, why = ask.parse(self.line("add try 4"))[0]
        self.assertEqual((why, k["action"], k["n"]), (None, "add", 4))


class TestAdapter(Base):
    def setUp(self):
        super().setUp()
        p = mock.patch.object(adapter, "RUNS", self.runs)
        p.start()
        self.addCleanup(p.stop)

    def test_8_try_verb(self):
        seen = []

        def try_change(run, code, change, by, **k):
            seen.append((code, change, by, k))
            print("1 paid generation(s) on x — price not on record")
            return [{"n": 1, "made": "tries/P2/try-1.jpg", "judge": None}]
        with mock.patch.object(TP, "try_change", try_change):
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                code = adapter.main(["try", "%s__%s" % (BRAND, LABEL), "2", "picture", "0: brighter", "--by", "the team",
                                     "--model", "gemini-3-pro-image", "--count", "2"])
        self.assertEqual(code, 0)
        got = json.loads(out.getvalue())                                       # stdout stays JSON
        self.assertEqual((got["ok"], got["tries"][0]["n"]), (True, 1))
        self.assertEqual(seen, [("P2", "brighter", "the team", {"model": "gemini-3-pro-image", "count": 2, "from_try": None})])
        code, got = adapter.try_("%s__%s" % (BRAND, LABEL), "1", "words", "[]", "the team")
        self.assertEqual(code, 2)
        code, got = adapter.try_("%s__%s" % (BRAND, LABEL), "1", "go", None, "the team")
        self.assertEqual(code, 2)


class TestPlane(Base):
    def test_9_nothing_written_into_the_registry_or_the_house_and_the_kind_is_whole(self):
        tops = (REPO / "components" / "models", REPO / "components" / "generative-model-house")
        before = snapshot(*tops)
        self.tri(count=2)
        with contextlib.redirect_stdout(self.out):
            TP.add(self.run, "P1", 1, "the team", place=self.place)
        self.assertEqual(snapshot(*tops), before)
        self.assertEqual(len(self.outcomes()), 3)
        m = json.loads((REPO / "platform" / "data" / "kinds" / "model-outcome.json").read_text())
        self.assertEqual((m["kind"], m["title"], m["open_items"], m["items"]), ("model-outcome", "Model outcomes", True, []))
        self.assertTrue(m["note"].strip())
        self.assertEqual([f["key"] for f in m["verdict_fields"]],
                         ["model", "door", "purpose", "brand", "judge", "picked", "tries_before_pick", "cost"])
        self.assertTrue(all(f.get("type") and f.get("label") for f in m["verdict_fields"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
