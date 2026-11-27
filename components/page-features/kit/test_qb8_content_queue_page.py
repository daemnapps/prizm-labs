"""QB-8 (content queue Tuesday): Next move and a waiting summary, how long a piece has waited, shared links first,
phone cards.

The page's own rule functions (nextMove, daysFrom, isStuck, waitText, isShared) are lifted out of its script and run
in node with a fixed "today", so the rules are tested as the page runs them: the Next move map by stage, the stuck
rule (over 7 days in a stage; never an email or a live piece), "waiting N days" and "N days to send", the link
preference (Drive and Docs first) and "no shared link yet". Statically: the summary's counts (with "updated after
owner's list"), the Latest note line on every row and card (email_lead, 2026-10-23), the amber line
past 48 h, the Next move column after Stage, and a phone rule (max-width 640px) that turns rows into cards. check.py
and js-parse exit 0. Stdlib only, no network, no Chrome, no git. Run from the repo root:
    python3 components/page-features/kit/test_qb8_content_queue_page.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import serve  # noqa: E402  kit/serve.py, for ROOT and TEMPLATES only

ROOT = serve.ROOT
TPL = os.path.join(ROOT, serve.TEMPLATES)
PAGE = os.path.join(TPL, "content-queue.html")
FEATURES = os.path.join(TPL, "content-queue.features.json")
RULES = ("val", "isEmail", "turnWho", "isBank", "groupOf", "nextMove", "today", "daysFrom", "isStuck", "plural", "waitText", "isShared")
CONSTS = ("owner_STAGES", "editor_STAGES", "STUCK_DAYS", "SHARED_HOSTS", "BANK_STAGES", "NEEDS_YOU")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def script(text):
    return re.findall(r"<script>([\s\S]*?)</script>", text)[0]


def lift(src, name):
    """One `function name(…) {…}` out of the page's script, braces balanced."""
    m = re.search(r"\n  function %s\(" % name, src)
    if not m:
        raise AssertionError("no function %s in the page" % name)
    i, depth = src.index("{", m.end()), 0
    for j in range(i, len(src)):
        depth += {"{": 1, "}": -1}.get(src[j], 0)
        if depth == 0:
            return src[m.start():j + 1]
    raise AssertionError("unbalanced %s" % name)


def const(src, name):
    m = re.search(r"var %s = ([^;]+);" % name, src) or re.search(r"[ ,]%s = ([^,;]+)[,;]" % name, src)
    if not m:
        raise AssertionError("no %s in the page" % name)
    return "var %s = %s;" % (name, m.group(1))


@unittest.skipUnless(shutil.which("node"), "node is not on PATH")
class Rules(unittest.TestCase):
    """The page's rules, run as the page runs them, on 2026-10-27 (a Tuesday)."""

    @classmethod
    def setUpClass(cls):
        src = script(read(PAGE))
        body = "\n".join([const(src, c) for c in CONSTS] + [lift(src, f) for f in RULES])
        cls.js = (body.replace("function today() {", "function today() { return Date.parse('2026-10-27T00:00:00');")
                  + "\nvar cases = JSON.parse(process.argv[1]); var out = {};"
                  + "\nObject.keys(cases).forEach(function (k) { var c = cases[k];"
                  + " out[k] = c.fn === 'isShared' ? isShared(c.arg) : eval(c.fn)(c.arg); });"
                  + "\nprocess.stdout.write(JSON.stringify(out));")

    def run_cases(self, cases):
        p = subprocess.run([shutil.which("node"), "-e", self.js, json.dumps(cases)], capture_output=True, text=True,
                           timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout)

    def test_next_move_by_stage(self):
        rows = {s: {"type": "image-ad", "stage": s} for s in
                ("idea", "brief", "brief-needs-you", "making", "editing", "final-needs-you", "launch", "live")}
        rows["email-editor"] = {"type": "email", "stage": "making", "turn": "editor: pictures"}
        rows["email-email_lead"] = {"type": "email", "stage": "making", "turn": "email_lead: Go"}
        rows["email-none"] = {"type": "email", "stage": "launch", "turn": ""}
        rows["gone"] = {"type": "image-ad", "stage": "making", "gone": "2026-10-20"}
        rows["video-making"] = {"type": "video-ad", "stage": "making"}            # editor makes no video
        rows["video-editing"] = {"type": "video-ad", "stage": "editing"}
        rows["video-creator"] = {"type": "video-ad", "stage": "making", "who": "creator"}
        rows["video-review"] = {"type": "video-ad", "stage": "brief-needs-you", "who": "creator"}
        rows["static-assigned"] = {"type": "image-ad", "stage": "making", "who": "victoria"}
        rows["added-editor"] = {"type": "image-ad", "stage": None, "who": "editor"}    # added on the page, no stage yet
        rows["added-nobody"] = {"type": "image-ad", "stage": None}
        got = self.run_cases({k: {"fn": "nextMove", "arg": r} for k, r in rows.items()})
        self.assertEqual(got, {"idea": "owner", "brief": "owner", "brief-needs-you": "owner", "making": "editor",
                               "editing": "", "final-needs-you": "owner", "launch": "", "live": "",
                               "email-editor": "editor", "email-email_lead": "email_lead", "email-none": "", "gone": "",
                               "video-making": "owner", "video-editing": "owner", "video-creator": "creator",
                               "video-review": "owner", "static-assigned": "Victoria",
                               "added-editor": "editor", "added-nobody": ""})

    def test_bank_apart_from_work(self):
        rows = {"teardown": {"type": "video-ad", "stage": "idea"}, "writing": {"type": "image-ad", "stage": "brief"},
                "review": {"type": "video-ad", "stage": "brief-needs-you"}, "making": {"type": "video-ad", "stage": "making"},
                "email": {"type": "email", "stage": "brief", "turn": "editor: pictures"},
                "live": {"type": "video-ad", "stage": "live"}}
        got = self.run_cases({k: {"fn": "groupOf", "arg": r} for k, r in rows.items()})
        self.assertEqual(got, {"teardown": "bank", "writing": "bank", "review": "now", "making": "work",
                               "email": "now", "live": "live"})

    def test_stuck_over_seven_days_never_an_email_or_live(self):
        rows = {"8 days": {"type": "image-ad", "stage": "brief", "since": "2026-10-19"},
                "7 days": {"type": "image-ad", "stage": "brief", "since": "2026-10-20"},
                "no since": {"type": "image-ad", "stage": "brief", "since": None},
                "email": {"type": "email", "stage": "making", "since": "2026-09-01"},
                "live": {"type": "image-ad", "stage": "live", "since": "2026-09-01"},
                "removed": {"type": "image-ad", "stage": "brief", "since": "2026-09-01", "removed": True}}
        got = self.run_cases({k: {"fn": "isStuck", "arg": r} for k, r in rows.items()})
        self.assertEqual(got, {"8 days": True, "7 days": False, "no since": False, "email": False, "live": False,
                               "removed": False})

    def test_waiting_and_days_to_send(self):
        rows = {"static": {"type": "image-ad", "stage": "making", "since": "2026-10-24T09:00:00"},
                "one": {"type": "image-ad", "stage": "making", "since": "2026-10-26"},
                "live": {"type": "image-ad", "stage": "live", "since": "2026-10-01"},
                "email": {"type": "email", "stage": "making", "send_date": "2026-11-01", "send_date_ok": True},
                "today": {"type": "email", "stage": "launch", "send_date": "2026-10-27", "send_date_ok": True},
                "past": {"type": "email", "stage": "launch", "send_date": "2026-10-20", "send_date_ok": True},
                "unreadable": {"type": "email", "stage": "making", "send_date": "soon", "send_date_ok": False}}
        got = self.run_cases({k: {"fn": "waitText", "arg": r} for k, r in rows.items()})
        self.assertEqual(got, {"static": "waiting 3 days", "one": "waiting 1 day", "live": "",
                               "email": "5 days to send", "today": "sends today", "past": "", "unreadable": ""})

    def test_shared_hosts(self):
        urls = {"drive": "https://drive.google.com/drive/folders/x", "docs": "https://docs.google.com/document/d/y",
                "mac": "http://127.0.0.1:8795/", "other": "https://example.com/a", "path": "/qthumb/a.jpg"}
        got = self.run_cases({k: {"fn": "isShared", "arg": u} for k, u in urls.items()})
        self.assertEqual(got, {"drive": True, "docs": True, "mac": False, "other": False, "path": False})


class Page(unittest.TestCase):
    def setUp(self):
        self.text = read(PAGE)
        self.src = script(self.text)

    def template(self, tid):
        m = re.search(r'<template id="%s">([\s\S]*?)</template>' % tid, self.text)
        self.assertTrue(m, tid)
        return m.group(1)

    def test_next_move_column_after_stage(self):
        head = re.findall(r"<th>([^<]*)</th>", self.template("cq-t-group"))
        self.assertEqual(head[:3], ["Type", "Stage", "Next move"])
        for tid in ("cq-t-row", "cq-t-row-ro"):
            cells = re.findall(r'<td class="(c-[a-z]+)"', self.template(tid))
            self.assertEqual(cells[:3], ["c-type", "c-stage", "c-next"], tid)
            self.assertIn('class="v-wait"', self.template(tid))

    def test_summary_counts_and_focus(self):
        box = re.search(r'<div class="summary" id="cq-summary"[^>]*>([\s\S]*?)</div>', self.text)
        self.assertTrue(box)
        self.assertEqual(re.findall(r'data-focus="([a-z]+)"', box.group(1)), ["owner", "stuck", "newer"])
        self.assertIn("waiting on owner", box.group(1))
        self.assertIn("stuck over 7 days", box.group(1))
        self.assertIn("var shown = inTab.filter(inFocus);", self.src)       # a count filters the list

    def test_latest_note_on_every_row_and_card(self):
        for tid in ("cq-t-row", "cq-t-row-ro", "cq-t-item"):         # folded: one line until opened
            self.assertRegex(self.template(tid), r'<details class="latest v-latest"[^>]*><summary>', tid)
        body = lift(self.src, "fillLatest")
        self.assertIn("newer than owner's list", body)
        self.assertIn("data.owner_built", body)                            # newer = made after his list was built
        self.assertIn('if (focus === "newer") return isNewer(r);', self.src)

    def test_bank_folded_and_out_of_the_counts(self):
        body = lift(self.src, "renderSummary")
        self.assertIn("!bank", body)                                        # waiting on owner and stuck: real work only
        self.assertIn('<details class="group bank" data-feature="41">', self.template("cq-t-bank"))
        self.assertIn("det.open = bankOpen;", self.src)                     # folded unless opened

    def test_who_has_what_line(self):
        self.assertRegex(self.text, r'<div class="summary load" id="cq-load"[^>]*data-feature="40"')
        body = lift(self.src, "renderLoad")
        self.assertIn("whoOf(r)", body)                                     # an email counts for whose turn it is
        self.assertIn('"nobody yet"', body)
        self.assertIn('$("#cq-f-who").value', body)                         # a click filters by that person
        self.assertIn("val(r.who).trim().toLowerCase()", lift(self.src, "people"))   # creator is offered too

    def test_old_data_turns_amber(self):
        self.assertIn("OLD_HOURS = 48", self.src)
        self.assertIn('$("#cq-age").classList.toggle("is-old"', self.src)
        self.assertRegex(self.text, r"\.cq \.is-old\{color:var\(--wait\)")

    def test_mac_links_fold_and_no_shared_link_yet(self):
        body = lift(self.src, "fillLinks")
        self.assertIn('"no shared link yet"', body)
        self.assertIn('el("details", "mac")', body)
        self.assertIn("shared.concat(other)", body)                         # Drive and Docs before anything else

    def test_phone_cards(self):
        m = re.search(r"@media \(max-width:640px\)\{([\s\S]*?)\n\}", self.text)
        self.assertTrue(m, "no phone rule")
        rule = m.group(1)
        self.assertIn(".cq thead{display:none}", rule)
        self.assertIn(".cq tr{display:grid;grid-template-columns:1fr 1fr", rule)
        self.assertIn('.cq td.c-next::before{content:"Next move"}', rule)


class Checks(unittest.TestCase):
    def test_check_py_exits_0(self):
        p = subprocess.run([sys.executable, "-B", os.path.join(ROOT, "components", "page-features", "check.py"),
                            "--features", FEATURES, PAGE], cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_features_35_to_39(self):
        got = {f["n"]: f["name"] for f in json.loads(read(FEATURES))["features"] if 35 <= f["n"] <= 41}   # 42+: QB-9
        self.assertEqual(got, {35: "Next move", 36: "What is waiting: owner · editor · stuck",
                               37: "How long it has waited",
                               38: "Latest note, and whether it is newer than owner's list",
                               39: "Updated after owner's list", 40: "Who has what",
                               41: "Ideas and scripts (owner's bank), folded"})

    def test_js_parse_exits_0(self):
        node = shutil.which("node")
        self.assertTrue(node, "node is not on PATH")
        p = subprocess.run([node, os.path.join(TPL, "js-parse.test.mjs")], cwd=ROOT, capture_output=True, text=True,
                           timeout=300)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main()
