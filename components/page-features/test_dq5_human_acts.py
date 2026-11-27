#!/usr/bin/env python3
"""DQ-5 (human acts): every open dev follow-up is an act in its people's Up next groups, and leaves when ticked done.

    python3 components/page-features/test_dq5_human_acts.py

    (d) data and the writer, on a fixture workspace:
        - `file` takes a follow-up's `person` as one id or a list; a list on an issue, a person with no identity, a
          name twice, and `urgent` on an issue are refused, nothing written
        - dev_queue.build's `acts` holds every open follow-up (no parent, on an issue, on a card) with its assignees,
          `urgent` and `on`; a done one is not there; a non-dev PM task is in neither `issues` nor `acts`
        - `priority <follow-up> --urgent | --not-urgent` writes ONE tasks edit of `priority`; the newest wins; an
          issue, a no-op and a done follow-up are refused
    (v) the template platform/views/viewers/_templates/dev-queue.html, as it is on disk, in headless Chrome
        (test_pf18e_panel_opens.py's driver) from a stub server answering /data/dev-queue:
        1. an open follow-up with two people shows in both people's Up next groups, with the "✋ Human act" chip, no
           card id, no Built by, and "on: <parent>" opening the parent card or going to the parent issue
        2. its done tick removes it: rebuilt after `done`, it is on no column
        3. it never enters Shipped, Flagged, Reviewed or Your review, and the Issue queue holds issues only
        4. an urgent one sorts first in its group, with the red "Urgent" chip; a plain one comes after the cards
        5. a non-dev PM task never shows, its title nowhere on the page
        and the team board (no viewer) draws each act once in Up next
    (r) on the real task records as they stood at commit 3eecbdc697 (PINNED_AT), copied into a fixture workspace:
        TSK-20261030055827 (editor's pictures) is in its assignee's Up next "on: issue …", TSK-20261030055352
        (QB-4 (joint queue test) session) in email_lead's "on: QB-4"; the Issue queue holds no follow-up. Pinned, so a
        real task closing (editor's was ticked done at 5452145438) never turns this red (email_lead, 2026-10-30)
    No Chrome → prints SKIPPED with the reason; exits 0 only when CI_NO_CHROME=1 is set, else 1.

Fixtures are test_pf18b_review_marks.py's workspace (a test file) plus the items below, kept in this file (no .md
fixtures under components/). Stdlib only, Python 3.9. Writes only in temp folders; no network beyond 127.0.0.1.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "kit"))
import dev_issues  # noqa: E402
import dev_queue  # noqa: E402
import features  # noqa: E402
import test_pf18_dev_queue as pf18  # noqa: E402  the fixture repo
import test_pf18b_review_marks as pf18b  # noqa: E402  the fixture workspace with the review module
import test_pf18e_panel_opens as pf18e  # noqa: E402  the Chrome driver
import test_pf18k_people_views as pf18k  # noqa: E402  the stub server

REAL = features.ROOT
PAGE = os.path.join(REAL, "platform/views/viewers/_templates/dev-queue.html")
TASKS = dev_queue.TASKS + "/"
BUILD_AT = "2026-10-30T09:00:00Z"
ENV = pf18k.ENV
REAL_editor = "TSK-20261030055827"
REAL_QB4 = "TSK-20261030055352"
PINNED_AT = "3eecbdc697"     # the last commit with both real acts open: editor's handed to email_lead, not yet ticked done

ITEMS = [
    {"kind": "issue", "ref": "i", "title": "Pictures stopped on one Mac", "quote": "no picture since monday",
     "session": "dq5a01"},
    {"kind": "follow-up", "ref": "two", "title": "Sit together and run the joint test", "quote": "run it together",
     "session": "dq5a01", "parent": "i", "person": ["email_lead", "designer"]},
    {"kind": "follow-up", "ref": "urg", "title": "Restore the backup disk today", "quote": "today please",
     "session": "dq5a01", "person": "developer", "urgent": True},
    {"kind": "follow-up", "ref": "card", "title": "Send the note about the page server", "quote": "tell them",
     "session": "dq5a01", "parent": "PF-14", "person": "developer"},
    {"kind": "follow-up", "ref": "plain", "title": "Check the Time Machine run", "quote": "check it",
     "session": "dq5a01", "person": "developer"},
    {"kind": "follow-up", "ref": "gone", "title": "Ticked done before the build", "quote": "done soon",
     "session": "dq5a01", "person": "developer"},
]
NOT_DEV_TITLE = "Book the carrier pickup for Friday"
NOT_DEV = {"schema": 1, "kind": "tasks", "reviewer": "email_lead", "item": "TSK-20261030070000-book-the-carrier",
           "verdict": {"event": "create", "item": {"id": "TSK-20261030070000-book-the-carrier", "title": NOT_DEV_TITLE,
                                                   "status": "todo", "tags": ["ops", "follow-up"], "links": [],
                                                   "parent": "", "assignees": ["developer"], "priority": "urgent"}},
           "notes": "", "created": "2026-10-30T07:00:00Z", "via": "test"}


def run(root, *argv):
    out, err = io.StringIO(), io.StringIO()
    code = dev_issues.main(list(argv) + ["--root", root], out=out, err=err)
    return code, out.getvalue(), err.getvalue()


def file_list(root, items, now="2026-10-30T07:00:00Z"):
    pf18.write(root, "dq5-items.json", json.dumps(items))
    return run(root, "file", os.path.join(root, "dq5-items.json"), "--by", "developer", "--now", now)


def by_title(doc):
    return dict((e["title"], e["id"]) for e in doc["issues"])


def task_files(root):
    folder = os.path.join(root, TASKS)
    return sorted(os.listdir(folder)) if os.path.isdir(folder) else []


def workspace():
    """(root, ids by ref) with the items filed, PF-5 assigned to developer, the non-dev task and `gone` ticked done."""
    root = pf18b.workspace()
    code, _out, err = file_list(root, ITEMS)
    assert code == 0, err
    pf18.write(root, TASKS + "20261030T070000Z--email_lead--TSK-20261030070000-book-the-carrier.json", json.dumps(NOT_DEV))
    doc = dev_queue.build(root, now=BUILD_AT)
    t = by_title(doc)
    ids = dict((it["ref"], t[it["title"]]) for it in ITEMS)
    code, _out, err = run(root, "done", ids["gone"], "--by", "developer", "--now", "2026-10-30T07:30:00Z")
    assert code == 0, err
    dev_queue.assign(root, "PF-5", "developer", "developer", env=ENV, commit=False, now="2026-10-30T07:40:00Z")
    return root, ids


def real_tasks_at(root, commit=PINNED_AT):
    """The real repo's task records as they stood at `commit`, written into the fixture workspace `root`."""
    names = subprocess.run(["git", "-C", REAL, "ls-tree", "--name-only", commit, TASKS], check=True,
                           stdout=subprocess.PIPE, universal_newlines=True).stdout.split()
    for rel in names:
        if rel.endswith(".json"):
            body = subprocess.run(["git", "-C", REAL, "show", "%s:%s" % (commit, rel)], check=True,
                                  stdout=subprocess.PIPE, universal_newlines=True).stdout
            pf18.write(root, rel, body)
    return len(names)


class Data(unittest.TestCase):
    """(d)"""

    @classmethod
    def setUpClass(cls):
        cls.root, cls.ids = workspace()
        cls.doc = dev_queue.build(cls.root, now=BUILD_AT)
        cls.acts = dict((a["id"], a) for a in cls.doc["acts"])

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, True)

    def test_d1_person_as_a_list(self):
        ids = self.ids
        self.assertEqual(self.acts[ids["two"]]["assignees"], ["email_lead", "designer"])
        self.assertEqual(self.acts[ids["urg"]]["assignees"], ["developer"], "one id is still one id")
        before = task_files(self.root)
        base = {"kind": "follow-up", "title": "x", "quote": "q", "session": "s"}
        bad = [dict(base, kind="issue", person=["developer", "email_lead"]), dict(base, person=["developer", "vendor"]),
               dict(base, person=["developer", "developer"]), dict(base, person=[]), dict(base, kind="issue", urgent=True),
               dict(base, person="developer", urgent="yes")]
        code, _out, err = file_list(self.root, bad)
        self.assertEqual(code, 2, err)
        for words in ("item 1: only a follow-up takes a list of people",
                      "item 2: person 'vendor' has no team/people/<name>/identity.json",
                      "item 3: person names someone twice", "item 4: a follow-up needs its person",
                      "item 5: only a follow-up is filed urgent here", "item 6: urgent is true or false"):
            self.assertIn(words, err)
        self.assertEqual(task_files(self.root), before, "a refused list writes nothing")

    def test_d2_acts_are_the_open_follow_ups(self):
        ids, acts = self.ids, self.acts
        self.assertEqual(sorted(acts), sorted(ids[k] for k in ("two", "urg", "card", "plain")))
        self.assertNotIn(ids["gone"], acts, "a done follow-up is not an act")
        self.assertEqual(acts[ids["two"]]["on"]["type"], "issue")
        self.assertEqual(acts[ids["two"]]["on"]["id"], ids["i"])
        self.assertEqual(acts[ids["two"]]["on"]["title"], "Pictures stopped on one Mac")
        self.assertEqual((acts[ids["card"]]["on"]["type"], acts[ids["card"]]["on"]["id"]), ("card", "PF-14"))
        self.assertIsNone(acts[ids["plain"]]["on"])
        self.assertEqual([a["urgent"] for a in self.doc["acts"]], [True, False, False, False], "urgent first")
        self.assertEqual(self.doc["acts"][0]["id"], ids["urg"])
        everywhere = json.dumps(self.doc)
        self.assertNotIn(NOT_DEV_TITLE, everywhere, "a non-dev PM task is nowhere in the data")
        self.assertNotIn(NOT_DEV["item"], everywhere)
        for c in self.doc["cards"]:
            self.assertFalse(c["id"].startswith("TSK-"), "an act is never a card")

    def test_d3_priority_moves(self):
        root = pf18b.workspace()
        try:
            code, _out, err = file_list(root, ITEMS[:1] + ITEMS[4:5])
            self.assertEqual(code, 0, err)
            t = by_title(dev_queue.build(root, now=BUILD_AT))
            plain, issue = t["Check the Time Machine run"], t["Pictures stopped on one Mac"]
            before = task_files(root)
            code, out, err = run(root, "priority", plain, "--urgent", "--by", "developer", "--now", "2026-10-30T08:00:00Z")
            self.assertEqual(code, 0, err)
            new = sorted(set(task_files(root)) - set(before))
            self.assertEqual(len(new), 1, "one record")
            with open(os.path.join(root, TASKS, new[0]), encoding="utf-8") as fh:
                rec = json.load(fh)
            self.assertEqual(rec["verdict"], {"event": "edit", "field": "priority", "value": "urgent"})
            self.assertTrue(dict((a["id"], a) for a in dev_queue.build(root, now=BUILD_AT)["acts"])[plain]["urgent"])
            code, _out, err = run(root, "priority", plain, "--urgent", "--by", "developer", "--now", "2026-10-30T08:01:00Z")
            self.assertEqual(code, 2)
            self.assertIn("is urgent already", err)
            code, _out, err = run(root, "priority", plain, "--not-urgent", "--by", "developer", "--now",
                                  "2026-10-30T08:02:00Z")
            self.assertEqual(code, 0, err)
            self.assertFalse(dict((a["id"], a) for a in dev_queue.build(root, now=BUILD_AT)["acts"])[plain]["urgent"],
                             "the newest edit wins")
            code, _out, err = run(root, "priority", issue, "--urgent", "--by", "developer", "--now", "2026-10-30T08:03:00Z")
            self.assertEqual(code, 2)
            self.assertIn("only a follow-up takes --urgent", err)
            code, _out, err = run(root, "priority", plain, "--by", "developer", "--now", "2026-10-30T08:04:00Z")
            self.assertEqual(code, 2)
            self.assertIn("say --urgent or --not-urgent", err)
            self.assertEqual(run(root, "done", plain, "--by", "developer", "--now", "2026-10-30T08:05:00Z")[0], 0)
            code, _out, err = run(root, "priority", plain, "--urgent", "--by", "developer", "--now", "2026-10-30T08:06:00Z")
            self.assertEqual(code, 2)
            self.assertIn("is done already", err)
        finally:
            shutil.rmtree(root, True)


# Each column's tiles and acts by group: the h4 above the list, "rest" for the closed fold, "" for none
VIEW = """(() => {
  const out = {};
  document.querySelectorAll('section.column').forEach(sec => {
    const col = sec.id.slice(4); out[col] = {};
    sec.querySelectorAll('[data-tile], [data-act], [data-issue]').forEach(t => {
      const ul = t.closest('ul'); let g = '';
      if (ul.parentElement.tagName === 'DETAILS') g = 'rest';
      else { let e = ul.previousElementSibling; while (e && e.tagName !== 'H4') e = e.previousElementSibling;
             g = e ? e.textContent.split(' · ')[0] : ''; }
      const id = t.getAttribute('data-tile') || (t.getAttribute('data-act') ? 'act:' + t.getAttribute('data-act')
        : 'issue:' + t.getAttribute('data-issue'));
      (out[col][g] = out[col][g] || []).push(id);
    });
  });
  const acts = {};
  document.querySelectorAll('[data-act]').forEach(t => {
    acts[t.getAttribute('data-act')] = {chips: Array.from(t.querySelectorAll('.chip, .card-chip')).map(c => c.textContent),
      text: t.textContent.replace(/\\s+/g, ' '), refs: t.querySelectorAll('.card-ref').length,
      on: (t.querySelector('button.card-chip, a.act-on') || {}).textContent || null}; });
  const coltext = {};
  document.querySelectorAll('section.column').forEach(sec => { coltext[sec.id.slice(4)] = sec.textContent; });
  return {cols: out, acts: acts, coltext: coltext, text: document.body.textContent.replace(/\\s+/g, ' ')};
})()"""


class Views(unittest.TestCase):
    """(v) and (r)"""

    @classmethod
    def setUpClass(cls):
        binary, _why = pf18e.chrome_bin()
        cls.root, cls.ids = workspace()
        cls.doc = dev_queue.build(cls.root, now=BUILD_AT)
        with open(PAGE, "rb") as fh:
            cls.html = fh.read()
        cls.stub = pf18k.Stub(cls.html, cls.doc)
        cls.chrome = pf18e.Chrome(binary)

    @classmethod
    def tearDownClass(cls):
        cls.chrome.quit()
        cls.stub.stop()
        shutil.rmtree(cls.root, True)

    def page(self, viewer, doc=None):
        if doc is not None:
            self.stub.stop()
            type(self).stub = pf18k.Stub(self.html, doc)
        self.stub.viewer = viewer
        self.chrome.call("Page.navigate", url=self.stub.url)
        self.assertTrue(self.chrome.wait("document.readyState === 'complete' && "
                                         "document.getElementById('snapshot').textContent.indexOf('Read') === 0 && "
                                         "document.querySelectorAll('[data-tile]').length > 0"),
                        "the board never drew for %s: %s" % (viewer, self.chrome.exceptions))
        got = self.chrome.js(VIEW)
        self.assertEqual(self.chrome.exceptions, [], "no page exception")
        return got

    def where(self, v, act):
        return sorted((col, g) for col, groups in v["cols"].items() for g, ids in groups.items() if "act:" + act in ids)

    def test_v1_two_people_two_groups(self):
        two = self.ids["two"]
        v = self.page("developer")
        self.assertEqual(self.where(v, two), [("up-next", "email_lead"), ("up-next", "designer")])
        a = v["acts"][two]
        self.assertIn("✋ Human act", a["chips"])
        self.assertIn("With email_lead & designer", a["chips"])
        self.assertEqual(a["refs"], 0, "no card id")
        self.assertNotIn("Built by", a["text"])
        self.assertEqual(a["on"], "on: issue %s · Pictures stopped on one Mac" % self.ids["i"])
        self.assertTrue(v["acts"][self.ids["card"]]["on"].startswith("on: PF-14"), v["acts"][self.ids["card"]]["on"])
        for who in ("email_lead", "designer"):
            s = self.page(who)
            self.assertIn(("up-next", "You"), self.where(s, two), who)
            self.assertEqual(len(self.where(s, two)), 2, "%s: in You and in the other person's group" % who)
        # "on:" goes to the parent: the card's panel opens; the issue's tile is in the queue
        self.page("developer")
        self.assertTrue(self.chrome.js("(() => { document.querySelector('[data-act=\"%s\"] button.card-chip').click();"
                                       " return document.getElementById('panel').open; })()" % self.ids["card"]))
        self.chrome.js("document.getElementById('panel').close()")
        self.assertTrue(self.chrome.js("(() => { document.querySelector('[data-act=\"%s\"] a.act-on').click();"
                                       " return document.querySelector('[data-issue=\"%s\"]').classList.contains("
                                       "'selected'); })()" % (two, self.ids["i"])))

    def test_v2_done_removes_it(self):
        v = self.page("developer")
        self.assertEqual(self.where(v, self.ids["gone"]), [], "ticked done before the build: on no column")
        root, ids = workspace()
        try:
            code, _out, err = run(root, "done", ids["two"], "--by", "email_lead", "--now", "2026-10-30T08:00:00Z")
            self.assertEqual(code, 0, err)
            doc = dev_queue.build(root, now=BUILD_AT)
            self.assertNotIn(ids["two"], [a["id"] for a in doc["acts"]])
            for who in ("developer", "email_lead", None):
                after = self.page(who, doc)
                self.assertEqual(self.where(after, ids["two"]), [], "%s: done, off the board" % who)
                for col, words in after["coltext"].items():
                    if col != "issue-queue":
                        self.assertNotIn("Sit together and run the joint test", words, (who, col))
        finally:
            shutil.rmtree(root, True)
            self.page("developer", self.doc)

    def test_v3_never_shipped_or_reviewed(self):
        for who in ("developer", "email_lead", "designer", None):
            v = self.page(who)
            for act in self.doc["acts"]:
                for col, g in self.where(v, act["id"]):
                    self.assertEqual(col, "up-next", "%s: %s is in %s/%s" % (who, act["id"], col, g))
            queue = sum(v["cols"]["issue-queue"].values(), [])
            self.assertEqual(sorted(queue), ["issue:" + self.ids["i"]], "%s: the Issue queue holds issues only" % who)
        team = self.page(None)
        for act in self.doc["acts"]:
            self.assertEqual(self.where(team, act["id"]), [("up-next", "")], "the team board: each act once")

    def test_v4_urgent_first(self):
        v = self.page("developer")
        you = v["cols"]["up-next"]["You"]
        self.assertEqual(you[0], "act:" + self.ids["urg"], "the urgent act opens his group")
        self.assertIn("Urgent", v["acts"][self.ids["urg"]]["chips"])
        self.assertNotIn("Urgent", v["acts"][self.ids["plain"]]["chips"])
        self.assertLess(you.index("PF-5"), you.index("act:" + self.ids["plain"]), "plain acts after the cards")
        self.assertLess(you.index("PF-5"), you.index("act:" + self.ids["card"]))
        color = self.chrome.js("getComputedStyle(Array.from(document.querySelectorAll('[data-act=\"%s\"] .chip'))"
                               ".find(c => c.textContent === 'Urgent')).backgroundColor" % self.ids["urg"])
        red = self.chrome.js("(() => { const d = document.createElement('span'); d.style.color = 'var(--c-red)';"
                             " document.body.appendChild(d); const c = getComputedStyle(d).color; d.remove(); return c; })()")
        self.assertEqual(color, red, "the Urgent chip is red")
        self.assertEqual(self.page(None)["cols"]["up-next"][""][0], "act:" + self.ids["urg"], "team board too")

    def test_v5_a_non_dev_task_never_shows(self):
        for who in ("developer", "email_lead", None):
            self.assertNotIn(NOT_DEV_TITLE, self.page(who)["text"], who)

    def test_r_pinned_tree(self):
        root = pf18b.workspace()
        self.addCleanup(shutil.rmtree, root, True)
        self.assertGreater(real_tasks_at(root), 0, "the pinned commit's task records were read")
        doc = dev_queue.build(root)
        acts = dict((a["id"].split("-")[0] + "-" + a["id"].split("-")[1], a) for a in doc["acts"])
        self.assertIn(REAL_editor, acts, "editor's pictures is an open act at the pinned tree")
        self.assertIn(REAL_QB4, acts, "the QB-4 (joint queue test) session is an open act at the pinned tree")
        editor, qb4 = acts[REAL_editor], acts[REAL_QB4]
        # narrowed at DQ-8 (act panel)'s tree: editor's pictures was handed from developer to email_lead by a recorded assign (commit
        # 3eecbdc697), so the act shows in its own assignee's Up next, whoever the records name
        self.assertEqual((len(editor["assignees"]), editor["on"]["type"]), (1, "issue"))
        self.assertEqual((qb4["assignees"], qb4["on"]["type"], qb4["on"]["id"]), (["email_lead"], "card", "QB-4"))
        try:
            v = self.page(editor["assignees"][0], doc)
            self.assertIn(("up-next", "You"), self.where(v, editor["id"]))
            self.assertIn("✋ Human act", v["acts"][editor["id"]]["chips"])
            self.assertIn("on: issue ", v["acts"][editor["id"]]["text"])
            for g in v["cols"]["issue-queue"].values():
                for x in g:
                    self.assertTrue(x.startswith("issue:"), x)
            for x in sum(v["cols"]["issue-queue"].values(), []):
                self.assertEqual(dict((e["id"], e) for e in doc["issues"])[x[6:]]["kind"], "issue", x)
            s = self.page("email_lead", doc)
            self.assertIn(("up-next", "You"), self.where(s, qb4["id"]))
            self.assertIn("on: QB-4", s["acts"][qb4["id"]]["text"])
        finally:
            self.page("developer", self.doc)


def main():
    binary, why = pf18e.chrome_bin()
    if not binary:
        print("SKIPPED: %s; set CHROME_BIN to a Chrome or Chromium binary" % why)
        sys.exit(0 if os.environ.get("CI_NO_CHROME") == "1" else 1)
    unittest.main()


if __name__ == "__main__":
    main()
