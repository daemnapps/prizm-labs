#!/usr/bin/env python3
"""LD-88 (team station folders): Shared Assets/team/<person>/<station>/ seeded
from each team/people/<person>/identity.json `stations` list — proven offline.

    python3 components/gdrive-creator/tests/test_seed_team.py

A fake engine (find_file / folder / FOLDER_MIME / service) over an in-memory
tree, and a temp repo holding team/people/<p>/identity.json fixtures and
components/<name>/ folders. No Google package, no key, no network. Stdlib
only, 3.9.

  a  every missing folder is made exactly once; rows "made"; paths team/<p>[/<s>]
  b  a second run makes nothing: every row "already there"
  c  a folder already there is untouched (no create for it)
  d  an unknown station is "refused" with its why, nothing made for it, the
     others still made; the CLI exits 2
  e  dry_run calls no folder() at all and answers "would make"
  f  "stations" absent = the person folder only
  g  the source matches none of test_reach.py's no-delete/move/rename patterns
  h  the REAL repo's identity files (read only): every station is an existing
     components/<name>/ folder, and designer has exactly email-production and
     image-production
"""
import contextlib
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMPONENT = HERE.parent
REPO = COMPONENT.parent.parent
sys.path.append(str(COMPONENT))                    # APPEND — never insert at 0

from gdrive_creator import reach as R, seed_team as S   # noqa: E402

FOLDER = "application/vnd.google-apps.folder"
ROOT = "d-sa"


class FakeEngine(object):
    """The engine surface seed_team may use, over an in-memory tree. Any
    other name (delete, update, move, …) is recorded and FAILS."""

    FOLDER_MIME = FOLDER

    def __init__(self):
        self.nodes = {ROOT: {"name": "Shared Assets", "parent": None}}
        self.calls, self.n = [], 0

    def add(self, parent, name):
        self.n += 1
        nid = "f%d" % self.n
        self.nodes[nid] = {"name": name, "parent": parent}
        return nid

    def at(self, *names):
        cur = ROOT
        for name in names:
            hits = [k for k, v in self.nodes.items() if v["parent"] == cur and v["name"] == name]
            if len(hits) != 1:
                return None if not hits else hits
            cur = hits[0]
        return cur

    def creates(self):
        return [c for c in self.calls if c[0] == "folder"]

    def service(self):
        self.calls.append(("service",))
        return "svc"

    def _child(self, name, parent):
        for k, v in self.nodes.items():
            if v["parent"] == parent and v["name"] == name:
                return k
        return None

    def find_file(self, svc, name, parent, mime=None):
        self.calls.append(("find_file", name, parent, mime))
        hit = self._child(name, parent)
        return {"id": hit} if hit else None

    def folder(self, name, parent_id, svc=None):
        """Like the engine's: made only when it is not there."""
        self.calls.append(("folder", name, parent_id))
        return self._child(name, parent_id) or self.add(parent_id, name)

    def __getattr__(self, name):
        raise AssertionError("seed_team used engine.%s" % name)


class Base(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.repo = Path(t.name)
        for c in ("email-production", "image-production", "video-edit"):
            (self.repo / "components" / c).mkdir(parents=True)
        self.E = FakeEngine()

    def person(self, name, stations=None):
        d = self.repo / "team" / "people" / name
        d.mkdir(parents=True)
        data = {"person": name, "emails": [{"address": name + "@example.com"}]}
        if stations is not None:
            data["stations"] = stations
        (d / "identity.json").write_text(json.dumps(data, indent=2))

    def seed(self, **kw):
        kw.setdefault("drive_root", ROOT)
        return S.seed_team(repo=self.repo, find_engine=lambda: self.E, retired_ok=True, **kw)

    def states(self, rows):
        return [(r["path"], r["state"]) for r in rows]


class TestSeed(Base):
    def test_a_every_missing_folder_is_made_exactly_once(self):
        self.person("designer", ["email-production", "image-production"])
        self.person("editor", ["video-edit"])
        rows = self.seed()
        self.assertEqual(self.states(rows), [
            ("team/designer", "made"), ("team/designer/email-production", "made"),
            ("team/designer/image-production", "made"),
            ("team/editor", "made"), ("team/editor/video-edit", "made")])
        self.assertEqual(rows[4], {"person": "editor", "station": "video-edit",
                                   "path": "team/editor/video-edit", "state": "made", "why": None})
        self.assertIsNone(rows[0]["station"])
        made = sorted((c[1], self.E.nodes[c[2]]["name"]) for c in self.E.creates())
        self.assertEqual(made, sorted([
            ("team", "Shared Assets"), ("editor", "team"), ("video-edit", "editor"),
            ("designer", "team"), ("email-production", "designer"), ("image-production", "designer")]))
        for names in (("team",), ("team", "designer", "email-production"),
                      ("team", "editor", "video-edit")):
            self.assertIsInstance(self.E.at(*names), str, names)        # exactly one, no duplicate
        self.assertEqual({c[3] for c in self.E.calls if c[0] == "find_file"}, {FOLDER})

    def test_b_a_second_run_makes_nothing(self):
        self.person("designer", ["email-production", "image-production"])
        self.seed()
        before = (len(self.E.nodes), len(self.E.creates()))
        rows = self.seed()
        self.assertEqual({r["state"] for r in rows}, {"already there"})
        self.assertEqual(len(rows), 3)
        self.assertEqual((len(self.E.nodes), len(self.E.creates())), before)

    def test_c_a_folder_already_there_is_untouched(self):
        self.person("designer", ["email-production", "image-production"])
        team = self.E.add(ROOT, "team")
        designer = self.E.add(team, "designer")
        ep = self.E.add(designer, "email-production")
        self.E.add(ep, "keep.png")
        rows = self.seed()
        self.assertEqual(self.states(rows), [
            ("team/designer", "already there"), ("team/designer/email-production", "already there"),
            ("team/designer/image-production", "made")])
        self.assertEqual([c[1:] for c in self.E.creates()], [("image-production", designer)])
        self.assertEqual(self.E.at("team", "designer", "email-production"), ep)
        self.assertIsNotNone(self.E.at("team", "designer", "email-production", "keep.png"))

    def test_d_an_unknown_station_is_refused_by_name_and_the_rest_is_made(self):
        self.person("designer", ["email-production", "no-such-station", "image-production"])
        rows = self.seed()
        self.assertEqual(self.states(rows), [
            ("team/designer", "made"), ("team/designer/email-production", "made"),
            ("team/designer/no-such-station", "refused"), ("team/designer/image-production", "made")])
        self.assertEqual(rows[2]["why"],
                         "not a component: components/no-such-station/ does not exist")
        self.assertNotIn("no-such-station", [c[1] for c in self.E.calls if len(c) > 1])
        self.assertIsNone(self.E.at("team", "designer", "no-such-station"))

    def test_d_a_path_shaped_station_is_refused(self):
        self.person("designer", ["../team", "email-production/x"])
        rows = self.seed()
        self.assertEqual([r["state"] for r in rows], ["made", "refused", "refused"])
        self.assertTrue(all(r["why"].startswith("not a component name:") for r in rows[1:]))

    def test_d_the_cli_exits_2_on_a_refusal_and_prints_every_row(self):
        self.person("designer", ["email-production", "no-such-station"])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = S.main([], repo=self.repo, find_engine=lambda: self.E, drive_root=ROOT, retired_ok=True)
        self.assertEqual(code, 2)
        self.assertEqual(out.getvalue().splitlines(), [
            "made  team/designer",
            "made  team/designer/email-production",
            "refused  team/designer/no-such-station  — not a component: "
            "components/no-such-station/ does not exist",
            "made 2 · already there 0 · would make 0 · refused 1"])

    def test_the_cli_exits_0_when_nothing_is_refused(self):
        self.person("designer", ["email-production"])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = S.main(["--dry-run"], repo=self.repo, find_engine=lambda: self.E,
                          drive_root=ROOT, retired_ok=True)
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue().splitlines()[-1],
                         "made 0 · already there 0 · would make 2 · refused 0")

    def test_e_dry_run_creates_nothing(self):
        self.person("designer", ["email-production", "image-production"])
        self.person("engineer", [])
        team = self.E.add(ROOT, "team")
        self.E.add(team, "engineer")
        before = dict(self.E.nodes)
        rows = self.seed(dry_run=True)
        self.assertEqual(self.states(rows), [
            ("team/designer", "would make"),
            ("team/designer/email-production", "would make"),
            ("team/designer/image-production", "would make"),
            ("team/engineer", "already there")])
        self.assertEqual(self.E.creates(), [])
        self.assertEqual(self.E.nodes, before)

    def test_f_no_stations_key_is_the_person_folder_only(self):
        self.person("victoria")
        rows = self.seed()
        self.assertEqual(self.states(rows), [("team/victoria", "made")])

    def test_svc_is_made_from_the_engine_only_when_needed(self):
        self.seed()                                                 # nobody: no Drive call
        self.assertEqual(self.E.calls, [])
        self.person("designer", [])
        self.seed()
        self.assertEqual(self.E.calls[0], ("service",))

    def test_no_shared_assets_drive_is_a_named_nodrive(self):
        self.person("designer", [])

        class NoDrives(object):
            def drives(self):
                class D(object):
                    def list(self, **kw):
                        class Q(object):
                            def execute(self):
                                return {"drives": []}
                        return Q()
                return D()
        with self.assertRaises(R.NoDrive) as c:
            S.seed_team(repo=self.repo, svc=NoDrives(), find_engine=lambda: self.E, retired_ok=True)
        self.assertIn("Shared Assets", str(c.exception))
        self.assertEqual(self.E.creates(), [])

    def test_g_no_delete_move_or_rename_in_the_source(self):
        # copied from test_reach.py test_no_delete_move_or_rename_in_the_source
        bad = re.compile(r"\.delete\(|emptyTrash|removeParents|addParents|"
                         r"trashed\s*[\"']?\s*[:=]\s*True|os\.remove|\.unlink\(|"
                         r"rmtree|shutil\.move|\.rename\(|os\.replace|\.rmdir\(")
        src = (COMPONENT / "gdrive_creator" / "seed_team.py").read_text()
        self.assertIsNone(bad.search(src))
        self.assertNotIn(".update(", src)
        self.assertNotIn("write_text", src)


class TestRetired(unittest.TestCase):
    """Retired 2026-10-27 (the owner: no folder named after a person): the call and the command make nothing."""
    def test_r_the_call_refuses_and_makes_nothing(self):
        E = FakeEngine()
        with self.assertRaises(S.Retired) as c:
            S.seed_team(repo=REPO, find_engine=lambda: E, drive_root=ROOT)
        self.assertIn("handoffs/<role>", str(c.exception))
        self.assertEqual(E.creates(), [])

    def test_r_the_command_refuses_and_makes_nothing(self):
        E = FakeEngine()
        with contextlib.redirect_stderr(io.StringIO()) as err:
            code = S.main([], repo=REPO, find_engine=lambda: E, drive_root=ROOT)
        self.assertEqual(code, 3)
        self.assertIn("retired", err.getvalue())
        self.assertEqual(E.creates(), [])


class TestRealTeam(unittest.TestCase):
    def test_h_every_real_station_is_a_component_and_eve_has_her_two(self):
        E = FakeEngine()
        rows = S.seed_team(repo=REPO, find_engine=lambda: E, drive_root=ROOT, dry_run=True, retired_ok=True)
        refused = [(r["path"], r["why"]) for r in rows if r["state"] == "refused"]
        self.assertEqual(refused, [])
        self.assertEqual(E.creates(), [])
        designer = [r["station"] for r in rows if r["person"] == "designer" and r["station"]]
        self.assertEqual(designer, ["email-production", "image-production"])
        for r in rows:
            self.assertTrue(r["path"].startswith("team/"), r["path"])
            if r["station"]:
                self.assertTrue((REPO / "components" / r["station"]).is_dir(), r["station"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
