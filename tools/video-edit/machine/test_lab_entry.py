#!/usr/bin/env python3
"""The mini's door (lab_entry.py), checked without a model, a network or a
real kit: lab-run's --name value pairs become a `run.py start <kit>` call, or
on the hand-off route a `run.py handoff <folder>` call (LD-2 (portable video
kits)), refusals exit 2 before anything runs, and the run folder lands in
$OUT/<label>/ (VE-1 (video-edit mini door)). run.py is stubbed through `run`.

    /usr/bin/python3 tools/video-edit/machine/test_lab_entry.py
"""
import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lab_entry as E                # noqa: E402

BRAND = "testbrand"
LABEL = "ve-dry-01"
KIT = "runs/video-edit/kits/k1"
HANDOFF = "handoffs/video-editor_b0001_20261018"


def quiet(fn, *a, **kw):
    """Run fn, return (result_or_SystemExit, printed text)."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        try:
            got = fn(*a, **kw)
        except SystemExit as e:
            got = e
    return got, out.getvalue()


def runs_root_of(cmd):
    return Path(cmd[cmd.index("--runs-root") + 1])


class Door(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.keep_repo = E.REPO
        E.REPO = self.tmp / "repo"
        self.kit = E.REPO / KIT
        self.kit.mkdir(parents=True)
        (self.kit / "edit-kit.json").write_text("{}")
        self.out = self.tmp / "lab-out" / "mini-1"
        self.out.mkdir(parents=True)
        self.env = {"BRAND": BRAND, "OUT": str(self.out), "PATH": "/usr/bin"}
        self.calls = []

    def tearDown(self):
        E.REPO = self.keep_repo
        shutil.rmtree(str(self.tmp), ignore_errors=True)

    def stub(self, rc=0, write=True):
        """run.py start, stubbed: records the call and writes a fake run.json
        under the runs root it was handed."""
        def run(cmd, env=None):
            self.calls.append((cmd, env))
            if write:
                folder = runs_root_of(cmd) / BRAND / LABEL if "--runs-root" in cmd else Path(cmd[cmd.index("--out") + 1])
                folder.mkdir(parents=True)
                (folder / "run.json").write_text(json.dumps({"machine": "video-edit", "label": LABEL}))
            return rc
        return run

    def door(self, *extra, kit=KIT, env=None, run=None):
        return quiet(E.main, ["--kit", kit, "--label", LABEL, *extra],
                     self.env if env is None else env, run or self.stub())

    def refused(self, got, text, word):
        self.assertEqual(got, 2, text)
        self.assertIn(word, text)
        self.assertEqual(self.calls, [])
        self.assertEqual(list(self.out.iterdir()), [])

    # ---------------------------------------------------------------- the call
    def test_maps_kit_label_to_the_start_argv_exactly(self):
        got, text = self.door()
        self.assertEqual(got, 0, text)
        (cmd, env), = self.calls
        root = runs_root_of(cmd)
        # intent changed by verify 2026-10-21 row 16: never the retired model pause-cutter — run.py's take-whole cut
        self.assertEqual(cmd, [sys.executable, str(E.HERE / "run.py"), "start", str(self.kit.resolve()),
                               "--brand", BRAND, "--label", LABEL, "--runs-root", str(root), "--cut", "auto"])
        self.assertEqual(root.parent, self.out)
        self.assertTrue(root.name.startswith(".runs"))
        self.assertIn(" ".join(cmd), text)                  # printed before it runs

    def test_dry_run_words_add_dry_run(self):
        for word in ("yes", "true", "1", "YES"):
            self.calls.clear()
            shutil.rmtree(str(self.out / LABEL), ignore_errors=True)
            got, text = self.door("--dry_run", word)
            self.assertEqual(got, 0, text)
            self.assertEqual(self.calls[0][0][-1], "--dry-run")
        for word in ("no", "false", "0"):
            self.calls.clear()
            shutil.rmtree(str(self.out / LABEL), ignore_errors=True)
            got, text = self.door("--dry_run", word)
            self.assertEqual(got, 0, text)
            self.assertNotIn("--dry-run", self.calls[0][0])

    def test_two_routes_only_and_kit_is_the_default(self):
        # intent changed by LD-2 (portable video kits): exactly two routes, kit and handoff
        self.door("--dry_run", "yes")
        cmd = self.calls[0][0]
        self.assertEqual(cmd[2], "start")                     # no --route → the kit route
        for word in ("handoff", "pack", "line.py", "--approve"):
            self.assertNotIn(word, " ".join(cmd))
        for route in ("pack", "line", "from-run", "start"):
            self.calls.clear()
            got, _ = quiet(E.main, ["--route", route, "--kit", KIT, "--label", LABEL], self.env, self.stub())
            self.assertIsInstance(got, SystemExit)
            self.assertEqual(got.code, 2)
            self.assertEqual(self.calls, [])

    def test_a_kit_from_a_production_run_goes_through_line_py(self):
        # verify 2026-10-21 row 16: one edit path — a kit joined from a production run is cut by line.py on that run
        prod = E.REPO / "runs" / "video-production" / BRAND / LABEL
        prod.mkdir(parents=True)
        (prod / "run.json").write_text("{}")
        (self.kit / "edit-kit.json").write_text(json.dumps({"from_run": str(prod)}))
        got, text = self.door()
        self.assertEqual(got, 0, text)
        (cmd, env), = self.calls
        root = Path(cmd[cmd.index("--out") + 1]).parent.parent
        self.assertEqual(cmd, [sys.executable, str(E.HERE / "line.py"), str(prod), "--out", str(root / BRAND / LABEL)])
        self.assertEqual(root.parent, self.out)
        self.assertTrue((self.out / LABEL).is_dir())
        self.calls.clear()
        shutil.rmtree(str(self.out / LABEL), ignore_errors=True)
        got, text = self.door("--dry_run", "yes")
        self.assertEqual(got, 0, text)
        self.assertEqual(self.calls, [])                 # line.py has no dry run: the call is said, nothing runs
        self.assertIn("line.py", text)

    # ---------------------------------------------------------------- the hand-off route
    def handoff_folder(self):
        f = E.REPO / HANDOFF
        f.mkdir(parents=True, exist_ok=True)
        (f / "manifest.json").write_text(json.dumps({"role": "video-editor", "brand": BRAND}))
        return f

    def handoff_stub(self, rc=0, brand="handoffbrand", label="b0001_20261018"):
        """run.py handoff, stubbed: the hand-off names its OWN brand and label."""
        def run(cmd, env=None):
            self.calls.append((cmd, env))
            folder = runs_root_of(cmd) / brand / label
            folder.mkdir(parents=True)
            (folder / "run.json").write_text(json.dumps({"machine": "video-edit", "label": label}))
            return rc
        return run

    def test_handoff_route_maps_to_the_handoff_argv_exactly(self):
        f = self.handoff_folder()
        for word, tail in (("no", []), ("yes", ["--dry-run"])):
            self.calls.clear()
            shutil.rmtree(str(self.out / LABEL), ignore_errors=True)
            got, text = quiet(E.main, ["--route", "handoff", "--folder", HANDOFF, "--label", LABEL, "--dry_run", word],
                              self.env, self.handoff_stub())
            self.assertEqual(got, 0, text)
            (cmd, env), = self.calls
            root = runs_root_of(cmd)
            self.assertEqual(cmd, [sys.executable, str(E.HERE / "run.py"), "handoff", str(f.resolve()),
                                   "--runs-root", str(root), "--cut", "auto"] + tail)
            self.assertEqual(root.parent, self.out)
            self.assertEqual(env["AI_WORKSPACE"], str(E.REPO))
            for word_ in ("start", "--approve", "--brand"):
                self.assertNotIn(word_, cmd)

    def test_handoff_run_folder_lands_in_out_label(self):
        self.handoff_folder()
        got, text = quiet(E.main, ["--route", "handoff", "--folder", HANDOFF, "--label", LABEL], self.env, self.handoff_stub(rc=0))
        self.assertEqual(got, 0, text)
        self.assertEqual(json.loads((self.out / LABEL / "run.json").read_text())["label"], "b0001_20261018")
        self.assertEqual(sorted(p.name for p in self.out.iterdir()), [LABEL])   # the scaffold is gone

    def test_handoff_refuses_the_stop_and_cut_flags(self):
        self.handoff_folder()
        for extra in (["--approve", "timeline"], ["--note", "ok"], ["--controls", "c.json"], ["--versions"], ["--cut", "auto"]):
            got, text = quiet(E.main, ["--route", "handoff", "--folder", HANDOFF, "--label", LABEL, *extra], self.env, self.handoff_stub())
            self.assertIsInstance(got, SystemExit, text)
            self.assertEqual(got.code, 2)
        self.assertEqual(self.calls, [])
        self.assertEqual(list(self.out.iterdir()), [])

    def test_handoff_needs_its_folder_and_only_its_folder(self):
        self.handoff_folder()
        for args in (["--route", "handoff", "--label", LABEL],                                   # no --folder
                     ["--route", "handoff", "--folder", HANDOFF, "--kit", KIT, "--label", LABEL],  # a kit on the hand-off route
                     ["--folder", HANDOFF, "--kit", KIT, "--label", LABEL]):                       # a folder on the kit route
            got, _ = quiet(E.main, args, self.env, self.handoff_stub())
            self.assertIsInstance(got, SystemExit)
            self.assertEqual(got.code, 2)
        self.assertEqual(self.calls, [])

    def test_a_handoff_folder_outside_the_checkout_or_missing_is_refused(self):
        outside = self.tmp / "elsewhere"
        outside.mkdir()
        for folder, word in ((str(outside), "outside this checkout"), ("../elsewhere", "'..'"), ("handoffs/missing", "not a folder")):
            got, text = quiet(E.main, ["--route", "handoff", "--folder", folder, "--label", LABEL], self.env, self.handoff_stub())
            self.refused(got, text, word)
            self.assertIn("--folder", text)

    def test_child_env_sets_ai_workspace_and_leaves_the_rest(self):
        self.door()
        env = self.calls[0][1]
        self.assertEqual(env["AI_WORKSPACE"], str(E.REPO))
        self.assertEqual({k: v for k, v in env.items() if k != "AI_WORKSPACE"}, self.env)
        self.assertNotIn("AI_WORKSPACE", self.env)          # the caller's env is untouched

    def test_returns_the_childs_exit_code(self):
        got, text = self.door(run=self.stub(rc=7))
        self.assertEqual(got, 7, text)

    # ---------------------------------------------------------------- where it lands
    def test_the_run_folder_lands_in_out_label_and_the_scaffold_goes(self):
        got, text = self.door()
        self.assertEqual(got, 0, text)
        made = json.loads((self.out / LABEL / "run.json").read_text())
        self.assertEqual(made["label"], LABEL)
        self.assertEqual(sorted(p.name for p in self.out.iterdir()), [LABEL])
        self.assertFalse((E.REPO / "runs" / "video-edit" / BRAND).exists())   # nothing into the checkout

    def test_no_run_folder_made_still_returns_rc_and_cleans_the_scaffold(self):
        got, text = self.door("--dry_run", "yes", run=self.stub(rc=3, write=False))
        self.assertEqual(got, 3, text)
        self.assertEqual(list(self.out.iterdir()), [])

    # ---------------------------------------------------------------- refusals
    def test_missing_brand_or_out_is_refused_by_name(self):
        for env, word in (({"OUT": str(self.out)}, "$BRAND"), ({"BRAND": BRAND}, "$OUT")):
            got, text = self.door(env=env)
            self.refused(got, text, word)

    def test_a_kit_outside_the_checkout_is_refused(self):
        outside = self.tmp / "elsewhere"
        outside.mkdir()
        got, text = self.door(kit=str(outside))
        self.refused(got, text, "outside this checkout")

    def test_a_dotdot_kit_is_refused(self):
        (self.tmp / "elsewhere").mkdir()
        got, text = self.door(kit="../elsewhere")
        self.refused(got, text, "'..'")
        got, text = self.door(kit="runs/../" + KIT)         # even one that would land inside
        self.refused(got, text, "'..'")

    def test_a_non_folder_kit_is_refused(self):
        got, text = self.door(kit=KIT + "/edit-kit.json")
        self.refused(got, text, "not a folder")
        got, text = self.door(kit="runs/video-edit/kits/missing")
        self.refused(got, text, "not a folder")

    def test_an_existing_out_label_is_refused(self):
        (self.out / LABEL).mkdir()
        got, text = self.door()
        self.assertEqual(got, 2, text)
        self.assertIn("already exists", text)
        self.assertEqual(self.calls, [])

    def test_an_unknown_arg_is_an_argparse_exit_2(self):
        for extra in (["--approve", "timeline"], ["--brand", BRAND], ["extra"]):
            got, text = self.door(*extra)
            self.assertIsInstance(got, SystemExit)
            self.assertEqual(got.code, 2)
        self.assertEqual(self.calls, [])

    def test_kit_and_label_are_required(self):
        got, _ = quiet(E.main, ["--label", LABEL], self.env, self.stub())
        self.assertEqual(got.code, 2)
        got, _ = quiet(E.main, ["--kit", KIT], self.env, self.stub())
        self.assertEqual(got.code, 2)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
