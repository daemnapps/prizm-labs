"""reference_check — the receipt, the prompt compare, the inputs match, and the whole folder with a stubbed judge.

Every test builds a throwaway hand-off folder under `tempfile` and points AI_WORKSPACE at a throwaway workspace. No
network, no key, no model: the look judge is a stub and the url fetch is a stub.

    /usr/bin/python3 tools/image-edit/tests/test_reference_check.py
"""
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.append(str(HERE))
import reference_check as RC  # noqa: E402

try:
    from PIL import Image
except ImportError:                       # the look tests need real pictures; the rest do not
    Image = None

KEY = "testbrand_widget_brief-0001"
EL = "aaaa1111-2222-3333-4444-555566667777"
CAST = "cccc1111-2222-3333-4444-555566667777"
PROMPT = "INPUTS\nIMAGE 1 is the reference.\n\nTHE PICTURE\nThe   tub becomes the widget.\nRULES\nChange nothing else."


def picture(path, colour):
    path.parent.mkdir(parents=True, exist_ok=True)
    if Image is None:
        path.write_bytes(b"png " + colour.encode())
    else:
        Image.new("RGB", (90, 160), colour).save(path)
    return path


def sheet():
    el = {"kind": "product", "id": "widget", "name": "WIDGET", "element": {"id": EL, "name": "widget-sheet"}}
    return {"brief_key": KEY, "brand": "testbrand", "steps": [
        {"n": 1, "asset": f"{KEY}_asset-01.png", "what": "the main picture", "medium": "image", "job": "pictures.generate",
         "higgsfield_model": "gpt_image_2_5", "model_name": "GPT Image 2.5", "prompt": PROMPT,
         "references": [
             {"n": 1, "kind": "image", "role": "the reference", "local": "refs/step-01-image-1-swipe.jpg",
              "file": "x/refs/step-01-image-1-swipe.jpg", "element": None},
             {"n": 2, "kind": "image", "role": "the real WIDGET: its sheet", "local": "refs/product-widget-sheet.png",
              "file": "x/refs/product-widget-sheet.png", "element": el},
             {"n": 3, "kind": "image", "role": "the real WIDGET: its front", "local": "refs/product-widget-front.png",
              "file": "x/refs/product-widget-front.png", "element": el}],
         "cast": [{"who": "THE HOST", "element": {"id": CAST, "name": None},
                   "fallback": {"local": "refs/cast-host-master.png"}}],
         "settings": {"aspect_ratio": "9:16"}},
        {"n": 2, "asset": f"{KEY}_asset-02.png", "what": "words only", "medium": "image", "job": "words-only",
         "prompt": None, "references": [{"n": 1, "kind": "image", "role": "the plate", "local": "refs/approved-plate.png",
                                         "file": "x/refs/approved-plate.png", "element": None}],
         "settings": {}}]}


def good_receipt(**over):
    d = {"asset": f"{KEY}_asset-01.png", "step": 1, "higgsfield_generation_id": "gen-123", "model": "gpt_image_2_5",
         "prompt": PROMPT, "inputs": [
             {"n": 1, "kind": "image", "file": "step-01-image-1-swipe.jpg"},
             {"n": 2, "kind": "element", "file": "widget-sheet", "media_id": EL},
             {"kind": "element", "file": "the host", "media_id": CAST}],
         "settings": {"aspect_ratio": "9:16"}, "made_by": "an agent", "made_at": "2026-10-28T10:00"}
    d.update(over)
    return d


def set_step():
    return {"n": 3, "asset": f"{KEY}_asset-03.png", "what": "a set change", "medium": "image", "job": "set-change",
            "higgsfield_model": None, "model_name": "Higgsfield 3D Jutsu", "prompt": PROMPT,
            "set_request": {"change": "a bigger sign"}, "settings": {"aspect_ratio": "9:16"},
            "references": [{"n": 1, "kind": "image", "role": "the set's kept print", "local": "refs/approved-plate.png",
                            "file": "x/refs/approved-plate.png", "element": None, "look_only": True},
                           {"n": 2, "kind": "image", "role": "the product's casting sheet", "local": "refs/product-widget-sheet.png",
                            "file": "x/refs/product-widget-sheet.png", "element": None}]}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "brands").mkdir()
        (self.tmp / "components").mkdir()
        self.old = os.environ.get("AI_WORKSPACE")
        os.environ["AI_WORKSPACE"] = str(self.tmp)
        self.f = self.tmp / "runs/handoffs/graphic-designer/testbrand" / KEY
        for name, c in (("step-01-image-1-swipe.jpg", "red"), ("product-widget-sheet.png", "black"),
                        ("product-widget-front.png", "gray"), ("cast-host-master.png", "brown"),
                        ("approved-plate.png", "blue")):
            picture(self.f / "refs" / name, c)
        self.sheet = sheet()
        (self.f / "run.json").write_text(json.dumps(self.sheet))
        self.a1 = picture(self.f / "returned" / f"{KEY}_asset-01.png", "green")
        self.a2 = picture(self.f / "returned" / f"{KEY}_asset-02.png", "blue")

    def tearDown(self):
        if self.old is None:
            os.environ.pop("AI_WORKSPACE", None)
        else:
            os.environ["AI_WORKSPACE"] = self.old
        shutil.rmtree(self.tmp, ignore_errors=True)

    def receipt(self, data, asset=None, name=None):
        asset = asset or self.a1
        p = asset.with_name(name or asset.stem + RC.RECEIPT)
        p.write_text(data if isinstance(data, str) else json.dumps(data))
        return p

    def rc(self, asset=None):
        return RC.read_receipt(asset or self.a1)


class ReceiptTest(Base):
    def test_no_receipt_is_amber_and_says_so(self):
        r = RC.check_receipt(self.rc(), self.sheet["steps"][0], self.a1.name)
        self.assertEqual(r["state"], RC.AMBER)
        self.assertIn("can't prove the references", r["why"])

    def test_receipt_read_by_stem_or_by_full_name(self):
        self.receipt(good_receipt(), name=self.a1.name + RC.RECEIPT)
        self.assertEqual(self.rc()["kind"], "json")
        r = RC.check_receipt(self.rc(), self.sheet["steps"][0], self.a1.name)
        self.assertEqual((r["state"], r["generation"], r["made_by"]), (RC.OK, "gen-123", "an agent"))

    def test_unreadable_receipt_is_wrong_not_guessed(self):
        self.receipt("{not json")
        r = RC.check_receipt(self.rc(), self.sheet["steps"][0], self.a1.name)
        self.assertEqual(r["state"], RC.BAD)
        self.assertIn("not readable JSON", r["why"])

    def test_receipt_for_another_step_or_model_or_without_an_id_is_wrong(self):
        self.receipt(good_receipt(step=3, model="flux_2", higgsfield_generation_id=None))
        r = RC.check_receipt(self.rc(), self.sheet["steps"][0], self.a1.name)
        self.assertEqual(r["state"], RC.BAD)
        for bit in ("names step 3", "made with flux_2", "no generation or job id"):
            self.assertIn(bit, r["why"])

    def test_job_id_and_model_name_are_accepted(self):
        d = good_receipt(model="GPT Image 2.5")
        d.pop("higgsfield_generation_id")
        d["job_id"] = "job-9"
        self.receipt(d)
        self.assertEqual(RC.check_receipt(self.rc(), self.sheet["steps"][0], self.a1.name)["state"], RC.OK)

    def test_a_link_is_a_receipt_but_proves_neither_prompt_nor_inputs(self):
        self.a1.with_name(self.a1.stem + RC.LINK).write_text("\nhttps://higgsfield.ai/job/abc\n")
        rc, step = self.rc(), self.sheet["steps"][0]
        self.assertEqual(RC.check_receipt(rc, step, self.a1.name)["state"], RC.OK)
        self.assertEqual(RC.check_prompt(rc, step)["state"], RC.AMBER)
        self.assertEqual(RC.check_inputs(rc, step, self.f)["state"], RC.AMBER)
        self.a1.with_name(self.a1.stem + RC.LINK).write_text("I made it on Tuesday")
        self.assertEqual(RC.check_receipt(self.rc(), step, self.a1.name)["state"], RC.BAD)

    def test_a_step_with_no_model_call_needs_no_receipt(self):
        step = self.sheet["steps"][1]
        rc = self.rc(self.a2)
        self.assertEqual([RC.check_receipt(rc, step, self.a2.name)["state"], RC.check_prompt(rc, step)["state"],
                          RC.check_inputs(rc, step, self.f)["state"]], [RC.NA] * 3)


class PromptTest(Base):
    def test_word_for_word_with_whitespace_set_aside(self):
        self.receipt(good_receipt(prompt="  INPUTS IMAGE 1 is the reference.\r\n\tTHE PICTURE The tub becomes the "
                                         "widget. RULES Change nothing else. "))
        self.assertEqual(RC.check_prompt(self.rc(), self.sheet["steps"][0])["state"], RC.OK)

    def test_the_steps_own_element_placeholders_are_set_aside(self):
        sent = PROMPT.replace("The   tub", f"<<<{EL}>>> The tub").replace("IMAGE 1 is", "@widget-sheet IMAGE 1 is")
        self.receipt(good_receipt(prompt=sent))
        r = RC.check_prompt(self.rc(), self.sheet["steps"][0])
        self.assertEqual(r["state"], RC.OK)
        self.assertIn("2 element placeholder", r["why"])

    def test_another_placeholder_is_a_change(self):
        self.receipt(good_receipt(prompt=PROMPT + " <<<some-other-element>>>"))
        self.assertEqual(RC.check_prompt(self.rc(), self.sheet["steps"][0])["state"], RC.BAD)

    def test_a_changed_word_is_wrong_and_the_diff_names_it(self):
        self.receipt(good_receipt(prompt=PROMPT.replace("widget", "gizmo").replace("Change nothing else.", "")))
        r = RC.check_prompt(self.rc(), self.sheet["steps"][0])
        self.assertEqual(r["state"], RC.BAD)
        self.assertEqual((r["diff"][0]["sheet"], r["diff"][0]["sent"]), ("widget.", "gizmo."))
        self.assertIn("tub becomes the", r["diff"][0]["at"])
        self.assertEqual(r["diff"][1]["sheet"], "Change nothing else.")

    def test_no_receipt_or_no_prompt_in_it(self):
        self.assertEqual(RC.check_prompt(self.rc(), self.sheet["steps"][0])["state"], RC.AMBER)
        self.receipt(good_receipt(prompt=""))
        self.assertEqual(RC.check_prompt(self.rc(), self.sheet["steps"][0])["state"], RC.BAD)


class InputsTest(Base):
    def check(self, inputs, fetch=lambda url: None):
        self.receipt(good_receipt(inputs=inputs))
        return RC.check_inputs(self.rc(), self.sheet["steps"][0], self.f, fetch=fetch)

    def test_every_reference_in_order_by_name_element_and_cast(self):
        r = self.check(good_receipt()["inputs"])
        self.assertEqual(r["state"], RC.OK, r)
        self.assertEqual([m["by"] for m in r["matched"]], ["file name", "element id", "element id"])

    def test_files_instead_of_the_element_by_refs_name(self):
        r = self.check([{"n": 1, "file": "refs/step-01-image-1-swipe.jpg"}, {"n": 2, "file": "product-widget-sheet.png"},
                        {"n": 3, "file": "product-widget-front.png"}, {"file": "cast-host-master.png"}])
        self.assertEqual(r["state"], RC.OK, r)

    def test_a_missing_reference_is_named(self):
        r = self.check([{"n": 1, "file": "step-01-image-1-swipe.jpg"}, {"n": 2, "file": "product-widget-sheet.png"}])
        self.assertEqual(r["state"], RC.BAD)
        self.assertIn("IMAGE 3 (product-widget-front.png)", r["why"])
        self.assertIn("cast THE HOST", r["why"])

    def test_an_extra_input_is_named(self):
        r = self.check(good_receipt()["inputs"] + [{"file": "random-mood-board.jpg"}])
        self.assertEqual(r["state"], RC.BAD)
        self.assertIn("extra", r["why"])
        self.assertIn("random-mood-board.jpg", r["why"])

    def test_out_of_order_is_wrong(self):
        r = self.check([{"file": "product-widget-sheet.png"}, {"file": "step-01-image-1-swipe.jpg"},
                        {"file": "product-widget-front.png"}, {"media_id": CAST}])
        self.assertEqual(r["state"], RC.BAD)
        self.assertIn("out of order", r["why"])
        r = self.check([{"n": 2, "file": "step-01-image-1-swipe.jpg"}, {"media_id": EL}, {"media_id": CAST}])
        self.assertIn("went in as 2, the sheet makes it 1", r["why"])

    def test_matched_by_bytes_from_a_given_hash_or_a_fetched_url(self):
        digest = hashlib.sha256((self.f / "refs/step-01-image-1-swipe.jpg").read_bytes()).hexdigest()
        r = self.check([{"n": 1, "sha256": digest}, {"media_id": EL}, {"media_id": CAST}])
        self.assertEqual(r["state"], RC.OK, r)
        self.assertEqual(r["matched"][0]["by"], "file bytes")
        asked = []
        r = self.check([{"n": 1, "url": "https://cdn.example.com/u/abc"}, {"media_id": EL}, {"media_id": CAST}],
                       fetch=lambda url: asked.append(url) or digest)
        self.assertEqual((r["state"], asked), (RC.OK, ["https://cdn.example.com/u/abc"]))
        r = self.check([{"n": 1, "url": "https://cdn.example.com/u/zzz"}, {"media_id": EL}, {"media_id": CAST}],
                       fetch=lambda url: "0" * 64)
        self.assertEqual(r["state"], RC.BAD)

    def test_only_a_public_https_address_is_ever_downloaded(self):
        for bad in ("http://cdn.example.com/a.png", "https://localhost/a.png", "https://127.0.0.1/a.png",
                    "https://10.0.0.4/a.png", "https://192.168.1.2/a", "https://printer.local/a", "file:///etc/passwd",
                    "https://[::1]/a", "ftp://x.com/a"):
            self.assertFalse(RC.is_public_https(bad), bad)
        self.assertTrue(RC.is_public_https("https://d8j0ntlcm91z4.cloudfront.net/user/abc.png"))
        self.assertIsNone(RC.fetch_hash("http://cdn.example.com/a.png"))          # refused before any socket

    def test_no_inputs_list_is_wrong(self):
        self.receipt(good_receipt(inputs="the usual"))
        self.assertEqual(RC.check_inputs(self.rc(), self.sheet["steps"][0], self.f)["state"], RC.BAD)


@unittest.skipIf(Image is None, "Pillow is not on this machine")
class FolderTest(Base):
    def setUp(self):
        super().setUp()
        self.calls = []
        (self.f / "delivery.json").write_text(json.dumps({"files": [
            {"name": self.a1.name, "file": f"x/returned/{self.a1.name}"},
            {"name": self.a2.name, "file": f"x/returned/{self.a2.name}"}]}))

    def judge(self, verdicts):
        def j(img, tests, images):
            self.calls.append((Path(img).name, list(tests), [lab for _p, lab in images]))
            res = [{"test": i + 1, "verdict": v[0], "evidence": v[1]} for i, v in enumerate(verdicts(tests))]
            fails = [f"{tests[r['test'] - 1].split('.')[0]} — {r['evidence']}" for r in res if r["verdict"] != "PASS"]
            return fails, json.dumps({"results": res}), "stub-judge"
        return j

    def test_whole_folder_writes_the_verdict_three_places(self):
        self.receipt(good_receipt())
        rep = RC.check(self.f, judge=self.judge(lambda t: [("PASS", "same scene")] * len(t)))
        a1, a2 = rep["assets"]
        self.assertEqual([a1[k]["state"] for k in RC.COLS], [RC.OK] * 5)
        self.assertEqual((a1["overall"], a2["overall"]), (RC.OK, RC.OK))
        names = [t.split(" — ")[0] for t in self.calls[0][1]]
        self.assertEqual(names, ["BUILT ON ITS REFERENCE", "PRODUCT MATCHES ITS SHEET", "FACE MATCHES THE CAST"])
        self.assertEqual(len(self.calls[0][2]), 4)                     # swipe, sheet + front, the cast picture
        self.assertTrue(self.calls[0][2][1].endswith("its product sheet"))
        self.assertEqual([t.split(" — ")[0] for t in self.calls[1][1]], ["BUILT ON ITS PLATE"])
        saved = json.loads((self.f / RC.OUT_JSON).read_text())
        self.assertEqual(saved["summary"], {RC.OK: 2, RC.AMBER: 0, RC.BAD: 0})
        md = (self.f / RC.OUT_MD).read_text()
        self.assertIn(f"| `{self.a1.name}` | 1 | the maker's receipt | ✓ | ✓ | ✓ | ✓ | ✓ | **✓** |", md)
        d = json.loads((self.f / "delivery.json").read_text())
        self.assertEqual(d["files"][0]["reference_check"]["overall"], RC.OK)
        self.assertEqual(d["files"][0]["reference_check"]["inputs"], RC.OK)
        for f in saved["assets"]:
            self.assertFalse(f["file"].startswith("/"), "stored paths are folder-relative")

    def test_a_look_fail_is_wrong_and_too_small_to_tell_is_not_proven(self):
        RC.check(self.f, judge=self.judge(lambda t: [("PASS", "ok"), ("FAIL", "the widget is white"), ("PASS", "ok")]
                                          [:len(t)] if len(t) == 3 else [("PASS", "ok")]))
        rep = json.loads((self.f / RC.OUT_JSON).read_text())
        self.assertEqual(rep["assets"][0]["looks"]["state"], RC.BAD)
        self.assertIn("the widget is white", rep["assets"][0]["looks"]["why"])
        (self.f / RC.OUT_JSON).unlink()
        RC.check(self.f, judge=self.judge(lambda t: [("PASS", "ok"), ("FAIL", f"{RC.UNCLEAR}: a dark blur on the seat"),
                                                     ("PASS", "ok")][:len(t)] if len(t) == 3 else [("PASS", "ok")]))
        looks = json.loads((self.f / RC.OUT_JSON).read_text())["assets"][0]["looks"]
        self.assertEqual(looks["state"], RC.AMBER)
        self.assertIn("not provable at this size", looks["why"])

    def test_an_unanswered_test_is_not_judged_never_a_pass(self):
        rep = RC.check(self.f, judge=self.judge(lambda t: [("PASS", "ok")]))
        self.assertEqual(rep["assets"][0]["looks"]["state"], RC.AMBER)

    def test_no_judge_or_no_key_is_amber_never_faked(self):
        rep = RC.check(self.f, judge=False)
        self.assertTrue(all(a["looks"]["state"] == RC.AMBER for a in rep["assets"]))

        def nokey(img, tests, images):
            raise RC.NotJudged("no JUDGE_KEY on this machine")
        rep = RC.check(self.f, judge=nokey)
        self.assertIn("not judged: no JUDGE_KEY", rep["assets"][0]["looks"]["why"])
        self.assertEqual(rep["assets"][0]["overall"], RC.AMBER)

        def offline(img, tests, images):
            raise OSError("network is unreachable")
        self.assertEqual(RC.check(self.f, judge=offline)["assets"][0]["looks"]["state"], RC.AMBER)

    def test_a_judged_file_is_not_judged_again_until_it_changes(self):
        ok = self.judge(lambda t: [("PASS", "ok")] * len(t))
        RC.check(self.f, judge=ok)
        n = len(self.calls)
        rep = RC.check(self.f, judge=ok)
        self.assertEqual(len(self.calls), n)
        self.assertTrue(rep["assets"][0]["looks"].get("cached"))
        picture(self.a1, "yellow")
        RC.check(self.f, judge=ok)
        self.assertEqual(len(self.calls), n + 1)

    def test_a_file_no_step_names_and_a_folder_with_no_run_sheet(self):
        picture(self.f / "returned" / "final-final.png", "white")
        rep = RC.check(self.f, judge=False)
        stray = [a for a in rep["assets"] if a["file"].endswith("final-final.png")][0]
        self.assertEqual((stray["step"], stray["overall"]), (None, RC.AMBER))
        (self.f / "run.json").unlink()
        rep = RC.check(self.f, judge=False)
        self.assertIn("no run.json", rep["assets"][0]["receipt"]["why"])

    def test_wrong_inputs_make_the_file_wrong_in_every_record(self):
        self.receipt(good_receipt(inputs=[{"file": "step-01-image-1-swipe.jpg"}]))
        rep = RC.check(self.f, judge=False)
        self.assertEqual(rep["assets"][0]["overall"], RC.BAD)
        self.assertIn("✗", (self.f / RC.OUT_MD).read_text())
        d = json.loads((self.f / "delivery.json").read_text())
        self.assertEqual(d["files"][0]["reference_check"]["overall"], RC.BAD)


FIX = Path(__file__).resolve().parent / "fixtures"
SWAP_PROMPT = ("INPUTS\nIMAGE 1 is the reference.\nIMAGE 2 is the real WIDGET: its sheet. IMAGE 3 is the real WIDGET: its "
               "front.\nIMAGE 4 is the logo.\n\nTHE PICTURE\nThe tub becomes the widget; the logo as IMAGE 4 shows.\n"
               "RULES\nChange nothing else.")


def record(prompt=PROMPT, medias=(), elements=(), made_with="gpt_image_2_5", status="completed", **params):
    """A generation record in the shape Higgsfield's own tool returns it (show_generation_by_ids)."""
    p = {"prompt": prompt, "aspect_ratio": "9:16",
         "medias": [{"role": "image", "data": {"id": f"m{i}", "type": "media_input", "url": u}}
                    for i, u in enumerate(medias)],
         "reference_elements": [{"id": i, "name": n, "medias": [], "category": "prop"} for i, n in elements]}
    p.update(params)
    rec = {"id": "gen-rec-1", "type": "image", "status": status, "model": made_with, "params": p,
           "results": {"rawUrl": "https://cdn.example.com/result.png"}}
    return {"items": [rec], "jobs": [{"index": 0, "job_id": "gen-rec-1"}], "all_found": True}


class RecordTest(Base):
    """Higgsfield's own record of the generation is the authority, never the maker's word."""
    SWIPE = "https://cdn.example.com/user_x/0f3c-uploaded.png"

    def save(self, data, asset=None):
        asset = asset or self.a1
        p = asset.with_name(asset.stem + RC.RECORD)
        p.write_text(data if isinstance(data, str) else json.dumps(data))
        return p

    def media(self, mapping):
        return lambda url: mapping.get(url)

    def swipe_bytes(self):
        return (self.f / "refs/step-01-image-1-swipe.jpg").read_bytes()

    def test_the_record_outranks_the_receipt(self):
        self.receipt(good_receipt())                                       # the maker says all is well
        self.save(record(prompt=PROMPT + " And a hat."))                  # Higgsfield says otherwise
        rc = self.rc()
        self.assertEqual((rc["kind"], rc["file"]), ("record", f"{KEY}_asset-01.record.json"))
        self.assertEqual(RC.check_prompt(rc, self.sheet["steps"][0])["state"], RC.BAD)

    def test_the_bare_record_or_the_tools_reply_and_never_two(self):
        self.save(record()["items"][0])
        self.assertEqual(self.rc()["data"]["higgsfield_generation_id"], "gen-rec-1")
        two = record()
        two["items"].append(dict(two["items"][0], id="gen-rec-2"))
        self.save(two)
        rc = self.rc()
        self.assertIn("holds 2 generations", rc["error"])
        self.assertEqual(RC.check_receipt(rc, self.sheet["steps"][0], self.a1.name)["state"], RC.BAD)
        self.save("{not json")
        self.assertIn("not readable JSON", self.rc()["error"])
        self.save({"id": "x"})
        self.assertIn("not a Higgsfield generation record", self.rc()["error"])

    def test_record_receipt_column_status_and_model(self):
        self.save(record())
        r = RC.check_receipt(self.rc(), self.sheet["steps"][0], self.a1.name)
        self.assertEqual((r["state"], r["source"]), (RC.OK, "higgsfield record"))
        self.save(record(status="failed"))
        self.assertIn("failed, not completed", RC.check_receipt(self.rc(), self.sheet["steps"][0], self.a1.name)["why"])
        self.save(record(made_with="flux_kontext"))
        self.assertIn("made with flux_kontext", RC.check_receipt(self.rc(), self.sheet["steps"][0], self.a1.name)["why"])

    def test_words_appended_to_the_prompt_is_wrong_on_its_own(self):
        self.sheet["steps"][0]["words_on_top"] = [{"zone": "Zone A", "words": "Shaved 2 days ago"}]
        self.save(record(prompt=PROMPT + "\n\nWords set on top afterwards (never drawn by the model):\n\n"
                                         "- Zone A: `Shaved 2 days ago`"))
        r = RC.check_prompt(self.rc(), self.sheet["steps"][0])
        self.assertEqual(r["state"], RC.BAD)
        self.assertTrue(r["why"].startswith("words appended to the prompt"))
        self.assertNotIn("diff", r)                                        # the prompt itself is word for word
        self.assertNotIn("words_diff", r)

    def test_inputs_from_the_record_medias_by_bytes_and_elements_by_id(self):
        self.save(record(medias=[self.SWIPE], elements=[(EL, "widget-sheet"), (CAST, "the-host")]))
        r = RC.check_inputs(self.rc(), self.sheet["steps"][0], self.f,
                            fetch=lambda u: self.fail("the sha-only reader is not used for a record"),
                            fetch_media=self.media({self.SWIPE: self.swipe_bytes()}))
        self.assertEqual(r["state"], RC.OK, r["why"])
        self.assertEqual([m["by"] for m in r["matched"]], ["file bytes", "element id", "element id"])
        r = RC.check_inputs(self.rc(), self.sheet["steps"][0], self.f, fetch_media=self.media({}))
        self.assertEqual(r["state"], RC.BAD)                                # not read: never a match
        self.assertIn("IMAGE 1", r["why"])

    @unittest.skipIf(Image is None, "Pillow is needed to read a picture")
    def test_a_re_encoded_upload_is_the_picture_and_an_edit_of_it_is_not(self):
        import io
        src = self.f / "refs/step-01-image-1-swipe.jpg"
        im = Image.new("RGB", (90, 160), "white")                           # a smooth picture, as a photo is
        for x in range(90):
            for y in range(160):
                im.putpixel((x, y), (x * 2, y, 255 - y) if (x - 45) ** 2 + (y - 60) ** 2 > 400 else (20, 20, 20))
        im.save(src)
        buf = io.BytesIO()
        im.resize((180, 320)).save(buf, "JPEG", quality=92)                 # the uploader resized and re-encoded it
        self.save(record(medias=[self.SWIPE], elements=[(EL, "widget-sheet"), (CAST, "the-host")]))
        r = RC.check_inputs(self.rc(), self.sheet["steps"][0], self.f,
                            fetch_media=self.media({self.SWIPE: buf.getvalue()}))
        self.assertEqual(r["matched"][0]["by"], "the picture")
        self.assertEqual(r["state"], RC.OK)
        edit = im.copy()
        for x in range(20, 70):
            for y in range(40, 120):
                edit.putpixel((x, y), (250, 20, 20))                        # one change: not the reference any more
        buf = io.BytesIO()
        edit.save(buf, "PNG")
        r = RC.check_inputs(self.rc(), self.sheet["steps"][0], self.f, fetch_media=self.media({self.SWIPE: buf.getvalue()}))
        self.assertEqual(r["state"], RC.BAD)
        self.assertIn("missing: IMAGE 1", r["why"])

    def test_settings_against_the_sheet(self):
        st = self.sheet["steps"][0]
        st["settings"] = {"aspect_ratio": "9:16", "variant": "sunburst", "quality": "high", "count": 1}
        self.save(record(quality="high", model="sunburst"))
        r = RC.check_settings(self.rc(), st)
        self.assertEqual(r["state"], RC.OK, r["why"])
        self.save(record(quality="medium", model="sunburst"))
        self.assertIn("quality medium, the sheet says high", RC.check_settings(self.rc(), st)["why"])
        self.save(record(model="sunburst"))
        r = RC.check_settings(self.rc(), st)
        self.assertEqual(r["state"], RC.AMBER)
        self.assertIn("not stated: quality", r["why"])
        self.assertEqual(RC.check_settings(self.rc(), self.sheet["steps"][1])["state"], RC.NA)   # words only

    def test_the_element_line_in_for_its_files_exactly_as_the_run_sheet_says(self):
        st = dict(self.sheet["steps"][0], prompt=SWAP_PROMPT, cast=[])
        st["references"] = st["references"] + [{"n": 4, "kind": "image", "role": "the logo", "local": "refs/logo.png",
                                                "element": None}]
        swapped = RC.swap_in_elements(SWAP_PROMPT, st)
        line = ("IMAGE 2 is the real WIDGET, supplied as the element widget-sheet: every side of it, at its true size; "
                "copy the exact shape, label and finish.")
        self.assertIn(line, swapped)
        self.assertNotIn("its front", swapped)
        self.assertIn("IMAGE 3 is the logo.", swapped)                     # IMAGE 4 moved down by one
        self.assertIn("the logo as IMAGE 3 shows", swapped)
        for sent in (swapped, swapped.replace("element widget-sheet", f"element <<<{EL}>>>")):
            self.save(record(prompt=sent))
            r = RC.check_prompt(self.rc(), st)
            self.assertEqual(r["state"], RC.OK, r.get("diff"))
            self.assertIn("the element line in for its files", r["why"])
        self.save(record(prompt=swapped.replace("every side of it, at its true size", "its sheet")))
        self.assertEqual(RC.check_prompt(self.rc(), st)["state"], RC.BAD)  # the line reworded is a change

    def test_text_altered_in_transit_is_wrong_and_named(self):
        self.save(record(prompt=PROMPT + f" <<<{EL}0>>>"))
        r = RC.check_prompt(self.rc(), self.sheet["steps"][0])
        self.assertEqual(r["state"], RC.BAD)
        self.assertIn(RC.TRANSIT, r["why"])
        self.assertEqual(r["altered_ids"], [{"sent": EL + "0", "sheet": EL}])
        st = dict(self.sheet["steps"][0], prompt=PROMPT + " It is 11.15 cm tall.")
        self.save(record(prompt=PROMPT + " It is 11.5 cm tall."))
        r = RC.check_prompt(self.rc(), st)
        self.assertEqual(r["state"], RC.BAD)
        self.assertTrue(r["why"].startswith(RC.TRANSIT), r["why"])
        self.save(record(prompt=PROMPT + " It is 11.15 cm wide."))
        self.assertNotIn(RC.TRANSIT, RC.check_prompt(self.rc(), st)["why"])  # a changed word is not transit


class RealRecordTest(unittest.TestCase):
    """The real one (2026-10-28): Higgsfield's record of generation dec7526e, saved exactly as its tool returned it,
    against step 2 of the run sheet it was made from. The agent retyped the prompt and corrupted it."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.old = os.environ.get("AI_WORKSPACE")
        (self.tmp / "brands").mkdir()
        os.environ["AI_WORKSPACE"] = str(self.tmp)
        fx = json.loads((FIX / "brief-0232-step-2.json").read_text())
        self.step = fx["step"]
        self.f = self.tmp / "handoff"
        for r in self.step["references"]:
            picture(self.f / r["local"], ["blue", "black", "gray", "white"][r["n"] - 1])
        (self.f / "run.json").write_text(json.dumps({"brief_key": fx["brief_key"], "steps": [self.step]}))
        self.asset = picture(self.f / "returned" / self.step["asset"], "green")
        shutil.copy(FIX / "dec7526e.record.json", self.asset.with_name(Path(self.step["asset"]).stem + RC.RECORD))
        raw = json.loads((FIX / "dec7526e.record.json").read_text())["items"][0]
        self.plate_url = raw["params"]["medias"][0]["data"]["url"]

    def tearDown(self):
        if self.old is None:
            os.environ.pop("AI_WORKSPACE", None)
        else:
            os.environ["AI_WORKSPACE"] = self.old
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_dec7526e_against_step_2(self):
        plate = (self.f / "refs/approved-plate.png").read_bytes()
        rep = RC.check(self.f, judge=False, write=False, fetch_media=lambda u: plate if u == self.plate_url else None)
        a = rep["assets"][0]
        self.assertEqual(a["source"], "Higgsfield's record")
        self.assertEqual(a["receipt"]["state"], RC.OK)
        self.assertEqual(a["receipt"]["generation"], "dec7526e-8164-4c76-bc61-0c7b451338d7")
        # inputs: the plate by its bytes (its url's name is Higgsfield's own), the casting sheet element by id
        self.assertEqual(a["inputs"]["state"], RC.OK, a["inputs"]["why"])
        self.assertEqual([(m["by"], len(m["is"])) for m in a["inputs"]["matched"]], [("file bytes", 1), ("element id", 3)])
        self.assertEqual(a["settings"]["state"], RC.OK, a["settings"]["why"])
        # the prompt: wrong, and the diff names what the retyping did
        p = a["prompt"]
        self.assertEqual(p["state"], RC.BAD)
        self.assertIn("words appended to the prompt", p["why"])
        self.assertIn(("`Shaved", "`Shared"), [(d["sheet"], d["sent"]) for d in p["words_diff"]])
        pairs = [(d["sheet"], d["sent"]) for d in p["diff"]]
        for want in (("THE ONE CHANGE", "The one change"), ("− ⏻", "« »"), ("or dome", ""),
                     ("bristles-inward, facing the palm;", ""), ("nubs;", "numbs;")):
            self.assertIn(want, pairs)
        self.assertEqual(a["overall"], RC.BAD)


class HygieneTest(unittest.TestCase):
    def test_no_brand_named_in_code(self):
        src = (HERE / "reference_check.py").read_text().lower()
        brands = HERE.parent.parent / "brands"
        for b in [p.name for p in brands.iterdir() if p.is_dir()] if brands.is_dir() else []:
            self.assertIsNone(re.search(r"\b%s\b" % re.escape(b.lower()), src), b)

    def test_never_deletes_or_writes_outside_its_three_files(self):
        src = (HERE / "reference_check.py").read_text()
        for bad in ("unlink(", "rmtree(", "os.remove", "files().create", "files().update", "/Users/", "/Volumes"):
            self.assertNotIn(bad, src)


class TestSetChange(Base):
    """A set change is printed, not generated flat: its print call is the model, its kept print is only looked at."""

    def test_the_print_call_is_not_read_as_the_wrong_model(self):
        self.receipt(good_receipt(asset=f"{KEY}_asset-03.png", step=3, model="scene_builder_3d_generate_angles"), asset=self.a2)
        r = RC.check_receipt(RC.read_receipt(self.a2), set_step(), f"{KEY}_asset-03.png")
        self.assertEqual(r["state"], RC.OK, r)

    def test_the_kept_print_is_not_an_expected_input(self):
        got = RC.expected_inputs(set_step(), self.f)
        self.assertEqual([e["n"] for e in got], [2])

    def test_the_look_check_asks_for_the_change(self):
        tests, imgs = RC.look_plan(set_step(), self.f, "image")
        self.assertTrue(any("THE SET CHANGE IS THERE" in x and "a bigger sign" in x for x in tests))
        self.assertTrue(any("kept print" in label for _, label in imgs))


if __name__ == "__main__":
    unittest.main(verbosity=1)
