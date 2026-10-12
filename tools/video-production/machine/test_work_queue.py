"""work_queue.py — the shared ad list two computers work from without stepping on each other.

Run from this folder:  python3 -m unittest test_work_queue
No network, no keys: the "origin" is a bare repo in a temp folder, cloned twice — one
clone per computer."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

import work_queue as wq


def write(p, data):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data) if not isinstance(data, str) else data)
    return p


def workspace(root):
    """A minimal workspace: components/ + brands/ so repo_root() finds it."""
    (Path(root) / "components").mkdir(parents=True, exist_ok=True)
    (Path(root) / "brands").mkdir(parents=True, exist_ok=True)
    return Path(root)


def prod(ws, brand, label, **run):
    d = Path(ws) / "runs" / "video-production" / brand / label
    write(d / "run.json", dict({"machine": "video-production", "brand": brand, "label": label}, **run))
    return d


class Stages(unittest.TestCase):
    """Each stage is read from the files that prove it, never from a field anyone sets by hand."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.ws = workspace(self.tmp / "ws")
        self.drive = self.tmp / "drive"

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_every_stage_in_order(self):
        prod(self.ws, "b1", "a-song", format="song-ad", brief_id="brief-0001")                 # no song yet
        d = prod(self.ws, "b1", "a-broll", format="song-ad", brief_id="brief-0002")
        write(d / "song" / "song.mp3", "x")                                                      # song done
        prod(self.ws, "b1", "a-cut", format="song-ad", brief_id="brief-0003", song_file_drive="x.mp3")
        (self.ws / "runs" / "video-edit" / "b1" / "a-cut").mkdir(parents=True)                  # edit open
        prod(self.ws, "b1", "a-hooks", format="demonstration", brief_id="brief-0004")
        write(self.ws / "runs/video-edit/b1/a-hooks/deliverable/versions-index.json",
              {"brief": "brief-0004", "versions": [{"version_id": "control"}]})
        prod(self.ws, "b1", "a-card", format="demonstration", brief_id="brief-0005")
        write(self.ws / "runs/video-edit/b1/a-card/deliverable/versions-index.json",
              [{"version": "control"}, {"version": "h-a-x"}])                                    # the list shape
        prod(self.ws, "b1", "a-done", format="demonstration", brief_id="brief-0006")
        write(self.drive / "meta/b1/1-check/video/b1_p_brief-0006_batch-a/card.json", {"brief_id": "brief-0006"})
        ads = wq.scan(self.ws, self.drive)
        got = {k: v["stage"] for k, v in ads.items()}
        self.assertEqual(got, {"brief-0001": "song", "brief-0002": "b-roll", "brief-0003": "cut",
                               "brief-0004": "hooks", "brief-0005": "card", "brief-0006": "done"})

    def test_card_from_another_machine_shows_without_a_run_here(self):
        write(self.drive / "meta/b2/2-approved/video/b2_p_brief-0099_batch-a/card.json", {"brief_id": "brief-0099"})
        ad = wq.scan(self.ws, self.drive)["brief-0099"]
        self.assertEqual(ad["stage"], "done")
        self.assertFalse(ad["seen_here"])

    def test_sent_back_card_is_back_at_card(self):
        prod(self.ws, "b1", "x", format="demonstration", brief_id="brief-0007")
        write(self.drive / "meta/b1/sent-back/video/b1_p_brief-0007_batch-a/card.json", {"brief_id": "brief-0007"})
        self.assertEqual(wq.scan(self.ws, self.drive)["brief-0007"]["stage"], "card")

    def test_media_only_on_drive_still_counts(self):
        """A song made on the other computer is on the Drive mirror, never in git."""
        prod(self.ws, "b1", "s1", format="song-ad", brief_id="brief-0020")
        write(self.drive / "runs/video-production/b1/s1/song/song.mp3", "x")
        self.assertEqual(wq.scan(self.ws, self.drive)["brief-0020"]["stage"], "b-roll")

    def test_a_filed_card_outranks_files_this_machine_lacks(self):
        prod(self.ws, "b1", "s2", format="song-ad", brief_id="brief-0021")         # no song here at all
        write(self.drive / "meta/b1/1-check/video/b1_p_brief-0021_batch-a/card.json", {"brief_id": "brief-0021"})
        self.assertEqual(wq.scan(self.ws, self.drive)["brief-0021"]["stage"], "done")

    def test_runs_without_a_brief_are_left_out_unless_asked(self):
        prod(self.ws, "b1", "dry-run", format="song-ad")
        self.assertEqual(wq.scan(self.ws, None), {})
        self.assertIn("b1--dry-run", wq.scan(self.ws, None, include_all=True))

    def test_reruns_of_one_brief_are_one_ad_at_the_furthest_stage(self):
        prod(self.ws, "b1", "r1", format="demonstration", brief_id="brief-0010")
        prod(self.ws, "b1", "r2", format="demonstration", brief_id="brief-0010")
        (self.ws / "runs/video-edit/b1/r2").mkdir(parents=True)
        ad = wq.scan(self.ws, None)["brief-0010"]
        self.assertEqual((ad["stage"], ad["label"], sorted(ad["runs"])), ("cut", "r2", ["r1", "r2"]))


class Claims(unittest.TestCase):
    """Claim, refuse, go stale, take over, release — on a plain folder store."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.ws = workspace(self.tmp / "ws")
        prod(self.ws, "b1", "lab1", format="demonstration", brief_id="brief-0001")
        self.store = wq.DirStore(self.tmp / "records")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_second_machine_is_refused_while_the_first_works(self):
        wq.claim(self.ws, self.store, "brief-0001", me="mac-a", person="damon")
        with self.assertRaises(wq.Refused) as e:
            wq.claim(self.ws, self.store, "brief-0001", me="mac-b", person="editor")
        self.assertIn("mac-a", str(e.exception))
        self.assertEqual(len(self.store.records()), 1)          # the refusal wrote nothing

    def test_claiming_your_own_ad_again_writes_nothing(self):
        wq.claim(self.ws, self.store, "brief-0001", me="mac-a", person="damon")
        with self.assertRaises(wq.Refused):
            wq.claim(self.ws, self.store, "brief-0001", me="mac-a", person="damon")
        self.assertEqual(len(self.store.records()), 1)

    def _age_all(self, hours):
        for f in (self.tmp / "records").glob("*.json"):
            r = json.loads(f.read_text())
            r["created"] = wq.iso(wq.now_utc() - timedelta(hours=hours))
            f.write_text(json.dumps(r))

    def test_stale_claim_needs_take_over_and_names_what_it_replaced(self):
        wq.claim(self.ws, self.store, "brief-0001", me="mac-a", person="damon")
        self._age_all(7)
        with self.assertRaises(wq.Refused) as e:
            wq.claim(self.ws, self.store, "brief-0001", me="mac-b", person="editor")
        self.assertIn("stale", str(e.exception))
        _, rec = wq.claim(self.ws, self.store, "brief-0001", take_over=True, me="mac-b", person="editor")
        self.assertEqual(rec["verdict"]["takeover_of"]["machine"], "mac-a")
        self.assertEqual(wq.fold(self.store.records())["brief-0001"]["owner"]["machine"], "mac-b")

    def test_progress_keeps_a_claim_fresh(self):
        wq.claim(self.ws, self.store, "brief-0001", me="mac-a", person="damon")
        self._age_all(7)
        wq.progress(self.ws, self.store, "brief-0001", stage="cut", me="mac-a", person="damon")
        with self.assertRaises(wq.Refused) as e:
            wq.claim(self.ws, self.store, "brief-0001", take_over=True, me="mac-b", person="editor")
        self.assertNotIn("stale", str(e.exception))

    def test_only_the_owner_reports_progress_or_releases(self):
        wq.claim(self.ws, self.store, "brief-0001", me="mac-a", person="damon")
        with self.assertRaises(wq.Refused):
            wq.progress(self.ws, self.store, "brief-0001", stage="cut", me="mac-b", person="editor")
        with self.assertRaises(wq.Refused):
            wq.release(self.ws, self.store, "brief-0001", me="mac-b", person="editor")
        wq.release(self.ws, self.store, "brief-0001", me="mac-a", person="damon")
        wq.claim(self.ws, self.store, "brief-0001", me="mac-b", person="editor")   # free again

    def test_board_shows_the_other_machines_reported_stage(self):
        wq.claim(self.ws, self.store, "brief-0042", me="mac-b", person="editor")   # an ad mac-a has no run for
        wq.progress(self.ws, self.store, "brief-0042", stage="hooks", me="mac-b", person="editor")
        rows = {r["brief"]: r for r in wq.board(self.ws, self.store)}
        self.assertEqual((rows["brief-0042"]["stage"], rows["brief-0042"]["owner"]), ("hooks", "mac-b"))
        self.assertEqual(rows["brief-0001"]["owner"], None)

    def test_records_are_on_the_planes_shape(self):
        wq.claim(self.ws, self.store, "brief-0001", me="mac-a", person="damon")
        f = next((self.tmp / "records").glob("*.json"))
        self.assertRegex(f.name, r"^\d{8}T\d{6}Z--damon--brief-0001--claim\.json$")
        r = json.loads(f.read_text())
        for k in ("schema", "kind", "reviewer", "item", "verdict", "notes", "created", "via"):
            self.assertIn(k, r)
        self.assertEqual((r["kind"], r["verdict"]["event"], r["verdict"]["machine"]), ("video-queue", "claim", "mac-a"))

    def test_page_has_every_stage_and_who_is_on_it(self):
        wq.claim(self.ws, self.store, "brief-0001", me="mac-a", person="damon")
        html = wq.page_html(wq.board(self.ws, self.store), "mac-a", wq.iso(wq.now_utc()), 6)
        for word in ("Song", "B-roll", "Cut", "Hooks", "Card", "Done", "mac-a", "brief-0001"):
            self.assertIn(word, html)


def git(cwd, *args, check=True):
    p = subprocess.run(["git"] + list(args), cwd=str(cwd), capture_output=True, text=True)
    if check and p.returncode != 0:
        raise AssertionError("git %s: %s" % (" ".join(args), p.stderr))
    return p.stdout.strip()


class TwoComputers(unittest.TestCase):
    """The real transport: two clones of one origin. A claim counts once it is on origin/main,
    and publishing it never touches the clone's working tree or staged work."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.origin = self.tmp / "origin.git"
        git(self.tmp, "init", "--bare", "-b", "main", str(self.origin))
        seed = workspace(self.tmp / "seed")
        git(seed, "init", "-b", "main")
        self._ident(seed)
        write(seed / "README.md", "seed\n")
        git(seed, "add", "-A")
        git(seed, "commit", "-m", "seed")
        git(seed, "push", str(self.origin), "main")
        self.a = self._clone("mac-a")
        self.b = self._clone("mac-b")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _ident(self, d):
        git(d, "config", "user.email", "t@example.com")
        git(d, "config", "user.name", "t")

    def _clone(self, name):
        d = self.tmp / name
        git(self.tmp, "clone", "-q", str(self.origin), str(d))
        self._ident(d)
        workspace(d)
        return d

    def test_b_sees_a_claim_and_is_refused(self):
        wq.claim(self.a, wq.GitStore(self.a), "brief-0001", me="mac-a", person="damon")
        with self.assertRaises(wq.Refused) as e:
            wq.claim(self.b, wq.GitStore(self.b), "brief-0001", me="mac-b", person="editor")
        self.assertIn("mac-a", str(e.exception))

    def test_a_lost_race_is_rechecked_on_the_fresh_tip(self):
        sb = wq.GitStore(self.b)
        sb.fetch()                                          # b looked before a claimed…
        wq.claim(self.a, wq.GitStore(self.a), "brief-0001", me="mac-a", person="damon")
        rec = wq.make_record("claim", "brief-0001", "mac-b", "editor")
        with self.assertRaises(wq.Refused):                 # …but publish re-reads origin before pushing
            sb.publish(rec, wq._decide_claim("brief-0001", "mac-b", False, 6))

    def test_two_different_ads_both_land(self):
        sa, sb = wq.GitStore(self.a), wq.GitStore(self.b)
        sb.fetch()
        wq.claim(self.a, sa, "brief-0001", me="mac-a", person="damon")
        # b's local tip is now behind; its push is refused once, it refetches and lands
        wq.claim(self.b, sb, "brief-0002", me="mac-b", person="editor")
        owners = {k: v["owner"]["machine"] for k, v in wq.fold(sa.records()).items()}
        self.assertEqual(owners, {"brief-0001": "mac-a", "brief-0002": "mac-b"})

    def test_publishing_never_touches_the_working_tree_or_staged_work(self):
        write(self.a / "someone-elses.txt", "in flight\n")
        git(self.a, "add", "someone-elses.txt")             # another session's staged work
        head_before = git(self.a, "rev-parse", "HEAD")
        wq.claim(self.a, wq.GitStore(self.a), "brief-0001", me="mac-a", person="damon")
        self.assertEqual(git(self.a, "rev-parse", "HEAD"), head_before)          # local branch not moved
        self.assertEqual(git(self.a, "diff", "--cached", "--name-only"), "someone-elses.txt")
        self.assertFalse((self.a / wq.RECORDS_REL).exists())                     # nothing dropped in the tree
        tree = git(self.a, "ls-tree", "-r", "--name-only", "origin/main")
        self.assertNotIn("someone-elses.txt", tree)
        self.assertIn("platform/data/records/video-queue/", tree)

    def test_offline_means_not_claimed(self):
        git(self.a, "remote", "set-url", "origin", str(self.tmp / "gone.git"))
        with self.assertRaises(wq.Refused) as e:
            wq.GitStore(self.a).publish(wq.make_record("claim", "brief-0001", "mac-a", "damon"), lambda s: None)
        self.assertIn("NOT claimed", str(e.exception))


class RunsOnTheMinisPython(unittest.TestCase):
    """The video line's code must parse under the 3.9.6 interpreter a fresh Mac ships with
    (builder card rule 10) — a second editor's Mac has no 3.12 until someone installs it."""

    def test_every_file_parses_under_system_python(self):
        py = "/usr/bin/python3"
        if not os.path.exists(py):
            self.skipTest("no /usr/bin/python3 here")
        ver = subprocess.run([py, "-c", "import sys;print(sys.version_info[:2])"], capture_output=True, text=True).stdout
        if "(3, 9)" not in ver:
            self.skipTest("/usr/bin/python3 is not 3.9 here: %s" % ver.strip())
        repo = Path(__file__).resolve().parents[3]
        files = subprocess.run(["git", "ls-files", "tools/video-production", "tools/video-edit",
                                "tools/video-teardown", "components/local-studio"],
                               cwd=str(repo), capture_output=True, text=True).stdout.split()
        files = [f for f in files if f.endswith(".py")]
        script = ("import ast,sys\nbad=[]\nfor f in sys.argv[1:]:\n    try: ast.parse(open(f,encoding='utf-8').read())\n"
                  "    except SyntaxError as e: bad.append('%s:%s' % (f, e.lineno))\nprint('\\n'.join(bad))")
        out = subprocess.run([py, "-c", script] + files, cwd=str(repo), capture_output=True, text=True).stdout.strip()
        self.assertEqual(out, "", "these do not parse under Python 3.9:\n" + out)

    def test_no_x_or_y_annotation_is_evaluated_at_import(self):
        """`def f(a: dict | None)` parses on 3.9 but raises TypeError the moment the module is
        imported — unless the file has `from __future__ import annotations` or quotes it."""
        import ast
        repo = Path(__file__).resolve().parents[3]
        files = subprocess.run(["git", "ls-files", "tools/video-production", "tools/video-edit",
                                "tools/video-teardown", "components/local-studio"],
                               cwd=str(repo), capture_output=True, text=True).stdout.split()
        bad = []
        for f in files:
            if not f.endswith(".py"):
                continue
            src = (repo / f).read_text(encoding="utf-8")
            if "from __future__ import annotations" in src:
                continue
            try:
                tree = ast.parse(src)
            except SyntaxError:
                continue                                   # the parse test above names it
            for n in ast.walk(tree):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    anns = [a.annotation for a in n.args.args + n.args.kwonlyargs if a.annotation]
                    anns += [n.returns] if n.returns else []
                    for a in anns:
                        if any(isinstance(m, ast.BinOp) and isinstance(m.op, ast.BitOr) for m in ast.walk(a)):
                            bad.append("%s:%d" % (f, n.lineno))
        self.assertEqual(bad, [], "X | Y annotations that break on 3.9 at import:\n" + "\n".join(bad))


if __name__ == "__main__":
    unittest.main()
