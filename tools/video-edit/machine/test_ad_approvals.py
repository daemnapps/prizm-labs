#!/usr/bin/env python3
"""AR-1 (shared ad approvals) as reworked by AR-1b (approvals as verdicts): an Ad Runs OK is an `approve` verdict
on the ad's review request (lane ad-runs). The one reader, the approve CLI, the board's button, the runner's
re-check and the readers, checked with REAL git in temp folders — a bare origin and two clones, no network, never
a fake git.

    /usr/bin/python3 tools/video-edit/machine/test_ad_approvals.py

The lab files under test (serve.py, approve.py, line_runner.py, versions.py) are loaded by path; the old jsonl
parsers are kept below, verbatim in logic, as the reference the repointed readers must still agree with.
"""
import contextlib
import datetime
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
LAB = REPO / "lab" / "owner" / "ad-runs"
sys.path.insert(0, str(HERE))
import ad_approvals as A  # noqa: E402
import line as L          # noqa: E402

RR = A.RR


def lab(name, alias):
    spec = importlib.util.spec_from_file_location(alias, str(LAB / (name + ".py")))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)
    return mod


S = lab("serve", "serve")                  # approve.py imports it as `serve`: one module, one set of globals
AP = lab("approve", "lab_ad_approve")
LR = lab("line_runner", "lab_ad_line_runner")
V = lab("versions", "lab_ad_versions")     # not `versions`: the component has its own versions.py

BRAND = "testbrand"
WAIT_PROD = "ad-brief-01"    # brief written, nothing made: waiting for the production OK
WAIT_FINAL = "ad-cut-02"     # made, with a control cut: waiting for the final OK
REQ_AT = {(WAIT_PROD, "production"): "2026-10-17T04:00:00Z", (WAIT_FINAL, "final"): "2026-10-17T04:00:01Z"}
ENV_KEYS = ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM", "GIT_TERMINAL_PROMPT")
_saved_env = {}
_scratch = None


def setUpModule():
    global _scratch
    _scratch = Path(tempfile.mkdtemp()).resolve()
    (_scratch / "gitconfig").write_text("")
    for k in ENV_KEYS:
        _saved_env[k] = os.environ.get(k)
    os.environ.update(GIT_CONFIG_GLOBAL=str(_scratch / "gitconfig"), GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0")


def tearDownModule():
    for k, v in _saved_env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    shutil.rmtree(str(_scratch), ignore_errors=True)


def git(cwd, *args):
    r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError("git %s failed in %s: %s" % (" ".join(args), cwd, r.stderr))
    return r.stdout.strip()


def quiet(fn, *a, **kw):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        got = fn(*a, **kw)
    return got, out.getvalue()


def write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


def open_request(root, ad, step, created, lane=A.LANE, commit=True):
    """The request the board opens for an ad waiting at a step (AR-2 (ad board snapshot)'s act, done by hand)."""
    return RR.file_request(A.asset_for(ad, step), "link", ["owner"], lane, "owner", root=root, env={},
                           now=created, commit=commit)["item"]


def verdict(root, item, who, word, created, note=""):
    v = {"event": "verdict", "verdict": word}
    if note:
        v["note"] = note
    return RR.file_record(item, v, who, root=root, env={}, now=created, commit=False)


def stage_board(root):
    """Two ads on one batch: WAIT_PROD waits for the production OK, WAIT_FINAL for the final OK."""
    stages = {k: {"status": "done"} for k, _, _ in S.TEARDOWN_STEPS + S.WRITING_STEPS}
    for ad in (WAIT_PROD, WAIT_FINAL):
        write(root / "runs/video-teardown/_work" / ad / "run.json", json.dumps({"brand": BRAND, "stages": stages}))
        write(root / "runs/video-teardown/_work" / ad / "stages/5-brief.md", "# a brief\n")
    write(root / "runs/video-production" / BRAND / (WAIT_FINAL + "-prod") / "run.json", json.dumps({"label": WAIT_FINAL}))
    write(root / "runs/video-edit" / BRAND / (WAIT_FINAL + "-edit") / "renders/control.mp4", "")
    write(root / "runs/ad-runs/batches.json", json.dumps({"batches": [{
        "id": "b1", "name": "test", "brand": BRAND, "product": "p",
        "items": [{"id": WAIT_PROD, "kind": "video", "hook": "h"}, {"id": WAIT_FINAL, "kind": "video", "hook": "h"}]}]}))


class World(unittest.TestCase):
    """A bare origin holding the approver lists and the two open requests, and two clones of it, each with its
    own git user."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.origin = self.tmp / "origin.git"
        git(self.tmp, "init", "-q", "--bare", "-b", "main", str(self.origin))
        seed = self.tmp / "seed"
        git(self.tmp, "init", "-q", "-b", "main", str(seed))
        self.user(seed, "seed@example.com")
        write(seed / A.APPROVERS, json.dumps({"production": ["*"], "final": ["*"]}) + "\n")
        for who in ("editor-a", "editor-b"):    # each clone's address names its person by identity file (LD-77)
            write(seed / "team/people" / who / "identity.json",
                  json.dumps({"person": who, "emails": [{"address": who + "@example.com"}]}) + "\n")
        git(seed, "add", "-A")
        git(seed, "commit", "-q", "-m", "seed")
        self.req = {k: open_request(seed, k[0], k[1], at) for k, at in REQ_AT.items()}
        git(seed, "remote", "add", "origin", str(self.origin))
        git(seed, "push", "-q", "origin", "main")
        self.a = self.clone("a", "editor-a@example.com")
        self.b = self.clone("b", "editor-b@example.com")
        self.keep = (S.REPO, LR.REPO, LR.RUNS, LR.JOBS, LR.JOBDIR, LR.RESTARTS, LR.start_job, LR.run_versions,
                     V.REPO, V.RUNS, V.DONE, V.LOG, L.REPO)
        self.keep_people, A.REPO = A.REPO, self.a    # lab callers ask person_of(email) of REPO's team/people

    def tearDown(self):
        A.REPO = self.keep_people
        S.at_repo(self.keep[0])
        (LR.REPO, LR.RUNS, LR.JOBS, LR.JOBDIR, LR.RESTARTS, LR.start_job, LR.run_versions,
         V.REPO, V.RUNS, V.DONE, V.LOG, L.REPO) = self.keep[1:]
        for c in (self.a, self.b):
            self.assertFalse((c / ".git" / "MERGE_HEAD").exists(), c)
            self.assertFalse((c / ".git" / "rebase-merge").exists(), c)
            self.assertFalse((c / ".git" / "rebase-apply").exists(), c)
        shutil.rmtree(str(self.tmp), ignore_errors=True)

    def user(self, repo, email):
        git(repo, "config", "user.email", email)
        git(repo, "config", "user.name", email.split("@")[0])

    def clone(self, name, email):
        c = self.tmp / name
        git(self.tmp, "clone", "-q", str(self.origin), str(c))
        self.user(c, email)
        stage_board(c)                                   # the runs a clone sees (untracked, as in life)
        return c

    def approve(self, repo, *argv):
        return quiet(AP.main, list(argv), repo=repo)

    def records_here(self, repo):
        """Review records in the clone's working tree that git does not hold yet."""
        return git(repo, "status", "--porcelain", "--untracked-files=all", "--", RR.RECORDS_REL)

    def origin_verdicts(self):
        git(self.a, "fetch", "-q", "origin")
        out = []
        for name in git(self.a, "ls-tree", "--name-only", "origin/main", "--", RR.RECORDS_REL + "/").splitlines():
            rec = json.loads(git(self.a, "show", "origin/main:" + name))
            if rec["verdict"]["event"] == "verdict":
                out.append(rec)
        return out

    def runner_on(self, repo):
        started = []
        LR.REPO, LR.RUNS = repo, repo / "runs"
        LR.JOBS, LR.JOBDIR = repo / "runs/ad-runs/jobs.json", repo / "runs/ad-runs/jobs"
        LR.RESTARTS = repo / "runs/ad-runs/restart.jsonl"                    # his Restart asks, this clone's
        LR.start_job = lambda key, prompt: started.append(key) or {"pid": None, "dir": key, "state": "running"}
        LR.run_versions = lambda: None
        return started


# ---------------------------------------------------------------- the one reader
class Reader(World):
    def test_a_verdict_pushed_from_another_clone_is_seen_after_fetch_and_not_before(self):
        out = A.give(self.b, WAIT_PROD, "production", "editor-b", "go")             # commits its one path
        self.assertTrue(out["committed"])
        git(self.b, "push", "-q", "origin", "main")
        self.assertNotIn(WAIT_PROD, A.load(self.a, include_remote=True))           # not fetched yet
        git(self.a, "fetch", "-q", "origin")
        rec = A.load(self.a, include_remote=True)[WAIT_PROD]["production"]
        self.assertEqual((rec["id"], rec["step"], rec["approved_by"], rec["note"], rec["item"]),
                         (WAIT_PROD, "production", "editor-b", "go", self.req[(WAIT_PROD, "production")]))
        self.assertNotIn(WAIT_PROD, A.load(self.a, include_remote=False))          # local only: still not here
        self.assertEqual(self.records_here(self.a), "")                             # seen without a pull

    def test_the_ok_is_the_latest_approve_on_a_lane_ad_runs_request_naming_ad_and_step(self):
        r = self.a
        item = self.req[(WAIT_FINAL, "final")]
        verdict(r, item, "pm", "reject", "2026-10-17T05:00:00Z")
        self.assertNotIn(WAIT_FINAL, A.load(r, include_remote=False))              # a reject is not an OK
        verdict(r, item, "pm", "approve", "2026-10-17T05:00:01Z", note="first")
        verdict(r, item, "the team", "approve", "2026-10-17T05:00:02Z", note="second")
        got = A.load(r, include_remote=False)[WAIT_FINAL]["final"]
        self.assertEqual((got["approved_by"], got["note"], got["at"]), ("the team", "second", "2026-10-17T05:00:02Z"))
        verdict(r, item, "the team", "fix", "2026-10-17T05:00:03Z")               # her last word is no longer approve
        self.assertEqual(A.load(r, include_remote=False)[WAIT_FINAL]["final"]["approved_by"], "pm")
        RR.file_record(item, {"event": "close", "decision": "accepted"}, "owner", root=r, env={},
                       now="2026-10-17T05:00:04Z", commit=False)
        self.assertIn("final", A.load(r, include_remote=False)[WAIT_FINAL])        # open or closed, the OK stands
        # an approve on another lane, or on a request naming another step, is no OK for this one
        other = open_request(r, WAIT_PROD, "production", "2026-10-17T05:01:00Z", lane="static-ads", commit=False)
        verdict(r, other, "pm", "approve", "2026-10-17T05:01:01Z")
        verdict(r, self.req[(WAIT_PROD, "production")], "pm", "approve", "2026-10-17T05:01:02Z")
        self.assertEqual(set(A.load(r, include_remote=False)[WAIT_PROD]), {"production"})
        self.assertEqual(A.load(r, include_remote=False)[WAIT_PROD]["production"]["item"],
                         self.req[(WAIT_PROD, "production")])

    def test_the_old_per_ok_files_are_not_an_ok(self):
        write(self.a / "runs/ad-runs/approvals" / (WAIT_FINAL + "--final.json"),
              json.dumps({"id": WAIT_FINAL, "step": "final", "approved_by": "x@example.com", "at": "2026-10-17T04:30:00Z"}))
        self.assertEqual(A.load(self.a), {})

    def test_jsonl_seed_still_read_and_never_written(self):
        seed = write(self.a / A.LEGACY, "\n".join([
            json.dumps({"id": "old-1", "step": "production", "approved_by": "owner", "at": "2026-10-15T10:00:00"}),
            json.dumps({"id": "old-1", "approved_by": "owner"}),               # no step = final
            "not json",
            json.dumps({"step": "final"}),                                      # no id: skipped
        ]) + "\n")
        before = seed.read_bytes()
        verdict(self.a, self.req[(WAIT_FINAL, "final")], "editor-a", "approve", "2026-10-17T05:00:00Z")
        ok = A.load(self.a)
        self.assertEqual(set(ok["old-1"]), {"production", "final"})
        self.assertEqual(ok[WAIT_FINAL]["final"]["approved_by"], "editor-a")
        self.assertEqual(seed.read_bytes(), before)

    def test_give_needs_an_open_request_and_a_person(self):
        with self.assertRaises(LookupError):
            A.give(self.a, "ad-nowhere-9", "final", "editor-a")
        with self.assertRaises(A.Refused):
            A.give(self.a, WAIT_FINAL, "final", "Not A Person", commit=False)
        self.assertEqual(self.records_here(self.a), "")
        for bad in (("../x", "final"), (WAIT_PROD, "launch")):
            with self.assertRaises(ValueError):
                A.asset_for(*bad)
        self.assertEqual(A.names(A.asset_for(WAIT_PROD, "final")), (WAIT_PROD, "final"))
        self.assertIsNone(A.names({"warehouse": "url", "ref": "https://example.com/x", "title": "t"}))


# ---------------------------------------------------------------- who may approve
class Approvers(World):
    def lists(self, d):
        write(self.a / A.APPROVERS, json.dumps(d))

    def test_star_admits_anyone(self):
        for email in ("editor-a@example.com", "new.person@example.org"):
            for step in A.STEPS:
                self.assertEqual(A.may_approve(self.a, email, step), (True, ""))

    def test_off_list_refused_and_per_step(self):
        self.lists({"production": ["Boss@Example.com"], "final": ["*"]})
        self.assertTrue(A.may_approve(self.a, "boss@example.com", "production")[0])     # case-blind
        ok, why = A.may_approve(self.a, "editor-a@example.com", "production")
        self.assertFalse(ok)
        self.assertIn("not on the production list", why)
        self.assertTrue(A.may_approve(self.a, "editor-a@example.com", "final")[0])
        self.lists({"production": ["*"], "final": ["boss@example.com"]})
        self.assertFalse(A.may_approve(self.a, "editor-a@example.com", "final")[0])     # read on every call

    def test_no_email_no_list_or_no_file_refused(self):
        self.assertFalse(A.may_approve(self.a, "", "final")[0])
        self.lists({"production": ["*"]})
        self.assertIn("no list for the final step", A.may_approve(self.a, "x@example.com", "final")[1])
        (self.a / A.APPROVERS).unlink()
        self.assertIn("cannot read", A.may_approve(self.a, "x@example.com", "final")[1])

    def test_person_of_is_the_identity_file_or_nothing(self):
        """Narrowed to intent by LD-77 (one person resolver): the identity file names the person, case-blind;
        an address it does not list is nobody, whatever its local part."""
        self.assertEqual(A.person_of("Editor-A@Example.com", self.a), "editor-a")
        self.assertEqual(A.person_of("editor-a@elsewhere.org", self.a), "")
        self.assertEqual(A.person_of("new.person@example.org", self.a), "")
        self.assertEqual(A.person_of("", self.a), "")


# ---------------------------------------------------------------- approve.py
class ApproveCli(World):
    def test_not_waiting_is_refused_and_writes_nothing(self):
        head = git(self.a, "rev-parse", "HEAD")
        for ad, step, word in ((WAIT_PROD, "final", "no finished cut"), (WAIT_FINAL, "production", "not waiting"),
                               ("ad-nowhere-9", "final", "no ad with that id")):
            got, text = self.approve(self.a, ad, step)
            self.assertEqual(got, 2, text)
            self.assertIn(word, text)
        self.assertEqual(self.records_here(self.a), "")
        self.assertEqual(git(self.a, "rev-parse", "HEAD"), head)

    def test_off_list_is_refused_by_the_cli(self):
        write(self.a / A.APPROVERS, json.dumps({"production": ["boss@example.com"], "final": ["*"]}))
        got, text = self.approve(self.a, WAIT_PROD, "production")
        self.assertEqual(got, 2, text)
        self.assertIn("editor-a@example.com is not on the production list", text)
        self.assertEqual(self.records_here(self.a), "")

    def test_an_email_that_names_no_person_is_refused(self):
        self.user(self.a, "first.last@example.com")
        got, text = self.approve(self.a, WAIT_FINAL, "final")
        self.assertEqual(got, 2, text)
        self.assertIn("not a person id", text)
        self.assertEqual(self.records_here(self.a), "")

    def test_no_open_request_is_refused(self):
        write(self.a / "runs/video-production" / BRAND / (WAIT_PROD + "-prod") / "run.json", json.dumps({"label": WAIT_PROD}))
        write(self.a / "runs/video-edit" / BRAND / (WAIT_PROD + "-edit") / "renders/control.mp4", "")
        got, text = self.approve(self.a, WAIT_PROD, "final")      # waiting now, but the board opened no request
        self.assertEqual(got, 2, text)
        self.assertIn("no open ad-runs review request", text)
        self.assertEqual(self.records_here(self.a), "")

    def test_dry_run_checks_and_writes_nothing(self):
        head = git(self.a, "rev-parse", "HEAD")
        got, text = self.approve(self.a, WAIT_FINAL, "final", "--dry-run")
        self.assertEqual(got, 0, text)
        self.assertIn("nothing written", text)
        self.assertIn(self.req[(WAIT_FINAL, "final")], text)
        self.assertEqual(self.records_here(self.a), "")
        self.assertEqual(git(self.a, "rev-parse", "HEAD"), head)
        got, text = self.approve(self.a, WAIT_PROD, "final", "--dry-run")      # still checks (a)
        self.assertEqual(got, 2, text)

    def test_ok_is_a_verdict_committed_pushed_and_the_runner_on_the_other_clone_starts_it(self):
        write(self.b / "notes.md", "someone else's work\n")                    # origin moves on first
        git(self.b, "add", "notes.md")
        git(self.b, "commit", "-q", "-m", "unrelated")
        git(self.b, "push", "-q", "origin", "main")
        write(self.a / "scratch.md", "uncommitted, untouched\n")               # a teammate's dirty clone
        got, text = self.approve(self.a, WAIT_PROD, "production", "--note", "looks right")
        self.assertEqual(got, 0, text)
        self.assertIn("pushed to origin/main", text)
        [v] = self.origin_verdicts()
        self.assertEqual((v["item"], v["reviewer"], v["verdict"]),
                         (self.req[(WAIT_PROD, "production")], "editor-a",
                          {"event": "verdict", "verdict": "approve", "note": "looks right"}))
        self.assertEqual(self.records_here(self.a), "")                        # committed, nothing left over
        touched = git(self.a, "show", "--name-only", "--format=", "HEAD").splitlines()
        self.assertEqual(touched, [RR.RECORDS_REL + "/" + RR.filename(v)])     # one path
        self.assertTrue((self.a / "scratch.md").is_file())
        # the owner's side: clone b, never pulled — its runner fetches, re-checks and starts the job
        started = self.runner_on(self.b)
        quiet(LR.one_pass)
        self.assertEqual(started, ["production-" + WAIT_PROD])
        self.assertNotIn(RR.filename(v), [p.name for p in (self.b / RR.RECORDS_REL).iterdir()])  # seen without a pull
        # given once: the same OK from clone b is refused — the board there now says production is done
        got, text = self.approve(self.b, WAIT_PROD, "production")
        self.assertEqual(got, 2, text)
        self.assertIn("not waiting for a production OK", text)

    def test_two_clones_cannot_both_give_the_final_ok(self):
        got, text = self.approve(self.a, WAIT_FINAL, "final")
        self.assertEqual(got, 0, text)
        got, text = self.approve(self.b, WAIT_FINAL, "final")
        self.assertEqual(got, 2, text)
        self.assertIn("no finished cut waiting", text)
        self.assertEqual([v["reviewer"] for v in self.origin_verdicts()], ["editor-a"])

    def test_a_clone_off_main_is_refused_before_writing(self):
        git(self.a, "checkout", "-q", "-b", "side")
        got, text = self.approve(self.a, WAIT_PROD, "production")
        self.assertEqual(got, 2, text)
        self.assertIn("switch to main", text)
        self.assertEqual(self.records_here(self.a), "")


# ---------------------------------------------------------------- serve.py's button and mirror
class Board(World):
    def post(self, body, mirror=None, route="/api/approve"):
        from http.server import ThreadingHTTPServer
        import threading
        import urllib.request
        import urllib.error
        S.at_repo(self.a)
        S.MIRROR = mirror
        srv = ThreadingHTTPServer(("127.0.0.1", 0), S.H)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            req = urllib.request.Request("http://127.0.0.1:%d%s" % (srv.server_address[1], route),
                                         data=json.dumps(body).encode(), method="POST")
            direct = urllib.request.build_opener(urllib.request.ProxyHandler({}))     # never through a proxy
            try:
                with direct.open(req, timeout=30) as r:
                    return r.status, json.loads(r.read())
            except urllib.error.HTTPError as e:
                with e:
                    return e.code, json.loads(e.read())
        finally:
            srv.shutdown()
            srv.server_close()
            S.MIRROR = None

    def test_button_files_the_verdict_named_by_this_clones_address_uncommitted(self):
        head = git(self.a, "rev-parse", "HEAD")
        self.assertEqual(self.post({"id": WAIT_FINAL, "step": "final"}), (200, {"ok": True}))
        rec = A.load(self.a, include_remote=False)[WAIT_FINAL]["final"]
        self.assertEqual((rec["approved_by"], rec["item"]), ("editor-a", self.req[(WAIT_FINAL, "final")]))
        self.assertEqual(git(self.a, "rev-parse", "HEAD"), head)                 # written, not committed
        self.assertNotEqual(self.records_here(self.a), "")
        code, body = self.post({"id": WAIT_FINAL, "step": "final"})
        self.assertEqual(code, 409, body)                                       # the board's rule, unchanged
        self.assertEqual(self.post({"id": "ad-nowhere-9"})[0], 404)

    def test_button_honours_the_approver_list(self):
        write(self.a / A.APPROVERS, json.dumps({"production": ["*"], "final": ["boss@example.com"]}))
        code, body = self.post({"id": WAIT_FINAL, "step": "final"})
        self.assertEqual(code, 403, body)
        self.assertEqual(self.records_here(self.a), "")

    @unittest.skip("serve.py's --mirror was removed by its owner in 91814ff66f (2026-10-17); the mini copy retires with the dashboard route — restore this test if --mirror returns")
    def test_mirror_refuses_and_says_view_only(self):
        code, body = self.post({"id": WAIT_FINAL, "step": "final"}, mirror="the mini")
        self.assertEqual(code, 403)
        self.assertIn("view only — approve in your own Claude", body["error"])
        self.assertEqual(self.records_here(self.a), "")
        for route in ("/api/drop", "/api/undrop", "/api/restart"):              # his marks: refused there too
            self.assertEqual(self.post({"id": WAIT_FINAL}, mirror="the mini", route=route)[0], 403, route)
        self.assertFalse((self.a / "runs/ad-runs/dropped.jsonl").exists())
        self.assertFalse((self.a / "runs/ad-runs/restart.jsonl").exists())

    def test_drop_still_takes_an_ad_out_of_the_queue_at_the_button(self):
        self.assertEqual(self.post({"id": WAIT_FINAL}, route="/api/drop"), (200, {"ok": True, "ids": [WAIT_FINAL]}))
        code, body = self.post({"id": WAIT_FINAL, "step": "final"})
        self.assertEqual(code, 409, body)
        self.assertEqual(self.records_here(self.a), "")


# ---------------------------------------------------------------- the runner re-checks before it acts
class Recheck(World):
    def test_a_stale_production_ok_is_refused_logged_and_never_acted_on(self):
        write(self.a / A.LEGACY, "\n".join(json.dumps(x) for x in (
            {"id": WAIT_FINAL, "step": "production", "approved_by": "owner"},   # production already made
            {"id": "ad-gone-7", "step": "production", "approved_by": "owner"},  # not on the board at all
        )) + "\n")
        verdict(self.a, self.req[(WAIT_PROD, "production")], "editor-a", "approve", "2026-10-17T05:00:00Z")
        started = self.runner_on(self.a)
        _, text = quiet(LR.one_pass)
        self.assertEqual(started, ["production-" + WAIT_PROD])               # the live OK, and only it
        self.assertIn("stale OK refused, not acted on: production for %s" % WAIT_FINAL, text)
        self.assertIn("stale OK refused, not acted on: production for ad-gone-7 — no ad with that id", text)
        self.assertEqual(sorted(json.loads(LR.JOBS.read_text())), ["production-" + WAIT_PROD])

    def test_a_retry_of_a_job_already_started_is_not_a_new_act(self):
        write(self.a / A.LEGACY, json.dumps({"id": WAIT_FINAL, "step": "production", "approved_by": "owner"}) + "\n")
        started = self.runner_on(self.a)
        write(LR.JOBS, json.dumps({"production-" + WAIT_FINAL: {"state": "waiting-usage", "retry_at": 0}}))
        _, text = quiet(LR.one_pass)
        self.assertEqual(started, ["production-" + WAIT_FINAL])
        self.assertNotIn("stale", text)

    def test_versions_refuses_a_stale_final_ok_and_makes_the_live_one(self):
        write(self.a / "runs/video-production" / BRAND / "old-ad-5-prod" / "run.json", json.dumps({"label": "old-ad-5"}))
        write(self.a / A.LEGACY, json.dumps({"id": "old-ad-5", "approved_by": "owner"}) + "\n")   # off the board
        verdict(self.a, self.req[(WAIT_FINAL, "final")], "editor-a", "approve", "2026-10-17T05:00:00Z")
        V.REPO, V.RUNS = self.a, self.a / "runs"
        V.DONE, V.LOG = self.a / "runs/ad-runs/versions-done.json", self.a / "runs/ad-runs/versions.log"
        _, text = quiet(V.main, ["--dry-run", "--no-fetch"])
        self.assertEqual([l.split()[1] for l in text.splitlines() if l.startswith("versions:")], [WAIT_FINAL])
        self.assertIn("stale OK refused, not acted on: final for old-ad-5 — no ad with that id", text)

    def test_line_reads_the_final_verdict(self):
        L.REPO = self.a
        self.assertFalse(L.approved({"label": WAIT_FINAL}, None))
        verdict(self.a, self.req[(WAIT_PROD, "production")], "editor-a", "approve", "2026-10-17T05:00:00Z")
        self.assertFalse(L.approved({"label": WAIT_PROD}, None))                # a production OK is not the final
        verdict(self.a, self.req[(WAIT_FINAL, "final")], "editor-a", "approve", "2026-10-17T05:00:01Z")
        self.assertTrue(L.approved({"label": WAIT_FINAL}, None))


# ---------------------------------------------------------------- the owner's 17 Oct rules meet the verdicts
class HisRules(World):
    """Drop / Undo, the old-week rule and a Restart ask (2ceb95d990) decide whether an ad is waiting; the verdict
    is only where an OK comes from. A verdict for an ad his rules took out of the queue is a stale OK."""

    def mark(self, name, rec):
        f = self.a / "runs/ad-runs" / name
        with f.open("a") as fh:
            fh.write(json.dumps(rec) + "\n")

    def test_a_verdict_on_a_dropped_ad_is_refused_until_he_undoes_the_drop(self):
        self.mark("dropped.jsonl", {"id": WAIT_PROD, "at": "2026-10-17T06:00:00", "by": "owner"})
        verdict(self.a, self.req[(WAIT_PROD, "production")], "editor-a", "approve", "2026-10-17T06:00:01Z")
        started = self.runner_on(self.a)
        _, text = quiet(LR.one_pass)
        self.assertEqual(started, [])
        self.assertIn("stale OK refused, not acted on: production for %s" % WAIT_PROD, text)
        got, said = self.approve(self.a, WAIT_PROD, "production", "--dry-run")
        self.assertEqual(got, 2, said)
        self.assertIn("not waiting for a production OK", said)
        self.mark("dropped.jsonl", {"id": WAIT_PROD, "at": "2026-10-17T06:01:00", "by": "owner", "undo": True})
        quiet(LR.one_pass)
        self.assertEqual(started, ["production-" + WAIT_PROD])                  # the same verdict, live again

    def test_a_verdict_on_an_old_ad_is_refused_until_he_asks_for_a_restart(self):
        old = "ad-old-11"
        opened = (datetime.date.today() - datetime.timedelta(days=21)).isoformat()
        stages = {k: {"status": "done"} for k, _, _ in S.TEARDOWN_STEPS + S.WRITING_STEPS}
        write(self.a / "runs/video-teardown/_work" / old / "run.json",
              json.dumps({"brand": BRAND, "stages": stages, "opened": opened}))
        write(self.a / "runs/video-teardown/_work" / old / "stages/5-brief.md", "# a brief\n")
        item = open_request(self.a, old, "production", "2026-10-17T06:00:00Z", commit=False)
        verdict(self.a, item, "editor-a", "approve", "2026-10-17T06:00:01Z")
        started = self.runner_on(self.a)
        _, text = quiet(LR.one_pass)
        self.assertEqual(started, [])
        self.assertIn("stale OK refused, not acted on: production for %s" % old, text)
        self.assertIn("Old · restart to go ahead", text)
        # his Restart on an old ad: back into the approval queue (no job of its own), and the OK now stands
        self.mark("restart.jsonl", {"id": old, "at": "2026-10-17T06:02:00", "by": "owner", "kind": "video",
                                    "what": "back into the approval queue", "from_step": ""})
        quiet(LR.one_pass)
        self.assertEqual(started, ["production-" + old])

    def test_restart_asks_run_with_no_ok_anywhere(self):
        self.mark("restart.jsonl", {"id": WAIT_PROD, "at": "2026-10-17T06:00:00", "by": "owner", "kind": "video",
                                    "from_step": "3"})
        started = self.runner_on(self.a)
        self.assertEqual(A.load(self.a), {})
        quiet(LR.one_pass)
        jobs = json.loads(LR.JOBS.read_text())
        [key] = jobs
        self.assertTrue(key.startswith("restart-%s-" % WAIT_PROD), key)
        self.assertIn("Can't restart by itself", jobs[key]["said"])              # no source video in a test clone
        self.assertEqual(started, [])


# ---------------------------------------------------------------- the readers, jsonl only
def old_serve_approvals(f):
    out = {}
    if f.is_file():
        for line in f.read_text().splitlines():
            try:
                r = json.loads(line)
                out.setdefault(r["id"], {})[r.get("step") or "final"] = r
            except Exception:
                pass
    return out


def old_line_approved(f, rj, brief):
    if not f.is_file():
        return False
    keys = {k for k in (brief, rj.get("label"), rj.get("brief")) if k}
    src = str(rj.get("source_brief") or rj.get("brief_from") or "")
    for line in f.read_text().splitlines():
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if (rec.get("step") or "final") != "final":
            continue
        i = rec.get("id", "")
        if i and (i in keys or (len(i) > 5 and i in src) or any(i.endswith(k) or k.endswith(i) for k in keys)):
            return True
    return False


SEED = [
    {"id": "nobrief-1", "step": "production", "approved_by": "owner"},
    {"id": "brand_prod_brief-0007", "step": "production", "approved_by": "owner"},
    {"id": "brand_prod_brief-0007", "approved_by": "owner", "note": "no step = final"},
    "not json",
    {"step": "final", "approved_by": "owner"},
    {"id": "brief-0009", "step": "final", "approved_by": "owner"},
    {"id": "later-3", "step": "production", "approved_by": "owner"},
    {"id": "brief-0009", "step": "final", "approved_by": "owner", "note": "the later line wins"},
    {"id": "prod-only-4", "step": "production", "approved_by": "owner"},
]


class Readers(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.r = self.tmp / "repo"
        git(self.tmp, "init", "-q", "-b", "main", str(self.r))                 # a clone with no origin
        self.f = write(self.r / A.LEGACY, "\n".join(x if isinstance(x, str) else json.dumps(x) for x in SEED) + "\n")
        self.before = self.f.read_bytes()
        self.keep = (S.REPO, L.REPO)

    def tearDown(self):
        S.at_repo(self.keep[0])
        L.REPO = self.keep[1]
        self.assertEqual(self.f.read_bytes(), self.before)                     # the seed is never written
        shutil.rmtree(str(self.tmp), ignore_errors=True)

    def test_serve_board_reader(self):
        S.at_repo(self.r)
        self.assertEqual(S.approvals(), old_serve_approvals(self.f))
        self.assertEqual(S.approvals()["brief-0009"]["final"]["note"], "the later line wins")

    def test_line_approved(self):
        L.REPO = self.r
        cases = [({"label": "brand_prod_brief-0007"}, None), ({"label": "x"}, "brief-0009"),
                 ({"label": "x", "source_brief": "runs/a/brief-0009/b.md"}, None), ({"label": "prod-only-4"}, None),
                 ({"label": "nothing-here"}, None), ({"label": "acme_brief-0009"}, None), ({}, "0007"), ({}, None)]
        got = [L.approved(rj, b) for rj, b in cases]
        self.assertEqual(got, [old_line_approved(self.f, rj, b) for rj, b in cases])
        self.assertEqual(got, [True, True, True, False, False, True, True, False])


if __name__ == "__main__":
    unittest.main()
