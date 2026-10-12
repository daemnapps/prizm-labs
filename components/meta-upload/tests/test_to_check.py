"""The lane feeders' promises (CARD.md): one card folder per finished ad, media copied in
and named, words never invented, pages from the catalog, nothing re-filed once decided,
and every test writes only into its own fake meta/ root."""
import csv, json, os, shutil, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "components/naming"))
import card_words as W
import to_check as T
import feed_image, feed_video, feed_carousel, feed_creator
import delivery_rule as DR

CARD_KEYS = ["schema", "brand", "lane", "format", "ad_name", "old_name", "brief_id", "product", "avatar",
             "angle", "media", "words", "copy_checked", "pages", "made_by", "made_at", "checks", "approval", "meta"]

RENDER = """**`FORMAT: caption`**

**BODY A**

First body, long enough to be found again by its own words.

See how it works 👉

*61 words.*

---

**BODY B**

A draft that gets rewritten.

*20 words.*

**BODY B** *(final)*

The final second body, which replaces its draft.

*22 words.*

**One line each.** notes to us, never copy.

---

**HEADLINES — two.**

1. **It comes right back** — 4 words
2. **Not stubborn. It's remembered.** — 4 words

**DESCRIPTIONS**

1. **Turmeric body scrub** — 3 words

---

**CHECKS**
"""


def png(p, size=(90, 160)):
    from PIL import Image
    p.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (200, 120, 40)).save(p)
    return p


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "meta"
        self.env = mock.patch.dict(os.environ, {"META_CARDS_ROOT": str(self.root)})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.tmp)


class Words(unittest.TestCase):
    def test_render_bodies_lists_and_final_rewrite(self):
        r = W.parse_render(RENDER)
        self.assertEqual(list(r["bodies"]), ["caption"])
        self.assertEqual(len(r["bodies"]["caption"]), 2)
        self.assertTrue(r["bodies"]["caption"][1].startswith("The final second body"))
        self.assertEqual(r["headlines"], ["It comes right back", "Not stubborn. It's remembered."])
        self.assertEqual(r["descriptions"], ["Turmeric body scrub"])

    def test_a_bracketed_word_count_ends_the_body(self):
        """`(48 words)` ends a body as `*48 words.*` does — the writer's note under it never reaches the ad."""
        r = W.parse_render("**FORMAT: short-form**\n\n**BODY A**\n\nThe body itself.\n\n(48 words)\n\n"
                           "*What it's doing:* a note for the buyer.\n\n**BODY B**\n\nSecond.\n\n*(12 words)*\n")
        self.assertEqual(r["bodies"]["short-form"], ["The body itself.", "Second."])

    def test_nothing_is_invented(self):
        self.assertEqual(W.parse_render("just prose")["headlines"], [])
        self.assertEqual(W.missing(W.empty()), ["no primary text", "no headline"])

    def test_run_found_by_its_body(self):
        with tempfile.TemporaryDirectory() as t:
            run = Path(t) / "runs/copywriter/brand-a/fn-x"
            run.mkdir(parents=True)
            (run / "stage8--render.md").write_text(RENDER)
            body = "First body, long enough to be found again by its own words.\n\nSee how it works 👉\n\n*61 words.*"
            self.assertEqual(W.run_for_body("brand-a", body, Path(t)), run)
            self.assertIsNone(W.run_for_body("brand-a", "A body nobody ever wrote, anywhere at all.", Path(t)))

    def test_runs_for_brief_by_number_token(self):
        with tempfile.TemporaryDirectory() as t:
            for label in ("p130-h1-v1-apology", "p1300-other", "x-p13-y"):
                d = Path(t) / "runs/copywriter/brand-a" / label
                d.mkdir(parents=True)
                (d / "stage8--render.md").write_text(RENDER)
            got = [d.name for d in W.runs_for_brief("brand-a", "brief-0130", Path(t))]
            self.assertEqual(got, ["p130-h1-v1-apology"])

    def test_runs_for_brief_by_the_folder_its_source_sits_in(self):
        """chain.py copy labels a run by its swipe, not its brief: the run still
        belongs to the brief when its source file sits in the brief's own run."""
        with tempfile.TemporaryDirectory() as t:
            for label, src in (("brand-a-01-swipe", "runs/image-teardown/brand-a/brand-a-01-swipe/out/01-teardown.md"),
                               ("brand-a-02-other", "runs/image-teardown/brand-a/brand-a-02-other/out/01-teardown.md")):
                d = Path(t) / "runs/copywriter/brand-a" / label
                d.mkdir(parents=True)
                (d / "stage8--render.md").write_text(RENDER)
                (d / "run.json").write_text(json.dumps({"source_path": src}))
            with mock.patch.object(W, "brief_run_names", lambda *a, **k: {"brand-a-01-swipe"}):
                got = [d.name for d in W.runs_for_brief("brand-a", "brief-0998", Path(t))]
            self.assertEqual(got, ["brand-a-01-swipe"])


class BriefPage(Base):
    """No pages passed: the card carries the brief's own landing page (page_pick,
    chosen when the brief was written). Pages passed always win."""
    def test_card_inherits_the_briefs_page(self):
        m = [png(self.tmp / "src" / "a.png")]
        with mock.patch.object(T.PP, "landing_ids", lambda *a, **k: ["link_brand-a_cpk_landing"]):
            p = T.to_check("brand-a", "image", "flexible", m, W.empty(), [], None,
                           product="glow-body-scrub", brief="brief-0154", batch="260923a", dry_run=True)
            self.assertEqual([x["link_id"] for x in p["card"]["pages"]], ["link_brand-a_cpk_landing"])
            p = T.to_check("brand-a", "image", "flexible", m, W.empty(), ["link_brand-a_cpk_quiz"], None,
                           product="glow-body-scrub", brief="brief-0154", batch="260923a", dry_run=True)
            self.assertEqual([x["link_id"] for x in p["card"]["pages"]], ["link_brand-a_cpk_quiz"])

    def test_no_brief_page_means_no_page(self):
        m = [png(self.tmp / "src" / "a.png")]
        with mock.patch.object(T.PP, "landing_ids", lambda *a, **k: []):
            p = T.to_check("brand-a", "image", "flexible", m, W.empty(), [], None,
                           product="glow-body-scrub", brief="brief-0154", batch="260923a", dry_run=True)
        self.assertEqual(p["card"]["pages"], [])


class Card(Base):
    def test_writes_folder_media_and_exact_card(self):
        m = [png(self.tmp / "src" / "b.png"), png(self.tmp / "src" / "a.png")]
        p = T.to_check("brand-a", "image", "flexible", m,
                       {"primary": ["Body"], "headlines": ["H"], "descriptions": []}, ["link_brand-a_cpk_quiz"],
                       {"tool": "image-edit", "run": "runs/x"}, product="glow-body-scrub", brief="p154",
                       batch="260923a", old_name="old")
        ad = "brand-a_glow-body-scrub_brief-0154_batch-2026-09-23-a"
        target = self.root / "brand-a/1-check/image" / ad
        self.assertEqual(p["state"], "filed")
        self.assertEqual(p["target"], target)
        self.assertEqual(sorted(x.name for x in target.iterdir()),
                         sorted(["card.json", f"{ad}_asset-01.png", f"{ad}_asset-02.png"]))
        c = json.loads((target / "card.json").read_text())
        self.assertEqual(list(c), CARD_KEYS)
        self.assertEqual(c["schema"], "meta-card/1")
        self.assertEqual(c["media"], [f"{ad}_asset-01.png", f"{ad}_asset-02.png"])
        self.assertEqual(c["pages"], [{"link_id": "link_brand-a_cpk_quiz",
                                       "url": "https://recipe.brand-a.example/brand-a-scrub-cpk/quiz/"}])
        self.assertEqual((c["avatar"], c["angle"]), ("avatar-four", "pigment-memory"))   # from the brief header
        self.assertEqual(c["made_by"], {"tool": "image-edit", "run": "runs/x", "creator": None})
        self.assertIsNone(c["approval"])
        self.assertTrue(m[0].is_file(), "the source is copied, never moved")
        self.assertEqual(list(self.root.rglob("*.partial-*")), [])

    def test_unknown_link_refused(self):
        with self.assertRaises(T.Refused):
            T.to_check("brand-a", "image", "flexible", [png(self.tmp / "a.png")], None, ["link_brand-a_nope"],
                       product="x", brief="none", batch="batch-2026-10-01-a")

    def test_dry_run_writes_nothing(self):
        p = T.to_check("brand-a", "video", "flexible", [self.tmp / "not-made-yet.mp4"], None, [],
                       product="glow-body-scrub", brief="brief-0191", batch="batch-2026-10-01-a", dry_run=True)
        self.assertEqual(p["state"], "would file")
        self.assertEqual(p["missing_words"], ["no primary text", "no headline"])
        self.assertFalse(self.root.exists())

    def test_a_thumbnail_rides_with_its_video(self):
        """4 Oct 2026 (the owner: "unique thumbnails per creative"): thumbs[i] goes with media[i], named after it."""
        kw = dict(product="glow-body-scrub", brief="brief-0154", batch="batch-2026-10-01-a")
        vids = [png(self.tmp / "v1.png"), png(self.tmp / "v2.png")]
        p = T.to_check("brand-a", "image", "flexible", vids, None, [], thumbs=[png(self.tmp / "t1.png", (1080, 1920))], **kw)
        c = json.loads((p["target"] / "card.json").read_text())
        self.assertEqual(len(c["media"]), 2)
        self.assertEqual(list(c["thumbs"]), [c["media"][0]])
        self.assertTrue(c["thumbs"][c["media"][0]].endswith("_asset-01_thumb.png"))
        self.assertTrue((p["target"] / c["thumbs"][c["media"][0]]).is_file())

    def test_a_refile_keeps_the_same_folder(self):
        """4 Oct 2026: a refile swapped the whole folder, so its Drive link changed and the shared one was trashed.
        The folder stays; its files are swapped inside it, and a file the new card no longer lists goes."""
        kw = dict(product="glow-body-scrub", brief="brief-0154", batch="batch-2026-10-01-a")
        p = T.to_check("brand-a", "image", "flexible", [png(self.tmp / "a.png"), png(self.tmp / "b.png")], None, [], **kw)
        folder = p["target"]; ino = folder.stat().st_ino
        q = T.to_check("brand-a", "image", "flexible", [png(self.tmp / "c.png")], None, [], replace=True, **kw)
        self.assertEqual(q["state"], "replaced")
        self.assertEqual(folder.stat().st_ino, ino)                  # the same folder, not a new one
        self.assertEqual(sorted(f.name for f in folder.iterdir()), sorted(["card.json", q["files"][0][1]]))
        self.assertFalse(any(f.name.startswith(".") for f in folder.parent.iterdir()))

    def test_never_refiled_once_decided(self):
        kw = dict(product="glow-body-scrub", brief="brief-0154", batch="batch-2026-10-01-a")
        src = [png(self.tmp / "a.png")]
        p = T.to_check("brand-a", "image", "flexible", src, None, [], **kw)
        self.assertEqual(T.to_check("brand-a", "image", "flexible", src, None, [], **kw)["state"],
                         "skipped: already in 1-check")
        self.assertEqual(T.to_check("brand-a", "image", "flexible", src, None, [], replace=True, **kw)["state"],
                         "replaced")
        c = json.loads((p["target"] / "card.json").read_text())
        c["approval"] = {"by": "the owner", "decision": "approve"}
        (p["target"] / "card.json").write_text(json.dumps(c))
        self.assertEqual(T.to_check("brand-a", "image", "flexible", src, None, [], replace=True, **kw)["state"],
                         "skipped: already decided on in 1-check")
        shutil.move(str(p["target"]), str(self.root / "brand-a/3-live/image" / p["target"].name))
        self.assertEqual(T.to_check("brand-a", "image", "flexible", src, None, [], **kw)["state"],
                         "skipped: already in 3-live")

    def test_lane_and_format_must_agree(self):
        with self.assertRaises(T.Refused):
            T.to_check("brand-a", "image", "carousel", [png(self.tmp / "a.png")], None, [],
                       product="x", brief="none", batch="batch-2026-10-01-a")


class ImageLane(Base):
    def make_drop(self):
        repo = self.tmp / "repo"
        old = "branda-glowbodyscrub-static-ai-none-avatarfour-darkspots-tonememory-apothecary-specstarburst-p154-9x16-260923a"
        d = repo / "runs/image-edit/brand-a/260923a/deliverable" / old
        d.mkdir(parents=True)
        (d / "manifest.json").write_text(json.dumps({"ad_name": old, "batch": "260923a", "product": "glow-body-scrub",
                                                     "brief": "p154", "ads": []}))
        for n in (2, 1):
            png(d / f"{old}-a{n:02d}.png")
        run = repo / "runs/copywriter/brand-a/fn-x"
        run.mkdir(parents=True)
        (run / "stage8--render.md").write_text(RENDER)
        with (d.parent / "copy.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["brief", "ad_name", "primary_text", "alt_text"])
            w.writerow(["p154", old, "First body, long enough to be found again by its own words.\n\nSee how it works 👉\n\n*61 words.*", ""])
        return repo, old

    def test_headlines_come_back_from_the_writer(self):
        repo, old = self.make_drop()
        [(p, why, src)] = feed_image.feed("brand-a", "260923a", ["link_brand-a_cpk_landing"], repo=repo)
        self.assertIsNone(why)
        c = json.loads((p["target"] / "card.json").read_text())
        self.assertEqual(c["old_name"], old)
        self.assertEqual(c["words"]["primary"], ["First body, long enough to be found again by its own words.\n\nSee how it works 👉"])
        self.assertEqual(c["words"]["headlines"], ["It comes right back", "Not stubborn. It's remembered."])
        self.assertEqual(c["words"]["descriptions"], ["Turmeric body scrub"])
        self.assertTrue(c["media"][0].endswith("_asset-01.png"))
        self.assertIn("fn-x", src)


class VideoLane(Base):
    def test_master_goes_to_check_with_handoff_pages(self):
        h = self.tmp / "handoff"
        h.mkdir()
        (h / "manifest.json").write_text(json.dumps({"role": "video-editor", "brand": "brand-a", "batch": None,
            "briefs": [{"id": "brief-0191", "product_id": "product_brand-a_glow-body-scrub",
                        "link_ids": ["link_brand-a_cpk_quiz"]}]}))
        master = self.tmp / "final.mp4"
        master.write_bytes(b"\0" * 64)
        p, src = feed_video.file_master("brand-a", "brief-0191", "glow-body-scrub", "batch-2026-10-01-a",
                                        master, handoff=h)
        ad = "brand-a_glow-body-scrub_brief-0191_batch-2026-10-01-a"
        self.assertEqual(p["target"], self.root / "brand-a/1-check/video" / ad)
        self.assertTrue((p["target"] / f"{ad}_asset-01.mp4").is_file())
        c = json.loads((p["target"] / "card.json").read_text())
        self.assertEqual([x["link_id"] for x in c["pages"]], ["link_brand-a_cpk_quiz"])
        self.assertEqual(c["words"], {"primary": [], "headlines": [], "descriptions": []})   # none written for 0191


    def test_video_editor_finish_files_the_card(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("handoff_run", REPO / "tools/video-edit/machine/handoff_run.py")
        HR = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(HR)
        h = self.tmp / "handoff"
        h.mkdir()
        (h / "manifest.json").write_text(json.dumps({"role": "video-editor", "brand": "brand-a",
            "briefs": [{"id": "brief-0191", "product_id": "product_brand-a_glow-body-scrub"}]}))
        master = self.tmp / "m.mp4"
        master.write_bytes(b"\0")
        got = HR.to_check(self.tmp / "run", {"brand": "brand-a", "brief": "brief-0191", "product": "glow-body-scrub",
                                             "folder": h}, master, "batch-2026-10-01-a", REPO)
        self.assertEqual(got["state"], "filed")
        self.assertTrue(got["folder"].startswith(str(self.root)))
        self.assertEqual(got["missing"], ["no primary text", "no headline"])


class CarouselLane(Base):
    def test_slides_in_order_as_png(self):
        run = self.tmp / "run"
        png(run / "slide-02.png")
        png(run / "slide-01.png")
        from PIL import Image
        Image.new("RGB", (90, 160)).save(run / "slide-03.jpg")
        png(run / "slide-01-reject-copied-face.png")
        p, _ = feed_carousel.feed(run, "brand-b", "gadget-bump-eliminator", links=["link_brand-b_store_method-quiz"])
        ad = p["card"]["ad_name"]
        self.assertEqual(p["card"]["format"], "carousel")
        self.assertEqual(p["card"]["media"], [f"{ad}_slide-{n:02d}.png" for n in (1, 2, 3)])
        with Image.open(p["target"] / f"{ad}_slide-03.png") as im:
            self.assertEqual(im.format, "PNG")
        again, _ = feed_carousel.feed(run, "brand-b", "gadget-bump-eliminator")
        self.assertEqual(again["card"]["ad_name"], ad)       # the same run finds its own card
        self.assertTrue(again["state"].startswith("skipped"))

    def test_a_delivery_folder_in_either_naming(self):
        d = self.tmp / "gadget brief-0004"
        png(d / "gadget brief-0004--slide-02--v1.png")
        png(d / "gadget brief-0004--slide-02--v2.png")
        png(d / "gadget brief-0004--slide-01--v1.png")
        png(d / "gadget brief-0004--swipe-slide-01--v1.png")
        order, gaps = feed_carousel.slides(d)
        self.assertEqual(gaps, [])
        self.assertEqual([f.name for _, f in order],
                         ["gadget brief-0004--slide-01--v1.png", "gadget brief-0004--slide-02--v2.png"])
        u = self.tmp / "brand-b_gadget_brief-0004_batch-2026-10-02-a"
        for n in (2, 1, 3):
            png(u / f"brand-b_gadget_brief-0004_batch-2026-10-02-a_asset-{n:02d}.png")
        order, gaps = feed_carousel.slides(u)
        self.assertEqual([n for n, _ in order], [1, 2, 3])

    def test_sequence_run_and_gap(self):
        run = self.tmp / "seq"
        one = png(self.tmp / "plate.png")
        s2 = png(run / "slide-02/out.png")
        run.mkdir(exist_ok=True)
        (run / "sequence.json").write_text(json.dumps({"slide_one": str(one), "slides": [
            {"slide": 2, "delivered": [str(s2)]}, {"slide": 3, "delivered": []}]}))
        with self.assertRaises(T.Refused) as e:
            feed_carousel.feed(run, "brand-b", "gadget-bump-eliminator")
        self.assertIn("3", str(e.exception))
        p, _ = feed_carousel.feed(run, "brand-b", "gadget-bump-eliminator", picks={3: str(s2)}, dry_run=True)
        self.assertEqual([Path(s).name for s, _ in p["files"]], ["plate.png", "out.png", "out.png"])


class CreatorLane(Base):
    def test_named_delivery_goes_to_check_and_launch_sheet_still_works(self):
        watched = self.tmp / "creators/brand-a/nova/DELIVERABLES"
        ad = "brand-a_glow-body-scrub_brief-0191_batch-2026-10-01-a"
        f = watched / ad
        f.mkdir(parents=True)
        (f / f"{ad}_asset-02.mp4").write_bytes(b"\0" * 8)
        (f / f"{ad}_asset-01.mp4").write_bytes(b"\0" * 8)
        (f / "control-swipe.mp4").write_bytes(b"\0" * 8)          # rides along, not the work
        res = DR.to_check("brand-a", watched, ["link_brand-a_cpk_quiz"])
        [(p, why, _)] = res
        self.assertIsNone(why)
        c = json.loads((p["target"] / "card.json").read_text())
        self.assertEqual(c["lane"], "creator")
        self.assertEqual(c["media"], [f"{ad}_asset-01.mp4", f"{ad}_asset-02.mp4"])
        self.assertEqual(c["made_by"]["creator"], "nova")
        self.assertEqual(c["made_by"]["tool"], "delivery-rule")
        self.assertTrue((f / f"{ad}_asset-01.mp4").is_file(), "the delivery folder is never touched")
        DR.launch_sheet("brand-a", watched)
        self.assertIn(ad, (watched / "READY-TO-LAUNCH.md").read_text())

    def test_dry_run_plans_only(self):
        watched = self.tmp / "w"
        ad = "brand-a_glow-face-scrub_brief-0167_batch-2026-09-29-a"
        png(watched / ad / f"{ad}_asset-01.png")
        [(p, _, _)] = DR.to_check("brand-a", watched, dry_run=True)
        self.assertEqual(p["state"], "would file")
        self.assertFalse(self.root.exists())


if __name__ == "__main__":
    unittest.main()


class Plain(unittest.TestCase):
    def test_markdown_never_reaches_the_ad(self):
        import to_check as T
        w = T.clean_words({"primary": ["**Six half-used tubes.** One *actually* worked. 5 * 3 stays"], "headlines": ["__It__ works"]})
        self.assertEqual(w["primary"], ["Six half-used tubes. One actually worked. 5 * 3 stays"])
        self.assertEqual(w["headlines"], ["It works"])


class CopyMachineStep(unittest.TestCase):
    """2026-10-09 (the owner): every card with no words runs the copywriter on its brief before it files —
    and only a real filing does: a test or proof root never starts it."""

    def test_runs_the_copywriter_when_the_card_has_no_words(self):
        calls = []
        got = {"primary": ["Body."], "headlines": ["Head"], "descriptions": ["Desc"]}
        seq = iter([(W.empty(), None), (got, "run")])
        with mock.patch.object(W, "for_brief", side_effect=lambda *a, **k: next(seq)):
            w = T.copy_machine("brand-a", "brief-0001", "x", run=lambda cmd, check=False: calls.append(cmd))
        self.assertEqual(w, got)
        self.assertTrue(calls and calls[0][1].endswith("brief_words.py") and "brief-0001" in calls[0])

    def test_already_written_is_not_written_again(self):
        calls = []
        got = {"primary": ["Body."], "headlines": ["Head"], "descriptions": ["Desc"]}
        with mock.patch.object(W, "for_brief", return_value=(got, "run")):
            self.assertEqual(T.copy_machine("brand-a", "brief-0001", run=lambda c, check=False: calls.append(c)), got)
        self.assertEqual(calls, [])

    def test_a_test_root_never_starts_it(self):
        with mock.patch.object(T, "copy_machine", side_effect=AssertionError("must not run")), \
                mock.patch.object(T, "plan", side_effect=T.Refused("stop here")):
            with self.assertRaises(T.Refused):
                T.to_check("brand-a", "video", "flexible", [], W.empty(), brief="brief-0001", root="/tmp/x")


class CardReadsTheCheckedCopy(unittest.TestCase):
    """2026-10-09: the card reads the copy-checked final over the stage 8 draft, and a held run gives nothing."""

    def test_final_wins_and_held_gives_nothing(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            (d / "stage8--render.md").write_text("draft")
            self.assertEqual(W.render_of(d), "draft")
            (d / "final--copy.md").write_text("final")
            self.assertEqual(W.render_of(d), "final")
            (d / "check.json").write_text(json.dumps({"held": True}))
            self.assertEqual(W.render_of(d), "")
