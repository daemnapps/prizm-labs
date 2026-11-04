"""QB-1 (queue core): cq.py and the writers, under temp folders only — never the repo's runs/queue/ or
runs/queue-shadow/. git is exercised only through the run seam.

    python3 components/creative-queue/test_qb1_cli.py
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))
import cq  # noqa: E402
import qcore  # noqa: E402

FIXTURES = HERE / "fixtures" / "legacy"
# the two copied entries, found by what they carry (brand names stay in the fixtures, never in code)
LEGACY = {json.loads(f.read_text())["id"]: json.loads(f.read_text()) for f in FIXTURES.glob("*/*.json")}
REMOVED_ID = next(i for i, e in LEGACY.items() if e.get("removed") is True)
DECIDED_ID = next(i for i, e in LEGACY.items() if isinstance(e.get("decided"), dict))


def call(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cq.main(argv)
    return code, out.getvalue(), err.getvalue()


class FakeGit:
    """A stand-in for subprocess.run: records every git call; `push_fails` pushes fail before one succeeds."""

    def __init__(self, push_fails=0, fail=None, email="pm@company.com"):
        self.calls, self.push_fails, self.fail, self.email = [], push_fails, fail, email

    def __call__(self, args, **kw):
        self.calls.append(list(args))
        sub = args[1]
        if sub == self.fail:
            return SimpleNamespace(returncode=1, stdout="", stderr="%s went wrong" % sub)
        if sub == "push" and self.push_fails:
            self.push_fails -= 1
            return SimpleNamespace(returncode=1, stdout="", stderr="rejected (fetch first)")
        if sub == "config":
            return SimpleNamespace(returncode=0 if self.email else 1, stdout=(self.email or "") + "\n", stderr="")
        if sub == "rev-parse":
            return SimpleNamespace(returncode=0, stdout="abc123\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def subs(self):
        return [" ".join(c[1:3]) if c[1] == "pull" else c[1] for c in self.calls]


class Temp(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="qb1-")).resolve()     # macOS: /var is /private/var
        self.root = self.tmp / "root"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def lines(self, person):
        files = sorted((self.root / "decisions" / person).glob("*.jsonl"))
        return [json.loads(x) for f in files for x in f.read_text().splitlines() if x.strip()]


class Decisions(Temp):
    def test_each_op_appends_one_line(self):
        runs = [["set", "q1", "priority", "top"],
                ["add", "q2", "--title", "New idea", "--brand", "b", "--type", "video-ad"],
                ["remove", "q1"], ["restore", "q1"], ["approve", "q2"]]
        for n, argv in enumerate(runs, 1):
            code, out, err = call(argv + ["--by", "pm", "--root", str(self.root), "--no-commit"])
            self.assertEqual(code, 0, err)
            path = next((self.root / "decisions" / "pm").glob("*.jsonl"))
            self.assertEqual(out, "decision: %s\n" % path)
            self.assertEqual(len(self.lines("pm")), n)
        got = self.lines("pm")
        self.assertEqual([x["op"] for x in got], ["set", "add", "remove", "restore", "approve"])
        self.assertEqual((got[0]["field"], got[0]["value"]), ("priority", "top"))
        self.assertEqual(got[1]["value"], {"title": "New idea", "brand": "b", "type": "video-ad"})
        for x in got:
            self.assertEqual((x["schema"], x["by"]), (1, "pm"))
            self.assertIsNotNone(qcore._utc(x["made"]))
            self.assertNotIn("legacy", x)
        self.assertEqual(path.name, got[0]["made"][:10] + ".jsonl")      # the UTC day names the file

    def test_by_defaults_to_git_email(self):
        fake = FakeGit(email="engineer@company.com")
        with mock.patch.object(cq, "RUN", fake):
            code, out, err = call(["remove", "q1", "--root", str(self.root), "--no-commit"])
        self.assertEqual(code, 0, err)
        self.assertEqual(self.lines("engineer")[0]["by"], "engineer")
        self.assertEqual(fake.subs(), ["config"])
        with mock.patch.object(cq, "RUN", FakeGit(email=None)):
            code, out, err = call(["remove", "q1", "--root", str(self.root), "--no-commit"])
        self.assertEqual(code, 1)
        self.assertIn("--by", err)

    def test_bad_decisions_refused_with_reason(self):
        code, _, err = call(["set", "q1", "removed", "yes", "--by", "pm", "--root", str(self.root), "--no-commit"])
        self.assertEqual(code, 1)
        code, _, err = call(["set", "q1", "requested_stage", "nowhere", "--by", "pm", "--root", str(self.root),
                             "--no-commit"])
        self.assertEqual(code, 1)
        self.assertIn("requested_stage", err)
        for rec, word in (({"id": "q", "op": "delete"}, "op"), ({"id": "q", "op": "set", "field": "stage"}, "field"),
                          ({"op": "remove"}, "id"), ({"id": "q", "op": "remove", "by": "owner"}, "own log"),
                          ({"id": "q", "op": "remove", "legacy": True}, "legacy")):
            with self.assertRaises(ValueError) as cm:
                qcore.append_decision(self.root, "pm", rec)
            self.assertIn(word, str(cm.exception))
        with self.assertRaises(ValueError):
            qcore.append_decision(self.root, "../escape", {"id": "q", "op": "remove"})
        self.assertFalse((self.root / "decisions").exists() and self.lines("pm"))

    def test_without_no_commit_commits_exactly_the_written_file(self):
        fake = FakeGit()
        with mock.patch.object(cq, "RUN", fake):
            code, out, err = call(["approve", "q1", "--by", "pm", "--root", str(self.root)])
        self.assertEqual(code, 0, err)
        path = str(next((self.root / "decisions" / "pm").glob("*.jsonl")))
        self.assertEqual(fake.subs(), ["add", "commit", "push", "rev-parse"])
        self.assertEqual(fake.calls[0], ["git", "add", "--", path])
        self.assertEqual(fake.calls[1][-2:], ["--", path])
        self.assertIn("commit: abc123", out)


class RebuildShow(Temp):
    def seed(self):
        qcore.write_observation(self.root, "mac", {"q1": {"title": "One", "observed_stage": "making"}},
                                now="2026-10-22T02:00:00Z")
        for argv in (["set", "q1", "requested_stage", "launch"], ["add", "q2", "--title", "Two"]):
            self.assertEqual(call(argv + ["--by", "pm", "--root", str(self.root), "--no-commit"])[0], 0)

    def test_rebuild_writes_index_and_prints_summary(self):
        self.seed()
        code, out, err = call(["rebuild", "--root", str(self.root), "--now", "2026-10-22T03:00:00Z", "--no-commit"])
        self.assertEqual(code, 0, err)
        self.assertEqual(out, "index: 2 entries · sources: mac 3600s\n")
        idx = json.loads((self.root / "index.json").read_text())
        self.assertEqual(idx["built"], "2026-10-22T03:00:00Z")
        self.assertEqual([e["id"] for e in idx["entries"]], ["q1", "q2"])
        self.assertIs(idx["entries"][0]["stage_differs"], True)
        code, _, err = call(["rebuild", "--root", str(self.root), "--now", "yesterday", "--no-commit"])
        self.assertEqual(code, 1)

    def test_show_prints_entry(self):
        self.seed()
        code, out, err = call(["show", "q1", "--root", str(self.root)])
        self.assertEqual(code, 0, err)
        e = json.loads(out)
        self.assertEqual((e["id"], e["observed_stage"], e["requested_stage"]), ("q1", "making", "launch"))
        self.assertEqual(e["decided_by"]["requested_stage"]["by"], "pm")
        self.assertEqual(call(["show", "nope", "--root", str(self.root)])[0], 1)
        self.assertFalse((self.root / "index.json").exists())      # show writes nothing


class ImportLegacy(Temp):
    def test_two_fixture_entries(self):
        self.assertEqual(sorted(p.stem for p in FIXTURES.glob("*/*.json")), sorted([DECIDED_ID, REMOVED_ID]))
        self.assertNotEqual(DECIDED_ID, REMOVED_ID)
        code, out, err = call(["import-legacy", "--from", str(FIXTURES), "--root", str(self.root), "--no-commit"])
        self.assertEqual(code, 0, err)
        self.assertEqual(out, "legacy: 2 entries, 2 decisions\n")
        o = json.loads((self.root / "observations" / "localhost.json").read_text())
        self.assertEqual((o["schema"], o["source"]), (1, "localhost"))
        self.assertIsNotNone(qcore._utc(o["as_of"]))
        rm, dd = o["entries"][REMOVED_ID], o["entries"][DECIDED_ID]
        self.assertEqual((rm["observed_stage"], dd["observed_stage"]), ("making", "final-needs-you"))
        for k in ("stage", "id") + cq.LEGACY_HUMAN:
            self.assertNotIn(k, rm)
            self.assertNotIn(k, dd)
        self.assertEqual(rm["title"], LEGACY[REMOVED_ID]["title"])
        self.assertEqual(rm["history"], LEGACY[REMOVED_ID]["history"])      # every other field carried as observed
        legacy = [json.loads(x) for x in (self.root / "decisions" / "owner" / "legacy.jsonl").read_text().splitlines()]
        self.assertEqual(legacy, [
            {"schema": 1, "id": DECIDED_ID, "op": "approve", "field": None,
             "value": {"action": "go", "stage": "final-needs-you", "at": "2026-10-18T14:31:16"},
             "by": "owner", "made": "2026-10-18T14:31:16", "legacy": True},
            {"schema": 1, "id": REMOVED_ID, "op": "remove", "field": None, "value": None,
             "by": "owner", "made": "2026-10-19T17:20:31", "legacy": True}])
        # the imported queue reduces: the removal is a tombstone, the go an approval waiting to run
        code, out, err = call(["rebuild", "--root", str(self.root), "--no-commit"])
        self.assertEqual(code, 0, err)
        idx = {e["id"]: e for e in json.loads((self.root / "index.json").read_text())["entries"]}
        self.assertIs(idx[REMOVED_ID]["removed"], True)
        self.assertEqual(idx[DECIDED_ID]["approved"], {"by": "owner", "made": "2026-10-18T14:31:16"})
        self.assertEqual(idx[DECIDED_ID]["execution"], "pending")
        # a second import changes nothing, so it writes and commits nothing
        fake = FakeGit()
        with mock.patch.object(cq, "RUN", fake):
            code, out, err = call(["import-legacy", "--from", str(FIXTURES), "--root", str(self.root)])
        self.assertEqual((code, fake.calls), (0, []))

    def test_person_fields_take_their_own_timestamp(self):
        src = self.tmp / "old"
        shutil.copytree(FIXTURES, src)
        e = {"id": "b_x_brief-0001", "stage": "brief", "priority": "top", "note": "n", "who": None,
             "history": [{"stage": "brief", "at": "2026-10-17T17:11:11"},
                         {"set": {"priority": "top"}, "by": "the owner", "at": "2026-10-18T09:00:00"},
                         {"set": {"note": "n"}, "by": "the owner", "at": "2026-10-22T02:20:07+00:00"}],
             "created": "2026-10-17T17:11:11", "updated": "2026-10-22T02:20:07+00:00"}
        (src / "b").mkdir()
        (src / "b" / "b_x_brief-0001.json").write_text(json.dumps(e))
        (src / "b" / "not-an-entry.json").write_text(json.dumps({"id": "something else"}))
        (src / "b" / "b_old_idea.json").write_text(json.dumps({"id": "b_old_idea", "moved_to": "b_x_brief-0001"}))
        code, out, err = call(["import-legacy", "--from", str(src), "--root", str(self.root), "--no-commit"])
        self.assertEqual(code, 0, err)
        self.assertEqual(out, "legacy: 3 entries, 4 decisions\n")
        mine = {(x["op"], x["field"]): x for x in self.lines("owner") if x["id"] == "b_x_brief-0001"}
        self.assertEqual(sorted(mine), [("set", "note"), ("set", "priority")])
        self.assertEqual(mine[("set", "priority")]["made"], "2026-10-18T09:00:00")
        self.assertEqual(mine[("set", "note")]["made"], "2026-10-22T02:20:07+00:00")
        self.assertTrue(all(x["legacy"] for x in self.lines("owner")))


class LiveGuard(Temp):
    def make_repo(self, switch):
        repo = self.tmp / "repo"
        (repo / "brands").mkdir(parents=True, exist_ok=True)
        (repo / "components" / "creative-queue").mkdir(parents=True, exist_ok=True)
        f = repo / "components" / "creative-queue" / "live-switch.json"
        if switch is None:
            f.unlink() if f.exists() else None
        else:
            f.write_text(switch)
        return repo

    def test_real_repo_switch_is_off_and_refuses(self):
        self.assertEqual(json.loads((HERE / "live-switch.json").read_text())["live"], "off")
        with mock.patch.dict(os.environ):
            os.environ.pop("AI_WORKSPACE", None)
            self.assertEqual(qcore.live_state(), "off")
            with self.assertRaises(qcore.Refused) as cm:
                qcore.check_root(qcore.live_root())         # check only: nothing is written
            self.assertEqual(str(cm.exception), qcore.REFUSED)
            self.assertEqual(qcore.shadow_root(), qcore.live_root().parent / "queue-shadow")

    def test_fires_with_switch_off(self):
        repo = self.make_repo(json.dumps({"live": "off"}))
        live = repo / "runs" / "queue"
        with mock.patch.dict(os.environ, {"AI_WORKSPACE": str(repo)}):
            for argv in (["rebuild"], ["set", "q1", "note", "x", "--by", "pm"], ["show", "q1"],
                         ["import-legacy", "--from", str(FIXTURES)]):
                code, out, err = call(argv + ["--root", str(live), "--no-commit"])
                self.assertEqual(code, 2)
                self.assertEqual(err, "REFUSED: the live queue is off (components/creative-queue/live-switch.json)"
                                      " — build-only until QB-4 (joint queue test)\n")
            code, _, _ = call(["rebuild", "--root", str(live / "sub"), "--no-commit"])
            self.assertEqual(code, 2)
            code, _, _ = call(["rebuild", "--root", str(repo / "runs" / "queue" / ".." / "queue"), "--no-commit"])
            self.assertEqual(code, 2)
        self.assertFalse(live.exists())
        for bad in (None, "not json", json.dumps({"live": "ON"}), json.dumps({"live": True}), json.dumps(["on"])):
            self.make_repo(bad)
            self.assertEqual(qcore.live_state(repo), "off")
            with self.assertRaises(qcore.Refused):
                qcore.check_root(live, repo=repo)

    def test_releases_with_switch_on(self):
        repo = self.make_repo(json.dumps({"_what": "temp", "live": "on"}))
        live = repo / "runs" / "queue"
        self.assertEqual(qcore.live_state(repo), "on")
        self.assertEqual(qcore.check_root(live, repo=repo), live.resolve())
        with mock.patch.dict(os.environ, {"AI_WORKSPACE": str(repo)}):
            code, out, err = call(["rebuild", "--root", str(live), "--now", "2026-10-22T03:00:00Z", "--no-commit"])
        self.assertEqual(code, 0, err)
        self.assertTrue((live / "index.json").is_file())

    def test_shadow_and_temp_roots_are_never_refused(self):
        repo = self.make_repo(json.dumps({"live": "off"}))
        self.assertEqual(qcore.check_root(qcore.shadow_root(repo), repo=repo), (repo / "runs" / "queue-shadow").resolve())
        self.assertEqual(qcore.check_root(self.root, repo=repo), self.root.resolve())


class CommitPaths(Temp):
    def test_add_commit_by_path_push(self):
        fake = FakeGit()
        sha = qcore.commit_paths([self.root / "a.jsonl", self.root / "index.json"], "msg", self.tmp, run=fake)
        self.assertEqual(sha, "abc123")
        self.assertEqual(fake.calls, [
            ["git", "add", "--", "root/a.jsonl", "root/index.json"],
            ["git", "commit", "-m", "msg", "--", "root/a.jsonl", "root/index.json"],
            ["git", "push"],
            ["git", "rev-parse", "HEAD"]])

    def test_rejected_push_pulls_no_rebase_then_pushes(self):
        fake = FakeGit(push_fails=1)
        self.assertEqual(qcore.commit_paths(["x"], "msg", self.tmp, run=fake), "abc123")
        self.assertEqual(fake.subs(), ["add", "commit", "push", "pull --no-rebase", "push", "rev-parse"])

    def test_three_rejected_pushes_raise_naming_push(self):
        fake = FakeGit(push_fails=5)
        with self.assertRaises(RuntimeError) as cm:
            qcore.commit_paths(["x"], "msg", self.tmp, run=fake)
        self.assertIn("git push", str(cm.exception))
        self.assertEqual(fake.subs(), ["add", "commit", "push", "pull --no-rebase", "push", "pull --no-rebase", "push"])

    def test_failed_step_is_named(self):
        for step, word in (("add", "git add"), ("commit", "git commit"), ("rev-parse", "git rev-parse")):
            with self.assertRaises(RuntimeError) as cm:
                qcore.commit_paths(["x"], "msg", self.tmp, run=FakeGit(fail=step))
            self.assertIn(word, str(cm.exception))
        fake = FakeGit(push_fails=1, fail="pull")
        with self.assertRaises(RuntimeError) as cm:
            qcore.commit_paths(["x"], "msg", self.tmp, run=fake)
        self.assertIn("git pull --no-rebase", str(cm.exception))
        self.assertNotIn("rev-parse", fake.subs())


class WriteObservation(Temp):
    def test_none_when_unchanged(self):
        entries = {"q1": {"title": "One", "observed_stage": "making"}}
        p = qcore.write_observation(self.root, "mac", entries, now="2026-10-22T02:00:00Z")
        self.assertEqual(p, self.root / "observations" / "mac.json")
        self.assertIsNone(qcore.write_observation(self.root, "mac", json.loads(json.dumps(entries)),
                                                  now="2026-10-22T02:30:00Z"))
        self.assertEqual(json.loads(p.read_text())["as_of"], "2026-10-22T02:00:00Z")   # untouched
        entries["q1"]["execution"] = "done"
        self.assertEqual(qcore.write_observation(self.root, "mac", entries, now="2026-10-22T02:45:00Z"), p)
        self.assertEqual(json.loads(p.read_text())["as_of"], "2026-10-22T02:45:00Z")
        obs, decs = qcore.load(self.root)
        self.assertEqual((list(obs), decs), (["mac"], []))
        with self.assertRaises(ValueError):
            qcore.write_observation(self.root, "mac", {"q1": {"execution": "maybe"}})
        with self.assertRaises(ValueError):
            qcore.write_observation(self.root, "Mac Book", entries)


if __name__ == "__main__":
    unittest.main()
