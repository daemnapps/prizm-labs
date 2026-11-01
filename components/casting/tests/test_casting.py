#!/usr/bin/env python3
"""Tests for the casting component.

    python3 components/casting/tests/test_casting.py

Stdlib `unittest`, and it must pass on `/usr/bin/python3` (3.9), so no 3.10+
syntax anywhere. **No network, no model, no real key, and nothing
written outside a temporary directory.** Every test builds its own throwaway
workspace under `tempfile`, points `AI_WORKSPACE` at it, and passes a stub
element library, a stub footage reader, a stub generator and a stub judge — so
a test never reaches the real `brands/`, the real `runs/`, a real endpoint or
the Drive mount (`mirror=False` everywhere, and the mount is never touched).
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent))                  # APPEND — never insert at 0
import casting as C                                # noqa: E402


# ---------------------------------------------------------------- the stubs

class StubLibrary:
    """Stands in for components/elements/machine/elements.py."""

    class Unknown(KeyError):
        pass

    def __init__(self):
        self.rows = {
            ("style", "image"): {
                "plain-room": {"id": "plain-room", "name": "Plain room",
                               "what": "a real room, flat light"},
                "reserved": {"id": "reserved", "name": "Reserved",
                             "what": "[TO DEFINE] nothing yet"}},
            ("format", "image"): {
                "sheet": {"id": "sheet", "name": "Sheet", "what": "a reference sheet"}},
        }

    def get(self, element, asset, id_):
        book = self.rows.get((element, asset), {})
        if id_ not in book:
            raise self.Unknown("`%s` is not a %s for %s — known: %s"
                               % (id_, element, asset, ", ".join(book) or "none yet"))
        return book[id_]


class StubReader:
    """Stands in for image-production's asset reader."""

    def __init__(self, described=None, shelf=None):
        self._described = described or []
        self._shelf = shelf or []
        self.calls = []

    def described(self, brand, force=False):
        self.calls.append(("described", brand))
        return list(self._described)

    def pick(self, brand, direction, product=None, want_people=None, limit=4,
             force=False):
        self.calls.append(("pick", brand, direction))
        return list(self._shelf), []


def png_bytes(w=2, h=2):
    """A real PNG, written with the stdlib — nothing imported, nothing drawn."""
    import struct
    import zlib
    raw = b"".join(b"\x00" + b"\x7f\x7f\x7f" * w for _ in range(h))

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b""))


def stub_runner(made, fail=()):
    """Answers like the generator door, and records every call. It never opens
    a socket and never starts a subprocess."""
    calls = []

    def runner(argv, env, cwd):
        calls.append({"argv": list(argv), "cwd": cwd,
                      "key_in_env": bool(env.get("OPENAI_API_KEY"))})
        step = Path(argv[-1]).stem.replace("job-", "")
        if step in fail:
            return "", "the door said no"
        out = Path(made) / ("out-%s.png" % step)
        out.write_bytes(png_bytes())
        return "wrote %s\n" % out, ""
    runner.calls = calls
    return runner


def stub_judge(fails_for=()):
    """`caller(prompt, image_path, entry) -> str`, the judge's own seam."""
    seen = []

    def caller(prompt, image_path, entry):
        seen.append({"image": image_path, "prompt_chars": len(prompt)})
        name = Path(image_path).stem.replace("out-", "")
        n = prompt.count("\n1. ") and 1 or 1        # at least one test
        del n
        if name in fails_for:
            return json.dumps({"results": [{"test": 1, "verdict": "FAIL",
                                            "evidence": "the stub failed it"}]})
        return json.dumps({"results": []})
    caller.seen = seen
    return caller


# --------------------------------------------------------- the fake workspace

def workspace(root):
    """A throwaway tree that looks like the repo: components/ and brands/."""
    root = Path(root)
    (root / "components").mkdir(parents=True, exist_ok=True)
    b = root / "brands" / "acme"
    reg = b / "core-avatars" / "casting"
    reg.mkdir(parents=True, exist_ok=True)
    (reg / "authority.json").write_text(json.dumps({
        "_title": "Acme", "_open": ["no night-shift explainer has been built"],
        "people": [{"id": "vee", "name": "Vee", "role": "pharmacist",
                    "fronts": "the mechanism explanation slot",
                    "hair": "short", "element_id": "el-1",
                    "hf_voice_element_id": "vo-1"}]}))
    (reg / "roster.json").write_text(json.dumps({
        "people": [{"id": "kip", "name": "Kip", "problem": "ingrown hairs",
                    "lane": "tired-king", "note": "Teenage. Never used."}]}))
    (reg / "identities.json").write_text(json.dumps({
        "people": {"kip": {"element_id": "el-2", "soul_id": "soul-2"}}}))
    (b / "ai-cast").mkdir(parents=True, exist_ok=True)
    (root / "brands" / "other" / "ai-cast" / "zed").mkdir(parents=True, exist_ok=True)
    (root / "brands" / "other" / "ai-cast" / "zed" / "character.md").write_text(
        "# Zed — the night baker\n\nThe one who proves the routine at 4am.\n\n"
        "## Basics\n- wardrobe: an apron\n")
    return root


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = workspace(self.tmp)
        self._env = os.environ.get("AI_WORKSPACE")
        os.environ["AI_WORKSPACE"] = str(self.root)
        self.lib = StubLibrary()

    def tearDown(self):
        if self._env is None:
            os.environ.pop("AI_WORKSPACE", None)
        else:
            os.environ["AI_WORKSPACE"] = self._env
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def frame(self, name="frame_01.jpg"):
        f = Path(self.tmp) / name
        f.write_bytes(png_bytes())
        return str(f)

    def reader(self, **kw):
        return StubReader(**kw)

    def req(self, **over):
        r = {"brand": "acme", "role": "night baker", "id": "nb", "kind": "authority",
             "noun": "man", "who": "a man in his fifties", "wardrobe": "an apron",
             "world": "a bakery at 4am, flat overhead light",
             "baseline": self.frame(), "out": str(Path(self.tmp) / "run")}
        r.update(over)
        return r


# ------------------------------------------------------------------- the bank

class TestBank(Base):
    def test_the_one_call_answers_with_the_banked_person(self):
        a = C.cast(brand="acme", role="pharmacist")
        self.assertTrue(a["covered"])
        self.assertEqual(a["person"]["id"], "vee")
        self.assertEqual(a["where"], "authority")

    def test_a_role_nobody_covers_is_a_gap_with_its_evidence(self):
        a = C.cast(brand="acme", role="night baker")
        self.assertFalse(a["covered"])
        self.assertIsNone(a["person"])
        self.assertIn("no record says more than half", a["gap"]["said"])
        self.assertIn("no night-shift explainer has been built", a["gap"]["open_items"])

    def test_a_describing_word_is_never_coverage(self):
        """A free-text note saying "Teenage" does not make Kip a teenage
        skateboarder — the split between role fields and describing fields is
        the whole reason coverage can be trusted."""
        a = C.cast(brand="acme", role="teenage skateboarder")
        self.assertFalse(a["covered"])
        self.assertTrue(a["candidates"])
        self.assertEqual(a["candidates"][0]["id"], "kip")
        self.assertEqual(a["candidates"][0]["role_words"], [])

    def test_a_brand_whose_cast_is_only_bibles_is_answered_not_refused(self):
        a = C.cast(brand="other", role="night baker")
        self.assertTrue(a["covered"])
        self.assertEqual(a["person"]["id"], "zed")
        self.assertEqual(a["where"], "bible")

    def test_castability_is_read_off_the_record_never_assumed(self):
        a = C.cast(brand="acme", role="pharmacist")
        self.assertTrue(a["castable"]["cinema"])
        self.assertEqual(a["castable"]["why"], [])
        b = C.cast(brand="other", role="night baker")
        self.assertFalse(b["castable"]["cinema"])
        self.assertEqual(len(b["castable"]["why"]), 2)

    def test_an_unreadable_registry_is_a_problem_not_an_empty_bank(self):
        (self.root / "brands" / "acme" / "core-avatars" / "casting"
         / "roster.json").write_text("{ not json")
        a = C.cast(brand="acme", role="pharmacist")
        self.assertTrue(any("could not be read" in p for p in a["problems"]))

    def test_two_registries_on_disk_are_reported(self):
        (self.root / "brands" / "acme" / "ai-cast" / "casting").mkdir(parents=True)
        a = C.cast(brand="acme", role="pharmacist")
        self.assertTrue(any("TWO cast registries" in p for p in a["problems"]))

    def test_no_brand_is_ever_defaulted(self):
        with self.assertRaises(SystemExit):
            C.cast(brand=None, role="pharmacist")
        with self.assertRaises(SystemExit):
            C.cast(brand="nope", role="pharmacist")


# ----------------------------------------------------------------- the search

class TestSearch(Base):
    def rows(self):
        d = Path(self.tmp) / "rec"
        d.mkdir(exist_ok=True)
        (d / "frame_01.jpg").write_bytes(png_bytes())
        (d / "frame_02.jpg").write_bytes(png_bytes())
        return [{"path": "/x/a.mp4", "name": "a.mp4", "kind": "footage",
                 "collection": "acme-creators", "said": "a baker in a bakery",
                 "record": str(d)}]

    def test_it_asks_the_shared_reader_and_writes_no_search_of_its_own(self):
        r = self.reader(described=self.rows())
        rows, _why = C.search.baselines("acme", "baker, bakery", reader=r)
        self.assertEqual(r.calls[0], ("described", "acme"))
        self.assertEqual(rows[0]["baseline"], str(Path(self.tmp) / "rec" / "frame_01.jpg"))
        self.assertIn("baker", rows[0]["words"])

    def test_a_record_with_no_frame_is_not_a_baseline(self):
        rows = self.rows()
        rows[0]["record"] = str(Path(self.tmp) / "empty")
        got, _why = C.search.baselines("acme", "baker", reader=self.reader(described=rows))
        self.assertEqual(got, [])

    def test_a_missing_index_says_so_instead_of_answering_nothing(self):
        _got, why = C.search.baselines("acme", "baker", reader=self.reader())
        self.assertTrue(any("no footage records" in w for w in why))

    def test_a_caller_named_baseline_wins_outright(self):
        f = self.frame()
        got = C.search.choose("acme", "baker", given=f,
                              reader=self.reader(described=self.rows()))
        self.assertEqual(got["baseline"], f)
        self.assertIn("a person picked the frame", got["why"])


# ------------------------------------------------------------------ prompting

class TestPrompting(Base):
    def test_every_generating_step_has_a_prompt_file(self):
        for step in C.GENERATING:
            self.assertTrue(C.prompting.latest(step).is_file())

    def test_the_skeletons_ask_only_for_slots_that_exist(self):
        for step in C.GENERATING:
            skeleton = C.prompting.body(C.prompting.latest(step))
            asked = set(C.prompting.SLOT.findall(skeleton))
            self.assertEqual(asked - set(C.prompting.ORDER[step]), set(),
                             "%s asks for a slot nothing fills" % step)

    def test_the_anchor_takes_no_slots_on_purpose(self):
        text, _p = C.prompting.render("anchor", self.req())
        self.assertEqual(C.prompting.SLOT.findall(text), [])
        self.assertIn("ONLY source of identity", text)

    def test_the_master_prompt_says_a_different_person_out_loud(self):
        text, _p = C.prompting.render("master", self.req())
        self.assertIn("Change ONLY the person", text)
        self.assertIn("DIFFERENT man", text)
        self.assertIn("BASELINE, not a likeness", text)

    def test_the_standing_rules_are_on_every_slotted_prompt(self):
        rules = C.prompting.standing_rules()
        for step in ("master", "detail"):
            text, _p = C.prompting.render(step, self.req(detail="hands"))
            self.assertIn(rules.splitlines()[0], text)

    def test_a_documentation_header_is_never_sent(self):
        text, _p = C.prompting.render("master", self.req())
        self.assertNotIn("Lifted verbatim", text)


# ---------------------------------------------------------------- the dry run

class TestDryRun(Base):
    def test_it_writes_nothing_anywhere(self):
        req = self.req()                           # the frame first, then the snapshot
        before = sorted(str(p) for p in self.root.rglob("*"))
        r, resolved = C.dry_run(req, lib=self.lib,
                                reader=self.reader(described=[]))
        after = sorted(str(p) for p in self.root.rglob("*"))
        self.assertEqual(before, after)
        self.assertFalse((Path(self.tmp) / "run").exists())
        self.assertIsNotNone(resolved)
        self.assertEqual(r.missing, 0)

    def test_it_resolves_the_prompts_exactly_as_they_would_be_sent(self):
        _r, resolved = C.dry_run(self.req(), lib=self.lib, reader=self.reader())
        self.assertIn("master", resolved["prompts"])
        self.assertIn("anchor", resolved["prompts"])
        self.assertNotIn("detail", resolved["prompts"])
        self.assertIn("a bakery at 4am", resolved["prompts"]["master"]["text"])

    def test_a_covered_role_is_reported_as_missing_before_anything_runs(self):
        r, _resolved = C.dry_run(self.req(role="pharmacist", id="vee2"),
                                 lib=self.lib, reader=self.reader())
        self.assertTrue(any("already cast" in p for p in r.problems))

    def test_the_question_alone_is_free(self):
        before = sorted(str(p) for p in self.root.rglob("*"))
        r, answer = C.dry_who("acme", "pharmacist")
        self.assertEqual(before, sorted(str(p) for p in self.root.rglob("*")))
        self.assertTrue(answer["covered"])
        self.assertEqual(r.missing, 0)


# ------------------------------------------------------------------ the gates

class TestGates(Base):
    def problems(self, req, **kw):
        req, answer, _p = C.resolve(req, lib=self.lib,
                                    reader=self.reader(**kw))
        return C.gates.input_problems(req, answer, build=True)

    def test_a_role_the_bank_covers_never_gets_a_new_face(self):
        p = self.problems(self.req(role="pharmacist", id="vee2"))
        self.assertTrue(any("already cast" in x for x in p))
        self.assertTrue(any("never gets a new face" in x for x in p))

    def test_identity_from_a_paragraph_is_refused(self):
        p = self.problems(self.req(baseline=None))
        self.assertTrue(any("identity comes from an IMAGE" in x for x in p))

    def test_a_baseline_that_is_not_on_this_machine_is_refused(self):
        p = self.problems(self.req(baseline="/nope/frame.jpg"))
        self.assertTrue(any("not a file on this machine" in x for x in p))

    def test_the_noun_is_never_defaulted(self):
        p = self.problems(self.req(noun=None))
        self.assertTrue(any("`noun`" in x for x in p))

    def test_the_record_a_row_belongs_in_is_declared_never_guessed(self):
        p = self.problems(self.req(kind=None))
        self.assertTrue(any("`kind` is not declared" in x for x in p))

    def test_an_unknown_element_is_refused_naming_the_real_ones(self):
        el = C.gates.resolve_elements({"style": "nope"}, self.lib)
        self.assertTrue(el["problems"])
        self.assertIn("plain-room", el["problems"][0])

    def test_an_element_named_but_not_defined_is_refused(self):
        el = C.gates.resolve_elements({"style": "reserved"}, self.lib)
        self.assertTrue(any("not defined yet" in p for p in el["problems"]))

    def test_a_real_element_passes_and_reaches_the_prompt(self):
        req = self.req(style="plain-room")
        req, _a, prompts = C.resolve(req, lib=self.lib, reader=self.reader())
        self.assertEqual(req["_elements"]["problems"], [])
        self.assertIn("Plain room", prompts["master"]["text"])

    def test_a_clean_build_holds_at_no_gate(self):
        self.assertEqual(self.problems(self.req()), [])


# ------------------------------------------------------------------ the build

class TestBuild(Base):
    def build(self, req=None, fail=(), judge_fails=(), **kw):
        made = Path(self.tmp) / "door"
        made.mkdir(exist_ok=True)
        self.runner = stub_runner(made, fail)
        self.judge = stub_judge(judge_fails)
        return C.build(req or self.req(), lib=self.lib,
                       reader=self.reader(), runner=self.runner,
                       judge_caller=self.judge, mirror=False,
                       echo=lambda *a, **k: None, **kw)

    def test_the_nine_steps_are_declared_and_all_recorded(self):
        self.assertEqual([s["key"] for s in C.STEPS],
                         ["gap", "search", "baseline", "master", "anchor",
                          "detail", "bible", "register", "mirror"])
        out = self.build()
        self.assertEqual(sorted(set(s["key"] for s in out["steps"])),
                         sorted(set(s["key"] for s in C.STEPS)))

    def test_the_anchor_references_the_master_never_the_last_output(self):
        out = self.build(self.req(detail="hands and forearms"))
        refs = [c["argv"] for c in self.runner.calls]
        self.assertEqual(len(refs), 3)
        jobs = [json.loads(Path(a[-1]).read_text()) for a in refs]
        # the anchor's and the detail's reference are both the MASTER's picture
        self.assertEqual(jobs[1]["reference"], jobs[2]["reference"])
        self.assertNotEqual(jobs[0]["reference"], jobs[1]["reference"])

    def test_pictures_land_in_the_brands_cast_folder_the_way_they_already_do(self):
        out = self.build()
        c = C.paths.character("acme", "nb")
        self.assertTrue(c["master"].is_file())
        self.assertTrue(c["anchor"].is_file())
        self.assertEqual(out["filed"]["master"], str(c["master"]))

    def test_a_held_sheet_is_never_filed_and_nothing_derives_from_it(self):
        out = self.build(judge_fails=("master",))
        self.assertFalse(C.paths.character("acme", "nb")["master"].is_file())
        statuses = dict((s["key"], s["status"]) for s in out["steps"])
        self.assertEqual(statuses["master"], "held")
        self.assertEqual(statuses["anchor"], "skipped")
        self.assertIn("media", out["held"])
        self.assertTrue((Path(out["out"]) / "held" / "master-why.md").is_file())

    def test_a_door_that_returns_nothing_is_a_failure_that_says_so(self):
        out = self.build(fail=("master",))
        statuses = dict((s["key"], s["status"]) for s in out["steps"])
        self.assertEqual(statuses["master"], "failed")
        self.assertIn("media", out["held"])

    def test_the_detail_board_is_never_a_default(self):
        out = self.build()
        statuses = dict((s["key"], s["status"]) for s in out["steps"])
        self.assertEqual(statuses["detail"], "skipped")
        self.assertEqual(len(self.runner.calls), 2)

    def test_the_key_never_reaches_the_record(self):
        os.environ["OPENAI_API_KEY"] = "not-a-real-key-and-never-written-down"
        try:
            out = self.build()
        finally:
            os.environ.pop("OPENAI_API_KEY", None)
        text = (Path(out["out"]) / "run.json").read_text()
        self.assertNotIn("not-a-real-key", text)
        self.assertTrue(self.runner.calls[0]["key_in_env"])

    def test_every_prompt_is_saved_as_sent(self):
        out = self.build()
        for step in ("master", "anchor"):
            f = Path(out["out"]) / ("%s--prompt-as-sent.txt" % step)
            self.assertTrue(f.is_file())
            self.assertEqual(f.read_text().strip(),
                             out["prompts"][step]["text"].strip())

    def test_the_run_record_carries_the_assignment_and_the_state(self):
        out = self.build()
        rec = json.loads((Path(out["out"]) / "run.json").read_text())
        self.assertEqual(rec["machine"], "casting")
        self.assertEqual(rec["brand"], "acme")
        self.assertEqual(rec["role"], "night baker")
        self.assertEqual(rec["state"], "filed")
        self.assertFalse(rec["covered_before"])


# --------------------------------------------------------------- registration

class TestRegistration(Base):
    def test_it_proposes_and_never_writes_into_the_brand(self):
        reg = self.root / "brands" / "acme" / "core-avatars" / "casting"
        before = dict((p.name, p.read_text()) for p in reg.iterdir())
        made = Path(self.tmp) / "door"
        made.mkdir(exist_ok=True)
        out = C.build(self.req(), lib=self.lib, reader=self.reader(),
                      runner=stub_runner(made), judge_caller=stub_judge(),
                      mirror=False, echo=lambda *a, **k: None)
        after = dict((p.name, p.read_text()) for p in reg.iterdir())
        self.assertEqual(before, after)
        self.assertTrue((Path(out["out"]) / "register" / "proposed-row.json").is_file())
        self.assertTrue((Path(out["out"]) / "register" / "REGISTER.md").is_file())

    def test_the_proposed_row_goes_to_the_record_the_kind_declares(self):
        p = C.registration.proposal(self.req(kind="roster"))
        self.assertEqual(p["file"], "roster.json")
        p = C.registration.proposal(self.req(kind="authority"))
        self.assertEqual(p["file"], "authority.json")

    def test_the_row_carries_nothing_nobody_supplied(self):
        row = C.registration.row_for({"id": "nb", "kind": "authority",
                                      "role": "night baker"})
        self.assertNotIn("hair", row)
        self.assertEqual(row["status"], "draft")

    def test_the_bible_is_a_draft_in_the_run_not_in_the_brand(self):
        made = Path(self.tmp) / "door"
        made.mkdir(exist_ok=True)
        out = C.build(self.req(), lib=self.lib, reader=self.reader(),
                      runner=stub_runner(made), judge_caller=stub_judge(),
                      mirror=False, echo=lambda *a, **k: None)
        self.assertTrue((Path(out["out"]) / "bible" / "character.md").is_file())
        self.assertFalse(C.paths.character("acme", "nb")["bible"].is_file())

    def test_what_is_still_open_is_said_out_loud(self):
        p = C.registration.proposal(self.req())
        self.assertEqual(len(p["still_open"]), 2)
        self.assertTrue(any("Element" in s for s in p["still_open"]))
        self.assertTrue(any("voice element" in s for s in p["still_open"]))


# -------------------------------------------------------------- the contract

class TestContract(Base):
    def test_an_unknown_field_is_refused_not_ignored(self):
        req = self.req()
        req["colour"] = "blue"
        with self.assertRaises(SystemExit) as e:
            C.resolve(req, lib=self.lib, reader=self.reader())
        self.assertIn("colour", str(e.exception))

    def test_the_question_takes_only_a_brand_and_a_role(self):
        with self.assertRaises(SystemExit):
            C.cast(brand="acme", role="x", style="plain-room")

    def test_importing_the_component_reads_no_key_and_opens_no_socket(self):
        import subprocess
        code = ("import sys; sys.path.append(%r); import casting; "
                "print('ok')" % str(HERE.parent))
        env = dict(os.environ)
        env.pop("OPENAI_API_KEY", None)
        env["HOME"] = self.tmp
        r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                           text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ok", r.stdout)


# ------------------------------------------------------- brand-agnostic, real

class TestBrandAgnostic(unittest.TestCase):
    """Run against the REAL brands tree — reading only, nothing written."""

    def test_no_brand_name_appears_in_any_code_or_prompt_file(self):
        env = os.environ.pop("AI_WORKSPACE", None)
        try:
            home = C.paths.home()
            brands = [p.name for p in C.paths.brands_dir().iterdir()
                      if p.is_dir() and not p.name.startswith(("_", "."))]
        finally:
            if env is not None:
                os.environ["AI_WORKSPACE"] = env
        self.assertTrue(brands, "no brands on disk — this test proves nothing")
        files = list((home / "casting").glob("*.py")) + list(home.glob("*.py")) \
            + list((home / "prompts").glob("*.md")) \
            + list((home / "tests").glob("*.py"))
        for f in files:
            text = f.read_text().lower()
            for b in brands:
                self.assertNotIn(b.lower(), text, "%s names the brand `%s`" % (f.name, b))

    def test_no_person_from_any_brands_cast_is_named_in_code_or_prompts(self):
        env = os.environ.pop("AI_WORKSPACE", None)
        try:
            home = C.paths.home()
            names = set()
            for b in C.paths.brands_dir().iterdir():
                if not b.is_dir() or b.name.startswith(("_", ".")):
                    continue
                for reg in C.paths.registries(b.name):
                    for f in ("roster.json", "authority.json"):
                        try:
                            data = json.loads((reg / f).read_text())
                        except (OSError, ValueError):
                            continue
                        for row in data.get("people") or []:
                            if isinstance(row, dict) and row.get("id"):
                                names.add(str(row["id"]).lower())
                cast = C.paths.brand(b.name)["cast"]
                if cast.is_dir():
                    for d in cast.iterdir():
                        if d.is_dir() and (d / "character.md").is_file():
                            names.add(d.name.lower())
        finally:
            if env is not None:
                os.environ["AI_WORKSPACE"] = env
        self.assertTrue(names, "no banked people on disk — this test proves nothing")
        import re
        files = list((home / "casting").glob("*.py")) + list(home.glob("*.py")) \
            + list((home / "prompts").glob("*.md"))
        for f in files:
            text = f.read_text().lower()
            for n in names:
                if len(n) < 4:
                    continue
                self.assertIsNone(re.search(r"\b%s\b" % re.escape(n), text),
                                  "%s names the banked person `%s`" % (f.name, n))

    def test_no_file_here_is_named_after_a_stdlib_module(self):
        import sys as _sys
        stdlib = set(getattr(_sys, "stdlib_module_names", ()))
        if not stdlib:                             # 3.9 has no such attribute
            stdlib = {"json", "types", "select", "code", "copy", "string", "time",
                      "site", "token", "parser", "queue", "signal", "socket",
                      "struct", "test", "uuid", "io", "os", "re", "abc", "enum"}
        home = C.paths.home()
        for f in list(home.rglob("*.py")):
            self.assertNotIn(f.stem, stdlib, "%s shadows a stdlib module" % f)


if __name__ == "__main__":
    unittest.main(verbosity=2)
