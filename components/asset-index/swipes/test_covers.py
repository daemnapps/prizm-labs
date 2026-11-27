#!/usr/bin/env python3
"""covers.py: an avatar's own covers in the swipe index, a pull brought in from outside, and the move each cover makes.

    /usr/bin/python3 components/asset-index/swipes/test_covers.py

  a  an avatar file drives the pull: only the hashtags, accounts and topics it lists are asked for, on the platforms
     it lists; the file is kept beside the raw results
  b  rows from an avatar pull carry the avatar and what carried them (`via`); the avatar's floor and topic words
     apply, the discovery surfaces' 21-day limit does not
  c  index keeps the rows of other pulls: discovery covers and an avatar's covers sit in one covers.json; the
     per-platform sums stay the discovery surfaces'; avatars.json holds one record per avatar
  d  find with an avatar returns only that avatar's covers, by likes, or by views when asked
  e  find falls back to the discovery covers and says so: an avatar with no covers, and an avatar whose covers all
     fail the other filters
  f  import brings an outside pull into the index with its avatar, carries its breakdown, leaves out a row with no
     picture and counts it, changes nothing in the pull folder, keeps the rows already there, and can run twice
  g  derive_move reads the move from the breakdown's own fields and leaves `unrated` where it says none
  h  moves fills only the rows that lack one, never overwrites an eye read, takes eye reads by id, and find matches
     a cover's main move or one it also makes
  i  each switch puts its part back: avatar off refuses pull and import and hides avatar rows from find; move off
     refuses moves and ignores --move
  j  one post seen on a discovery surface and by an avatar is one row
  k  an eye read survives a re-import and a re-index; a newer eye read in the pull's breakdown wins
  l  a second pull for an avatar keeps the avatar's covers it does not carry (an import, then an index)
  m  a cover an avatar also sees stays the avatar's when the next discovery pull drops it
  n  find takes an avatar name in any spelling (spaces, underscores, capitals); a bad name raises ValueError in
     Python and stops only the command line
  o  the tightened move rules: impossible-object is read from the breakdown; a plain open mouth or a thing held to
     the camera is not a face at its limit or a thing pushed at the lens
  p  the picture, not the cover's words: a scream or a push named only in the cover's text is not the picture's move,
     and a line is shown literally only when its words name something in a picture past real (surreal 2 or 3)
  q  a discovery pull replaces only the rows of the sources it ran: a narrower pull keeps the other sources' covers
     and their eye reads
No network, no key, no model: the Apify door and the key loader are fakes, every folder is a temp folder.
"""
import contextlib
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import covers as C  # noqa: E402

FIX = HERE / "fixtures" / "avatar-pull"
AVATAR = "example-home-baker"
EYE = {"frame": "face", "people": "one", "expression": "neutral", "shot": "medium", "zoom": "native",
       "text_style": "none", "text_words": 0, "text_case": "none", "text_place": "none", "grade": "native",
       "marks": ["none"], "look": "native", "shows": "person in a room", "absurd": 0}
MEASURE = {"text": "", "text_lines": 0, "text_words": 0, "text_area": 0, "text_line_height": 0, "text_centre_y": None,
           "faces": 1, "face_area": 0.1, "hands": 0, "brightness": 0.5, "contrast": 0.2, "saturation": 0.3,
           "colourfulness": 30.0, "dominant": ["#000000"], "width": 18, "height": 32}


def days_ago(n):
    return (datetime.now(timezone.utc) - timedelta(days=n)).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def tag_item(code, likes, plays, tag, caption, age=400, **more):
    return {"url": f"https://www.instagram.com/p/{code}/", "shortCode": code, "displayUrl": f"https://example.invalid/{code}.jpg",
            "likesCount": likes, "videoPlayCount": plays, "commentsCount": 10, "timestamp": days_ago(age),
            "inputUrl": f"https://www.instagram.com/explore/tags/{tag}", "ownerUsername": "example.account",
            "caption": caption, "videoDuration": 20.0, **more}


def general_row(n, likes, views=None, **eye):
    return {"platform": "instagram", "surface": "Instagram Explore (US locale)", "url": f"https://www.instagram.com/reel/Gen0000000{n}/",
            "cover_url": "https://example.invalid/g.jpg", "views": views, "likes": likes, "comments": 1,
            "posted": days_ago(3), "author": "example.general", "followers": None, "caption": "", "kind": "reel",
            "duration": None, "age_days": 3.0, "source": "ig-explore", "id": f"ig-n000000{n}", "_eye": {**EYE, **eye}}


def picture(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(FIX / "covers" / "FxBread00001.jpg", path)


def pull_folder(d, rows, avatar=None):
    """A pull folder ready for `index`: rows.json, measure.json, breakdown.json, a picture per row."""
    d.mkdir(parents=True, exist_ok=True)
    eye = {r["id"]: r.pop("_eye", dict(EYE)) for r in rows}
    (d / "rows.json").write_text(json.dumps(rows))
    (d / "measure.json").write_text(json.dumps({r["id"]: MEASURE for r in rows}))
    (d / "breakdown.json").write_text(json.dumps(eye))
    for r in rows:
        picture(d / "covers" / f"{r['id']}.jpg")
    if avatar:
        (d / "avatar.json").write_text(json.dumps(avatar))
    return d


def quiet(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*a, **k)


def tree(d):
    return {str(p.relative_to(d)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(d.rglob("*")) if p.is_file()}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="covers-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("COVER_SWIPES_OFF", None)

    def general_index(self, rows=None):
        out = self.tmp / "index"
        rows = rows or [general_row(1, 50000), general_row(2, 90000), general_row(3, 20000, views=700000)]
        quiet(C.index, pull_folder(self.tmp / "general", rows), out)
        return out

    def rows(self, out):
        return json.loads((out / "covers.json").read_text())


class AvatarPull(Base):
    AV = {"avatar": AVATAR, "who": "home bakers", "platforms": ["instagram", "tiktok"],
          "hashtags": ["#sourdough", "homebaking"], "accounts": ["@example.account"], "topics": ["bread scoring"],
          "on_topic": ["bread", "sourdough"], "floor": {"instagram": {"likes": 6000}}}

    def test_a_avatar_file_drives_the_pull(self):
        f = self.tmp / "avatar.json"
        f.write_text(json.dumps(self.AV))
        jobs = C.avatar_jobs(C.read_avatar(f), "2026-01-01")
        self.assertEqual(sorted(jobs), ["av-ig-accounts", "av-ig-tags", "av-tt-accounts", "av-tt-tags", "av-tt-topics"])
        self.assertEqual(jobs["av-ig-tags"][1]["hashtags"], ["sourdough", "homebaking"])
        self.assertEqual(jobs["av-ig-accounts"][1]["directUrls"], ["https://www.instagram.com/example.account/"])
        self.assertEqual(jobs["av-tt-topics"][1]["searchQueries"], ["bread scoring"])
        tags_only = self.tmp / "tags-only.json"
        tags_only.write_text(json.dumps({**self.AV, "platforms": ["instagram"], "accounts": []}))
        self.assertEqual(list(C.avatar_jobs(C.read_avatar(tags_only), "2026-01-01")), ["av-ig-tags"])

        asked = []

        def api(path, token, data=None):
            asked.append((path.split("?")[0], data))
            if path.startswith("acts/"):
                return {"data": {"id": "run-" + path.split("/")[1], "defaultDatasetId": "ds-" + path.split("/")[1]}}
            if path.startswith("actor-runs/"):
                return {"data": {"status": "SUCCEEDED", "defaultDatasetId": "ds", "usageTotalUsd": 0.1}}
            return [tag_item("FxBread00009", 9000, 1000, "sourdough", "bread")]
        loader = types.ModuleType("loader")
        loader.key = lambda name: "fake"
        d = self.tmp / "pull"
        with mock.patch.dict(sys.modules, {"loader": loader}), mock.patch.object(C, "_api", api), mock.patch.object(C.time, "sleep", lambda s: None):
            quiet(C.pull, d, "ANY_KEY_NAME", None, 1, avatar=f)
        started = [p for p, data in asked if p.startswith("acts/")]
        self.assertEqual(len(started), 5)
        self.assertNotIn("acts/agentx~instagram-trending-scraper/runs", started)      # no discovery source is asked for
        self.assertEqual(json.loads((d / "avatar.json").read_text())["avatar"], AVATAR)
        self.assertTrue((d / "raw" / "av-ig-tags.json").exists())

    def test_b_rows_carry_the_avatar(self):
        d = self.tmp / "pull"
        (d / "raw").mkdir(parents=True)
        (d / "avatar.json").write_text(json.dumps(self.AV))
        (d / "raw" / "av-ig-tags.json").write_text(json.dumps([
            tag_item("FxBread00011", 45000, 900000, "sourdough", "my bread, a year old post", age=400),
            tag_item("FxBread00012", 5500, 50000, "sourdough", "bread under this avatar's floor"),
            tag_item("FxBread00013", 80000, 70000, "homebaking", "nothing to do with it"),
            tag_item("FxBread00014", -1, 300000, "sourdough", "bread, likes hidden"),
        ]))
        quiet(C.rows, d)
        got = json.loads((d / "rows.json").read_text())
        self.assertEqual([r["id"] for r in got], ["ig-ead00011"])
        r = got[0]
        self.assertEqual((r["avatar"], r["via"], r["likes"], r["views"], r["source"]), (AVATAR, "#sourdough", 45000, 900000, "av-ig-tags"))
        self.assertGreater(r["age_days"], C.MAX_AGE_DAYS)             # the discovery age limit did not drop it

    def test_b_avatar_source_needs_its_avatar_file(self):
        d = self.tmp / "pull"
        (d / "raw").mkdir(parents=True)
        (d / "raw" / "av-ig-tags.json").write_text("[]")
        with self.assertRaises(SystemExit):
            quiet(C.rows, d)


class Index(Base):
    def avatar_index(self, out, likes=(41000, 96000, 7000), views=(880000, 310000, 1500000), eyes=None):
        rows = []
        for n, (lk, vw) in enumerate(zip(likes, views), 1):
            r = general_row(n, lk, vw, **((eyes or {}).get(n) or {}))
            r.update(id=f"ig-av00000{n}", url=f"https://www.instagram.com/p/Av0000000{n}/", source="av-ig-tags",
                     avatar=AVATAR, via="#sourdough", surface="Instagram, avatar feed · #sourdough")
            rows.append(r)
        quiet(C.index, pull_folder(self.tmp / "avatar", rows, {"avatar": AVATAR, "who": "home bakers", "hashtags": ["sourdough"]}), out)

    def test_c_index_keeps_other_pulls(self):
        out = self.general_index()
        before = json.loads((out / "patterns.json").read_text())
        self.avatar_index(out)
        rows = self.rows(out)
        self.assertEqual(sorted(r["id"] for r in rows if not r["avatar"]), ["ig-n0000001", "ig-n0000002", "ig-n0000003"])
        self.assertEqual(sorted(r["id"] for r in rows if r["avatar"] == AVATAR), ["ig-av000001", "ig-av000002", "ig-av000003"])
        self.assertEqual(json.loads((out / "patterns.json").read_text()), before)     # the sums are the discovery surfaces'
        av = json.loads((out / "avatars.json").read_text())[AVATAR]
        self.assertEqual((av["covers"], av["who"], av["hashtags"], av["median_likes"]), (3, "home bakers", ["sourdough"], 41000))
        quiet(C.index, self.tmp / "general", out)                                      # the discovery pull again
        self.assertEqual(len(self.rows(out)), 6)
        self.avatar_index(out, likes=(41000,), views=(880000,))                        # the avatar's pull again, smaller
        self.assertEqual(sorted(r["id"] for r in self.rows(out) if r["avatar"]), ["ig-av000001", "ig-av000002", "ig-av000003"])

    def test_d_find_by_avatar_ranked(self):
        out = self.general_index()
        self.avatar_index(out)
        res = C.find_covers(out, avatar=AVATAR)
        self.assertEqual((res["scope"], res["avatar"], res["note"]), ("avatar", AVATAR, ""))
        self.assertEqual([s["likes"] for s in res["covers"]], [96000, 41000, 7000])
        self.assertTrue(all(s["avatar"] == AVATAR for s in res["covers"]))
        self.assertEqual([s["views"] for s in C.find_covers(out, avatar=AVATAR, rank="views")["covers"]], [1500000, 880000, 310000])
        self.assertEqual(len(C.find_covers(out, avatar=AVATAR, limit=2)["covers"]), 2)
        self.assertEqual({s["id"] for s in C.find_covers(out)["covers"]}, {"ig-n0000001", "ig-n0000002", "ig-n0000003"})
        text = io.StringIO()
        with contextlib.redirect_stdout(text):
            C.main(["find", str(out), "--avatar", AVATAR, "--json", "--limit", "1"])
        said = json.loads(text.getvalue())
        self.assertEqual((said["scope"], said["covers"][0]["likes"], said["covers"][0]["frame_file"]), ("avatar", 96000, "covers/ig-av000002.jpg"))

    def test_e_find_falls_back_and_says_so(self):
        out = self.general_index()
        res = C.find_covers(out, avatar="example-nobody")
        self.assertEqual(res["scope"], "general-fallback")
        self.assertIn("example-nobody has no covers in the index", res["note"])
        self.assertEqual(len(res["covers"]), 3)
        self.avatar_index(out)
        res = C.find_covers(out, avatar=AVATAR, frame="product")                       # its covers, none pass: no fallback
        self.assertEqual((res["scope"], res["avatar"], res["covers"]), ("avatar", AVATAR, []))
        self.assertIn("has 3 covers, none pass these filters", res["note"])
        res = C.find_covers(out, avatar=AVATAR, move="wrong-scale")
        self.assertEqual((res["scope"], res["covers"]), ("avatar", []))
        os.environ["COVER_SWIPES_OFF"] = "avatar-scope"                               # the switch puts the wide fallback back
        res = C.find_covers(out, avatar=AVATAR, frame="product")
        self.assertEqual((res["scope"], res["covers"]), ("general-fallback", []))
        self.assertIn("has 3 covers, none pass these filters", res["note"])
        os.environ.pop("COVER_SWIPES_OFF")
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            C.main(["find", str(out), "--avatar", "example-nobody"])
        self.assertIn("NOTE: avatar example-nobody has no covers in the index", err.getvalue())

    def test_j_one_post_two_pulls_is_one_row(self):
        out = self.general_index()
        shared = general_row(1, 50000)
        shared.update(source="av-ig-tags", avatar=AVATAR, via="#sourdough")
        quiet(C.index, pull_folder(self.tmp / "avatar", [shared], {"avatar": AVATAR}), out)
        rows = self.rows(out)
        self.assertEqual(len(rows), 3)
        one = next(r for r in rows if r["id"] == "ig-n0000001")
        self.assertEqual((one["avatar"], one["avatar_also"], one["source"]), (None, [AVATAR], "ig-explore"))
        self.assertEqual([s["id"] for s in C.find_covers(out, avatar=AVATAR)["covers"]], ["ig-n0000001"])
        self.assertEqual(len(C.find_covers(out)["covers"]), 3)
        quiet(C.index, self.tmp / "general", out)
        self.assertEqual(next(r for r in self.rows(out) if r["id"] == "ig-n0000001")["avatar_also"], [AVATAR])


class Import(Base):
    def test_f_import_an_outside_pull(self):
        out = self.general_index()
        before = tree(FIX)
        counts = quiet(C.import_pull, FIX, out, FIX / "avatar.json", pulled="2026-11-11")
        self.assertEqual(tree(FIX), before)                                            # the pull folder is untouched
        self.assertEqual(counts, {"avatar": AVATAR, "imported": 3, "left_out": {"no picture": 1}, "index": 6})
        rows = {r["id"]: r for r in self.rows(out)}
        self.assertEqual(sorted(i for i, r in rows.items() if r["avatar"] == AVATAR), ["ig-ead00001", "ig-ead00002", "ig-ead00003"])
        one = rows["ig-ead00001"]
        self.assertEqual((one["platform"], one["url"], one["likes"], one["views"], one["via"], one["author"], one["pulled"]),
                         ("instagram", "https://www.instagram.com/p/FxBread00001/", 41200, 880000, "#sourdough", "example.baker.one", "2026-11-11"))
        self.assertEqual((one["kind_of_swipe"], one["frame_file"], one["breakdown"]["absurd"]), ("cover", "covers/ig-ead00001.jpg", 2))
        self.assertEqual((one["move"], one["move_by"]), ("wrong-scale", "breakdown"))
        self.assertEqual((rows["ig-ead00002"]["move"], rows["ig-ead00002"]["breakdown"]), ("unrated", {}))
        self.assertTrue((out / "covers" / "ig-ead00001.jpg").stat().st_size > 0)
        self.assertEqual(len([r for r in rows.values() if not r["avatar"]]), 3)       # the rows already there are kept
        res = C.find_covers(out, avatar=AVATAR)
        self.assertEqual([s["id"] for s in res["covers"]], ["ig-ead00002", "ig-ead00001", "ig-ead00003"])
        self.assertEqual(json.loads((out / "avatars.json").read_text())[AVATAR]["moves"], {"wrong-scale": 1, "unrated": 2})
        again = quiet(C.import_pull, FIX, out, FIX / "avatar.json", pulled="2026-11-11")
        self.assertEqual((again["imported"], again["index"]), (3, 6))

    def test_f_import_from_the_command_line_by_name(self):
        out = self.tmp / "index"
        with contextlib.redirect_stdout(io.StringIO()):
            C.main(["import", str(FIX), str(out), "--avatar", "example-other-name", "--rows", str(FIX / "keep.json")])
        self.assertEqual({r["avatar"] for r in self.rows(out)}, {"example-other-name"})
        with self.assertRaises(SystemExit):
            quiet(C.main, ["import", str(FIX), str(out)])                              # no avatar named


class Moves(Base):
    CASES = [
        ("impossible-scene", [], {"absurd": 3, "frame": "graphic", "shows": "cartoon figure under a moon"}),
        ("wrong-scale", ["absurd-subject"], {"absurd": 2, "shows": "man balancing a tower of glasses"}),
        ("absurd-subject", [], {"absurd": 2, "shows": "poster, huge yellow script title"}),      # huge is the type's size
        ("face-at-limit", [], {"absurd": 1, "shows": "man head back, mouth wide open"}),
        ("face-at-limit", [], {"absurd": 0, "expression": "shock", "frame": "face", "shot": "close", "shows": "woman in a kitchen, small caption", "text_style": "outline", "text_words": 4}),
        ("before-after", ["impossible-scene", "pointed-at"], {"absurd": 3, "marks": ["arrow"], "shows": "before/after panels joined by a red arrow"}),
        ("pointed-at", ["price-as-hook"], {"absurd": 1, "marks": ["arrow", "price"], "shows": "man holding two packs, price labels, red arrows"}),
        ("price-as-hook", [], {"absurd": 1, "shows": 'creator pointing at an advent calendar, caps "$276 ADVENT CALENDAR?!"'}),
        ("one-odd-thing", [], {"absurd": 1, "shows": 'woman holding a fig, serif "The humble fig\'s secret"'}),
        ("thing-to-lens", [], {"absurd": 0, "shows": "driver pushing a small object at the camera"}),
        ("one-odd-thing", [], {"absurd": 1, "shows": "dog digging into a leaf pile"}),
        ("as-shot", [], {"absurd": 0, "shows": "singer on stage under a light beam"}),
        ("unrated", [], {"absurd": 0, "text_style": "native-box", "text_words": 7, "shows": "student in a classroom, white box black text"}),
    ]

    def test_g_move_from_the_breakdown(self):
        for want, also, eye in self.CASES:
            move, got_also, why = C.derive_move({**EYE, **eye})
            self.assertEqual((move, got_also), (want, also), eye["shows"])
            self.assertTrue(why or move == "unrated")
        self.assertEqual(C.derive_move({}), ("unrated", [], ""))
        self.assertEqual(C.derive_move({"shows": "a thing"}), ("unrated", [], ""))
        self.assertTrue(set(m for m, _, _ in self.CASES) - {"unrated"} <= set(C.MOVES))
        self.assertEqual(C.BREAKDOWN["move"], list(C.MOVES))

    def old_index(self):
        """An index written before the move field: rows with a breakdown and no move."""
        out = self.tmp / "index"
        (out / "covers").mkdir(parents=True)
        rows = []
        for n, (want, also, eye) in enumerate(self.CASES):
            r = general_row(n, 1000 * (n + 1))
            r.update(id=f"ig-case{n:04d}", breakdown={**r.pop("_eye"), **eye}, measure=MEASURE, frame_file=f"covers/ig-case{n:04d}.jpg",
                     kind_of_swipe="cover", use=["paid", "organic"], pulled="2026-11-11")
            rows.append(r)
        bare = general_row(99, 5)
        bare.pop("_eye")
        bare.update(id="ig-bare0000", breakdown={}, measure={}, frame_file="covers/ig-bare0000.jpg")
        (out / "covers.json").write_text(json.dumps(rows + [bare]))
        return out

    def test_h_moves_fills_what_is_missing(self):
        out = self.old_index()
        self.assertTrue(all("move" not in r for r in self.rows(out)))
        counts = quiet(C.moves, out)
        rows = {r["id"]: r for r in self.rows(out)}
        self.assertEqual([rows[f"ig-case{n:04d}"]["move"] for n in range(len(self.CASES))], [c[0] for c in self.CASES])
        self.assertEqual((rows["ig-bare0000"]["move"], rows["ig-bare0000"]["move_by"]), ("unrated", None))
        self.assertEqual(counts["unrated"], 2)
        self.assertEqual(rows["ig-case0001"]["move_by"], "breakdown")
        self.assertIn("tower of", rows["ig-case0001"]["move_why"])

        with contextlib.redirect_stdout(io.StringIO()):                                # two eye reads, by id
            C.main(["moves", str(out), "--set", "ig-bare0000=impossible-object", "ig-case0011=face-at-limit"])
        rows = {r["id"]: r for r in self.rows(out)}
        self.assertEqual((rows["ig-bare0000"]["move"], rows["ig-bare0000"]["move_by"]), ("impossible-object", "eye"))
        quiet(C.moves, out, None, True)                                                # --redo re-reads rule-made rows only
        rows = {r["id"]: r for r in self.rows(out)}
        self.assertEqual((rows["ig-case0011"]["move"], rows["ig-case0011"]["move_by"]), ("face-at-limit", "eye"))
        self.assertEqual(rows["ig-case0000"]["move"], "impossible-scene")
        with self.assertRaises(SystemExit):
            quiet(C.moves, out, {"ig-case0000": "not-a-move"})
        with self.assertRaises(SystemExit):
            quiet(C.moves, out, {"ig-nothere": "as-shot"})

        self.assertEqual([s["id"] for s in C.find_covers(out, move="wrong-scale")["covers"]], ["ig-case0001"])
        also = {s["id"] for s in C.find_covers(out, move="pointed-at")["covers"]}
        self.assertEqual(also, {"ig-case0005", "ig-case0006"})                         # a main move and one a cover also makes
        self.assertEqual([s["id"] for s in C.find_covers(out, move="unrated")["covers"]], ["ig-case0012"])
        text = io.StringIO()
        with contextlib.redirect_stdout(text):
            C.main(["find", str(out), "--move", "before-after"])
        self.assertEqual(text.getvalue().split()[-2:], ["before-after", "-"])

    def test_h_index_writes_the_move_and_an_eye_read_wins(self):
        rows = [general_row(1, 10, shows="man balancing a tower of glasses", absurd=2),
                general_row(2, 20, shows="man balancing a tower of glasses", absurd=2, move="impossible-object")]
        out = self.general_index(rows)
        got = {r["id"]: (r["move"], r["move_by"]) for r in self.rows(out)}
        self.assertEqual(got, {"ig-n0000001": ("wrong-scale", "breakdown"), "ig-n0000002": ("impossible-object", "eye")})


class Merge(Base):
    def test_k_eye_read_survives_reimport_and_reindex(self):
        out = self.general_index()
        quiet(C.import_pull, FIX, out, FIX / "avatar.json", pulled="2026-11-11")
        quiet(C.moves, out, {"ig-ead00003": "before-after", "ig-n0000001": "impossible-object"})
        quiet(C.import_pull, FIX, out, FIX / "avatar.json", pulled="2026-11-11")
        quiet(C.index, self.tmp / "general", out)
        rows = {r["id"]: r for r in self.rows(out)}
        self.assertEqual((rows["ig-ead00003"]["move"], rows["ig-ead00003"]["move_by"]), ("before-after", "eye"))
        self.assertEqual((rows["ig-n0000001"]["move"], rows["ig-n0000001"]["move_by"]), ("impossible-object", "eye"))
        self.assertEqual(json.loads((out / "avatars.json").read_text())[AVATAR]["moves"], {"wrong-scale": 1, "unrated": 1, "before-after": 1})
        newer = json.loads((self.tmp / "general" / "breakdown.json").read_text())     # an eye read in the pull itself wins
        newer["ig-n0000001"]["move"] = "as-shot"
        (self.tmp / "general" / "breakdown.json").write_text(json.dumps(newer))
        quiet(C.index, self.tmp / "general", out)
        self.assertEqual(next(r["move"] for r in self.rows(out) if r["id"] == "ig-n0000001"), "as-shot")

    def test_k_switch_off_is_the_old_merge(self):
        out = self.general_index()
        quiet(C.import_pull, FIX, out, FIX / "avatar.json", pulled="2026-11-11")
        quiet(C.moves, out, {"ig-ead00003": "before-after"})
        os.environ["COVER_SWIPES_OFF"] = "merge-keeps"
        quiet(C.import_pull, FIX, out, FIX / "avatar.json", pulled="2026-11-11")
        self.assertEqual(next(r["move"] for r in self.rows(out) if r["id"] == "ig-ead00003"), "unrated")
        one = general_row(7, 9000)
        one.update(id="ig-av000007", url="https://www.instagram.com/p/Av00000007/", source="av-ig-accounts", avatar=AVATAR)
        quiet(C.index, pull_folder(self.tmp / "second", [one], {"avatar": AVATAR}), out)
        self.assertEqual([r["id"] for r in self.rows(out) if r["avatar"] == AVATAR], ["ig-av000007"])

    def test_l_second_pull_keeps_the_imported_covers(self):
        out = self.general_index()
        quiet(C.import_pull, FIX, out, FIX / "avatar.json", pulled="2026-11-11")
        one = general_row(7, 9000)
        one.update(id="ig-av000007", url="https://www.instagram.com/p/Av00000007/", source="av-ig-accounts", avatar=AVATAR)
        again = general_row(8, 77000)                                                  # an imported post, newer numbers
        again.update(id="ig-ead00001", url="https://www.instagram.com/p/FxBread00001/", source="av-ig-accounts", avatar=AVATAR)
        quiet(C.index, pull_folder(self.tmp / "second", [one, again], {"avatar": AVATAR}), out)
        mine = {r["id"]: r for r in self.rows(out) if r["avatar"] == AVATAR}
        self.assertEqual(sorted(mine), ["ig-av000007", "ig-ead00001", "ig-ead00002", "ig-ead00003"])
        self.assertEqual(mine["ig-ead00001"]["likes"], 77000)
        self.assertEqual(len(self.rows(out)), 7)
        self.assertEqual(json.loads((out / "avatars.json").read_text())[AVATAR]["covers"], 4)

    def test_m_discovery_drop_keeps_what_an_avatar_sees(self):
        out = self.general_index()
        shared = general_row(1, 50000)
        shared.update(source="av-ig-tags", avatar=AVATAR, via="#sourdough")
        own = general_row(5, 8000)
        own.update(id="ig-av000005", url="https://www.instagram.com/p/Av00000005/", source="av-ig-tags", avatar=AVATAR)
        quiet(C.index, pull_folder(self.tmp / "avatar", [shared, own], {"avatar": AVATAR}), out)
        quiet(C.moves, out, {"ig-n0000001": "wrong-scale"})
        later = [general_row(2, 90000), general_row(3, 20000, views=700000)]          # the next discovery pull drops n1
        quiet(C.index, pull_folder(self.tmp / "general-2", later), out)
        rows = {r["id"]: r for r in self.rows(out)}
        self.assertEqual(sorted(rows), ["ig-av000005", "ig-n0000001", "ig-n0000002", "ig-n0000003"])
        kept = rows["ig-n0000001"]
        self.assertEqual((kept["avatar"], kept.get("avatar_also"), kept["move"]), (AVATAR, None, "wrong-scale"))
        self.assertEqual(sorted(s["id"] for s in C.find_covers(out, avatar=AVATAR)["covers"]), ["ig-av000005", "ig-n0000001"])
        self.assertEqual(sorted(s["id"] for s in C.find_covers(out)["covers"]), ["ig-n0000002", "ig-n0000003"])
        os.environ["COVER_SWIPES_OFF"] = "merge-keeps"
        quiet(C.index, self.tmp / "general", out)
        quiet(C.index, pull_folder(self.tmp / "general-3", [general_row(2, 90000)]), out)
        self.assertNotIn("ig-n0000001", {r["id"] for r in self.rows(out)})


class Names(Base):
    def test_n_find_takes_any_spelling(self):
        out = self.general_index()
        quiet(C.import_pull, FIX, out, FIX / "avatar.json", pulled="2026-11-11")
        for spelt in ("Example Home Baker", "example_home_baker", " example-home-baker ", "EXAMPLE--HOME  BAKER"):
            res = C.find_covers(out, avatar=spelt)
            self.assertEqual((res["scope"], res["avatar"], len(res["covers"])), ("avatar", AVATAR, 3), spelt)
        for bad in ("bad/name!", "  ", self.tmp / "no-such-avatar.json"):
            with self.assertRaises(ValueError):
                C.find_covers(out, avatar=bad)
        with self.assertRaises(ValueError):
            C.read_avatar(self.tmp / "no-such-avatar.json")
        with self.assertRaises(SystemExit) as stop:                                    # the command line stops, with words
            quiet(C.main, ["find", str(out), "--avatar", "bad/name!"])
        self.assertIn("avatar name", str(stop.exception))
        os.environ["COVER_SWIPES_OFF"] = "avatar-slug"                                 # the switch puts the strict name back
        with self.assertRaises(SystemExit):
            C.find_covers(out, avatar="Example Home Baker")


class MoveRules(Base):
    # (breakdown, the move with the tightened rules on, the move with them off)
    LOOSE = [
        ({"absurd": 1, "expression": "shock", "frame": "face+product", "shot": "close",
          "shows": "man holding a burrito and a bowl, mouth open, in a restaurant"}, ("one-odd-thing", []), ("face-at-limit", [])),
        ({"absurd": 1, "expression": "smile", "frame": "face+product", "shot": "close",
          "shows": 'woman holding a fig to camera, large white serif "The humble fig\'s disturbing secret"'},
         ("one-odd-thing", []), ("thing-to-lens", [])),
        ({"absurd": 0, "shot": "close", "shows": "driver smiling, holding a small object to camera"}, ("as-shot", []), ("thing-to-lens", [])),
        ({"absurd": 0, "expression": "shock", "frame": "face", "shot": "medium", "text_style": "outline", "text_words": 4,
          "shows": "woman holding her stomach in a kitchen, small white outlined caption"}, ("unrated", []), ("face-at-limit", [])),
        ({"absurd": 0, "expression": "shock", "frame": "face", "shot": "medium", "shows": "couple in a living room, woman mouth open"},
         ("as-shot", []), ("face-at-limit", [])),
        ({"absurd": 1, "expression": "shock", "frame": "face", "shot": "close", "shows": "streamer mouth open beside game art"},
         ("face-at-limit", []), ("face-at-limit", [])),
        ({"absurd": 0, "shot": "extreme-close", "shows": "hand holding a jar to camera"}, ("thing-to-lens", []), ("thing-to-lens", [])),
        ({"absurd": 2, "frame": "product", "shows": "a handbag made of bread on a table"},
         ("impossible-object", ["absurd-subject"]), ("absurd-subject", [])),
        ({"absurd": 3, "frame": "product", "shows": "a sneaker melting on a stove"},
         ("impossible-object", ["impossible-scene"]), ("impossible-scene", [])),
        ({"absurd": 3, "frame": "graphic", "shows": "cartoon building with a face in one window"},
         ("impossible-scene", []), ("impossible-scene", [])),
    ]

    def test_o_tightened_rules(self):
        for eye, on, off in self.LOOSE:
            got = C.derive_move({**EYE, **eye})
            self.assertEqual(got[:2], on, eye["shows"])
            self.assertTrue(got[2] or got[0] == "unrated")
        os.environ["COVER_SWIPES_OFF"] = "move-rules"
        for eye, on, off in self.LOOSE:
            self.assertEqual(C.derive_move({**EYE, **eye})[:2], off, eye["shows"])
        for want, also, eye in Moves.CASES:                                             # the shared cases mean the same
            self.assertEqual(C.derive_move({**EYE, **eye})[:2], (want, also), eye["shows"])


class PictureNotWords(Base):
    # (breakdown, the move with `move-picture` on, the move with it off)
    WORDS = [
        ({"absurd": 1, "expression": "smile", "frame": "face+product", "shot": "close",
          "shows": 'woman holding a fig to camera, large white serif "The humble fig\'s disturbing secret"'},
         ("one-odd-thing", []), ("line-shown-literally", [])),
        ({"absurd": 1, "expression": "intense", "frame": "face+product", "shot": "close",
          "shows": 'creator pointing at an advent calendar, white outlined caps "$276 ADVENT CALENDAR?!"'},
         ("price-as-hook", []), ("price-as-hook", ["line-shown-literally"])),
        ({"absurd": 2, "frame": "face+product", "shot": "close",
          "shows": 'woman beside a giant fig, serif "The fig that ate my kitchen"'},
         ("wrong-scale", ["absurd-subject", "line-shown-literally"]), ("wrong-scale", ["absurd-subject", "line-shown-literally"])),
        ({"absurd": 0, "expression": "neutral", "frame": "face", "shot": "medium", "text_style": "outline", "text_words": 2,
          "shows": 'woman in a kitchen, red caps "Screaming deals"'}, ("unrated", []), ("face-at-limit", [])),
        ({"absurd": 0, "expression": "neutral", "frame": "face", "shot": "medium", "text_style": "outline", "text_words": 5,
          "shows": 'man at a desk, white caps "Push it to the camera"'}, ("unrated", []), ("thing-to-lens", [])),
        ({"absurd": 0, "expression": "shock", "frame": "face", "shot": "close", "text_style": "outline", "text_words": 2,
          "shows": 'TV character shouting into a mic, small yellow "Happy Diwali!"'}, ("face-at-limit", []), ("face-at-limit", [])),
        ({"absurd": 0, "shot": "medium", "shows": "driver pushing a small object at the camera, white caption"},
         ("thing-to-lens", []), ("thing-to-lens", [])),
        # a comma or semicolon inside the cover's quoted words never splits them into a part read as picture
        ({"absurd": 0, "text_style": "outline", "text_words": 5,
          "shows": 'woman in a kitchen, red caps "Hurry, screaming deals, today only"'}, ("unrated", []), ("face-at-limit", [])),
        ({"absurd": 0, "text_style": "outline", "text_words": 6,
          "shows": 'man at a desk, white caps "Stop, push it to the camera, now"'}, ("unrated", []), ("thing-to-lens", [])),
        ({"absurd": 0, "text_style": "outline", "text_words": 4,
          "shows": 'woman in a kitchen, yellow "Wow; screaming deals; now"'}, ("unrated", []), ("face-at-limit", [])),
        ({"absurd": 0, "text_style": "outline", "text_words": 3,
          "shows": 'woman in a kitchen, red caps \u201cHurry, screaming deals\u201d'}, ("unrated", []), ("face-at-limit", [])),
        ({"absurd": 0, "text_style": "outline", "text_words": 2,
          "shows": 'man screaming at a desk, white caps "Big, news"'}, ("face-at-limit", []), ("face-at-limit", [])),
    ]

    def test_p_the_picture_not_the_words(self):
        for eye, on, off in self.WORDS:
            got = C.derive_move({**EYE, **eye})
            self.assertEqual(got[:2], on, eye["shows"])
            self.assertTrue(got[2] or got[0] == "unrated")
        os.environ["COVER_SWIPES_OFF"] = "move-picture"
        for eye, on, off in self.WORDS:
            self.assertEqual(C.derive_move({**EYE, **eye})[:2], off, eye["shows"])


def source_row(n, likes, source, platform="instagram", **eye):
    """A discovery row from a named source (general_row is Instagram Explore, US)."""
    r = general_row(n, likes, **eye)
    pre = {"instagram": "ig", "tiktok": "tt"}[platform]
    r.update(platform=platform, source=source, id=f"{pre}-n000000{n}", url=f"https://example.invalid/{source}/{n}")
    return r


class ByPull(Base):
    def three_sources(self):
        rows = [source_row(1, 50000, "ig-explore"), source_row(2, 90000, "ig-explore-ca"),
                source_row(3, 20000, "tt-explore", "tiktok")]
        out = self.general_index(rows)
        quiet(C.moves, out, {"tt-n0000003": "wrong-scale", "ig-n0000002": "as-shot"})
        return out

    def test_q_narrow_discovery_pull_keeps_the_other_sources(self):
        out = self.three_sources()
        quiet(C.index, pull_folder(self.tmp / "ig-only", [source_row(1, 60000, "ig-explore")]), out)
        rows = {r["id"]: r for r in self.rows(out)}
        self.assertEqual(sorted(rows), ["ig-n0000001", "ig-n0000002", "tt-n0000003"])
        self.assertEqual((rows["tt-n0000003"]["move"], rows["tt-n0000003"]["move_by"]), ("wrong-scale", "eye"))
        self.assertEqual((rows["ig-n0000002"]["move"], rows["ig-n0000002"]["move_by"]), ("as-shot", "eye"))
        self.assertEqual(rows["ig-n0000001"]["likes"], 60000)
        self.assertEqual(sorted(json.loads((out / "patterns.json").read_text())), ["instagram", "tiktok"])

    def raw(self, d, *names):
        (d / "raw").mkdir(parents=True, exist_ok=True)
        for name in names:
            (d / "raw" / f"{name}.json").write_text("[]")
        return d

    def test_q_a_source_replaces_its_rows_only_when_it_brought_one(self):
        out = self.three_sources()
        d = self.raw(pull_folder(self.tmp / "ig-two", [source_row(4, 70000, "ig-explore")]), "ig-explore", "ig-explore-ca")
        quiet(C.index, d, out)                                                         # -ca ran and kept no row
        rows = {r["id"]: r for r in self.rows(out)}
        self.assertEqual(sorted(rows), ["ig-n0000002", "ig-n0000004", "tt-n0000003"])
        self.assertEqual((rows["ig-n0000002"]["move"], rows["ig-n0000002"]["move_by"]), ("as-shot", "eye"))

    def test_q_a_pull_that_came_back_empty_wipes_nothing(self):
        out = self.three_sources()
        before = sorted(r["id"] for r in self.rows(out))
        quiet(C.index, self.raw(pull_folder(self.tmp / "tt-empty", []), "tt-explore"), out)
        rows = {r["id"]: r for r in self.rows(out)}
        self.assertEqual(sorted(rows), before)
        self.assertEqual((rows["tt-n0000003"]["move"], rows["tt-n0000003"]["move_by"]), ("wrong-scale", "eye"))

    def test_q_a_row_whose_cover_never_came_wipes_nothing(self):
        out = self.three_sources()
        d = self.raw(pull_folder(self.tmp / "tt-no-cover", [source_row(6, 40000, "tt-explore", "tiktok")]), "tt-explore")
        (d / "covers" / "tt-n0000006.jpg").unlink()                                   # the cover fetch failed
        quiet(C.index, d, out)
        rows = {r["id"]: r for r in self.rows(out)}
        self.assertEqual(sorted(rows), ["ig-n0000001", "ig-n0000002", "tt-n0000003"])
        self.assertEqual(rows["tt-n0000003"]["move_by"], "eye")

    def test_q_an_avatar_pull_with_a_stale_discovery_raw_file_keeps_discovery_rows(self):
        out = self.three_sources()
        mine = dict(source_row(7, 30000, "av-ig-tags"), avatar=AVATAR)
        quiet(C.index, self.raw(pull_folder(self.tmp / "avatar-pull", [mine]), "av-ig-tags", "ig-explore"), out)
        self.assertEqual(sorted(r["id"] for r in self.rows(out)),
                         ["ig-n0000001", "ig-n0000002", "ig-n0000007", "tt-n0000003"])

    def test_q_a_row_with_no_source_goes_with_any_discovery_pull(self):
        out = self.three_sources()
        rows = self.rows(out)
        bare = dict(rows[0], id="ig-n0000009", url="https://example.invalid/none/9")
        bare.pop("source")                                                             # which pull brought it is unknown
        (out / "covers.json").write_text(json.dumps(rows + [bare]))
        quiet(C.index, pull_folder(self.tmp / "tt-only", [source_row(5, 30000, "tt-explore", "tiktok")]), out)
        self.assertEqual(sorted(r["id"] for r in self.rows(out)), ["ig-n0000001", "ig-n0000002", "tt-n0000005"])

    def test_q_switch_off_is_the_group_merge(self):
        out = self.three_sources()
        os.environ["COVER_SWIPES_OFF"] = "merge-by-pull"
        quiet(C.index, pull_folder(self.tmp / "ig-only", [source_row(1, 60000, "ig-explore")]), out)
        self.assertEqual([r["id"] for r in self.rows(out)], ["ig-n0000001"])


class Switches(Base):
    def test_i_avatar_off(self):
        out = self.general_index()
        quiet(C.import_pull, FIX, out, FIX / "avatar.json")
        os.environ["COVER_SWIPES_OFF"] = "avatar"
        self.assertFalse(C.switch("avatar"))
        self.assertTrue(C.switch("move"))
        for call in (lambda: C.import_pull(FIX, out, FIX / "avatar.json"), lambda: C.pull(self.tmp / "p", avatar=FIX / "avatar.json")):
            with self.assertRaises(SystemExit) as stop:
                quiet(call)
            self.assertIn("switched off", str(stop.exception))
        res = C.find_covers(out, avatar=AVATAR)
        self.assertEqual((res["scope"], len(res["covers"])), ("general", 3))
        self.assertIn("avatar switch is off", res["note"])
        self.assertEqual(len(self.rows(out)), 6)                                        # nothing is deleted by switching off
        quiet(C.index, self.tmp / "general", out)
        self.assertEqual(len(self.rows(out)), 6)

    def test_i_move_off(self):
        out = self.general_index([general_row(1, 10, shows="man balancing a tower of glasses", absurd=2)])
        os.environ["COVER_SWIPES_OFF"] = "move"
        with self.assertRaises(SystemExit):
            quiet(C.moves, out)
        res = C.find_covers(out, move="as-shot")
        self.assertEqual(len(res["covers"]), 1)
        self.assertIn("move switch is off", res["note"])
        quiet(C.index, self.tmp / "general", out)
        fresh = self.tmp / "fresh"
        quiet(C.index, self.tmp / "general", fresh)
        self.assertNotIn("move", self.rows(fresh)[0])

    def test_i_all_off_and_the_file(self):
        os.environ["COVER_SWIPES_OFF"] = "all"
        self.assertFalse(C.switch("avatar") or C.switch("move"))
        os.environ.pop("COVER_SWIPES_OFF")
        f = self.tmp / "switches.json"
        f.write_text(json.dumps({"avatar": {"on": False}, "move": {"on": True}}))
        with mock.patch.object(C, "SWITCHES", f):
            self.assertEqual((C.switch("avatar"), C.switch("move")), (False, True))
        on = json.loads((HERE / "switches.json").read_text())
        self.assertEqual((on["avatar"]["on"], on["move"]["on"]), (True, True))
        for name in ("merge-keeps", "avatar-slug", "avatar-scope", "move-rules", "merge-by-pull", "move-picture"):
            self.assertTrue(on[name]["on"], name)
            self.assertTrue(on[name]["off_means"], name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
