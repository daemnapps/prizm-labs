#!/usr/bin/env python3
"""The culture read — stage 1k (the owner, 2026-10-05: "The more we're aware of
culture … We can literally just leverage that authority").

Where it sits (after the teardown, before the doctrine read, in the teardown
set so it runs with no route), how the writing stages read it ({culture_read},
soft when absent), the free comment pull and its fallbacks, the search
grounding switch, and the teardown shelf. No model, no network, no brand file
written.

    python3 test_culture_read.py
"""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chain as C                                            # noqa: E402
import culture as CU                                         # noqa: E402
import file_run as FR                                        # noqa: E402

_s = importlib.util.spec_from_file_location("td_run_culture", HERE / "run.py")
R = importlib.util.module_from_spec(_s); _s.loader.exec_module(R)
_g = importlib.util.spec_from_file_location("td_gemini_breakdown", C.CM / "tools" / "gemini_breakdown.py")
G = importlib.util.module_from_spec(_g); _g.loader.exec_module(G)

READERS = ("stage2", "stage3", "stage4b", "stage5")
INFO = {"webpage_url": "https://example.invalid/p/abc", "extractor_key": "Instagram",
        "channel": "someone", "uploader": "Some One", "upload_date": "20261001",
        "description": "a caption", "like_count": 500000, "comment_count": 2000,
        "comments": [
            {"author": "a", "text": "who is that?", "like_count": 0, "parent": None},
            {"author": "b", "text": "never thought I'd see <the character> hooping", "like_count": 0, "parent": None},
            {"author": "c", "text": "", "like_count": 0, "parent": None}]}


def keys(route="ai", lane="ORGANIC"):
    return [s["key"] for s in C.stages("", "", route, lane)]


class Ordering(unittest.TestCase):
    def test_after_the_teardown_before_the_doctrine_read(self):
        for route in ("ai", "creator", "founder"):
            for lane in ("ORGANIC", "ALREADY AN AD", ""):
                k = keys(route, lane)
                self.assertEqual(k.index("stage1k"), k.index("stage1") + 1, (route, lane))
                self.assertLess(k.index("stage1k"), k.index("stage1c"))
                for reader in READERS:
                    self.assertLess(k.index("stage1k"), k.index(reader))

    def test_teardown_side_runs_with_no_route(self):
        self.assertIn("stage1k", R.TEARDOWN_KEYS)
        s = next(x for x in C.stages("", "", "creator", "ORGANIC") if x["key"] == "stage1k")
        self.assertEqual(s["id"], "1k")
        self.assertEqual(s["engine"], "gemini-video")
        self.assertTrue(s["search"])
        self.assertTrue(s["prompt"].endswith("stage1k-culture-v3-damon.md"))
        self.assertIn("video-teardown/prompts/stage-1k-culture", s["prompt"])

    def test_no_route_runs_it_and_holds_writing(self):
        ran, st = [], {"label": "t", "slug": "t", "stages": {}, "triage_lane": "ORGANIC"}
        d = Path(tempfile.mkdtemp())
        plan = [dict(key=k, id=k, name=k, engine="x", version="v1", prompt="")
                for k in ("stage0", "stage1", "stage1k", "stage1c", "stage1b", "stage2", "stage3")]
        with mock.patch.object(R, "open_run", lambda *a, **k: (d, st)), \
                mock.patch.object(R, "save", lambda *a: None), \
                mock.patch.object(R, "file_to_repo", lambda d: None), \
                mock.patch.object(R, "say", lambda *a, **k: None), \
                mock.patch.object(R, "run_stage", lambda d, st, s, e, redo=False: ran.append(s["key"]) or True), \
                mock.patch.object(R.C, "stages", lambda *a, **k: [dict(x) for x in plan]), \
                mock.patch.object(R.C, "mirror_to_drive", lambda slug: None):
            R.run_video(None, "t", "somebrand")
        self.assertEqual(ran, ["stage0", "stage1", "stage1k", "stage1c", "stage2"])
        self.assertEqual(st["waiting_for"], "route")

    def test_a_composed_run_has_no_swipe_to_read(self):
        self.assertIn("stage1k", C.route_for("FRAMEWORK")["skip"])

    def test_rulings_never_reach_it(self):
        src = (HERE / "run.py").read_text()
        self.assertIn('if key not in TEARDOWN_KEYS and _rp.exists()', src)


class Binding(unittest.TestCase):
    def test_every_reader_binds_and_asks_once(self):
        for route in ("ai", "creator"):
            for s in C.stages("", "", route, "ORGANIC"):
                if s["key"] not in READERS:
                    continue
                self.assertEqual(s["vars"].get("culture_read"), "!culture_read", (route, s["key"]))
                text = Path(s["prompt"]).read_text()
                self.assertEqual(text.count("{culture_read}"), 1, f"{Path(s['prompt']).name}")

    def test_the_read_asks_only_for_the_swipe(self):
        s = next(x for x in C.stages("", "", "ai", "ORGANIC") if x["key"] == "stage1k")
        self.assertEqual(s["vars"], {"teardown_record": "@stage1", "post_talk": "!post_talk"})
        import re
        asks = set(re.findall(r"\{([a-z0-9_]+)\}", Path(s["prompt"]).read_text()))
        self.assertEqual(asks, {"teardown_record", "post_talk"})

    def test_examples_are_marked_illustrative_before_the_first_one(self):
        t = Path(C.newest("stage1k")[0]).read_text()
        note = t.find("illustrative")
        self.assertGreater(note, -1)
        self.assertLess(note, t.lower().find("example of the shape"))
        self.assertLess(note, t.find("e.g."))

    def test_culture_read_resolves_soft(self):
        got, origin = C.resolve_source("!culture_read", "", {"stage1k": "CULTURE LOAD: HEAVY"})
        self.assertTrue(got.startswith("CULTURE LOAD: HEAVY"))
        self.assertIn("1k", origin)
        got, _ = C.resolve_source("!culture_read", "", {})
        self.assertTrue(got.startswith("NO CULTURE READ"))

    def test_culture_map_resolves_soft(self):
        got, _ = C.resolve_source("!culture_map", "", {})
        self.assertTrue(got.startswith("NO CULTURE MAP"))
        got, _ = C.resolve_source("!culture_map", "brand-b", {"avatar": "no-such-avatar"})
        self.assertTrue(got.startswith("NO CULTURE MAP"))
        if (C.WS / "brands/<brand>/core-avatars/avatar-one").is_dir():
            got, origin = C.resolve_source("!culture_map", "brand-b", {"avatar": "avatar-one"})
            first = next(l for l in got.splitlines() if l.strip() and not l.startswith("<!--"))
            self.assertTrue(first.startswith("# Culture map") or first.startswith("# Humor map"))
            # an older prompt still asking for humor_map gets the same file
            got2, _ = C.resolve_source("!humor_map", "brand-b", {"avatar": "avatar-one"})
            self.assertEqual(got, got2)

    def test_post_talk_resolves_from_the_run(self):
        got, _ = C.resolve_source("!post_talk", "", {"post_talk": "POST: x"})
        self.assertTrue(got.startswith("POST: x"))
        got, _ = C.resolve_source("!post_talk", "", {})
        self.assertTrue(got.startswith("NO POST TALK"))

    def test_dry_run_resolves_every_variable(self):
        import dryrun as DR
        for route in ("ai", "creator"):
            res = DR.resolve(HERE / "run.py", "culture-dry-run-test", sorted(
                p.name for p in (C.WS / "brands").iterdir() if p.is_dir() and not p.name.startswith((".", "_")))[0],
                route=route, stop="1k")
            ids = [r["stage"]["key"] for r in res["stages"]]
            self.assertEqual(ids[-1], "stage1k")
            row = res["stages"][-1]
            self.assertFalse(row["unbound"])
            self.assertTrue(all(st != DR.MISSING for _, st, _ in row["vars"]), row["vars"])


class CommentPull(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.calls = []

    def runner(self, write=True):
        def run(cmd, **k):
            self.calls.append(cmd)
            if write:
                out = Path(cmd[cmd.index("-o") + 1]).parent
                (out / "post.info.json").write_text(json.dumps(INFO))
            import subprocess
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return run

    def test_no_url_and_no_info_says_so_and_spends_nothing(self):
        txt = CU.post_talk(self.d, {"stages": {}}, runner=self.runner())
        self.assertTrue(txt.startswith("NO POST TALK"))
        self.assertIn("no post URL", txt)
        self.assertEqual(self.calls, [])

    def test_url_on_the_run_pulls_with_ytdlp(self):
        with mock.patch.object(CU, "ytdlp", lambda: "/usr/bin/yt-dlp"):
            txt = CU.post_talk(self.d, {"post_url": "https://example.invalid/p/abc"}, runner=self.runner())
        cmd = self.calls[0]
        self.assertTrue(cmd[0].endswith("yt-dlp"))
        for flag in ("--skip-download", "--write-comments", "--write-info-json"):
            self.assertIn(flag, cmd)
        self.assertIn("never thought I'd see <the character> hooping", txt)
        self.assertIn("C2 · @b", txt)
        self.assertIn("likes: n/a", txt)
        self.assertIn("of 2,000 on the post", txt)
        self.assertIn("CAPTION (verbatim):\na caption", txt)
        filed = json.loads((self.d / "post-talk.json").read_text())
        self.assertEqual(len(filed["comments"]), 2)          # the empty one is dropped

    def test_a_pull_that_returns_nothing_is_said_and_the_stage_continues(self):
        with mock.patch.object(CU, "ytdlp", lambda: "/usr/bin/yt-dlp"):
            txt = CU.post_talk(self.d, {"post_url": "https://example.invalid/p/abc"},
                               runner=self.runner(write=False))
        self.assertTrue(txt.startswith("NO POST TALK"))
        self.assertIn("yt-dlp returned nothing", txt)

    def test_a_runner_that_fails_is_said(self):
        def boom(*a, **k):
            raise OSError("offline")
        with mock.patch.object(CU, "ytdlp", lambda: "/usr/bin/yt-dlp"):
            txt = CU.post_talk(self.d, {"post_url": "https://example.invalid/p/abc"}, runner=boom)
        self.assertTrue(txt.startswith("NO POST TALK"))
        self.assertIn("offline", txt)

    def test_no_ytdlp_is_said(self):
        with mock.patch.object(CU, "ytdlp", lambda: None):
            txt = CU.post_talk(self.d, {"post_url": "https://example.invalid/p/abc"}, runner=self.runner())
        self.assertIn("yt-dlp is not installed", txt)
        self.assertEqual(self.calls, [])

    def test_an_info_json_in_the_run_is_read_without_a_url(self):
        (self.d / "Dd9abc.info.json").write_text(json.dumps(INFO))
        txt = CU.post_talk(self.d, {"stages": {}}, runner=self.runner())
        self.assertEqual(self.calls, [])
        self.assertIn("POST: https://example.invalid/p/abc", txt)

    def test_a_post_json_beside_the_video_gives_the_url(self):
        (self.d / "post.json").write_text(json.dumps({"url": "https://example.invalid/p/xyz"}))
        self.assertEqual(CU.post_url(self.d, {"video": str(self.d / "source.mp4")}),
                         "https://example.invalid/p/xyz")

    def test_never_apify(self):
        self.assertNotIn("apify", (HERE / "culture.py").read_text().lower().replace("never apify", "")
                         .replace("never spend apify", "").replace("not apify", ""))


class TheStageRuns(unittest.TestCase):
    """run_stage on 1k: the post talk is pulled, the read searches, the output files."""

    def test_run_stage_fills_and_searches(self):
        d = Path(tempfile.mkdtemp())
        (d / "stages").mkdir(); (d / "prompts").mkdir()
        (d / "stages" / "1-teardown.md").write_text("THE RECORD: a man in a suit dunks.\n")
        (d / "Dd9abc.info.json").write_text(json.dumps(INFO))
        video = d / "source.mp4"; video.write_bytes(b"\x00")
        st = {"slug": "t", "label": "t", "brand": "zz", "video": str(video), "stages": {
            "stage1": {"status": "done", "out": "stages/1-teardown.md"}}}
        stage = next(x for x in C.stages("", "", "ai", "ORGANIC") if x["key"] == "stage1k")
        seen = {}

        def fake(prompt_path, v, out):
            seen["search"] = R._SEARCH
            seen["prompt"] = Path(prompt_path).read_text()
            Path(out).write_text("CULTURE LOAD: HEAVY\nPOST TALK: 2 of 2,000\n")
            return "fake"
        with mock.patch.object(R, "gemini_video", fake), \
                mock.patch.object(R, "say", lambda *a, **k: None), \
                mock.patch.object(R, "source_url", lambda v: ""), \
                mock.patch.object(R, "creative_qc", lambda *a, **k: {}), \
                mock.patch.object(R, "record_time", lambda *a, **k: None), \
                mock.patch.object(R, "library_home", lambda v, l, st: d / "library"), \
                mock.patch.object(R.L, "save_teardown", lambda *a, **k: None):
            ok = R.run_stage(d, st, stage, {})
        self.assertTrue(ok)
        self.assertTrue(seen["search"])
        self.assertFalse(R._SEARCH)                          # switched off after the read
        self.assertIn("THE RECORD: a man in a suit dunks.", seen["prompt"])
        self.assertIn("never thought I'd see <the character> hooping", seen["prompt"])
        self.assertNotIn("{post_talk}", seen["prompt"])
        self.assertEqual(st["stages"]["stage1k"]["out"], "stages/1k-culture.md")
        self.assertTrue((d / "stages" / "1k-culture.md").read_text().startswith("CULTURE LOAD"))


class Grounding(unittest.TestCase):
    def test_search_turns_on_the_tool_and_files_receipts(self):
        sent = {}

        def req(url, data=None, headers=None, **k):
            sent["body"] = json.loads(data)
            return {"candidates": [{"content": {"parts": [{"text": "R1 — a character"}, {"text": " · a film"}]},
                                    "groundingMetadata": {
                                        "webSearchQueries": ["quoted line film"],
                                        "groundingChunks": [{"web": {"uri": "https://example.invalid/a",
                                                                     "title": "A page"}}]}}]}
        with mock.patch.object(G, "req", req):
            out = G.analyze("k", "m", "uri", "video/mp4", "", prompt="read it", search=True)
        self.assertEqual(sent["body"]["tools"], [{"google_search": {}}])
        self.assertTrue(out.startswith("R1 — a character · a film"))
        self.assertIn("SEARCH RECEIPTS", out)
        self.assertIn("quoted line film", out)
        self.assertIn("A page — https://example.invalid/a", out)

    def test_a_read_that_never_searched_is_asked_again_then_marked(self):
        calls = []

        def req(url, data=None, headers=None, **k):
            calls.append(1)
            return {"candidates": [{"content": {"parts": [{"text": "R1 — from memory"}]}}]}
        with mock.patch.object(G, "req", req):
            out = G.analyze("k", "m", "uri", "video/mp4", "", prompt="read it", search=True)
        self.assertEqual(len(calls), 2)
        self.assertIn("SEARCH RECEIPTS — none", out)
        self.assertIn("unverified", out)

    def test_no_search_is_unchanged(self):
        sent = {}

        def req(url, data=None, headers=None, **k):
            sent["body"] = json.loads(data)
            return {"candidates": [{"content": {"parts": [{"text": "plain"}]}}]}
        with mock.patch.object(G, "req", req):
            out = G.analyze("k", "m", "uri", "video/mp4", "", prompt="read it")
        self.assertNotIn("tools", sent["body"])
        self.assertEqual(out, "plain")

    def test_the_machine_passes_search_only_while_the_flag_is_up(self):
        calls = []

        def run(cmd, **k):
            calls.append(cmd)
            Path(cmd[cmd.index("--out") + 1]).write_text("x")
            import subprocess
            return subprocess.CompletedProcess(cmd, 0, "", "")
        out = Path(tempfile.mkdtemp()) / "o.md"
        with mock.patch.object(R.subprocess, "run", run):
            R.gemini_video(Path("p.md"), Path("v.mp4"), out)
            R._SEARCH = True
            try:
                R.gemini_video(Path("p.md"), Path("v.mp4"), out)
            finally:
                R._SEARCH = False
        self.assertNotIn("--search", calls[0])
        self.assertIn("--search", calls[1])


class Shelf(unittest.TestCase):
    def test_the_read_files_on_the_teardown_shelf(self):
        self.assertEqual(FR.shelf("stages/1k-culture.md"), FR.TOOL)
        self.assertEqual(FR.shelf("prompts/1k-culture.md"), FR.TOOL)
        self.assertEqual(FR.shelf("post-talk.json"), FR.TOOL)
        t = Path(tempfile.mkdtemp())
        run = t / "a-run"
        (run / "stages").mkdir(parents=True)
        (run / "run.json").write_text(json.dumps({"slug": "a-run", "brand": "zz"}))
        (run / "stages" / "1k-culture.md").write_text("CULTURE LOAD: NONE\n")
        (run / "post-talk.json").write_text("{}")
        FR.file_run(run, repo=t / "repo")
        td = t / "repo/runs/video-teardown/zz/a-run"
        self.assertTrue((td / "stages/1k-culture.md").is_file())
        self.assertTrue((td / "post-talk.json").is_file())
        self.assertFalse((t / "repo/runs/video-writing").exists())


if __name__ == "__main__":
    unittest.main()
