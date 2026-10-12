#!/usr/bin/env python3
"""The chain replay (the owner, 2026-09-30: "make the moves, and then do a test run
on the chains … take what we already did end to end and make sure it moves,
like the chains actually move from step to step to step").

A real, finished run is played back through TODAY's chain: the current
plan, the current prompts from their current homes, every variable resolved
from the real brand files, every gate the code runs. Only the model calls are
answered from the record — each stage gets back the words that stage wrote on
the real run — so it spends nothing. Anything that reaches for the network
fails the test by name.

What is replayed and not re-judged: the model answers, the swipe match and the
manifest (both are AI judges), the web research and the Drive. What runs for
real: the plan, the route lock, prompt resolution for every stage, the
structure lock, the hook format check, the brand-file fills, the assemble, and
the filing to both shelves.

    python3 test_chain_replay.py
"""
import importlib.util
import io
import json
import os
import shutil
import socket
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chain as C                                            # noqa: E402

_TMP = Path(tempfile.mkdtemp(prefix="chain-replay-"))
C.runs_root = lambda *a, **k: _TMP
import run as R                                              # noqa: E402
import file_run as FR                                        # noqa: E402
R.RUNS = _TMP

WS = C.WS
REPLAYS = [  # (brand, filed run, route) — the one filed run whose record
    # passes today's teardown checks, written both ways: the teardown is
    # route-free, so the same record carries the creator and the ai line
    ("brand-a", "run-a-face-scrub", "creator"),
    ("brand-a", "run-a-face-scrub", "ai"),
]


def _no_network(*a, **k):
    raise AssertionError("the replay reached for the network — it must spend nothing")


def _recorded(brand, slug, name):
    for shelf in ("video-writing", "video-teardown"):
        f = WS / "runs" / shelf / brand / slug / "stages" / name
        if f.is_file():
            return f.read_text()
    return None


def _product_from_record(brand, slug):
    """The product a run was written for, when its run.json never said: the
    product file whose own text is in the rewrite's prompt as sent."""
    sent = WS / "runs" / "video-writing" / brand / slug / "prompts" / "3-injection.md"
    if not sent.is_file():
        return None
    text = sent.read_text(errors="replace")
    hits = []
    for f in sorted((WS / "brands" / brand / "products").glob("**/*.md")):
        if f.name.lower() in ("readme.md", "offer-bank.md", "subscriptions.md"):
            continue
        body = f.read_text(errors="replace").strip()
        probe = next((l for l in body.splitlines() if len(l.strip()) > 40), "")[:120]
        if probe and probe in text:
            hits.append(f.parent.name if f.name == "product.md" else f.stem)
    return hits[0] if len(hits) == 1 else None


class Replay(unittest.TestCase):
    def replay(self, brand, slug, route, relax_teardown=False):
        """route None = the teardown only (the route lock). relax_teardown lets
        an old record below today's teardown bar through, so its WRITING can
        still be replayed — replay_all.py reports the bar separately."""
        if not (WS / "runs" / "video-teardown" / brand / slug).is_dir():
            self.skipTest(f"{slug} is not filed in this checkout")
        t = Path(tempfile.mkdtemp(prefix=f"replay-{slug}-"))
        video = t / "source.mp4"
        video.write_bytes(b"\x00")              # a stub: the audio passes skip themselves
        answered, missing = [], []

        def answer(out):
            out = Path(out)
            txt = _recorded(brand, slug, out.name)
            if txt is None:
                missing.append(out.name)
                txt = f"(replay: the real run has no {out.name})\n"
            out.write_text(txt)
            answered.append(out.name)
            if out.name.startswith("1-"):
                for f in ("transcript.json", "sound-sheet.json", "sound-sheet.md"):
                    src = WS / "runs" / "video-teardown" / brand / slug / f
                    if src.is_file():
                        shutil.copyfile(src, out.parent.parent / f)
            return "replay"

        real_spec = importlib.util.spec_from_file_location

        def spec(name, path, *a, **k):
            s = real_spec(name, path, *a, **k)
            if name not in ("swipe_match", "manifest", "slot_research"):
                return s
            loader = s.loader

            class _L:
                def create_module(self, sp):
                    return None

                def exec_module(self, m):
                    m.__file__ = str(path)
                    loader.exec_module(m)
                    if name == "swipe_match":
                        m.check = lambda d, brief: (True, [])
                    elif name == "manifest":
                        m.check = lambda d, b, brief: (True, [])
                    else:
                        m.fill = lambda d, **k: {"filled": [], "holes": 0}
            return importlib.util.spec_from_loader(name, _L())

        filed = {}

        def file_it(d):
            filed["dest"], filed["copied"], _ = FR.file_run(d, repo=t / "repo")

        stubs = {"research": types.SimpleNamespace(inputs=lambda st: {}),
                 "mark_used": types.SimpleNamespace(run=lambda d, st, out: (Path(out).write_text("(replay)\n"), "replay")[1]),
                 "motion": types.SimpleNamespace(check=lambda v: {"verdict": "moving", "movement": 1.0}),
                 "framework_bank": types.SimpleNamespace(refresh=lambda *a, **k: None),
                 "records": types.SimpleNamespace(main=lambda *a, **k: None)}
        import subprocess
        done = lambda *a, **k: subprocess.CompletedProcess(a[0] if a else [], 0, "", "")
        with mock.patch.object(R, "gemini_video", lambda p, v, out: answer(out)), \
                mock.patch.object(R, "gemini_text", lambda p, out: answer(out)), \
                mock.patch.object(R, "claude", lambda text, out: answer(out)), \
                mock.patch.object(R, "with_retry", lambda fn, what, **k: fn()), \
                mock.patch.object(R, "library_home", lambda v, l, st: t / "library"), \
                mock.patch.object(R, "source_url", lambda v: "https://example.invalid/swipe"), \
                mock.patch.object(R, "record_time", lambda *a, **k: None), \
                mock.patch.object(R, "TIMES", t / "stage-times.json"), \
                mock.patch.object(R, "file_to_repo", file_it), \
                mock.patch.object(R, "stay_awake", lambda *a, **k: None), \
                mock.patch.object(R, "rebuild_board", lambda *a, **k: None), \
                mock.patch.object(R.L, "save_teardown", lambda *a, **k: None), \
                mock.patch.object(C, "mirror_to_drive", lambda *a, **k: None), \
                mock.patch.object(importlib.util, "spec_from_file_location", spec), \
                mock.patch.object(socket.socket, "connect", _no_network), \
                mock.patch.object(subprocess, "run", done), \
                mock.patch.dict(sys.modules, stubs), \
                mock.patch.object(R, "thin_visuals", (lambda b: None) if relax_teardown else R.thin_visuals), \
                mock.patch.object(R, "off_doctrine_sections", (lambda b: []) if relax_teardown else R.off_doctrine_sections), \
                mock.patch.dict(os.environ, {"DAEMN_STRUCTURE_APPROVALS": "all",
                                             "VT_NO_AUDIO_TEARDOWN": "1"}), \
                redirect_stdout(io.StringIO()) as buf:
            product = json.loads((WS / "runs" / "video-teardown" / brand / slug / "run.json").read_text()).get("product")
            product = product or _product_from_record(brand, slug)
            ok = R.run_video(video, f"replay-{slug}-{route}", brand, route=route, stop="7b", product=product,
                             extras={"product": product or "", "brand_name": brand, "video_count": "1",
                                     "declared_avatar": "", "declared_sub": "", "declared_audience": ""})
        log = buf.getvalue()
        st = json.loads((_TMP / C.run_slug(R.slug(f"replay-{slug}-{route}")) / "run.json").read_text())
        return ok, log, st, answered, missing, filed, t

    def test_each_route_moves_from_step_to_step(self):
        for brand, slug, route in REPLAYS:
            with self.subTest(route=route, run=slug):
                ok, log, st, answered, missing, filed, t = self.replay(brand, slug, route)
                done = [k for k, r in st["stages"].items() if r.get("status") == "done"]
                print(f"\n{route:8} {slug}: {len(done)} steps done — {' → '.join(r.get('name') or k for k, r in st['stages'].items() if r.get('status') == 'done')}")
                held = {k: r.get("why") or r.get("status") for k, r in st["stages"].items()
                        if r.get("status") not in ("done", "skipped")}
                self.assertTrue(ok, f"stopped: {held}\n{log[-3000:]}")
                self.assertFalse(held, f"held: {held}\n{log[-3000:]}")
                self.assertEqual(st["production_route"], route)
                self.assertIn("stage5", done)
                self.assertNotIn("stage6", st["stages"])          # no more frames
                for key in ("stage3", "stage4b", "stage5"):
                    self.assertIn("copywriter/prompts/video", st["stages"][key]["prompt_file"])
                for key in ("stage0", "stage1", "stage1c", "stage2"):
                    self.assertIn("video-teardown/prompts", st["stages"][key]["prompt_file"])
                repo = t / "repo" / "runs"
                self.assertTrue(any((repo / "video-teardown").rglob("1-teardown.md")))
                self.assertTrue(any((repo / "video-writing").rglob("5-brief.md")))


if __name__ == "__main__":
    unittest.main(verbosity=1)
