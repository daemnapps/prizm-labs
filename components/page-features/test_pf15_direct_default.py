#!/usr/bin/env python3
"""PF-15 (direct by default): every wired button of a page-features family has a run entry in its family's run table
(_templates/<family>.actions.json: `direct` with a kind, or `via_claude` with a written why), the going-live and
share checks refuse one without by number, and every button runs through the one component-owned kit/act.js.

    (a) a fixture family with a wired action and no run entry fails check_live and share by number
    (b) via claude without why fails; with why passes; a direct entry with no kind fails, with one passes
    (c) the four real families pass the run-entry rule at HEAD; each page's act.js block is kit/act.js byte for byte
    (d) act.js against a fake server, in node (a static check when node is absent): quick → the result line; job →
        polls /job/<id> to done; 428 → the server's confirm, then the same body with confirmed; Cancel runs nothing;
        409 is never retried or copied; a fetch failure → the request line is copied; unserved → copied, no fetch

Stdlib only, Python 3.9. Writes only in temp folders.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import features  # noqa: E402
import live  # noqa: E402
import share  # noqa: E402

REAL = features.ROOT
TPL = features.TEMPLATES
ACT_JS = os.path.join(HERE, "kit", "act.js")
FAMILIES = ["emails", "content-queue", "outlier-demo", "run-detail"]
FAM = "runfam"
PERSON = "fixp"
TEMPLATE = "%s/%s.html" % (TPL, FAM)
DRAFT = "%s/%s/drafts/%s--try.html" % (features.VIEWERS, PERSON, FAM)
NO_ENTRY = ("A31: wired button with no run entry — add it to runfam.actions.json direct, "
            "or via: claude with why")
NO_WHY = "A31: via: claude with no why — write why it is not direct in runfam.actions.json"
RULE_WORDS = ("run entry", "run entries", "via: claude", "via_claude", "run table")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def act_block(text):
    """The script inside a page's act.js block, or None."""
    span = live._act_span(text)
    if span is None:
        return None
    block = text[span[0]:span[1]]
    head = '<script id="pf-act">\n'
    return block[block.index(head) + len(head):block.rindex("</script>")]


DOC = {
    "title": "Run table fixture family", "owner": PERSON, "schema": 1, "schema_minor": 2, "status": "draft",
    "state_words": {"wired": "works today", "after-card": "needs a card", "not-built": "nothing yet"},
    "kinds": {
        "data": {"letter": "D", "name": "Data", "means": "a value saved in a data file"},
        "rule": {"letter": "R", "name": "Rule", "means": "the page works it out"},
        "media": {"letter": "M", "name": "Pictures", "means": "a picture"},
        "layout": {"letter": "L", "name": "Layout", "means": "arrangement"},
        "action": {"letter": "A", "name": "Action", "means": "a button that runs a component's own command"}},
    "page": TEMPLATE, "retired": [],
    "features": [
        {"n": 1, "name": "Navigation", "kind": "layout", "state": "wired", "status": "draft", "source": None,
         "anchor": "1"},
        {"n": 31, "name": "Move the part", "kind": "action", "state": "wired", "status": "draft",
         "source": {"component": "fixcomp", "file": "components/fixcomp/door.py run()", "field": "run"},
         "anchor": "31"},
        {"n": 32, "name": "Later button", "kind": "action", "state": "not-built", "status": "draft",
         "source": None},
    ]}


def page(act=True):
    block = ""
    if act:
        block = "%s\n<script id=\"pf-act\">\n%s</script>\n%s\n" % (live.ACT_START, read(ACT_JS), live.ACT_END)
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<title>runfam</title>\n'
            '<script type="application/json" id="fo-prefs">{"features": {}, "changes": []}</script>\n</head>\n'
            '<body>\n<nav data-feature="1">Navigation</nav>\n<button data-feature="31">Move</button>\n'
            + block +
            '<script>document.querySelector("button").onclick=()=>pfAct(31,{item:"a"},{family:"runfam"});</script>\n'
            '%s\n<script>/* the overlay */</script>\n%s\n</body>\n</html>\n' % (live.OVERLAY_START, live.OVERLAY_END))


class FakeGit(object):
    def __init__(self):
        self.calls = []

    def __call__(self, argv, cwd):
        self.calls.append(list(argv))
        return 0, "listed\n", ""


class Fixture(unittest.TestCase):
    """(a), (b) and the act.js block on a family made for the test."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="pf15-")
        self.addCleanup(shutil.rmtree, self.root, True)
        write(os.path.join(self.root, TPL, FAM + ".features.json"), features.dumps(DOC))
        write(os.path.join(self.root, TEMPLATE), page())
        write(os.path.join(self.root, DRAFT), page())

    def table(self, obj):
        write(os.path.join(self.root, TPL, FAM + ".actions.json"), json.dumps(obj))

    def live_lines(self):
        r = live.check_live(DRAFT, person=PERSON, root=self.root)
        self.assertIsNone(r["refused"], r)
        return r["failures"]

    def share_blockers(self, page_rel=TEMPLATE):
        r = share.share_check(page_rel, person=PERSON, root=self.root, runner=FakeGit(), scan=lambda t: [])
        self.assertIsNone(r["refused"], r)
        return r

    def rule_lines(self, lines):
        return [x for x in lines if any(w in x for w in RULE_WORDS)]

    # (a)
    def test_a_no_run_entry_fails_going_live_and_share_by_number(self):
        self.table({"direct": {}})
        lines = self.live_lines()
        self.assertIn(NO_ENTRY, lines)
        self.assertIn("A31: actions wait for PF-4 (page starter kit)'s router; act(n) is not built", lines)
        self.assertFalse([x for x in self.rule_lines(lines) if x.startswith("A32")], "a not-built button needs no entry")
        r = self.share_blockers()
        a31 = [b for b in r["blockers"] if b["tag"] == "A31" and "run entry" in b["what"]]
        self.assertEqual(len(a31), 1, r["blockers"])
        self.assertEqual((a31[0]["level"], a31[0]["hard"], a31[0]["owner"]), ("USE", True, PERSON))
        self.assertEqual("A31: " + a31[0]["what"], NO_ENTRY)
        self.assertIn("runfam.actions.json", a31[0]["fix"])
        self.assertEqual(r["use"], "blocked")
        self.assertIn("  " + NO_ENTRY, share.render(r))   # hard: template mode stops on it (PF-9c (share warns))

    def test_a_no_actions_file_still_fails_going_live(self):
        self.assertIn(NO_ENTRY, self.live_lines())

    # (b)
    def test_b_via_claude_needs_a_why(self):
        for entry in ({"via": "claude"}, {"via": "claude", "why": "  "}):
            self.table({"direct": {}, "via_claude": {"31": entry}})
            self.assertIn(NO_WHY, self.live_lines())
            self.assertIn(NO_WHY, ["%s: %s" % (b["tag"], b["what"]) for b in self.share_blockers()["blockers"]])
        self.table({"direct": {"31": {"via": "claude"}}})
        self.assertIn(NO_WHY, self.live_lines(), "via claude in direct is held to the same why")
        self.table({"via_claude": {"31": {"via": "claude", "why": "external send: the wall's go rule"}}})
        self.assertEqual(self.rule_lines(self.live_lines()), [])
        self.assertEqual(self.rule_lines(["%s: %s" % (b["tag"], b["what"])
                                          for b in self.share_blockers()["blockers"]]), [])
        self.table({"via_claude": {"31": {"why": "no via"}}})
        self.assertTrue(self.rule_lines(self.live_lines()), "a via_claude entry must say via: claude")

    def test_b_direct_entry_needs_a_kind(self):
        self.table({"direct": {"31": {"run": "cq", "verb": "set"}}})
        lines = self.live_lines()
        self.assertTrue([x for x in lines if x.startswith("A31: its run entry has no kind")], lines)
        for kind in live.RUN_KINDS:
            self.table({"direct": {"31": {"kind": kind, "run": "cq", "verb": "set"}}})
            lines = self.live_lines()
            self.assertEqual(self.rule_lines(lines), [], kind)
            self.assertFalse([x for x in lines if "router" in x], "a button with its run entry is routed")
            self.assertFalse([b for b in self.share_blockers()["blockers"] if b["tag"] == "A31" and b["hard"]])
        self.table({"direct": {"31": {"kind": "quick", "run": "cq"}},
                    "via_claude": {"31": {"via": "claude", "why": "both"}}})
        self.assertIn("A31: run entries in both direct and via_claude — keep one", self.live_lines())
        self.table({"direct": []})
        self.assertTrue([x for x in self.live_lines() if x.startswith("page: the run table")])
        self.assertTrue([b for b in self.share_blockers()["blockers"] if b["hard"] and "run table" in b["what"]])

    def test_act_block_is_component_owned(self):
        self.table({"direct": {"31": {"kind": "quick", "run": "cq"}}})
        self.assertFalse([x for x in self.live_lines() if "act.js" in x])
        write(os.path.join(self.root, DRAFT), page().replace("pfAct.poll = 3000", "pfAct.poll = 10"))
        self.assertIn("page: the act.js block was edited; it is component-owned", self.live_lines())
        write(os.path.join(self.root, DRAFT), page(act=False))
        self.assertTrue([x for x in self.live_lines() if x.startswith("page: the buttons call pfAct but the act.js")])
        text = live.transform(page())
        self.assertEqual(act_block(text), read(ACT_JS), "the live form keeps act.js")


class RealFamilies(unittest.TestCase):
    """(c) at HEAD, read-only."""

    def test_c_every_wired_button_has_a_run_entry(self):
        for fam in FAMILIES:
            doc = features.load(os.path.join(REAL, TPL, fam + ".features.json"))
            found = live.run_entry_findings(doc, fam, live.run_table(fam, REAL))
            self.assertEqual(found, [], (fam, [(e["n"], w) for e, w in found]))
            r = share.share_check("%s/%s.html" % (TPL, fam), root=REAL, runner=FakeGit(), scan=lambda t: [])
            self.assertIsNone(r["refused"], r)
            self.assertFalse([b for b in r["blockers"] if any(w in b["what"] for w in RULE_WORDS)], fam)

    def test_c_check_live_run_entry_rule_on_a_draft_of_each_template(self):
        for fam in FAMILIES:
            root = tempfile.mkdtemp(prefix="pf15-real-")
            self.addCleanup(shutil.rmtree, root, True)
            for ext in ("html", "features.json", "actions.json"):
                src = os.path.join(REAL, TPL, "%s.%s" % (fam, ext))
                if os.path.isfile(src):
                    write(os.path.join(root, TPL, "%s.%s" % (fam, ext)), read(src))
            draft = "%s/%s/drafts/%s--try.html" % (features.VIEWERS, PERSON, fam)
            write(os.path.join(root, draft), read(os.path.join(REAL, TPL, fam + ".html")))
            r = live.check_live(draft, person=PERSON, root=root)
            self.assertIsNone(r["refused"], r)
            bad = [x for x in r["failures"] if any(w in x for w in RULE_WORDS) or "router" in x or "act.js" in x]
            self.assertEqual(bad, [], fam)

    def test_c_the_real_tables(self):
        e = live.run_table("emails", REAL)
        self.assertEqual(e["57"], [("via_claude", {"via": "claude", "why": "external send: the wall takes email_lead's go as her "
                                                   "typed word to her own Claude; PF-13d (Go button) closed with no build, "
                                                   "email_lead 2026-11-02"})])
        o = live.run_table("outlier-demo", REAL)
        for n in ("25", "26", "55"):
            self.assertEqual(o[n][0][0], "via_claude")
            self.assertEqual(o[n][0][1]["why"], "no team component; waits for Outlier's backend (owner)")
        for n in ("14", "16", "17", "58", "59", "60"):
            self.assertEqual(o[n][0][1]["kind"], "quick")
        self.assertIsNone(live.run_table("run-detail", REAL), "run-detail has no wired button and no table")

    def test_c_each_page_carries_act_js_whole_and_calls_it(self):
        act = read(ACT_JS)
        self.assertNotIn("</script", act)
        self.assertNotIn("<!--", act)
        for fam, call in (("emails", "pfAct(n,b,{family:\"emails\""), ("emails", "pfUpload(f,id,{family:\"emails\"})"),
                          ("content-queue", "window.pfAct(body.n, body, {family: \"content-queue\""),
                          ("outlier-demo", "pfAct(n,{item,field,value:value??\"\"},{family:\"outlier-demo\"")):
            text = read(os.path.join(REAL, TPL, fam + ".html"))
            self.assertEqual(act_block(text), act, fam)
            self.assertIn(call, text)
            outside = text.replace(text[slice(*live._act_span(text))], "")
            self.assertNotIn('fetch("/act"', outside, "%s: no button calls the kit on its own" % fam)
            self.assertNotIn("X-Kit-Token", outside, fam)
        self.assertIsNone(live._act_span(read(os.path.join(REAL, TPL, "run-detail.html"))))


HARNESS = r"""
const fs = require("fs"), vm = require("vm");
const src = fs.readFileSync(process.argv[1], "utf8");
function el() {   // as the DOM: setting textContent drops the children; `seen` keeps every line ever shown
  let own = "";
  const e = {className: "", style: {}, kids: [], seen: [], value: "",
    appendChild(k) { this.kids.push(k); this.seen.push(k.textContent); }, select() {}, remove() {}};
  Object.defineProperty(e, "textContent", {get() { return own; }, set(v) { own = v; e.kids = []; }});
  Object.defineProperty(e, "text", {get() { return (own ? [own] : []).concat(e.kids.map(k => k.textContent)).join("|"); }});
  return e;
}
function answer(code, obj) { return {status: code, ok: code >= 200 && code < 300, json: async () => obj}; }
function page(o) {
  const calls = [], copied = [], confirms = [], boxes = {};
  const w = {
    location: {origin: o.origin || "http://127.0.0.1:8765"}, isSecureContext: true,
    navigator: {clipboard: {writeText: t => { copied.push(t); return Promise.resolve(); }}},
    confirm: m => { confirms.push(m); return o.ok !== false; },
    document: {
      querySelector: q => (o.token && q === 'meta[name="kit-token"]') ? {getAttribute: () => o.token} : null,
      getElementById: id => boxes[id] || (boxes[id] = el()), createElement: () => el(), body: el(), execCommand() {}},
    fetch: async (path, init) => {
      calls.push({path, method: (init && init.method) || "GET", body: init && init.body, headers: (init && init.headers) || {}});
      return o.server(path, init); }};
  vm.runInContext(src, vm.createContext({window: w, Blob, setTimeout, console}));
  w.pfAct.poll = 5;
  return {w, calls, copied, confirms, boxes};
}
const body = c => JSON.parse(c.body);
const must_not = () => { throw new Error("must not fetch"); };
const costly = (path, init) => JSON.parse(init.body).confirmed ? answer(200, {ok: true, said: "ran"})
  : answer(428, {ok: false, confirm: "Redo the whole email: it calls a model and costs money.", said: "confirm first"});
(async () => {
  const out = {};
  let p = page({token: "T", server: () => answer(200, {ok: true, said: "first\nsaved who"})});
  let r = await p.w.pfAct(24, {item: "a1", field: "who", value: "editor"}, {family: "content-queue", into: "said"});
  out.quick = {ok: r.ok, line: p.boxes.said.text,
    calls: p.calls.map(c => [c.method, c.path, body(c), c.headers["X-Kit-Token"], c.headers["Content-Type"]])};

  let polls = 0;
  const ticks = [];
  p = page({token: "T", server: path => path === "/act"
    ? answer(202, {ok: true, job: "j1", ask: "Request (e1, part 2): move up", state: "queued"})
    : answer(200, ++polls < 2 ? {state: "running", said: "building"} : {state: "done", said: "built\nchecked"})});
  r = await p.w.pfAct(31, {item: "e1", part: 2, value: "up"}, {family: "emails", into: "said", tick: t => ticks.push(t.state)});
  out.job = {ok: r.ok, state: r.state, line: p.boxes.said.text, paths: p.calls.map(c => c.method + " " + c.path), ticks,
    seen: p.boxes.said.seen};

  p = page({token: "T", server: costly});
  r = await p.w.pfAct(29, {item: "e1", part: "-", note: "warmer"}, {family: "emails", into: "said"});
  out.confirm = {ok: r.ok, confirms: p.confirms, bodies: p.calls.map(body), line: p.boxes.said.text};

  p = page({token: "T", ok: false, server: costly});
  r = await p.w.pfAct(29, {item: "e1", part: "-", note: "warmer"}, {family: "emails", into: "said", ask: "Request (e1, part -): redo"});
  out.cancel = {ok: r.ok, cancelled: !!r.cancelled, posts: p.calls.length, copied: p.copied, line: p.boxes.said.text};

  p = page({token: "T", server: () => answer(409, {ok: false, said: "already working on e1", job: "j0"})});
  r = await p.w.pfAct(27, {item: "e1", part: "-"}, {family: "emails", into: "said", ask: "Request (e1, part -): fill"});
  out.busy = {status: r.status, posts: p.calls.length, copied: p.copied, confirms: p.confirms, line: p.boxes.said.text};

  p = page({token: "T", server: () => { throw new TypeError("Failed to fetch"); }});
  r = await p.w.pfAct(26, {item: "e1", part: 2}, {family: "emails", into: "said", ask: "Request (e1, part 2): ok"});
  out.failure = {fallback: !!r.fallback, copied: p.copied, line: p.boxes.said.text};

  p = page({token: "T", server: () => answer(202, {ok: true, job: "j2", ask: "Request (e1, part -): redo"})});
  p.w.fetch = async (path, init) => { p.calls.push({path}); return path === "/act"
    ? answer(202, {ok: true, job: "j2", ask: "Request (e1, part -): redo"})
    : answer(200, {state: "failed", said: "line 9: no picture"}); };
  r = await p.w.pfAct(30, {item: "e1", part: 1}, {family: "emails", into: "said", ask: "page line"});
  out.failedJob = {ok: r.ok, copied: p.copied, line: p.boxes.said.text};

  p = page({server: must_not});
  r = await p.w.pfAct(26, {item: "e1"}, {family: "emails", into: "said", ask: "Request (e1, part 2): ok"});
  out.unserved = {fallback: !!r.fallback, unserved: !!r.unserved, fetches: p.calls.length, copied: p.copied,
    served: p.w.pfServed(), line: p.boxes.said.text};

  p = page({token: "T", origin: "https://example.com", server: must_not});
  r = await p.w.pfAct(26, {item: "e1"}, {family: "emails", ask: "Request (e1, part 2): ok"});
  out.foreign = {fetches: p.calls.length, copied: p.copied, served: p.w.pfServed()};

  p = page({token: "T", server: () => answer(403, {ok: false, said: "ask your Claude: this button is not direct"})});
  r = await p.w.pfAct(57, {item: "e1"}, {family: "emails", fallback: x => ({mine: true, said: x.said, status: x.status})});
  out.pageFallback = {r, copied: p.copied};

  p = page({token: "T", server: () => answer(200, {ok: true, path: "runs/x/media/own/a.png"})});
  r = await p.w.pfUpload(new Blob(["png"], {type: "image/png"}), "e 1", {family: "emails"});
  out.upload = {ok: r.ok, path: r.path, call: [p.calls[0].method, p.calls[0].path, p.calls[0].headers["Content-Type"],
    p.calls[0].headers["X-Kit-Token"]]};
  p = page({server: must_not});
  r = await p.w.pfUpload(new Blob(["png"]), "e1", {family: "emails"});
  out.uploadUnserved = {ok: r.ok, fetches: p.calls.length};
  console.log(JSON.stringify(out));
})().catch(e => { console.error(e && e.stack || e); process.exit(1); });
"""


@unittest.skipUnless(shutil.which("node"), "node is not installed: ActStatic below checks act.js by its text")
class ActInNode(unittest.TestCase):
    """(d) every kind through act.js against a fake server."""

    @classmethod
    def setUpClass(cls):
        p = subprocess.run([shutil.which("node"), "-e", HARNESS, ACT_JS], capture_output=True, text=True, timeout=60)
        if p.returncode != 0:
            raise AssertionError(p.stdout + p.stderr)
        cls.out = json.loads(p.stdout.strip().splitlines()[-1])

    def test_quick_posts_once_with_the_token_and_shows_the_result(self):
        q = self.out["quick"]
        self.assertTrue(q["ok"])
        self.assertEqual(q["calls"], [["POST", "/act", {"item": "a1", "field": "who", "value": "editor",
                                                         "family": "content-queue", "n": 24}, "T", "application/json"]])
        self.assertEqual(q["line"], "✓ Done · saved who")

    def test_job_polls_to_done(self):
        j = self.out["job"]
        self.assertTrue(j["ok"])
        self.assertEqual(j["state"], "done")
        self.assertEqual(j["paths"], ["POST /act", "GET /job/j1", "GET /job/j1"])
        self.assertEqual(j["ticks"], ["queued", "running"])
        self.assertEqual(j["line"], "✓ Done · checked")
        self.assertEqual(j["seen"], ["Working…", "working… 0 s", "working… 0 s · building", "✓ Done · checked"])

    def test_confirm_job_confirms_with_the_servers_words_then_posts_confirmed(self):
        c = self.out["confirm"]
        self.assertTrue(c["ok"])
        self.assertEqual(c["confirms"], ["Redo the whole email: it calls a model and costs money."])
        self.assertEqual(len(c["bodies"]), 2)
        self.assertNotIn("confirmed", c["bodies"][0])
        self.assertEqual(c["bodies"][1], dict(c["bodies"][0], confirmed=True))
        x = self.out["cancel"]
        self.assertEqual((x["ok"], x["cancelled"], x["posts"], x["copied"]), (False, True, 1, []))
        self.assertEqual(x["line"], "Not run: you pressed Cancel.")

    def test_409_is_never_retried_confirmed_or_copied(self):
        b = self.out["busy"]
        self.assertEqual((b["status"], b["posts"], b["copied"], b["confirms"]), (409, 1, [], []))
        self.assertEqual(b["line"], "already working on e1: wait for its line to say done.")

    def test_a_fetch_failure_copies_the_request_line(self):
        f = self.out["failure"]
        self.assertTrue(f["fallback"])
        self.assertEqual(f["copied"], ["Request (e1, part 2): ok"])
        self.assertEqual(f["line"], "Didn't run here: Failed to fetch. The request is copied: paste it in Claude."
                                    "|Request (e1, part 2): ok")
        g = self.out["failedJob"]
        self.assertFalse(g["ok"])
        self.assertEqual(g["copied"], ["Request (e1, part -): redo"], "a failed job copies its own line")
        self.assertTrue(g["line"].startswith("It stopped: line 9: no picture."), g["line"])

    def test_unserved_copies_without_any_fetch(self):
        u = self.out["unserved"]
        self.assertEqual((u["fallback"], u["unserved"], u["fetches"], u["served"]), (True, True, 0, False))
        self.assertEqual(u["copied"], ["Request (e1, part 2): ok"])
        self.assertTrue(u["line"].startswith("Not served by a page server. The request is copied"), u["line"])
        f = self.out["foreign"]
        self.assertEqual((f["fetches"], f["copied"], f["served"]), (0, ["Request (e1, part 2): ok"], False))
        self.assertEqual(self.out["uploadUnserved"], {"ok": False, "fetches": 0})

    def test_the_pages_own_fallback_wins(self):
        pf = self.out["pageFallback"]
        self.assertEqual(pf["r"], {"mine": True, "said": "ask your Claude: this button is not direct", "status": 403})
        self.assertEqual(pf["copied"], [])

    def test_upload(self):
        u = self.out["upload"]
        self.assertEqual((u["ok"], u["path"]), (True, "runs/x/media/own/a.png"))
        self.assertEqual(u["call"], ["POST", "/upload?family=emails&item=e%201", "image/png", "T"])


class ActStatic(unittest.TestCase):
    """(d) without node: the script says each step."""

    def test_act_js_names_every_step(self):
        text = read(ACT_JS)
        for want in ('call("/act"', '"/job/"', "r.status === 428", "confirmed: true", "r.status === 409",
                     "r.status !== 202", 'meta[name="kit-token"]', "clipboard", "pfAct.poll = 3000",
                     '"/upload?family="', "w.pfAct = pfAct", "w.pfUpload = pfUpload", "w.pfServed"):
            self.assertIn(want, text)


if __name__ == "__main__":
    unittest.main()
