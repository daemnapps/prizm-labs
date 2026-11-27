#!/usr/bin/env python3
"""The content board (content-queue.html, its first view; the list is #list), the creative check-in's view (developer, check-in 2026-11-03, Zoom
GMT20261103-110146; task TSK-20261103143518 (check-in board)), and Copy for Claude on editor's and creator's hand-offs.

The board is read only. Its rules live between the page's `board-core:start` / `board-core:end` markers; this test
runs that block in node with the page's own helpers (val, plural, isEmail, turnWho, briefOf, productOf, sameBrief,
keepQueued) over a small fixture, and checks which column, person and flag each piece gets, how pieces gather into
cards, and the line Copy for Claude copies. The To make column (email_lead, 2026-11-04) is the promo calendar's pieces
from view.py's `calendar`, before any brief: owner has them, its emails and texts are only counted. Nothing runs against the repo's data.

    /usr/bin/python3 components/page-features/kit/test_content_board.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REAL = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PAGE = os.path.join(REAL, "platform/views/viewers/_templates/content-queue.html")
FEATURES = os.path.join(REAL, "platform/views/viewers/_templates/content-queue.features.json")
TODAY = "2026-11-03"


def read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def fn(page, name):
    """One of the page's functions, whole: a one-line one, or up to its closing two-space brace."""
    one = re.search(r"^  function %s\(.*\}\s*(//.*)?$" % name, page, re.M)
    if one and one.group(0).count("{") == one.group(0).count("}"):
        return one.group(0) + "\n"
    return re.search(r"  function %s\([\s\S]*?\n  \}\n" % name, page).group(0)


def core(page):
    return re.search(r"  // board-core:start\n([\s\S]*?)  // board-core:end\n", page).group(1)


def run_node(js):
    p = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
    if p.returncode != 0:
        raise AssertionError(p.stderr)
    return json.loads(p.stdout)


def hand(key, title, brand, back=0, done=False, moment=None, versions=None):
    return {"key": key, "title": title, "brand": brand, "returned_work": back, "done": {"by": "editor"} if done else None,
            "moment": moment, "versions": versions,
            "drive_url": "https://drive.google.com/drive/folders/x-" + key}


DATA = {
    "owner_built": "2026-10-30T17:49:00",
    "loose": {"brand_a_flex-face-brush_brief-0318": {"who": "creator"},   # sent to creator (since 2026-11-11 only a sent hand-off is his)
              "brand_a_flex-face-brush_brief-0301": {"due": "2026-11-06"},
              "brand_a_flex-face-brush_brief-0305": {"due": "2026-11-06"},
              "brand_a_flex-face-brush_brief-0306": {"due": "2026-11-05"},
              "brand_b_brilliance-body-scrub_brief-0310": {"due": "2026-11-01"}},
    "rows": [
        # owner's brief review, waiting 10 days: at risk
        {"id": "brand_a_crush_brief-0100", "title": "Old brief", "brand": "brand_a", "type": "image-ad",
         "stage": "brief-needs-you", "since": "2026-10-24", "in_owner": True},
        # waiting 3 days: on track
        {"id": "brand_a_crush_brief-0101", "title": "New brief", "brand": "brand_a", "type": "image-ad",
         "stage": "brief-needs-you", "since": "2026-10-31", "in_owner": True},
        # the queue row of a hand-off under an old short key, dated: the hand-off stands for it
        {"id": "brand_a_flex_brief-0297", "title": "Black Friday flat-lay", "brand": "brand_a", "type": "image-ad",
         "stage": "making", "who": "editor", "due": "2026-11-05", "since": "2026-10-29", "in_owner": True},
        # face scrub 0314 is not body scrub 0314: stays its own row (the 2026-11-03 rule)
        {"id": "brand_b_brilliance-face-scrub_brief-0314", "title": "Face scrub 0314", "brand": "brand_b",
         "type": "image-ad", "stage": "brief-needs-you", "since": "2026-11-01", "in_owner": True},
        {"id": "brand_a_flex_brief-0500", "title": "A swipe", "brand": "brand_a", "type": "video-ad", "stage": "idea"},
        {"id": "brand_a_flex_brief-0501", "title": "A script", "brand": "brand_a", "type": "video-ad", "stage": "brief"},
        {"id": "brand_a_flex_brief-0502", "title": "Live one", "brand": "brand_a", "type": "image-ad", "stage": "live"},
        {"id": "brand_a_flex_brief-0503", "title": "Removed", "brand": "brand_a", "type": "image-ad",
         "stage": "making", "removed": True},
        {"id": "brand_a_flex_brief-0504", "title": "Gone", "brand": "brand_a", "type": "image-ad",
         "stage": "making", "gone": "2026-10-30"},
        # owner's own video line: nobody named, no date
        {"id": "brand_b_scrub_brief-0600", "title": "Video line", "brand": "brand_b", "type": "video-ad",
         "stage": "making", "since": "2026-10-20", "in_owner": True},
        {"id": "brand_b_scrub_brief-0601", "title": "Cutting", "brand": "brand_b", "type": "video-ad",
         "stage": "editing", "who": "creator", "due": "2026-11-20", "in_owner": True},
        {"id": "brand_b_scrub_brief-0602", "title": "Final", "brand": "brand_b", "type": "video-ad",
         "stage": "final-needs-you", "since": "2026-10-20", "in_owner": True},
        # emails: editor's pictures due tomorrow (at risk), one scheduled (Launch), one sent (live)
        {"id": "brand_a__nov-05", "title": "Email A", "brand": "brand_a", "type": "email", "turn": "editor: pictures",
         "editor_due": "2026-11-04", "send_date": "2026-11-06", "send_date_ok": True,
         "email_link": {"url": "http://127.0.0.1:8765/#brand_a__nov-05"}},
        {"id": "brand_a__nov-06", "title": "Email B", "brand": "brand_a", "type": "email", "turn": "editor: pictures",
         "editor_due": "2026-11-04", "send_date": "2026-11-07", "send_date_ok": True},
        # a brand_b email on the same picture day: a card of its own, by brand (email_lead, 2026-11-03)
        {"id": "brand_b__nov-06", "title": "Email P", "brand": "brand_b", "type": "email", "turn": "editor: pictures",
         "editor_due": "2026-11-04", "send_date": "2026-11-07", "send_date_ok": True},
        # a Black Friday email, its pictures due the same day as the statics: a lot of its own, in the campaign
        {"id": "brand_a__nov-43", "title": "Email BF", "brand": "brand_a", "type": "email", "turn": "editor: pictures",
         "editor_due": "2026-11-06", "send_date": "2026-11-30", "send_date_ok": True, "moment": "black-friday"},
        # held: 5 pictures to fill (editor's) and a price only email_lead settles, pictures due in 2 days: act now
        {"id": "brand_a__nov-09", "title": "Email H", "brand": "brand_a", "type": "email", "turn": "editor: pictures",
         "status": "held", "held": ["5 picture slot(s) still to fill"], "held_email_lead": ["price $49.99 · not in the brand's price list"],
         "editor_due": "2026-11-05", "send_date": "2026-11-09", "send_date_ok": True},
        # held on email_lead's decision only, far off: at risk, not act now
        {"id": "brand_b__nov-20", "title": "Email G", "brand": "brand_b", "type": "email", "turn": "editor: pictures",
         "status": "held", "held": [], "held_email_lead": ["guarantee not word for word"],
         "editor_due": "2026-11-20", "send_date": "2026-11-24", "send_date_ok": True},
        {"id": "brand_b__nov-04", "title": "Email C", "brand": "brand_b", "type": "email", "status": "scheduled",
         "turn": "Scheduled · 2026-11-05", "send_date": "2026-11-05", "send_date_ok": True},
        {"id": "brand_b__nov-01", "title": "Email D", "brand": "brand_b", "type": "email", "stage": "live",
         "turn": "Sent 2026-11-01", "send_date": "2026-11-01", "send_date_ok": True},
    ],
    # owner's promo calendar (view.py `calendar`): planned pieces, no brief yet
    "calendar": {"as_of": "2026-11-04T05:30:31Z", "entries": [
        {"id": "cal-bf-edit", "brand": "brand_a", "type": "video-ad", "role": "video editor", "lane": "promo",
         "moment": "black-friday", "due": "2026-11-05", "title": "Black Friday 2026 · Video ad 1 · brand_a"},
        {"id": "cal-xmas-org", "brand": "brand_b", "type": "video-ad", "role": "organic", "lane": "promo",
         "moment": "christmas", "due": "2026-12-20", "title": "Christmas · Organic 1"},
        {"id": "cal-ever", "brand": "brand_a", "type": "image-ad", "role": "designer", "lane": "evergreen",
         "moment": None, "due": "2026-11-15", "title": "Evergreen · Image ad 1"},
        {"id": "cal-page", "brand": "brand_b", "type": "landing-page", "role": "developer", "lane": "promo",
         "moment": "black-friday", "due": "2026-11-02", "title": "Black Friday · Page 1"},
        {"id": "cal-mail", "brand": "brand_b", "type": "email", "role": "email", "moment": "black-friday", "due": "2026-11-13"},
        {"id": "cal-sms", "brand": "brand_b", "type": "email", "role": "sms", "moment": "black-friday", "due": "2026-11-13"},
    ]},
}
STATICS = {"rows": [
    hand("brand_a_flex-face-brush_brief-0297", "Black Friday flat-lay", "brand_a", back=2),
    hand("brand_a_flex-face-brush_brief-0301", "Black Friday mail day", "brand_a", moment="black-friday"),
    hand("brand_b_brilliance-body-scrub_brief-0310", "Wardrobe jailbreak", "brand_b"),
    hand("brand_b_brilliance-body-scrub_brief-0314", "Bubble haul", "brand_b"),
    hand("brand_a_flex-face-brush_brief-0296", "Warehouse", "brand_a", back=10, done=True),
    # all five versions back, no Done: finished all the same (owner, 2026-11-04: returned/ is the signal)
    hand("brand_a_flex-face-brush_brief-0302", "Black Friday Draft", "brand_a", back=5, versions=5),
    # two of five back, no Done: still editor's
    hand("brand_a_flex-face-brush_brief-0305", "Barbershop", "brand_a", back=2, versions=5, moment="black-friday"),
    # due in 2 days with nothing back: act now (email_lead, 2026-11-04)
    hand("brand_a_flex-face-brush_brief-0306", "Ejection notice", "brand_a", back=0, versions=5),
]}
VIDEOS = {"rows": [hand("brand_a_flex-face-brush_brief-0318", "Barber Mission", "brand_a")]}


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class Rules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        page = read(PAGE)
        helpers = "".join(fn(page, n) for n in ("val", "plural", "isEmail", "turnWho", "briefOf", "productOf",
                                                 "sameBrief", "roundOf", "keepQueued", "uniq"))
        js = helpers + core(page) + """
var b = boardPieces(%s, %s, %s), lots = boardLots(b.pieces, %s);
console.log(JSON.stringify({
  pieces: b.pieces.map(function (p) { return [p.id, p.col, p.who || "", p.flag]; }),
  bank: b.bank, live: b.live, calMail: b.calMail, calAsOf: b.calAsOf, laterDays: BOARD_LATER_DAYS,
  cols: BOARD_COLS.map(function (c) { return c.key; }),
  plan: b.pieces.filter(function (p) { return p.col === "plan"; }).map(function (p) { return [p.id, p.type, p.moment, p.maker]; }),
  lots: lots.map(function (g) { return [g.col, g.who || "", g.type, g.items.length, g.flag, g.why, g.moment]; }),
  order: BOARD_COLS.map(function (c) { return columnOrder(lots.filter(function (g) { return g.col === c.key; }))
    .map(function (x) { return x.due || ""; }); }),
  orderFlags: columnOrder(lots.filter(function (g) { return g.col === "making"; })).map(function (x) { return [x.due || "", x.flag]; }),
  camps: campaigns(lots.filter(function (g) { return g.col === "making"; })).map(function (c) {
    return [c.moment, c.flag, c.due, c.lots.map(function (g) { return [g.type, g.brand, g.items.length]; })]; }),
  names: ["black-friday", "nba-regular-season", "veterans-day", "evergreen"].map(momentName),
  line: claudeLine("brand_b_brilliance-body-scrub_brief-0314", "brand_b", "graphic-designer"),
  days: boardDays(b.pieces, %s, "editor"),
  ends: ["2026-11-03", "2026-11-05", "2026-11-07"].map(function (d) { return workdayEnd(d, BOARD_WORKDAYS); }),
  sets: ["editor", "creator"].reduce(function (o, who) { ["@working", "@coming", "@finished", "@nodate"].forEach(function (w) {
    o[who + w] = b.pieces.filter(function (p) { return makerHas(p, who, w); }).map(function (p) { return p.id; }).sort(); }); return o; }, {}),
  whoHas: ["editor", "creator", "owner", "email_lead", "Nobody yet"].reduce(function (o, who) {
    o[who] = b.pieces.filter(function (p) { return boardWhoHas(p, who); }).map(function (p) { return p.id; }).sort(); return o; }, {}),
  planWhy: lots.filter(function (g) { return g.col === "plan" && g.type === "video"; }).map(function (g) { return g.why; }),
  onDay: boardDays(b.pieces, %s, "editor").map(function (d) {
    return [d.day, d.n, lots.filter(function (g) { return lotOnDay(g, "editor", d.day, %s); })
                          .reduce(function (s, g) { return s + g.items.length; }, 0)]; })
}));""" % (json.dumps(DATA), json.dumps(STATICS), json.dumps(VIDEOS), json.dumps(TODAY), json.dumps(TODAY),
           json.dumps(TODAY), json.dumps(TODAY))
        cls.got = run_node(js)
        cls.by_id = {p[0]: p[1:] for p in cls.got["pieces"]}

    def test_each_piece_once_in_its_column_with_its_person_and_flag(self):
        self.assertEqual(self.by_id, {
            "brand_a_flex-face-brush_brief-0297": ["making", "editor", "risk"],      # its queue row's due, Nov 5
            "brand_a_flex-face-brush_brief-0301": ["making", "editor", "risk"],      # its own loose date, Nov 6
            "brand_b_brilliance-body-scrub_brief-0310": ["making", "editor", "late"],   # loose Nov 1, passed
            "brand_b_brilliance-body-scrub_brief-0314": ["making", "editor", "unclear"],  # no date, not on owner's list
            "brand_a_flex-face-brush_brief-0296": ["review", "owner", ""],         # editor pressed Done: owner's button
            "brand_a_flex-face-brush_brief-0302": ["review", "owner", ""],         # 5 of 5 back, no Done: finished
            "brand_a_flex-face-brush_brief-0305": ["making", "editor", "risk"],       # 2 of 5 back: still hers, due Nov 6
            "brand_a_flex-face-brush_brief-0306": ["making", "editor", "late"],       # due in 2 days, nothing back
            "brand_a__nov-09": ["making", "editor", "late"],                          # held, pictures due in 2 days
            "brand_b__nov-20": ["making", "editor", "risk"],                         # held on email_lead's decision
            "brand_a_flex-face-brush_brief-0318": ["making", "creator", "unclear"],
            "brand_a_crush_brief-0100": ["brief", "owner", "waiting"],             # waiting 10 days: its own grey mark
            "brand_a_crush_brief-0101": ["brief", "owner", ""],
            "brand_b_brilliance-face-scrub_brief-0314": ["brief", "owner", ""],   # never joined to body scrub 0314
            "brand_b_scrub_brief-0600": ["making", "owner", "unclear"],           # owner's video line
            "brand_b_scrub_brief-0601": ["editing", "creator", ""],
            "brand_b_scrub_brief-0602": ["review", "owner", "waiting"],
            "brand_a__nov-05": ["making", "editor", "risk"],                          # pictures due tomorrow
            "brand_a__nov-06": ["making", "editor", "risk"],
            "brand_a__nov-43": ["making", "editor", "risk"],
            "brand_b__nov-06": ["making", "editor", "risk"],                          # pictures due Nov 6
            "brand_b__nov-04": ["launch", "", ""],
            "cal-bf-edit": ["plan", "owner", "risk"],                             # due in 2 days, no brief yet
            "cal-xmas-org": ["plan", "owner", ""],
            "cal-ever": ["plan", "owner", ""],
            "cal-page": ["plan", "owner", "late"],
        })

    def test_a_day_box_picks_exactly_its_own_pieces(self):
        """Victoria, 2026-11-04: "are the dates supposed to be clickable". A click on a day shows the cards holding that
        maker's pieces due that day, Past due included: as many pieces as the box counts, and only editor's."""
        self.assertTrue(self.got["onDay"])
        for day, n, shown in self.got["onDay"]:
            self.assertEqual(shown, n, "day %s: the box counts %d, the board shows %d" % (day, n, shown))
        self.assertIn("late", [d[0] for d in self.got["onDay"]], "Past due is a box too")

    def test_each_column_runs_soonest_due_first(self):
        """email_lead, 2026-11-05: "ver lo que está due primero y de ahí vaya bajando a lo que sigue due" (what is due first
        on top, then down to what is due next). Campaigns and loose cards together, by due day; no date last."""
        for col in self.got["order"]:
            dated = [d for d in col if d]
            self.assertEqual(dated, sorted(dated))
            self.assertEqual(col, dated + [""] * (len(col) - len(dated)), "cards with no date go last")
        flags = self.got["orderFlags"]
        for (d1, f1), (d2, f2) in zip(flags, flags[1:]):
            if d1 == d2:
                rank = {"late": 4, "risk": 3, "unclear": 2, "waiting": 1, "": 0}
                self.assertGreaterEqual(rank[f1], rank[f2], "same day: the worse flag first")

    def test_each_maker_working_on_coming_and_finished(self):
        """email_lead, 2026-11-05: what creator is working on and what is coming to him; editor the same."""
        s = self.got["sets"]
        self.assertEqual(s["creator@working"], ["brand_a_flex-face-brush_brief-0318", "brand_b_scrub_brief-0601"])
        self.assertEqual(s["creator@nodate"], ["brand_a_flex-face-brush_brief-0318"], "0601 has a due date")
        self.assertEqual(s["creator@coming"], ["cal-bf-edit"], "the calendar's video editor piece")
        self.assertEqual(s["editor@coming"], ["cal-ever"], "the calendar's designer piece")
        self.assertEqual(s["creator@finished"], [])
        self.assertIn("brand_a_flex-face-brush_brief-0296", s["editor@finished"], "Done pressed: finished")
        self.assertIn("brand_a_flex-face-brush_brief-0302", s["editor@finished"], "every version back: finished")
        for w in s["editor@working"]:
            self.assertNotIn(w, s["editor@finished"])
        self.assertNotIn("cal-xmas-org", s["creator@coming"] + s["editor@coming"], "organic is nobody's by role")
        self.assertEqual(self.got["planWhy"], [["no brief yet", "then: creator (video editor)"]])

    def test_the_left_filters_work_in_every_view_and_the_menu_folds(self):
        """designer via email_lead, 2026-11-12: the People filter on the left works in every view, and the menu can fold away."""
        page = read(PAGE)
        self.assertIn('people = ["email_lead", "editor", "creator", "owner"].filter(function (w) { return load[w] && (!boardWho || w === boardWho); });', page)
        self.assertIn("&& (!boardWho || whoOf(r) === boardWho.toLowerCase()) && (!boardBrand || val(r.brand).toLowerCase() === boardBrand); });", page)
        self.assertIn('calPick = ""; render(); return; }   // a person filters the view you are on', page, "picking a person keeps the view")
        self.assertIn('id="cq-rail-fold"', page); self.assertIn('id="cq-rail-open"', page)
        self.assertIn(".cq.rail-min .wrap>.rail{display:none}", page)
        # email_lead, 2026-11-12: "no puedo hacer scroll en el board ... metido como en un cuadro": the Board has no pane of its own
        self.assertIn(".cq .bd-cols{display:grid;grid-template-columns:repeat(6,minmax(172px,1fr));gap:12px;align-items:start;padding-bottom:8px}", page)
        self.assertNotIn("overscroll-behavior:contain", page)
        # email_lead, 2026-11-12: no legend and no purpose line on the Calendar; a note under the week only when something is open
        self.assertNotIn('<p class="cal-key">', page)
        self.assertIn('<p class="cal-note" id="cq-cal-note" data-feature="82" hidden></p>', page)
        # email_lead, 2026-11-12: "que sea solo si hay algo overdue ... una alerta": before today and not done; today is not overdue
        self.assertIn('if (d < today) open = open.concat(load[w][d] || []);', page)
        self.assertIn('box.innerHTML = late.length ? "Overdue: " + late.join(" · ") : ""; box.hidden = !late.length;', page, "nothing overdue: no note")
        self.assertNotIn("Still to do this week", page)

    def test_overdue_rolls_to_today_and_the_week_holds_until_friday_ends(self):
        """email_lead, 2026-11-13: overdue work "que se corra para el día siguiente, pero como overdue", and "no me cambies la
        semana hasta que se acabe mi viernes"."""
        got = self._core("""console.log(JSON.stringify([rollDay("2026-11-13"), rollDay("2026-11-14"), rollDay("2026-11-15"),
          rollDay("2026-11-16"), weekOf(rollDay("2026-11-13")), weekOf(rollDay("2026-11-14"))]));""")
        self.assertEqual(got, ["2026-11-13", "2026-11-16", "2026-11-16", "2026-11-16", "2026-11-09", "2026-11-16"],
                         "Friday keeps its own week; Saturday and Sunday open the next one")
        page = read(PAGE)
        self.assertIn("calWeek = weekOf(rollDay(isoToday())) <= last ? weekOf(rollDay(isoToday())) : first;", page)
        self.assertNotIn("weekOf(nextWorkday(isoToday()))", page, "Friday no longer jumps to next week")
        self.assertIn('var x = calWho(w, d, load, evDay[d], d === rollDay(today));', page, "overdue sits on today's box")
        self.assertIn('b.appendChild(kindLine(g.items.length, g.word, g.items, "bad", "overdue: "));', page)
        self.assertIn('[[late, "Overdue: its day has passed and it is not done yet"]', page, "and opens in today's list")
        self.assertNotIn('"mg-late"', page, "no separate Past due strip")
        # designer via email_lead, 2026-11-16: "no puede ir para atrás en el calendar": past weeks with done work are reachable
        self.assertIn('var d = k.replace(/^[+!=]/, "");', page, "done days count toward the range")
        self.assertIn("if (weekOf(d) < first) first = weekOf(d);", page, "the first week can be before this one")

    def test_brands_filter_from_the_pieces(self):
        """email_lead, 2026-11-11: "necesito poder filtrar también por marca". No brand is written in the page; the rail builds them."""
        page = read(PAGE)
        self.assertIn('id="cq-brandseg" data-feature="90"', page)
        self.assertNotIn('data-brand="', page, "brand buttons come from the pieces, never hard-coded")
        self.assertIn("var shown = boardBrand ? mine.filter(function (p) { return val(p.brand).toLowerCase() === boardBrand; }) : mine;", page,
                      "a brand narrows inside the picked person")
        self.assertNotIn('class="r-brand"><i>', page, "no logo square")

    def test_picking_a_person_keeps_only_their_pieces(self):
        """developer, 2026-11-05 call: "if you filter for editor, does it just show her stuff on this board?\""""
        h, s, pieces = self.got["whoHas"], self.got["sets"], self.got["pieces"]
        for who in ("editor", "creator"):
            for w in ("@working", "@coming", "@finished"):
                if who == "editor" and w == "@coming": continue   # hidden from her filter, asserted just below
                for i in s[who + w]:
                    self.assertIn(i, h[who], who + w + " is on " + who + "'s board")
        for i in s["editor@coming"]:
            self.assertNotIn(i, h["editor"], "email_lead, 2026-11-11: no brief yet is not on editor's filter")
        self.assertIn("var PLANNED_HIDDEN = [\"editor\"];", read(PAGE))
        self.assertIn('if (c[0] === "@coming" && PLANNED_HIDDEN.indexOf(who) >= 0) return;', read(PAGE), "and no planned count in her row")
        self.assertIn("brand_a_flex-face-brush_brief-0296", h["owner"], "editor's finished static is owner's move: on both boards")
        self.assertIn("brand_a_flex-face-brush_brief-0296", h["editor"])
        self.assertNotIn("cal-ever", h["creator"], "a designer piece is not coming to the video editor")
        self.assertEqual(h["Nobody yet"], sorted(p[0] for p in pieces if not p[2]))
        for who in ("editor", "creator", "owner", "email_lead"):
            mine = {p[0] for p in pieces if p[2] == who}
            self.assertTrue(mine <= set(h[who]), "every piece whose next move is " + who + " stays on their board")
        page = read(PAGE)
        self.assertIn('<template id="cq-t-who"><button type="button" class="b-who" data-feature="68"></button></template>', page)
        self.assertIn('boardWho = boardWho === w ? "" : w; boardFocus = ""; dayFocus = ""; render();', page)   # render: the rail's name and the title follow (2026-11-11)
        self.assertIn('if (per) { boardWho = boardWho === per ? "" : per;', page, "owner and email_lead in the rail are the same filter")
        self.assertIn('if (boardWho !== who) return;', page, "a maker's days show once that maker is picked (2026-11-11)")
        self.assertIn('return g.lane === c.key && (!(boardFocus || dayFocus) || hitLot(g, today));', page, "a pick filters the columns, it does not dim them")
        self.assertLess(page.index('id="cq-bd-people"'), page.index('id="cq-bd-days"'), "the people first, then the picked maker's days")

    def test_stuck_and_sent_back_climb_to_act_now_in_production_and_edit_only(self):
        """developer, 2026-11-05 call: a flag until it is cleared; email_lead: "Only Production and Edit"."""
        page = read(PAGE)
        helpers = "".join(fn(page, n) for n in ("val", "plural", "isEmail", "turnWho", "briefOf", "productOf",
                                                 "sameBrief", "roundOf", "keepQueued", "uniq"))
        T = "2026-11-05"
        got = run_node(helpers + core(page) + """
var T = %s, P = [
  {id: "a", col: "making", who: "", due: "", since: "2026-10-01"},
  {id: "b", col: "making", who: "", due: "", since: "2026-10-30"},
  {id: "c", col: "editing", who: "owner", due: "", since: "2026-10-20"},
  {id: "d", col: "brief", who: "owner", due: "", since: "2026-09-01"},
  {id: "e", col: "making", who: "editor", due: "2026-11-20", since: "2026-09-01"},
  {id: "f", col: "making", who: "", due: "", since: "2026-11-01", row: {flag: "sent-back"}},
  {id: "g", col: "review", who: "owner", due: "", since: "2026-11-01", row: {flag: "sent-back"}}];
console.log(JSON.stringify({
  flags: P.map(function (p) { return [p.id, boardFlag(p, T), stuckDays(p, T)]; }),
  why: lotWhy({col: "making", who: "", items: [P[0], P[5]]}, T),
  prog: lotProgress([{handoff: {}, checks: true}, {handoff: {}, back: 3}, {handoff: {}}, {handoff: {}}, {}]),
  one: lotProgress([{handoff: {}}])}));""" % json.dumps(T))
        f = {x[0]: x[1:] for x in got["flags"]}
        self.assertEqual(f["a"], ["late", 35], "nobody, no date, 35 days in Production: Act now")
        self.assertEqual(f["b"], ["unclear", 0], "6 days: still only Unclear")
        self.assertEqual(f["c"], ["late", 16], "Edit counts too")
        self.assertEqual(f["d"][0], "waiting", "Brief review keeps Waiting")
        self.assertEqual(f["e"], ["", 0], "someone has it with a date: not stuck")
        self.assertEqual(f["f"][0], "late", "owner sent it back")
        self.assertNotEqual(f["g"][0], "late", "sent back counts in Production and Edit only")
        self.assertIn("in place 35 days", got["why"])
        self.assertIn("1 sent back by owner", got["why"])
        self.assertEqual(got["prog"], {"n": 4, "fin": 1, "bk": 1, "no": 2}, "hand-offs only")
        self.assertIsNone(got["one"], "one hand-off: no bar")

    def test_the_calendar_counts_each_persons_day(self):
        """email_lead, 2026-11-05: a calendar of each person's load per day, Monday to Friday, her emails to write in it."""
        page = read(PAGE)
        helpers = "".join(fn(page, n) for n in ("val", "plural", "isEmail", "turnWho", "briefOf", "productOf",
                                                 "sameBrief", "roundOf", "keepQueued", "uniq"))
        got = run_node(helpers + core(page) + """
var T = "2026-11-05", P = [
  {id: "e1", col: "making", who: "editor", due: "2026-11-06", type: "static"},
  {id: "e2", col: "making", who: "editor", due: "2026-11-08", type: "static"},    // a Sunday: on Friday the 6th
  {id: "e3", col: "making", who: "editor", due: "2026-11-02", type: "email"},     // before today
  {id: "d1", col: "plan", who: "owner", due: "2026-11-13", maker: "video editor"},
  {id: "d2", col: "brief", who: "owner", due: "", type: "static"},
  {id: "f1", col: "review", who: "owner", due: "2026-11-09", checks: true},
  {id: "l1", col: "launch", who: "", due: "2026-11-09"}],
  W = [{brand: "brand_b", slot: "nov-17", month: "2026-11", send: "2026-11-18", type: "moment"},
       {brand: "brand_a", slot: "nov-20", month: "2026-11", send: "2026-11-23", type: "sale-window"}];
var L = calLoad(P, W, T), ids = function (a) { return (a || []).map(function (p) { return p.id; }); };
console.log(JSON.stringify({eve6: ids(L.editor["2026-11-06"]), eveLate: ids(L.editor.late), owner: L.owner || null,
  creator: L.creator || null, steph16: ids(L.email_lead["2026-11-11"]), steph19: ids(L.email_lead["2026-11-16"]),
  eveComing17: ids(L.editor["+2026-11-17"]), eveComing20: ids(L.editor["+2026-11-20"]),
  months: [monthShift("2026-12", 1), monthShift("2026-01", -1)], heat: [0, 2, 3, 6, 10].map(calHeat),
  back: [workdayBack("2026-11-18", 2), workdayBack("2026-11-23", 1)]}));""")
        self.assertEqual(got["eve6"], ["e1", "e2"], "a Sunday's work lands on the Friday before")
        self.assertEqual(got["eveLate"], ["e3"])
        self.assertIsNone(got["owner"], "To make dates are campaign dates, a finished piece and Launch count for nobody")
        self.assertIsNone(got["creator"], "email_lead, 2026-11-12: a piece with no brief yet is on nobody's day; the Calendar shows what really exists")
        # email_lead's day is email_lead_LEAD working days before (5 from 2026-11-11, 3 from 2026-11-16: "Bájalo a 3 días") before the email must be on editor's page ("agéndame los correos más cerca")
        self.assertEqual(got["steph16"], ["brand_b__nov-17"], "on editor's page Mon 16 (two working days before a Wednesday send): email_lead writes it Wed 11")
        self.assertEqual(got["steph19"], ["brand_a__nov-20"], "on editor's page Thu 19: email_lead writes it Mon 16")
        self.assertEqual(got["eveComing17"], ["brand_b__nov-17"], "editor: the working day before")
        self.assertEqual(got["eveComing20"], ["brand_a__nov-20"])
        self.assertEqual(got["months"], ["2027-01", "2025-12"])
        self.assertEqual(got["heat"], ["", "h1", "h2", "h3", "h4"])
        self.assertEqual(got["back"], ["2026-11-16", "2026-11-20"])
        self.assertIn('<button type="button" data-view="calendar" aria-pressed="false" data-feature="74">Calendar</button>', page)
        self.assertIn('cal = location.hash === "#calendar"', page)

    def _core(self, js):
        page = read(PAGE)
        helpers = "".join(fn(page, n) for n in ("val", "plural", "isEmail", "turnWho", "briefOf", "productOf",
                                                 "sameBrief", "roundOf", "keepQueued", "uniq"))
        return run_node(helpers + core(page) + js)

    def test_every_view_gives_an_email_of_eves_the_calendars_day(self):
        """email_lead, 2026-11-10, "Regla del Calendar": editor counted 8 emails for Nov 10 in her view, the Calendar 7.
        brand_a-nov-58 had no saved deadline: her view took view.py's 5 working days before the send (Nov 10), the
        Calendar its free place at 7 a day (Nov 12). Now one day for it everywhere: the Calendar's."""
        got = self._core("""
function em(id, send, due, from) { return {id: id, type: "email", read_only: "email", brand: id.split("__")[0], title: id,
  turn: "editor: pictures", send_date: send, send_date_ok: true, editor_due: due, editor_due_from: from}; }
var rows = [];
["a", "b", "c", "d", "e", "f", "g"].forEach(function (k) { rows.push(em("brand_a__nov-1" + k, "2026-11-16", "2026-11-11", "deadlines.json")); });
rows.push(em("brand_a__nov-58", "2026-11-17", "2026-11-10", "5 working days before the send"));
rows.push(em("brand_b__nov-30", "2026-11-12", "2026-11-05", "5 working days before the send"));
rows.push(em("brand_b__nov-31", "2026-11-24", "2026-11-17", "5 working days before the send"));
var d = {rows: rows, towrite: [], loose: {"brand_b__nov-31": {due: "2026-11-20", due_by: "designer"}}};
eveDays(d, null, null, "2026-11-10", {});
var first = {}; d.rows.forEach(function (r) { first[r.id] = [r.editor_due, r.editor_due_from]; });
eveDays(d, null, null, "2026-11-10", {});
var again = {}; d.rows.forEach(function (r) { again[r.id] = r.editor_due; });
console.log(JSON.stringify({first: first, again: again}));""")
        f = got["first"]
        self.assertEqual(f["brand_a__nov-1a"], ["2026-11-11", "deadlines.json"], "a saved deadline stays")
        self.assertEqual(f["brand_a__nov-58"][0], "2026-11-12", "no saved date: the Calendar's day (Nov 11 is full at 7)")
        self.assertIn("editor's load", f["brand_a__nov-58"][1])
        self.assertEqual(f["brand_b__nov-30"][0], "2026-11-11", "sends Thu Nov 12, Nov 11 is full: won't make it, due the working day before")
        self.assertIn("won't make it", f["brand_b__nov-30"][1])
        self.assertEqual(f["brand_b__nov-31"], ["2026-11-20", "moved by designer"], "a mover's day is the day")
        self.assertEqual(got["again"]["brand_a__nov-58"], "2026-11-12", "a second render gives the same day, from view.py's value")

    def test_the_emails_page_takes_the_content_queues_day(self):
        """email_lead, 2026-11-10, "Sí, la de emails": the emails page has no rule of its own for editor's day any more. A date
        email_lead set wins; otherwise the day the content queue gives (it opens unseen beside the page and posts them)."""
        em = read(PAGE.replace("content-queue.html", "emails.html"))
        self.assertNotIn("editor_WORKDAYS", em.split('id="fo-features"')[0] + em.split('id="fo-features"')[1].split("</script>", 1)[1],
                         "the 5-working-days default is gone from the page's code")
        self.assertIn('f.src="/p/_templates/content-queue.html#editor-days"', em)
        self.assertIn("ev.origin!==location.origin", em, "only this page server's own content queue is heard")
        i = em.index("const QDAY={};")
        got = run_node(em[i:em.index("\n", em.index("function dueFrom", i))] + """
QDAY["brand_a__nov-58"] = {day: "2026-11-12", from: "editor's load, 7 a day (4 on statics days)"};
console.log(JSON.stringify([dueOf({id: "brand_a__nov-58", send_day: "2026-11-17"}), dueFrom({id: "brand_a__nov-58"}),
  dueOf({id: "brand_a__nov-13", editor_due: "2026-11-10", send_day: "2026-11-13"}), dueFrom({id: "x", editor_due: "2026-11-10"}),
  dueOf({id: "brand_b__nov-99", send_day: "2026-11-30"})]));""")
        self.assertEqual(got, ["2026-11-12", "editor's load, 7 a day (4 on statics days)", "2026-11-10", "set by email_lead", ""],
                         "the content queue's day; a set date wins; no day known: none invented")
        page = read(PAGE)
        self.assertIn("window.parent.postMessage({cqEveDays: days}, location.origin)", page)

    def test_priorities_order_the_column_and_drop_leaves(self):
        """developer, 2026-11-05 call: owner prioritizes in the check-in; email_lead: Now / Next / Later / Drop."""
        got = self._core("""
var d = {rows: [
  {id: "x_a_brief-0001", title: "A", brand: "brand_a", type: "image-ad", stage: "making", who: "editor", due: "2026-11-06", priority: null},
  {id: "x_a_brief-0002", title: "B", brand: "brand_a", type: "image-ad", stage: "making", who: "editor", due: "2026-11-20", priority: "1"},
  {id: "x_a_brief-0003", title: "C", brand: "brand_a", type: "carousel", stage: "making", who: "editor", due: "2026-11-01", priority: "low"},
  {id: "x_a_brief-0004", title: "D", brand: "brand_b", type: "image-ad", stage: "making", who: "editor", due: "2026-11-07", priority: "drop"},
  {id: "x_a_brief-0005", title: "E", brand: "brand_b", type: "carousel", stage: "making", who: "editor", due: "2026-11-09"}],
  loose: {"x_a_brief-0005": {priority: "top"}}};
var b = boardPieces(d, null, null), lots = boardLots(b.pieces, "2026-11-05");
console.log(JSON.stringify({ids: b.pieces.map(function (p) { return [p.id, p.prio]; }), dropped: b.dropped,
  order: columnOrder(lots.filter(function (g) { return g.col === "making"; })).map(function (x) { return x.lot.items[0].title; }),
  words: ["1", "2", "3", "top", "high", "normal", "low", "drop", "4", "", null, "Now"].map(prioNorm)}));""")
        self.assertEqual(got["dropped"], 1)
        self.assertNotIn("x_a_brief-0004", [x[0] for x in got["ids"]], "Drop: off the board")
        self.assertEqual(dict(got["ids"])["x_a_brief-0005"], "now", "a priority set on a loose id counts")
        self.assertEqual(got["order"], ["E", "B", "A", "C"], "Now first (soonest due among them), then not set, Later last though it is late")
        self.assertEqual(got["words"], ["now", "next", "later", "now", "now", "next", "later", "drop", "", "", "", "now"])

    def test_eves_load_packs_earliest_first_seven_a_day_statics_or_not(self):
        """email_lead, 2026-11-05: "que siempre tenga la mayor cantidad de correos posibles en su día"; from her next day.
        email_lead, 2026-11-10: "Siempre 7" (was 4 on a day with statics, 2026-11-06): a static due that day takes no email's place."""
        got = self._core("""
var T = "2026-11-19", R = function (id, due, send, set) { return {id: id, col: "making", who: "editor", type: "email", due: due, send: send,
  row: {editor_due_from: set ? "deadlines.json" : "5 working days before the send"}}; };
var P = [R("fixed1", "2026-11-20", "2026-11-24", true), R("fixed2", "2026-11-20", "2026-11-24", true),
         R("late1", "2026-11-18", "2026-11-20", true), R("w1", "2026-11-17", "2026-11-25", false),
         {id: "s1", col: "making", who: "editor", type: "static", due: "2026-11-23"}],
  W = []; for (var i = 1; i <= 9; i++) W.push({brand: "brand_b", slot: "nov-" + (10 + i), send: i <= 7 ? "2026-11-24" : "2026-11-25"});
var r = evePack(P, W, T, {}), off = evePack(P, W, T, {"2026-11-20": true});
var f = function (x) { return [x.day, x.fixed.map(function (p) { return p.id; }), x.packed.map(function (q) { return q.item.slot || q.item.id; }), x.cap]; };
console.log(JSON.stringify({start: r.start, days: r.days.map(f), late: r.late.map(function (p) { return p.id; }),
  over: r.overflow.map(function (q) { return q.item.slot || q.item.id; }), fit: r.fit, statics: r.statics,
  onPage: r.days[0].packed.map(function (q) { return q.onPageBy; }), offOver: off.overflow.length, offDays: off.days.slice(0, 3).map(f)}));""")
        self.assertEqual(got["start"], "2026-11-20", "today is over: from her next working day")
        self.assertEqual(got["days"][:3], [["2026-11-20", ["fixed1", "fixed2"], ["nov-11", "nov-12", "nov-13", "nov-14", "nov-15"], 7],   # a set deadline stays
                                           ["2026-11-23", [], ["nov-16", "nov-17", "w1", "nov-18", "nov-19"], 7],   # a static due that day: still 7
                                           ["2026-11-24", [], [], 7]])
        self.assertEqual(got["over"], [], "Tuesday's sends all fit by Monday")
        self.assertEqual(got["late"], ["late1"])
        self.assertEqual(got["fit"], 12)
        self.assertEqual(got["statics"], 1, "statics are not counted as emails")
        self.assertEqual(got["onPage"], ["2026-11-19"] * 5, "still to write: on her page the working day before")
        self.assertEqual(got["offDays"], [["2026-11-20", ["fixed1", "fixed2"], [], 0],   # a day off has no places: nothing packed on it
                                          ["2026-11-23", [], ["nov-11", "nov-12", "nov-13", "nov-14", "nov-15", "nov-16", "nov-17"], 7],
                                          ["2026-11-24", [], ["w1", "nov-18", "nov-19"], 7]], "a day off has no places")
        self.assertEqual(got["offOver"], 0, "Tuesday's sends fill Monday's seven; the rest send Wednesday")
        self.assertEqual(got["days"][-1][0], "2026-11-30", "every working day to the month's end")

    def test_seven_is_eves_floor_more_is_fine_fewer_says_why(self):
        """email_lead, 2026-11-10: "Lo que quiero es que no tenga menos de 7 a menos de que haya una justificación" (editor did 8
        that day; more may come later). 7 fills each day; a day above it is said plainly, never red; a day below it while
        later days hold emails names its reason (a day off, other work due) or says "no reason"; the last day is not short."""
        got = self._core("""
var T = "2026-11-19", F = function (id, due) { return {id: id, col: "making", who: "editor", type: "email", due: due, send: "2026-12-10",
  row: {editor_due_from: "deadlines.json"}}; }, P = [];
var n = {"2026-11-20": 5, "2026-11-23": 8, "2026-11-25": 6, "2026-11-26": 7, "2026-11-27": 3};
Object.keys(n).forEach(function (d) { for (var i = 0; i < n[d]; i++) P.push(F(d + "-" + i, d)); });
P.push({id: "s1", col: "making", who: "editor", type: "static", due: "2026-11-25"});
var r = evePack(P, [], T, {"2026-11-24": true});
console.log(JSON.stringify(r.days.slice(0, 6).map(function (x) { return [x.day, x.n, x.above, x.short, x.why]; })));""")
        self.assertEqual(got, [["2026-11-20", 5, 0, 2, ""],                  # 5 with later days full: 2 under, no reason
                               ["2026-11-23", 8, 1, 0, ""],                  # 8: one above, fine
                               ["2026-11-24", 0, 0, 7, "day off"],
                               ["2026-11-25", 6, 0, 1, "also 1 static due"],
                               ["2026-11-26", 7, 0, 0, ""],
                               ["2026-11-27", 3, 0, 0, ""]])                 # the last day with emails is never short
        page = read(PAGE)
        self.assertIn('b.appendChild(kindLine(em.length, "email", em));   // "7 emails", not "7 of 7" (designer, 2026-11-12); 7 is her floor: more is never red', page)
        self.assertNotIn("em.length > cap;", page, "more than 7 no longer turns the card red")
        self.assertIn('short + " under " + cap + (eveDay.why ? ": " + eveDay.why : ", no reason")', page)

    def test_eves_open_emails_reflow_from_her_today_and_done_counts_on_the_day_she_finished(self):
        """email_lead, 2026-11-16: "si editor hace 3 extra, que diga que entregó entre el viernes y hoy 14 emails, y que para
        mañana se reajusten a 7 emails". Her day is Bangkok's; what she finished that day takes its places."""
        got = self._core("""
var F = function (id, send) { return {id: id, col: "making", who: "editor", type: "email", due: "", send: send, row: {editor_due_from: "5 working days before the send"}}; };
var P = []; for (var i = 0; i < 12; i++) P.push(F("e" + i, "2026-12-0" + (1 + (i % 9))));
var rows = [{history: [{step: "editor finished the pictures", at: "2026-11-16T07:07:00+00:00"}]},
            {history: [{step: "editor finished the pictures", at: "2026-11-15T21:30:00+00:00"}]},
            {history: [{step: "editor finished the pictures", at: "2026-11-15T17:30:00+00:00"}]}];
var opt = eveOpt({rows: rows}, "2026-11-16"), r = evePack(P, [], "2026-11-16", {}, opt);
console.log(JSON.stringify({tz: [eveDay("2026-11-15T16:50:00Z"), eveDay("2026-11-15T17:30:00Z"), eveDay("2026-11-15T20:59:00Z"),
  eveDay("2026-11-15T21:00:00Z")], used: opt.used, from: opt.from,
  days: r.days.slice(0, 3).map(function (x) { return [x.day, x.n, x.used]; }),
  weekend: eveOpt({rows: []}, "2026-11-14").from, d: eveFinishedDay(rows[0])}));""")
        self.assertEqual(got["tz"], ["2026-11-15", "2026-11-15", "2026-11-15", "2026-11-16"],
                         "Bangkok's day, turning at 4am there (email_lead, 2026-11-25): 00:30 and 03:59 are still the day she "
                         "was working, 04:00 is the next")
        self.assertEqual(got["used"], {"2026-11-16": 2, "2026-11-15": 1})
        self.assertEqual(got["from"], "2026-11-16", "from her own today, not the day after")
        self.assertEqual(got["days"], [["2026-11-16", 5, 2], ["2026-11-17", 7, 0], ["2026-11-18", 0, 0]],
                         "two finished today: five more fit today, then seven tomorrow")
        self.assertEqual(got["weekend"], "2026-11-16", "a Saturday starts on Monday")
        self.assertEqual(got["d"], "2026-11-16", "a finished email sits on the day she finished it")
        page = read(PAGE)
        self.assertIn('who: "editor", day: eveFinishedDay(r) || val(r.editor_due),', page)

    def test_a_revision_and_a_numberless_hand_off_take_only_their_own_row(self):
        """email_lead, 2026-11-19: 0297/0298-holiday-revision showed "Overdue" the day they arrived, with the Nov 6 date of
        the Black Friday brief 0297; and editor's PM task never reached the board, eaten by a numberless idea hand-off."""
        got = self._core("""
var d = {rows: [
  {id: "brand_a_flex-face-brush_brief-0297", type: "image-ad", brand: "brand_a", stage: "making", who: "editor", due: "2026-11-06"},
  {id: "TSK-1-brand_b-x", type: "task", brand: "brand_b", title: "Storefront artwork", stage: null, who: "editor", due: "2026-11-25", read_only: "pm"}],
  loose: {}};
var st = {rows: [{key: "brand_a_flex-face-brush_brief-0297-holiday-revision", brand: "brand_a", title: "0297 fix", returned_work: 0,
                  revision: {round: null, why: "Correct $46 to $49"}},
                 {key: "brand_b_idea_dec26-s6", brand: "brand_b", title: "s6", returned_work: 0}]};
var b = boardPieces(d, st, {rows: []}).pieces, by = {}; b.forEach(function (p) { by[p.id] = [p.col, p.who, p.due]; });
var lots = boardLots(b, "2026-11-19"), rv = lots.filter(function (g) { return g.items.some(function (p) { return p.handoff && p.handoff.revision; }); })[0];
console.log(JSON.stringify({by: by, why: lotWhy(rv, "2026-11-19"), same: [sameBrief("brand_b_idea_dec26-s6", "TSK-1-brand_b-x"), sameBrief("a_b_brief-0001", "a_b_brief-0001-r2")]}));""")
        self.assertEqual(got["by"]["brand_a_flex-face-brush_brief-0297-holiday-revision"][2], "", "a revision does not take the original's Nov 6")
        self.assertEqual(got["by"]["TSK-1-brand_b-x"], ["making", "editor", "2026-11-25"], "the PM task is on the board with its own date")
        self.assertEqual(got["by"]["brand_b_idea_dec26-s6"][2], "", "a numberless hand-off takes no other row's date")
        self.assertIn("back for revision: Correct $46 to $49", got["why"])
        self.assertEqual(got["same"], [False, True])
        # 2026-11-19: a comment pasted mid-line once swallowed the title of every Calendar row; the title must be appended
        self.assertIn('p.title); t.addEventListener("click", open); body.appendChild(t);', read(PAGE))
        # email_lead, 2026-11-19: "que las pausas se vean en el calendar y en el board" and a PM task that explains itself
        held = self._core("""console.log(JSON.stringify([holdOf({row: {pm: {waiting_on: "December offer"}}}), holdOf({note: "On hold: x"}),
          holdOf({row: {note: "Held: y"}}), holdOf({note: "a note"})]));""")
        self.assertEqual(held, ["On hold: December offer", "On hold: x", "Held: y", ""])
        page = read(PAGE)
        self.assertIn('if (f.some(holdOf)) top.appendChild(el("span", "l-hold"', page, "an On hold tag on the Board card")
        self.assertIn('<p class="cal-hold" id="cq-cal-hold" data-feature="82" hidden></p>', page, "and a line under the Calendar week")
        self.assertIn('a.textContent = "Open the START card";', page, "a PM task opens its START card")
        self.assertIn("it is marked done in the PM.", page)
        self.assertIn('(pm.start || []).forEach(function (sec) {', page, "the START card's own words in the panel")
        page = read(PAGE)
        self.assertIn('uniq(f.map(function (p) { var h = holdOf(p), name =', page, "a hold says why on the card (the 10 brand_b Christmas statics wait on the December offer)")

    def test_a_writing_job_closes_once_owner_wrote_its_brief(self):
        """email_lead, 2026-11-24: the six Yai writing jobs stayed on creator's list after owner wrote them as briefs 0377-0382 on
        Nov 20 ("Sí, automático"). His register names the run each brief came from: the job's own key, or a later version."""
        got = self._core("""
var data = {register_runs: {"brand_b-yai-a1v3": {brief: "0377", opened: "2026-11-20"}, "brand_b-yai-b2v4": {brief: "0382", opened: "2026-11-20"},
  "brand_b-yai-a1-burn-leg-makeup-v2": {brief: "0376", opened: "2026-11-19"}, "brand_b-yai-c1v1": {brief: "0300", opened: "2026-11-01"}}};
function W(k) { return {key: k, writing: {held: false}, made: {at: "2026-11-19T08:55:58Z"}}; }
console.log(JSON.stringify([W("brand_b-yai-a1v3"), W("brand_b-yai-b2v3"), W("brand_b-yai-a2v3"), W("brand_b-yai-c1v2"), W("brand_b-yai-c1v1")]
  .map(function (s) { var w = writtenAs(s); return [s.key, w ? w.brief : "", handoffOff(s)]; })
  .concat([[ "not writing", writtenAs({key: "brand_b-yai-a1v3"}), handoffOff({key: "brand_b-yai-a1v3", rows: []})]])));""")
        self.assertEqual(got, [["brand_b-yai-a1v3", "0377", True], ["brand_b-yai-b2v3", "0382", True], ["brand_b-yai-a2v3", "", False],
                               ["brand_b-yai-c1v2", "", False], ["brand_b-yai-c1v1", "0300", True], ["not writing", None, False]],
                         "its own key or a later version closes it; an older version or another script never does; a video hand-off is untouched")

    def test_emails_email_lead_wrote_are_done_on_her_day(self):
        """email_lead, 2026-11-19: "Deberíamos poner las fechas en las que he escrito correos y cuántos ... en el calendar como
        hechos". The day the run was written, on her day, done; a weekend day counts on the Friday before."""
        got = self._core("""
function E(id, at) { return {id: id, type: "email", brand: "brand_a", title: "t", read_only: "email", turn: "editor: pictures", editor_due: "2026-12-08",
  send_date: "2026-12-12", written_at: at, history: []}; }
var d = {rows: [E("brand_a__a", "2026-11-19T17:29:54"), E("brand_a__b", "2026-11-19T18:02:00"), E("brand_a__c", "2026-11-08T10:00:00"), E("brand_a__d", null)]};
var b = boardPieces(d, null, null), w = b.done.filter(function (p) { return p.written; });
var load = calLoad(b.pieces, [], "2026-11-19", b.done);
console.log(JSON.stringify({days: w.map(function (p) { return [p.id, p.who, p.day]; }), word: kinds(w)[0].word,
  thu: (load.email_lead["=2026-11-19"] || []).length, fri: (load.email_lead["=2026-11-06"] || []).length}));""")
        self.assertEqual(got["days"], [["brand_a__a#written", "email_lead", "2026-11-19"], ["brand_a__b#written", "email_lead", "2026-11-19"],
                                       ["brand_a__c#written", "email_lead", "2026-11-06"]], "no day written, nothing made up")
        self.assertEqual(got["word"], "email written")
        self.assertEqual((got["thu"], got["fri"]), (2, 1), "done on the day she wrote them; Sunday Nov 8 on Friday Nov 6")

    def test_email_lead_never_writes_on_a_day_off(self):
        """email_lead, 2026-11-19 ("Sí, agrégalos"): off Fri Nov 20 and Mon Nov 23, vacation Nov 30 to Dec 4,
        the Bangkok week on, the Dec 14 flight off. A writing day on
        one moves to her next day on while that is before editor's page day, else back to her last day on."""
        got = self._core("""console.log(JSON.stringify([stephWriteDay("2026-11-26"), stephWriteDay("2026-11-27"),
  stephWriteDay("2026-12-04"), stephWriteDay("2026-11-24"), stephWriteDay(""), stephWriteDay("2026-12-10"), stephWriteDay("2026-12-17")]));""")
        self.assertEqual(got, ["2026-11-24", "2026-11-24", "2026-11-27", "2026-11-19", "", "2026-12-07", "2026-12-15"],
                         "Mon 23 off -> Tue 24; Tue 24 stays; Dec 1 (vacation) -> back to Fri Nov 27; Thu 19 stays; no page day, no day; "
                         "Bangkok Mon Dec 7 is a writing day; Mon Dec 14 (flight) -> Tue Dec 15, still before Dec 17's page day")

    def test_ahmeds_own_view_shows_only_what_was_sent_with_the_boards_day(self):
        """Audit, 2026-11-19: his view listed every folder in his inbox with no date (0332-0369 "no date yet" while the
        Calendar had them) and owner's held a3v2 and the unsent 0355 as his."""
        got = self._core("""
var k = ahmedView([
  {id: "brand_a_x_brief-0332", maker: "creator", role: "video-editor", unsent: false, due: "2026-11-20"},
  {id: "brand_b-yai-a3v2", maker: "creator", role: "video-editor", unsent: true, who: "owner", due: ""},
  {id: "brand_b_x_brief-0355", maker: "creator", role: "video-editor", unsent: true, who: "email_lead", due: ""},
  {id: "brand_b-yai-a1v3", maker: "creator", role: "video-editor", unsent: false, writing: true, due: "2026-11-20"},
  {id: "brand_a_x_brief-0297-holiday-revision", maker: "editor", role: "graphic-designer", unsent: false, due: "2026-11-20"}]);
console.log(JSON.stringify(k));""")
        self.assertEqual(got, {"brand_a_x_brief-0332": "2026-11-20", "brand_b-yai-a1v3": "2026-11-20"},
                         "only the videos sent to him, each with the Board's day; someone else's or unsent are not his")
        page = read(PAGE)
        self.assertIn("ahmedView(boardPieces(data, statics, videos).pieces)", page, "his view asks the Board")

    def test_ahmeds_videos_two_a_day_overdue_keeps_its_day(self):
        """email_lead, 2026-11-19: two briefs a day, from his next working day after they are sent ("ya su día terminó");
        one he hasn't finished stays overdue on the day it had and still takes a place; the rest move along, never
        overdue; a hand-set date stays."""
        got = self._core("""
function V(id, sent, fin, fixed) { return {id: "brand_a_x_brief-" + id, role: "video-editor", maker: "creator", who: "creator", unsent: false,
  sentDay: sent, finDay: fin || "", checks: !!fin, fixedDue: fixed || "", due: fixed || ""}; }
var out = [V("0001", "2026-11-13", "2026-11-16"), V("0002", "2026-11-13"), V("0003", "2026-11-13", "2026-11-17"),
           V("0004", "2026-11-13"), V("0005", "2026-11-13"), V("0006", "2026-11-13"), V("0007", "2026-11-17")];
ahmedFlow(out, "2026-11-19");
var early = [V("0011", "2026-11-18", "2026-11-19"), V("0012", "2026-11-18", "2026-11-19"), V("0013", "2026-11-18"), V("0014", "2026-11-18")];
ahmedFlow(early, "2026-11-19");
var email_lead = [V("0021", "", "", "2026-11-12"), V("0022", "2026-11-19"), V("0023", "2026-11-19"), V("0024", "2026-11-19"), V("0025", "2026-11-19")];
ahmedFlow(email_lead, "2026-11-19");
var late = [V("0031", "", "", "2026-11-19"), V("0032", "2026-11-19"), V("0033", "2026-11-19"), V("0034", "2026-11-19"), V("0035", "2026-11-19")];
ahmedFlow(late, "2026-11-20");
var f = function (a) { var o = {}; a.forEach(function (p) { o[p.id.slice(-4)] = p.due; }); return o; };
console.log(JSON.stringify({out: f(out), early: f(early), email_lead: f(email_lead), late: f(late)}));""")
        o = got["out"]
        self.assertEqual(o["0002"], "2026-11-16", "Mon's, not finished: overdue on Monday, still his")
        self.assertEqual(o["0004"], "2026-11-18", "Wed's, not finished: overdue on Wednesday")
        self.assertEqual((o["0005"], o["0006"], o["0007"]), ("2026-11-20", "2026-11-20", "2026-11-23"),
                         "today is full with the two overdue; the rest move along, two a day, never overdue")
        self.assertEqual(got["early"], {"0011": "", "0012": "", "0013": "2026-11-20", "0014": "2026-11-20"},
                         "both of today's done: tomorrow has the next two")
        self.assertEqual(got["email_lead"], {"0021": "2026-11-12", "0022": "2026-11-20", "0023": "2026-11-20", "0024": "2026-11-23", "0025": "2026-11-23"},
                         "sent today: none today, two tomorrow, two Monday")
        writing = self._core("""
var w = {id: "brand_b-yai-a1v3", role: "video-editor", maker: "creator", who: "creator", unsent: false, sentDay: "2026-11-19", finDay: "",
  checks: false, fixedDue: "", due: "", writing: true, handoff: {writing: {held: false}}};
var h = {id: "brand_b-yai-a3v2", handoff: {writing: {held: true, at: "stage5"}}};
ahmedFlow([w], "2026-11-20"); console.log(JSON.stringify([w.due, holdOf(h).indexOf("On hold") === 0]));""")
        self.assertEqual(writing, ["", True], "a writing job is not one of his two videos a day; a held one is on hold")
        held = self._core("""
var d = {towrite: [{brand: "brand_b", month: "2026-12", slot: "dec-05", send: "2026-12-07"}, {brand: "brand_a", month: "2026-12", slot: "dec-22", send: "2026-12-11"}],
  loose: {"brand_b__2026-12": {note: "On hold: brand_b December offer being decided"}}, rows: []};
splitHeld(d); var b = boardPieces(d, null, null).pieces, p = b.filter(function (x) { return x.id === "brand_b__dec-05"; })[0];
console.log(JSON.stringify([d.towrite.map(function (t) { return t.slot; }), d.towriteHeld.map(function (t) { return t.slot; }), p.due, holdOf(p)]));""")
        self.assertEqual(held, [["dec-22"], ["dec-05"], "", "On hold: brand_b December offer being decided"],
                         "email_lead, 2026-11-19: brand_b's December emails wait on the offer: off her days and editor's load, on hold")
        page = read(PAGE)   # email_lead, 2026-11-19: a short story and a plain next step in the panel; opening is obvious
        self.assertIn('hist.appendChild(el("li", "next", "Next: " + nextStep(p)));', page)
        self.assertIn('var ob = el("button", "l-open", "Details ›");', page, "a one-piece card has a Details button")
        self.assertIn('li.appendChild(el("span", "go", "Open ›"));', page, "each line in a card of several says it opens")
        self.assertIn('t = v ? (sn ? "Sent to " + cap(v)', page, "a who decision tells the story")
        self.assertIn('if (!one && holdOf(p)) li.insertBefore(el("span", "l-hold", "On hold"), li.firstChild);', read(PAGE),
                      "inside a card of several, the held one carries its own tag")
        self.assertEqual(got["late"], {"0031": "2026-11-19", "0032": "2026-11-20", "0033": "2026-11-23", "0034": "2026-11-23", "0035": "2026-11-24"},
                         "today's not finished: tomorrow it and one new, Monday two, Tuesday one")

    def test_a_task_is_work_that_is_not_an_ad_or_an_email(self):
        """email_lead, 2026-11-10 (option B), after designer's Loom ("que yo tuviera aquí un addtask ... storefront tal cosa"):
        + Add task in every view; a task sits with its person in Production, says what to do when opened, and on editor's
        day counts as other work due (her floor of 7 then says why)."""
        page = read(PAGE)
        self.assertIn('<select id="cq-a-type"><option value="task">Task</option>', page, "Task is the form's first type")
        self.assertIn('id="cq-addtask" data-feature="86"', page)
        self.assertIn('<div class="addmodal" id="cq-add" data-feature="12" hidden role="dialog"', page,
                      "a small New task window, as in editor's mockup (email_lead, 2026-11-10), opened from + Add task in every view")
        self.assertIn('$("#cq-addtask").addEventListener("click", openAdd);', page)
        self.assertNotIn('id="cq-a-prio"', page, "priority is set on the card, not in the window")
        self.assertIn('"landing-page": "page", "task": "task"}', page)
        self.assertIn('t === "task" ? "ty-task"', page)
        acts = json.loads(read(PAGE.replace("content-queue.html", "content-queue.actions.json")))["direct"]
        self.assertEqual(acts["12"]["args"]["type"], "task|image-ad|carousel|landing-page")
        self.assertEqual(acts["87"], {"kind": "quick", "run": "cq", "verbs": ["remove"]})
        got = self._core("""
var d = {rows: [{id: "brand_b_task_storefront", type: "task", brand: "brand_b", title: "Storefront", stage: null, who: "editor",
  due: "2026-11-25", note: "Redo the pictures"}]};
var b = boardPieces(d, null, null).pieces, t = b.filter(function (p) { return p.id === "brand_b_task_storefront"; })[0];
var F = function (id, due) { return {id: id, col: "making", who: "editor", type: "email", due: due, send: "2026-12-10", row: {editor_due_from: "deadlines.json"}}; };
var P = [t, F("a", "2026-11-25"), F("b", "2026-11-26")];
var r = evePack(P, [], "2026-11-24", {});
console.log(JSON.stringify({col: t.col, who: t.who, type: t.type, day: [r.days[0].day, r.days[0].n, r.days[0].short, r.days[0].why]}));""")
        self.assertEqual(got, {"col": "making", "who": "editor", "type": "task", "day": ["2026-11-25", 1, 6, "also 1 task due"]})

    def test_the_board_is_a_kanban_coloured_only_by_due_day(self):
        """email_lead, 2026-11-10: "Los due del día en rojo, los del día siguiente naranja, los de dos días después amarillo y
        más allá azul", then six steps (mock https://claude.ai/artifact/4azDcP1gkYWsroA5fKAk6R, "Sí, constrúyelo"):
        Production splits into Assigned and In progress (moves there by itself), Edit joins In progress, Done is by send
        day and never folded."""
        got = self._core("""
var T = "2026-11-10";
var P = [{id: "e1", col: "making", who: "editor", type: "email", due: "2026-11-11", brand: "brand_a"},
  {id: "e2", col: "making", who: "editor", type: "email", due: "2026-11-12", brand: "brand_a"},
  {id: "s1", col: "making", who: "editor", type: "static", due: "2026-11-16", brand: "brand_b", handoff: {}, back: 2},
  {id: "s2", col: "making", who: "editor", type: "static", due: "2026-11-16", brand: "brand_b", handoff: {}, back: 0},
  {id: "v1", col: "editing", who: "owner", type: "video", due: "", brand: "brand_a"},
  {id: "a1", col: "making", who: "creator", type: "video", due: "", brand: "brand_a", handoff: {}, back: 0, role: "video-editor"},
  {id: "a2", col: "making", who: "creator", type: "video", due: "2026-11-11", brand: "brand_a", handoff: {}, back: 0, role: "video-editor"},
  {id: "a3", col: "making", who: "creator", type: "video", due: "2026-11-18", brand: "brand_a", handoff: {}, back: 0, role: "video-editor"},
  {id: "a4", col: "making", who: "creator", type: "video", due: "2026-11-18", brand: "brand_a", handoff: {}, back: 0, role: "video-editor", req: "editing"},
  {id: "e3", col: "making", who: "editor", type: "email", due: "2026-11-11", brand: "brand_a", req: "editing"},
  {id: "d1", col: "launch", who: "", type: "email", send: "2026-11-13", brand: "brand_a", moment: "black-friday"},
  {id: "d2", col: "launch", who: "", type: "email", send: "2026-11-13", brand: "brand_b", moment: ""}];
var L = boardLots(P, T);
console.log(JSON.stringify({lanes: P.map(function (p) { return [p.id, p.lane]; }),
  lots: L.map(function (g) { return [g.lane, g.items.map(function (p) { return p.id; }).join(","), g.band, g.moment]; }),
  bands: ["2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13", ""].map(function (d) { return dueBand(d, T); }),
  fri: dueBand("2026-11-16", "2026-11-13")}));""")
        self.assertEqual(dict(got["lanes"]), {"e1": "progress", "e2": "assigned", "s1": "progress", "s2": "assigned", "v1": "progress",
                                              "a1": "assigned", "a2": "progress", "a3": "assigned", "a4": "progress", "e3": "progress", "d1": "launch", "d2": "launch"},
                         "In progress on a real signal (cut, work back, someone said so) or a maker's day, editor's or creator's (2026-11-11)")
        self.assertIn(["progress", "a2", "tomorrow", ""], got["lots"], "his day counts, as editor's (2026-11-11)")
        self.assertIn(["progress", "a4", "later", ""], got["lots"], "someone said he started it: In progress")
        self.assertEqual(got["bands"], ["today", "today", "tomorrow", "two", "later", "none"])
        self.assertEqual(got["fri"], "tomorrow", "working days: Monday is the day after Friday")
        done = [g for g in got["lots"] if g[0] == "launch"]
        self.assertEqual(done, [["launch", "d1,d2", "", ""]], "Done: one card per send day, both brands, never in a campaign")
        page = read(PAGE)
        self.assertIn('lots.filter(function (g) { return g.lane === c.key && (!(boardFocus || dayFocus) || hitLot(g, today)); })', page)
        self.assertIn('[["today", "today or past"], ["tomorrow", "tomorrow"], ["two", "in 2 days"], ["later", "later"], ["none", "no date"]]', page)
        self.assertNotIn('"l-flag " + g.flag', page, "no Act now / At risk pill on a card")
        self.assertIn('d = el("details", "lot " + tyClass(g.type)', page, "since 2026-11-11 a card's edge says its type, not its date (email_lead)")
        self.assertIn('.cq .lot[class*="ty-"]{border-left-color:var(--tc);border-left-width:6px}', page)
        self.assertIn('{key: "assigned", name: "Assigned"', page)
        self.assertIn('{key: "launch", name: "Done"', page)

    def test_sent_back_with_nobody_goes_to_brief_to_approve_with_owner(self):
        """email_lead, 2026-11-10 ("Sí, muévelas"): a piece owner sent back on Approve to Meta that nobody has (brand_a brief
        0251, 16 days in Production) is not Assigned: it sits in Brief to approve as owner's, still saying he sent it back."""
        got = self._core("""
var d = {rows: [{id: "brand_a_flex_brief-0251", type: "image-ad", brand: "brand_a", title: "x", stage: "making", who: null, flag: "sent-back", since: "2026-10-25"},
  {id: "brand_a_flex_brief-0252", type: "image-ad", brand: "brand_a", title: "y", stage: "making", who: "editor", flag: "sent-back", since: "2026-10-25"}]};
var P = boardPieces(d, null, null).pieces, L = boardLots(P, "2026-11-10");
console.log(JSON.stringify(P.map(function (p) { return [p.id, p.who, p.lane]; }).concat([L.filter(function (g) { return g.lane === "brief"; })[0].why])));""")
        self.assertEqual(got[:2], [["brand_a_flex_brief-0251", "owner", "brief"], ["brand_a_flex_brief-0252", "editor", "assigned"]])
        self.assertIn("owner sent it back", got[2])

    def test_the_calendar_keeps_what_was_done_on_its_day(self):
        """email_lead, 2026-11-10: "Quiero que en el calendar view no se eliminen las cosas que ya se hicieron en el día, sino
        que queden como que se hicieron". An email editor finished keeps her day (its saved deadline); a finished hand-off
        keeps its due day, else the day its last work came back; the day counts them against her 7 and says done."""
        got = self._core("""
var d = {rows: [{id: "brand_a__nov-15", type: "email", brand: "brand_a", title: "a", turn: "Scheduled · 2026-11-15", status: "scheduled",
    editor_due: "2026-11-10", editor_due_from: "deadlines.json", send_date: "2026-11-15"},
  {id: "brand_a__nov-20", type: "email", brand: "brand_a", title: "b", turn: "editor: pictures", editor_due: "2026-11-11", editor_due_from: "deadlines.json", send_date: "2026-11-20"}]};
var st = {rows: [{key: "brand_b_x_brief-0300", title: "s", brand: "brand_b", returned_work: 1, returned_files: 1, returned_pictures: 1, done: {at: "x"},
  returned_work_at: ["2026-11-09T10:00:00Z"]}]};
var b = boardPieces(d, st, null), load = calLoad(b.pieces, [], "2026-11-10", b.done);
console.log(JSON.stringify({done: b.done.map(function (p) { return [p.id, p.who, p.day]; }), eve10: (load.editor["=2026-11-10"] || []).length,
  eve09: (load.editor["=2026-11-09"] || []).map(function (p) { return p.type; })}));""")
        self.assertIn(["brand_a__nov-15", "editor", "2026-11-10"], got["done"])
        self.assertNotIn("brand_a__nov-20", [x[0] for x in got["done"]], "still on her turn: not done")
        self.assertEqual(got["eve10"], 1)
        got = self._core("""
var d = {rows: [{id: "brand_b_task_storefront", type: "task", brand: "brand_b", title: "Storefront", who: "owner", due: "2026-11-12", removed: true}]};
var b = boardPieces(d, null, null);
console.log(JSON.stringify({pieces: b.pieces.length, done: b.done.map(function (p) { return [p.id, p.who, p.day]; })}));""")
        self.assertEqual(got, {"pieces": 0, "done": [["brand_b_task_storefront", "owner", "2026-11-12"]]},
                         "a task taken off with Done stays on its day, done, with who did it (owner did the storefront, daily Nov 11)")
        page = read(PAGE)
        self.assertIn('people.forEach(function (w) { var x = calWho(w, d, load, evDay[d], d === rollDay(today)); if (x) cell.appendChild(x); });   // a past day keeps what was done on it', page)
        self.assertIn('[done, "\\u2713 Done"]', page, "the day's finished pieces, under their own heading (designer, 2026-11-12: done)")
        # email_lead, 2026-11-12: "2 videos · done: 2" read as the day's two being done. A day says to do and finished in words,
        # with the brief numbers when it holds a few, and finished pieces never wear the type colour.
        # designer, 2026-11-12: no "to do:", and "done" not "finished"; the green and the check mark tell them apart
        self.assertIn('b.appendChild(kindLine(g.items.length, g.word, g.items, "todo"));', page)
        self.assertIn('"done", g.word === "email written" ? "\\u2713 " : "\\u2713 done: "', page,
                      "done: for every kind; email_lead's written emails say \"\u2713 10 emails written\" (2026-11-19)")
        self.assertIn("(briefNums(items) || brandSplit(items))", page)
        self.assertIn(".cq .cl-sec.is-fin{--tc:var(--ok)}", page)

    def test_a_finished_video_sits_on_the_day_it_came_back(self):
        """email_lead, 2026-11-12: the Calendar should reflect how creator's videos were done. brand_a 0274 was planned for Nov 13
        and came back Nov 12: it shows done on Nov 12, not on its plan day. A static keeps its due day (2026-11-10)."""
        got = self._core("""
var K = "brand_a_flex-face-brush_brief-0274", K2 = "brand_b_x_brief-0300";
var d = {rows: [], loose: {}}; d.loose[K] = {who: "creator", due: "2026-11-13"}; d.loose[K2] = {due: "2026-11-13"};
var st = {rows: [{key: K2, title: "s", brand: "brand_b", returned_work: 1, returned_files: 1, returned_pictures: 1, done: {at: "x"},
  returned_work_at: ["2026-11-12T15:00:00Z"]}]};
var vids = {rows: [{key: K, title: "Entanglement", brand: "brand_a", form: "four parts", returned_work: 4, returned_files: 4,
  returned_work_at: ["2026-11-12T15:00:00Z", "2026-11-12T15:05:00Z"]}]};
var b = boardPieces(d, st, vids);
console.log(JSON.stringify(b.done.map(function (p) { return [p.id, p.type, p.day]; })));""")
        self.assertIn(["brand_a_flex-face-brush_brief-0274", "video", "2026-11-12"], got)
        self.assertIn(["brand_b_x_brief-0300", "static", "2026-11-13"], got)

    def test_drag_a_piece_to_a_day_and_a_task_to_a_column(self):
        """email_lead, 2026-11-10 ("Calendar y tareas"): on the Calendar a piece that can move drags from a day's list onto
        another day (the Move save, cq.py set due); on the Board only a task drags, and a task dragged to In progress shows
        there as started."""
        got = self._core("""
var d = {rows: [{id: "team_task_x", type: "task", brand: "team", title: "x", stage: null, who: "editor", due: "2026-11-12", requested_stage: "editing"},
  {id: "team_task_y", type: "task", brand: "team", title: "y", stage: null, who: "editor", due: "2026-11-12"}]};
var P = boardPieces(d, null, null).pieces, L = boardLots(P, "2026-11-10");
console.log(JSON.stringify(L.map(function (g) { return [g.items[0].id, g.lane, g.why[0]]; })));""")
        self.assertIn(["team_task_x", "progress", "started"], got)
        self.assertIn("team_task_y", [x[0] for x in got if x[1] == "assigned"])
        page = read(PAGE)
        self.assertIn('if (d >= today) dropDay(cell, d);', page, "a day of the week, today on, takes a dragged piece")
        self.assertIn('if (day && canMove(p) && kitToken()) { li.draggable = true;', page, "only what Move may move drags")
        acts = json.loads(read(PAGE.replace("content-queue.html", "content-queue.actions.json")))["direct"]
        self.assertEqual(acts["88"], {"kind": "quick", "run": "cq", "verb": "set", "fields": ["requested_stage"], "values": {"requested_stage": "making|editing"}})

    def test_an_incomplete_hand_off_is_shown_with_what_it_lacks(self):
        """email_lead, 2026-11-11 ("Sí, muéstralos"): brand_b 0324 and 0325, handed to creator by owner on Nov 3 in his own
        handoff.md format, were hidden because their folders lack BRIEF.md, RUN.md, run.json and refs/. An incomplete
        hand-off is the maker's work: it shows (creator's In progress), saying what the folder lacks; _superseded and a brief a
        queue row already shows are left out."""
        got = self._core("""
var vi = {rows: [], incomplete: [{brand: "brand_b", key: "brand_b_brilliance-body-scrub_brief-0324", missing: ["BRIEF.md", "RUN.md", "run.json", "refs/"]},
  {brand: "brand_a", key: "_superseded", missing: ["BRIEF.md"]},
  {brand: "brand_b", key: "brand_b_brilliance-face-scrub_brief-0330", missing: ["refs/"]}]};
var d = {rows: [{id: "brand_b_brilliance-face-scrub_brief-0330", type: "video-ad", brand: "brand_b", title: "q", stage: "making", who: "creator"}],
  loose: {"brand_b_brilliance-body-scrub_brief-0324": {who: "creator"}}};
var P = boardPieces(d, null, vi).pieces, L = boardLots(P, "2026-11-11");
var g = L.filter(function (g) { return g.items[0].id === "brand_b_brilliance-body-scrub_brief-0324"; })[0];
console.log(JSON.stringify({ids: P.map(function (p) { return p.id; }), title: g.items[0].title, lane: g.lane, who: g.who, why: g.why}));""")
        self.assertEqual(sorted(got["ids"]), ["brand_b_brilliance-body-scrub_brief-0324", "brand_b_brilliance-face-scrub_brief-0330"])
        self.assertEqual([got["title"], got["lane"], got["who"]], ["brand_b video, brief 0324", "assigned", "creator"],
                         "creator's, waiting in Assigned until its day or work back (2026-11-11)")
        self.assertIn("1 of 2: hand-off folder without the brief, the run sheet, the run file, references (open the folder on Drive)", got["why"],
                      "it shares creator's Assigned card with 0330; the card says which one lacks files")

    def test_damons_ledger_keeps_done_and_old_hand_offs_off_ahmeds_work(self):
        """email_lead, 2026-11-11: creator's page as close to what he is really doing as can be. A video hand-off owner's brief
        ledger marks Live is out (counted live); an old handoff.md folder he never listed is not shown; one he lists in
        Production is creator's."""
        got = self._core("""
var vi = {rows: [{key: "brand_b_brilliance-body-scrub_brief-0324", brand: "brand_b", title: "Kitchen To The Lab", form: "handoff.md", returned_work: 0},
  {key: "brand_b_brilliance-face-scrub_brief-0304", brand: "brand_b", title: "x", form: "handoff.md", returned_work: 0},
  {key: "brand_a_flex-face-brush_brief-0076", brand: "brand_a", title: "y", form: "handoff.md", returned_work: 0}]};
var d = {rows: [], ledger: {built: "2026-11-06", status: {"brand_b_brilliance-body-scrub_brief-0324": "Production", "brand_b_brilliance-face-scrub_brief-0304": "Live"}}};
var b = boardPieces(d, null, vi);
console.log(JSON.stringify({ids: b.pieces.map(function (p) { return p.id; }), live: b.live.video || 0}));""")
        self.assertEqual(got, {"ids": ["brand_b_brilliance-body-scrub_brief-0324"], "live": 1})

    def test_a_video_hand_off_is_ahmeds_once_it_was_sent(self):
        """email_lead, 2026-11-11: "técnicamente lo que se le ha asignado es los que se le mandaron por whatsapp". A video
        hand-off sent to creator (who: creator, recorded from the message) is his, In progress; one nobody sent yet sits in
        Assigned as email_lead's to send, saying so."""
        got = self._core("""
var vi = {rows: [{key: "brand_a_flex-face-brush_brief-0274", brand: "brand_a", title: "Entanglement", returned_work: 0},
  {key: "brand_a_flex-face-brush_brief-0318", brand: "brand_a", title: "Barber Mission", returned_work: 0}]};
var d = {rows: [], loose: {"brand_a_flex-face-brush_brief-0274": {who: "creator"}}};
var P = boardPieces(d, null, vi).pieces, L = boardLots(P, "2026-11-11");
console.log(JSON.stringify(L.map(function (g) { return [g.items[0].id.slice(-4), g.who, g.lane, g.why.indexOf("ready for creator, not sent yet") >= 0]; })));""")
        self.assertIn(["0274", "creator", "assigned", False], got, "sent, no day yet, nothing back: Assigned (2026-11-11)")
        self.assertIn(["0318", "email_lead", "assigned", True], got)

    def test_a_brief_shows_its_number_first(self):
        """email_lead, 2026-11-11: "para creator es más fácil hablar de números ... que sea más el número lo que se vea en el board
        y que igual tenga ... abajo el nombre". A card for one brief leads with its number, the name small under it; a
        batch lists its numbers as buttons that open each piece; a row in the open card starts with the number."""
        page = read(PAGE)
        self.assertIn('tt.appendChild(el("span", "l-num", n1)); s.appendChild(tt); s.appendChild(el("div", "l-name", f[0].title));', page)
        self.assertIn('var nb = el("div", "l-nums");', page)
        self.assertIn('(briefNum(p) ? briefNum(p) + " · " : "") + p.title', page)
        self.assertIn('var m = /brief-(\\d{3,5})\\b/.exec(val(p.id))', page)

    def test_owner_and_email_lead_get_the_same_row(self):
        """email_lead, 2026-11-11: "haz el mismo filtro para owner y para mí". For owner and email_lead: to review (Brief to approve,
        Final check), working on (Assigned, In progress), coming (Coming up), no date, each theirs; their days count any
        open piece of theirs with a day."""
        got = self._core("""
var P = [{id: "b1", who: "owner", col: "brief"}, {id: "r1", who: "owner", col: "review"}, {id: "m1", who: "owner", col: "making", due: "2026-11-12"},
  {id: "p1", who: "owner", col: "plan", due: "2026-11-20"}, {id: "w1", who: "email_lead", col: "plan", due: "2026-11-12"}, {id: "s1", who: "email_lead", col: "review", due: "2026-11-13"},
  {id: "l1", who: "email_lead", col: "launch", due: "2026-11-12"}];
var f = function (who, w) { return P.filter(function (p) { return makerHas(p, who, w); }).map(function (p) { return p.id; }); };
console.log(JSON.stringify({dr: f("owner", "@review"), dw: f("owner", "@working"), dc: f("owner", "@coming"), dn: f("owner", "@nodate"),
  sc: f("email_lead", "@coming"), sr: f("email_lead", "@review"), days: boardDays(P, "2026-11-11", "email_lead").map(function (d) { return [d.day, d.n]; })}));""")
        self.assertEqual(got, {"dr": ["b1", "r1"], "dw": ["m1"], "dc": ["p1"], "dn": ["b1", "r1"], "sc": ["w1"], "sr": ["s1"],
                               "days": [["2026-11-12", 1], ["2026-11-13", 1]]})
        far = self._core("""
var P = []; ["2026-11-20", "2026-11-23", "2026-11-24", "2026-11-25", "2026-11-26", "2026-11-27"].forEach(function (d, i) {
  P.push({id: "w" + i, who: "email_lead", col: "plan", due: d}); P.push({id: "e" + i, who: "editor", col: "making", due: d}); });
console.log(JSON.stringify({email_lead: boardDays(P, "2026-11-11", "email_lead").map(function (d) { return d.day; }), editor: boardDays(P, "2026-11-11", "editor").length}));""")
        self.assertEqual(far["email_lead"], ["2026-11-20", "2026-11-23", "2026-11-24", "2026-11-25", "2026-11-26"],
                         "email_lead's emails to write show on their next 5 days however far (2026-11-11: \"ponle fecha a mis emails por escribir\")")
        self.assertEqual(far["editor"], 0, "a maker's row keeps the next 5 working days")
        page = read(PAGE)
        self.assertIn('["editor", "creator", "owner", "email_lead"].forEach(function (who) {', page)

    def test_a_piece_keeps_its_history(self):
        """email_lead, 2026-11-11: "que haya un registro de qué día se terminaron las cosas ... para todos". An email's steps come
        from its card; a hand-off's from its hand-off day, the recorded send and each day work came back after it."""
        got = self._core("""
var e = {row: {history: [{step: "editor finished the pictures", at: "2026-11-10T10:11:03+00:00", by: "editor"}, {step: "Scheduled in Klaviyo", at: "2026-11-10T15:11:34", by: "email_lead"}]}};
var v = {id: "brand_b_x_brief-0324", maker: "creator", row: {note: "Sent to creator by owner on WhatsApp, Nov 3"},
  handoff: {handed: "2026-11-02", returned_work_at: ["2026-11-02T13:13:00Z", "2026-11-10T09:24:00Z", "2026-11-10T09:36:00Z"]}};
console.log(JSON.stringify({e: pieceHistory(e).map(function (x) { return x.text; }), v: pieceHistory(v).map(function (x) { return [x.at, x.text]; })}));""")
        self.assertEqual(got["e"], ["editor finished the pictures (editor)", "Scheduled in Klaviyo (email_lead)"])
        self.assertEqual(got["v"], [["2026-11-02", "Hand-off ready for creator"], ["2026-11-03", "Sent to creator by owner (WhatsApp)"],
                                    ["2026-11-10", "creator's work back in returned/: 2 files"]], "the Nov 2 file came before the hand-off: not his")

    def test_a_blocked_hand_off_is_its_owners_not_stephs(self):
        """email_lead, 2026-11-11: "no entiendo qué tengo que hacer yo con esos briefs si todavía no se los puedo enviar". A
        hand-off nobody sent is email_lead's to send unless someone else has to clear it first (who: owner): then it is his,
        with the reason."""
        got = self._core("""
var vi = {rows: [{key: "brand_a_flex-face-brush_brief-0322", brand: "brand_a", title: "Street interview", returned_work: 0},
  {key: "brand_a_flex-face-brush_brief-0318", brand: "brand_a", title: "Barber Mission", returned_work: 0}]};
var d = {rows: [], loose: {"brand_a_flex-face-brush_brief-0322": {who: "owner", note: "Needs the voice read first"}}};
var L = boardLots(boardPieces(d, null, vi).pieces, "2026-11-11");
console.log(JSON.stringify(L.map(function (g) { return [g.items[0].id.slice(-4), g.who, g.lane, g.why.filter(function (w) { return /creator|to do:/.test(w); })[0] || ""]; })));""")
        self.assertIn(["0322", "owner", "assigned", "owner to do: Needs the voice read first"], got)
        self.assertIn(["0318", "email_lead", "assigned", "ready for creator, not sent yet"], got)
        got = self._core("""
var vi = {rows: [{key: "brand_a_flex-face-brush_brief-0322", brand: "brand_a", title: "a", returned_work: 0},
  {key: "brand_a_flex-face-brush_brief-0318", brand: "brand_a", title: "b", returned_work: 0}]};
var d = {rows: [], loose: {"brand_a_flex-face-brush_brief-0322": {who: "owner", note: "Record the voice"},
  "brand_a_flex-face-brush_brief-0318": {who: "creator"}}};
var P = boardPieces(d, null, vi).pieces, ids = function (w) { return P.filter(function (p) { return boardWhoHas(p, w); }).map(function (p) { return p.id.slice(-4); }); };
console.log(JSON.stringify({creator: ids("creator"), owner: ids("owner")}));""")
        self.assertEqual(got, {"creator": ["0318"], "owner": ["0322"]},
                         "email_lead, 2026-11-12: owner's to clear is on owner's filter, not creator's, until it is sent to him")
        # email_lead, 2026-11-12: "en las tarjetas ... qué tiene que hacer para que pase a creator": two on one card, each its own need
        got = self._core("""
var vi = {rows: [{key: "brand_a_flex-face-brush_brief-0322", brand: "brand_a", title: "a", returned_work: 0},
  {key: "brand_a_flex-face-brush_brief-0321", brand: "brand_a", title: "b", returned_work: 0}]};
var d = {rows: [], loose: {"brand_a_flex-face-brush_brief-0322": {who: "owner", due: "2026-11-16", note: "Record the voice"},
  "brand_a_flex-face-brush_brief-0321": {who: "owner", due: "2026-11-16", note: "Write its RUN.md"}}};
var L = boardLots(boardPieces(d, null, vi).pieces, "2026-11-12");
console.log(JSON.stringify(L.map(function (g) { return g.why; })));""")
        self.assertEqual(len(got), 1, "one card for owner's two")
        for line in ("owner to do:", "0322: Record the voice", "0321: Write its RUN.md"):
            self.assertIn(line, got[0])

    def test_an_approved_email_to_write_is_assigned(self):
        """email_lead, 2026-11-11: "los emails que tengo que escribir ... que ya esté aprobado por owner, y lo tengo que escribir
        como que ya me toque en assign". An email the calendar's review marks approved is email_lead's, Assigned; one not yet
        approved stays in Coming up."""
        got = self._core("""
var W = [{brand: "brand_b", slot: "nov-60", send: "2026-11-27", type: "x", approved: true, evBy: "2026-11-20"},
         {brand: "brand_b", slot: "nov-61", send: "2026-11-27", type: "x", approved: false, evBy: "2026-11-20"}];
var P = boardPieces({rows: [], towrite: W}, null, null).pieces; boardLots(P, "2026-11-11");
console.log(JSON.stringify({lanes: P.map(function (p) { return [p.id, p.lane, p.who]; }),
  editor: P.filter(function (p) { return boardWhoHas(p, "editor"); }).length, email_lead: P.filter(function (p) { return boardWhoHas(p, "email_lead"); }).length}));""")
        self.assertEqual(got["lanes"], [["brand_b__nov-60", "assigned", "email_lead"], ["brand_b__nov-61", "plan", "email_lead"]])
        self.assertEqual([got["editor"], got["email_lead"]], [0, 2], "QC as editor, 2026-11-11: an email not written yet is in email_lead's filter, never editor's")

    def test_the_calendar_is_a_week_with_types_and_brands(self):
        """designer via email_lead, 2026-11-06: one week, and editor's day clear: how many emails, how many statics, which brands.
        email_lead, 2026-11-06: "que con 7 no salte a que está explotada": no colour for amounts."""
        got = self._core("""
var P = [{brand: "brand_a", type: "static"}, {brand: "brand_b", type: "static"}, {brand: "brand_a", type: "static"},
         {brand: "brand_a", type: "email"}, {brand: "brand_b", type: "email", col: "write"}];
console.log(JSON.stringify({weeks: ["2026-11-06", "2026-11-08", "2026-11-09", "2026-11-13"].map(weekOf),
  split: brandSplit(P.slice(0, 3)), kinds: kinds(P).map(function (g) { return [g.word, g.items.length]; })}));""")
        self.assertEqual(got["weeks"], ["2026-11-02", "2026-11-02", "2026-11-09", "2026-11-09"], "Monday of the week; Sunday is the week before")
        self.assertEqual(got["split"], "brand_a 2 · brand_b 1", "most first")
        self.assertEqual(got["kinds"], [["email", 1], ["email to write", 1], ["static", 3]], "emails first")
        page = read(PAGE)
        self.assertIn('<div class="mg wk" data-feature="75">', page)
        self.assertNotIn("calMonth", page, "no month left")
        self.assertIn('chip.classList.add("h0");', page, "no darker colour for more pieces")
        self.assertIn('kindLine(em.length, "email", em)', page, "editor's day says how many emails (designer, 2026-11-12: \"7 emails\", not \"7 of 7\")")

    def test_only_owner_designer_or_email_lead_move_an_email_off_the_rule(self):
        """email_lead, 2026-11-06: "que se pueda flexibilizar la regla si se mueve desde el queue por owner o designer".
        Who moved it is read from who saved the due (view.py loose due_by), never from the page."""
        got = self._core("""
var T = "2026-11-09", E = function (id, send) { return {id: id, type: "email", stage: null, status: "ready", turn: "editor: pictures", brand: "brand_b",
  send_date: send, send_date_ok: true, editor_due: "2026-11-10", editor_due_from: "5 working days before the send"}; };
var d = {rows: [E("a", "2026-11-20"), E("b", "2026-11-21"), E("c", "2026-11-22")],
  loose: {c: {due: "2026-11-10", due_by: "designer"}, b: {due: "2026-11-12", due_by: "editor"}}};
var b = boardPieces(d, {rows: []}, {rows: []}), r = evePack(b.pieces, [], T, {});
var at = {}; r.days.forEach(function (x) { x.fixed.concat(x.packed.map(function (f) { return f.item; })).forEach(function (p) { at[p.id] = x.day; }); });
console.log(JSON.stringify({at: at, pin: b.pieces.filter(function (p) { return p.pin; }).map(function (p) { return [p.id, p.pin.by]; })}));""")
        self.assertEqual(got["pin"], [["c", "designer"]], "designer's move pins it; editor's move does not")
        self.assertEqual(got["at"]["c"], "2026-11-10", "the pinned email stays on its day, though it sends last")
        self.assertEqual(got["at"]["a"], "2026-11-10", "the rest still pack earliest first around it")
        self.assertEqual(got["at"]["b"], "2026-11-10")
        page = read(PAGE)
        self.assertIn('var EMAIL_MOVERS = ["owner", "designer", "email_lead"];', page)
        self.assertIn('if (p.type === "email") return !!(p.row && p.who === "editor" && p.col === "making" && EMAIL_MOVERS.indexOf(viewer()) >= 0);', page)

    def test_a_redo_finishes_on_new_work_in_returned_whoever_made_it(self):
        """email_lead, 2026-11-06: if owner makes the statics editor has for Monday, "que se muevan solos". A hand-off put back
        on the list (a redo) is finished by a Done after it, or by as much work as the brief has versions newer than it."""
        got = self._core("""
var data = {loose: {k: {back_on: "2026-11-06T11:21:22Z", due: "2026-11-09"}}};
var old = ["2026-11-04T10:00:00.000Z", "2026-11-04T10:01:00.000Z", "2026-11-04T10:02:00.000Z", "2026-11-04T10:03:00.000Z", "2026-11-04T10:04:00.000Z"];
var S = function (at, done) { return {key: "k", versions: 5, returned_work: at.length, returned_work_at: at, done: done || null}; };
var newer = function (n) { var a = []; for (var i = 0; i < n; i++) a.push("2026-11-07T0" + i + ":00:00.000Z"); return a; };
console.log(JSON.stringify({
  old: handoffFinished(S(old)),
  three: handoffFinished(S(old.concat(newer(3)))),
  five: handoffFinished(S(old.concat(newer(5)))),
  doneBefore: handoffFinished(S(old, {at: "2026-11-05T09:00:00Z"})),
  doneAfter: handoffFinished(S(old, {at: "2026-11-07T09:00:00Z"})),
  video: handoffFinished({key: "k", versions: 0, returned_work: 6, returned_work_at: old.concat(newer(1))}, true),
  noTimes: handoffFinished({key: "k", versions: 5, returned_work: 10})}));""")
        self.assertFalse(got["old"], "the old work is not the redo")
        self.assertFalse(got["three"], "3 new of 5 versions: not yet")
        self.assertTrue(got["five"], "5 new pictures after the redo: finished, nobody pressed anything")
        self.assertFalse(got["doneBefore"])
        self.assertTrue(got["doneAfter"])
        self.assertTrue(got["video"], "a video redo: any new cut")
        self.assertFalse(got["noTimes"], "a list read before the dates existed: still waits")

    def test_a_click_opens_the_list_where_she_can_see_it(self):
        """email_lead, 2026-11-05: a click opened nothing she could see (Team wrote into editor's load's hidden list). editor's load,
        its own view, is gone since 2026-11-06 (email_lead: "Quita la vista del editor's load del calendario. Ya no hace falta."):
        one list, under the week, scrolled to."""
        page = read(PAGE)
        self.assertEqual(page.count('class="cal-list'), 1, "one list on the Calendar")
        self.assertEqual(page.count('$("#cq-cal > .cal-list")'), 2, "opened by calOpen, filled by calList")
        self.assertIn('if (calPick) l.scrollIntoView({behavior: "smooth", block: "start"})', page)
        for gone in ("renderEve", "ev-seg", "ev-box", "evePick", "calMode"):
            self.assertNotIn(gone, page)
        self.assertIn("evePack(b.pieces, tw, today, eveOff, eveOpt(data, eveToday()))", page, "the rule still places editor's emails in Team")

    def test_team_shows_eves_emails_where_her_load_puts_them(self):
        """email_lead, 2026-11-05: in Team, editor had nothing on the 17th and 18th, though emails were coming her way."""
        got = self._core("""
var T = "2026-11-12", W = []; for (var i = 1; i <= 9; i++) W.push({brand: "brand_b", slot: "nov-" + (20 + i), send: "2026-11-20", type: "sale-window"});
var r = evePack([], W, T, {}), L = calLoad([], W, T), ids = function (a) { return (a || []).map(function (p) { return p.id; }); };
console.log(JSON.stringify({eve13: ids(L.editor["+2026-11-13"]), eve16: ids(L.editor["+2026-11-16"]), eve19: ids(L.editor["+2026-11-19"]),
  stephLate: ids(L.email_lead.late)}));""")
        seven = ["brand_b__nov-%d" % i for i in range(21, 28)]
        self.assertEqual(got["eve13"], seven, "7 on her first day")
        self.assertEqual(got["eve16"], ["brand_b__nov-28", "brand_b__nov-29"], "the rest the next working day")
        self.assertEqual(got["eve19"], [], "not all piled on the day before the send")
        self.assertEqual(got["stephLate"], seven + ["brand_b__nov-28", "brand_b__nov-29"],
                         "email_lead's day is a week before editor's page (2026-11-11): for these, already past")

    def test_first_look_qc(self):
        """email_lead, 2026-11-05: a QC as someone opening the page for the first time (designer, owner, editor)."""
        page = read(PAGE)
        self.assertIn(".cq .lot .l-top,.cq .camp .l-top{display:flex;justify-content:space-between;gap:4px 6px;align-items:center;flex-wrap:wrap}", page,
                      "three marks on a card wrap instead of spilling out of it")
        self.assertIn('x.textContent = "Priority: " + PR_WORD[v]', page, "a priority pill says it is one, not 'owner Next'")
        self.assertIn('ownEmails === true ? "/p/" + who + "/emails.html#" + m[1] : val(u)', page,
                      "the emails link opens the person's own emails page only when it exists, else the team's on the same server")
        self.assertNotIn('a.href = r.email_link.url', page)
        self.assertNotIn("opens <code>http://127.0.0.1:8765</code>", page)
        self.assertIn("Not written yet. email_lead writes it by", page)
        self.assertIn('[gone, "Won\'t make it: no room for editor at " + editor_RULE + " before they send"]', page)
        self.assertIn('$("#cq-status").textContent = staticsNote("editor").trim(); renderCal(); return;', page, "the List's count line stays off the calendar")
        self.assertIn(".cq .mg-c::before{content:attr(data-i);font-weight:700}", page, "on a phone each chip keeps its person's initial")

    def test_wont_make_it_shows_in_team(self):
        got = self._core("""
var T = "2026-11-25", W = []; for (var i = 1; i <= 9; i++) W.push({brand: "brand_a", slot: "nov-" + (40 + i), send: "2026-11-27", type: "proof-drop"});
evePack([], W, T, {}); var L = calLoad([], W, T), n = function (a) { return (a || []).length; };
console.log(JSON.stringify({eve26: n(L.editor["+2026-11-26"]), missEve: n(L.editor["!2026-11-27"]), missSteph: n(L.email_lead["!late"]), stephLate: n(L.email_lead.late)}));""")
        self.assertEqual(got, {"eve26": 7, "missEve": 2, "missSteph": 2, "stephLate": 7},
                         "7 fit on the 26th; 2 won't make it, on the send day and on email_lead's (a week earlier since 2026-11-11, so past)")

    def test_emails_to_write_are_to_make_and_coming_to_editor(self):
        """email_lead, 2026-11-05: "deberíamos poner en to make los correos que tengo que escribir ... lo que le sigue a editor"."""
        got = self._core("""
var W = [{brand: "brand_b", slot: "nov-21", send: "2026-11-20", type: "sale-window", evBy: "2026-11-16"},
         {brand: "brand_a", slot: "nov-44", send: "2026-11-30", type: "proof-drop", evOver: true}];
var b = boardPieces({rows: [], towrite: W}, null, null), lots = boardLots(b.pieces, "2026-11-05");
var plan = b.pieces.filter(function (p) { return p.col === "plan"; });
console.log(JSON.stringify({plan: plan.map(function (p) { return [p.id, p.who, p.due, p.moment, p.type]; }),
  coming: b.pieces.filter(function (p) { return makerHas(p, "editor", "@coming"); }).length,
  why: lots.map(function (g) { return g.why; }), name: momentName("emails-to-write"),
  cal: calLoad(b.pieces, W, "2026-11-05").editor}));""")
        self.assertEqual(got["plan"], [["brand_b__nov-21", "email_lead", "2026-11-11", "emails-to-write", "email"],
                                       ["brand_a__nov-44", "email_lead", "2026-11-24", "emails-to-write", "email"]],
                         "email_lead's, 3 working days before it must be on editor's page (2026-11-16; was 5); one that won't make it, counted from two working days before its send; "
                         "Mon Nov 23 is her day off, so it moves to Tue Nov 24 (email_lead, 2026-11-19)")
        self.assertEqual(got["coming"], 2, "what comes next for editor")
        self.assertIn(["not written yet; then: editor (designer)"], got["why"])
        self.assertIn(["won't make it: no room for editor at 7 a day", "not written yet; then: editor (designer)"], got["why"])
        self.assertEqual(got["name"], "Emails to write")
        self.assertIn('if (f[0].towrite && g.due) meta.push("write by " + boardDay(g.due)', read(PAGE), "the card says email_lead's day, then editor's page day")
        self.assertEqual(sorted(got["cal"]), ["!2026-11-30", "+2026-11-19"], "the calendar counts them once, from towrite")

    def test_the_panel_and_tiles(self):
        page = read(PAGE)
        self.assertIn('<aside class="peek" id="cq-peek" aria-label="One piece" data-feature="71" hidden>', page)
        self.assertIn('<template id="cq-t-tile"><button type="button" class="tile" data-feature="70"><i class="dot"></i></button></template>', page)
        self.assertIn('<template id="cq-t-prog"><div class="l-prog" data-feature="69">', page)
        self.assertIn('<p class="p-stuck" data-feature="72"></p>', page)
        self.assertIn('<p class="p-note" data-feature="73"></p>', page)
        self.assertIn('t.addEventListener("click", function () { openPeek(g, p, today); });', page)
        self.assertIn('if (!$("#cq-add").hidden) closeAdd(); else if (!$("#cq-peek").hidden) closePeek();', page,
                      "Escape closes the panel; the New task window first when it is open (2026-11-10)")

    def test_the_hand_off_stands_for_its_queue_row(self):
        self.assertNotIn("brand_a_flex_brief-0297", self.by_id)

    def test_bank_live_removed_and_gone_are_not_drawn(self):
        self.assertEqual(self.got["bank"], 2)
        self.assertEqual(self.got["live"], {"static": 1, "email": 1})
        for gone in ("brand_a_flex_brief-0503", "brand_a_flex_brief-0504", "brand_a_flex_brief-0500"):
            self.assertNotIn(gone, self.by_id)

    def test_cards_gather_by_person_brand_type_and_day_worst_flag_first(self):
        lots = self.got["lots"]
        self.assertEqual(lots[0][:5], ["making", "editor", "static", 1, "late"])
        emails = [g for g in lots if g[2] == "email" and g[0] == "making" and not g[6]
                  and not any(w.startswith("held") for w in g[5])]     # the two held fixtures are their own cards
        self.assertEqual(len(emails), 2, "one person, one picture day: one card per brand")
        self.assertEqual(sorted(g[3] for g in emails), [1, 2], "two brand_a emails together, the brand_b one apart")
        self.assertEqual([g[4:6] for g in emails], [["risk", ["editor's day", "pictures due tomorrow"]]] * 2,
                         "her day counts as working on it: she finishes her day's emails (2026-11-11)")
        brief = [g for g in lots if g[0] == "brief" and g[2] == "static" and g[3] == 2 and not g[6]]
        self.assertEqual(len(brief), 1, "Brief review gathers by brand and type, not by day")
        self.assertEqual(brief[0][4:6], ["waiting", ["oldest waiting 10 days"]])

    def test_the_reasons_say_why(self):
        why = {(g[0], g[1], g[2], g[3]): g[5] for g in self.got["lots"]}
        every = [w for g in self.got["lots"] for w in g[5]]
        self.assertFalse([w for w in every if "owner's list" in w], "an old owner's list is said once at the top, never per card")
        # a one-piece card no longer counts "0 of 1 have work back" (QC as designer, 2026-11-11): its own line says it
        self.assertFalse([w for w in every if "of 1 have work back" in w], "a one-piece card never counts itself")
        self.assertIn("due in 2 days", every, "0306 and 0297 still say their due")
        self.assertIn("nothing back yet", every, "0306 (none back) says so in words")
        self.assertIn("files coming back", every, "an In progress card says why it is there")
        self.assertNotIn("1 of 2 with nothing back", every, "never said twice")
        self.assertIn("held for email_lead: price $49.99 · not in the brand's price list", every)
        self.assertIn("held: 5 picture slot(s) still to fill", every)
        self.assertIn("owner's video line, nobody named", why[("making", "owner", "video", 1)])
        finished = [g for g in self.got["lots"] if g[0] == "review" and g[1] == "owner" and g[2] == "static"]
        self.assertEqual(len(finished), 1, "finished statics gather into one owner card per brand")
        self.assertEqual(finished[0][3], 2, "0296 (Done) and 0302 (all back, no Done) together")
        self.assertIn("editor finished; owner's button picks it up", finished[0][5])

    def test_each_makers_days(self):
        days = {d["day"]: d for d in self.got["days"]}
        self.assertEqual(list(days)[0], "late", "past-due work comes first, as one box")
        self.assertEqual((days["late"]["n"], days["late"]["statics"]), (1, 1), "0310, due Nov 1")
        nov5 = days["2026-11-05"]
        self.assertEqual((nov5["n"], nov5["statics"], nov5["back"], nov5["emails"], nov5["held"]), (3, 2, 1, 1, 1),
                         "0297 (2 back) and 0306 (none) and the held nov-09 email")
        self.assertNotIn("2026-11-20", days, "the next 5 working days only")
        self.assertTrue(all(d == "late" or d <= "2026-11-09" for d in days),
                        "Tue Nov 3 + 5 working days ends Mon Nov 9 (email_lead, 2026-11-05)")
        self.assertEqual(self.got["ends"], ["2026-11-09", "2026-11-11", "2026-11-13"], "Tue, Thu, Sat: weekends skipped")
        self.assertFalse(any(d["heavy"] for d in self.got["days"]), "no day here is twice the middle day and 5 or more")

    def test_a_campaign_folds_its_own_lots_and_nothing_else(self):
        self.assertEqual(self.got["camps"], [["black-friday", "risk", "2026-11-06",
                                              [["static", "brand_a", 1], ["static", "brand_a", 1], ["email", "brand_a", 1]]]])
        # since the kanban (email_lead, 2026-11-10) the two statics sit in different lanes: one with work back is In progress
        others = [g for g in self.got["lots"] if g[0] == "making" and g[1] == "editor" and g[2] == "static" and not g[6]]
        self.assertEqual(len(others), 4, "0297, 0306, 0310 and 0314 stay out of the fold: their briefs name no campaign "
                                         "(0297, with work back, is In progress and 0306 Assigned, so they no longer share a card)")
        self.assertEqual(self.got["names"], ["Black Friday", "NBA Regular Season", "Veterans Day", "Evergreen"])

    def test_to_make_is_the_calendars_pieces_before_a_brief(self):
        self.assertEqual(self.got["cols"], ["plan", "brief", "assigned", "progress", "review", "launch"], "Coming up comes first (kanban, 2026-11-10)")
        self.assertEqual(self.got["plan"], [
            ["cal-bf-edit", "video", "black-friday", "video editor"],
            ["cal-xmas-org", "organic video", "christmas", "organic"],
            ["cal-ever", "static", "evergreen", "designer"],          # the evergreen lane folds as Evergreen
            ["cal-page", "page", "black-friday", "developer"]])
        self.assertEqual(self.got["calMail"], {"email": 1, "sms": 1}, "emails and texts are counted, never drawn")
        self.assertEqual(self.got["calAsOf"], "2026-11-04T05:30:31Z")
        self.assertEqual(self.got["laterDays"], 14)
        why = {g[0] + "|" + g[2]: g[5] for g in self.got["lots"] if g[0] == "plan"}
        self.assertEqual(why["plan|video"], ["no brief yet", "then: creator (video editor)"])
        self.assertEqual(why["plan|organic video"], ["then: organic"], "far off: no warning, only who makes it")
        self.assertEqual(why["plan|page"], ["past its date", "no brief yet", "then: developer"])

    def test_no_calendar_no_column_content(self):
        page = read(PAGE)
        helpers = "".join(fn(page, n) for n in ("val", "plural", "isEmail", "turnWho", "briefOf", "productOf",
                                                 "sameBrief", "roundOf", "keepQueued", "uniq"))
        got = run_node(helpers + core(page) + "var b = boardPieces({rows: []}, null, null);"
                       "console.log(JSON.stringify([b.pieces.length, b.calMail, b.calAsOf]));")
        self.assertEqual(got, [0, {"email": 0, "sms": 0}, ""])

    def test_copy_for_claude_names_the_full_key(self):
        self.assertEqual(self.got["line"],
                         "Make brief brand_b_brilliance-body-scrub_brief-0314 (brand_b, the graphic-designer hand-off "
                         "on Drive). Use the brief-handoff skill: show me each step before it spends credits, and save "
                         "what we make to its returned/ folder.")


class Page(unittest.TestCase):
    def test_markup(self):
        page = read(PAGE)
        self.assertIn('<template id="cq-t-camp"><details class="camp" data-feature="59">', page)
        self.assertIn('<template id="cq-t-send"><div class="l-send" data-feature="60"></div></template>', page)
        self.assertIn('<template id="cq-t-plancol"><section class="bd-col plan" data-feature="61"></section></template>', page)
        self.assertIn('<template id="cq-t-later"><details class="camp" data-feature="62">', page)
        self.assertIn('<template id="cq-t-calfresh"><span data-feature="63"></span></template>', page)
        # the board is the first view; Everyone became List (email_lead, 2026-11-03)
        self.assertIn('<button type="button" data-view="" aria-pressed="true" data-feature="50">Board</button>\n'
                      '        <button type="button" data-view="calendar" aria-pressed="false" data-feature="74">Calendar</button>\n'
                      '        <button type="button" data-view="list" aria-pressed="false">List</button>', page)
        self.assertNotIn(">Everyone<", page)
        self.assertIn('list = location.hash === "#list", cal = location.hash === "#calendar", board = !name && !list && !cal', page)
        self.assertIn('<main id="cq-board" class="bd" data-feature="51" hidden>', page)
        self.assertEqual(page.count('<button type="button" class="btn v-claude" data-feature="58">Copy for Claude</button>'), 2,
                         "on the static and the video hand-off")
        self.assertIn('claudeLine(s.key, s.brand, "graphic-designer")', page)
        self.assertIn('claudeLine(v.key, v.brand, "video-editor")', page)

    def test_a_makers_numbers_and_no_date_are_buttons(self):
        page = read(PAGE)
        self.assertIn('<template id="cq-t-mchip"><button type="button" class="d-chip" data-feature="66"></button></template>', page)
        self.assertIn('<template id="cq-t-nodate"><button type="button" class="d-day nodate" data-feature="67"></button></template>', page)

    def test_a_day_box_is_a_button(self):
        page = read(PAGE)
        self.assertIn('box = el("button", "d-day"', page)
        self.assertIn('btn.setAttribute("aria-pressed", String(dayFocus === key))', page)   # pick(), for days, numbers and No date
        self.assertIn("pick(box, key);", page)
        self.assertIn("the meaning of each number and day lives in its tooltip", page)

    def test_the_board_writes_only_a_priority_and_a_due(self):
        """Read only until 2026-11-05; then a priority, through the kit's direct 79. Since 2026-11-06 also a due date, a
        piece moved to another day on the Calendar (email_lead: "que se pueda mover de un día a otro"), through direct 24,
        field due only. Since 2026-11-10 also a task's Done (email_lead, option B), through direct 87, cq.py remove, tasks
        only. Nothing else, and never without the page server."""
        board = re.search(r"  function renderBoard\(\)[\s\S]*?\n  function uniq", read(PAGE)).group(0)
        for verb in ("change(", "pfAct(", "fetch("):
            self.assertNotIn(verb, board)
        self.assertEqual(board.count("direct("), 5)
        self.assertIn('direct({n: 88, item: p.id, field: "requested_stage", value: to})', board, "any card dragged between Assigned and In progress (2026-11-11)")
        self.assertIn('direct({n: 87, item: p.id, field: "remove"})', board, "a task dragged to Done")
        self.assertIn('if (lane === "launch" && !dragTask.items.every(function (p) { return p.type === "task"; })) return;', board, "only a task is done by a drag")
        self.assertIn('var TASK_LANES = {assigned: "making", progress: "editing", launch: "done"}', board, "only a task drags on the Board")
        self.assertIn('isTask = p.type === "task" && p.row;', board)
        self.assertIn('tdone.hidden = !(isTask && kitToken()) || fromPM(p);', board)
        self.assertIn('direct({n: 87, item: p.id, field: "remove"})', board)
        self.assertIn('direct({n: 79, item: p.id, field: "priority", value: v ? PR_VALUE[v] : ""})', board)
        self.assertIn('if (!kitToken()) { say.textContent = "Open the board from your page server to set this"; return; }', board)
        self.assertIn('direct({n: 24, item: p.id, field: "due", value: d})', board)
        self.assertIn('if (!kitToken()) { say.className = "say bad"; say.textContent = "Open the board from your page server to move it"; return; }', board)

    def test_the_queue_tells_the_page_who_is_looking(self):
        """2026-11-06: only owner, designer or email_lead move an email, so /data/queue carries the page server's person;
        asked per source ("viewer": true), so another family's source of the same name is untouched."""
        sys.path.insert(0, os.path.join(REAL, "components", "page-features", "kit"))
        import serve
        src = serve.Sources(lambda: serve.sources("content-queue", REAL), root=REAL)
        self.assertTrue(src.wants_viewer("queue"))
        self.assertFalse(src.wants_viewer("statics"))
        self.assertFalse(serve.Sources(lambda: serve.sources("outlier-demo", REAL), root=REAL).wants_viewer("queue"))

    def test_features(self):
        with open(FEATURES, encoding="utf-8") as fh:
            got = {f["n"]: (f["name"], f["kind"]) for f in json.load(fh)["features"] if f["n"] >= 50}
        self.assertEqual(got, {50: ("Board view switch", "layout"), 51: ("The board", "layout"),
                               52: ("How fresh each source is", "data"), 53: ("Due: today, tomorrow, in 2 days, later, no date", "rule"),
                               55: ("Who has the next move", "rule"), 56: ("The columns and their cards", "rule"),
                               57: ("Not on the board", "rule"), 58: ("Copy for Claude", "action"),
                               59: ("A campaign, folded", "rule"), 60: ("When an email sends, on its card", "data"),
                               61: ("To make: the promo calendar's pieces", "rule"),
                               62: ("Later, in To make", "rule"), 63: ("How fresh the promo calendar is", "data"),
                               64: ("Each maker's days", "rule"), 65: ("What this page is for", "layout"),
                               66: ("A maker's numbers: working on, coming, finished", "rule"),
                               67: ("No date, in a maker's row", "rule"), 68: ("Pick a person", "rule"),
                               69: ("How far along a batch is", "rule"), 70: ("A card's pictures", "media"),
                               71: ("One piece, up close", "rule"), 72: ("Stuck in Production or Edit", "rule"),
                               73: ("owner's note when he sent it back", "data"),
                               74: ("Calendar view switch", "layout"),
                               75: ("A week, Monday to Friday: who has what", "rule"),
                               76: ("email_lead's emails to write, and editor's coming", "rule"), 77: ("Change week", "layout"),
                               78: ("A day's pieces", "layout"),
                               79: ("Set a priority: Now / Next / Later / Drop", "action"),
                               81: ("Priority on a card, and the order it makes", "rule"),
                               82: ("editor's load", "rule"),
                               84: ("Move a piece to another day", "action"),
                               86: ("Tasks: + Add task, and what to do", "action"), 87: ("A task's Done", "action"),
                               88: ("Drag a card to In progress or back; a task to Done", "action"),
                               89: ("What happened to a piece, and what comes next", "rule"),
                               90: ("Brands: filter the Board by brand, alone or with a person", "layout")})


if __name__ == "__main__":
    unittest.main()
