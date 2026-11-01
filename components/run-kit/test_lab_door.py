#!/usr/bin/env python3
"""The shared lab door (run_kit/lab_door.py), checked without a model, a
network or a real CLI: each of the five component manifests turns a sample
lab-run request into that CLI's exact command line, refusals exit 2 before
anything runs, run folders land in $OUT/<label>/, and the meta-upload door can
never name approve.py or upload.py (LD-1 (shared lab door)); the ad-variations
and intake doors map the same way (LD-7 (four more doors)). The child is
stubbed through `run`; the manifests are the real ones in this checkout.

    /usr/bin/python3 components/run-kit/test_lab_door.py
"""
import contextlib
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
sys.path.insert(0, str(HERE))
from run_kit import lab_door as D    # noqa: E402

REAL = D.find_repo(__file__)         # this checkout, found by walking up
MANIFESTS = {
    "video-production": REAL / "tools/video-production/machine/lab_door.json",
    "image-teardown": REAL / "tools/image-teardown/lab_door.json",
    "image-production": REAL / "tools/image-production/lab_door.json",
    "image-edit": REAL / "tools/image-edit/lab_door.json",
    "meta-upload": REAL / "components/meta-upload/lab_door.json",
}
LD7_MANIFESTS = {                    # LD-7 (four more doors): manifests at the component root
    "ad-variations": REAL / "components/ad-variations/lab_door.json",
    "intake": REAL / "components/intake/lab_door.json",
}
BRAND = "testbrand"
FORBIDDEN = ("approve.py", "upload.py")


def quiet(fn, *a, **kw):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        got = fn(*a, **kw)
    return got, out.getvalue()


class Door(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.repo = self.tmp / "repo"
        (self.repo / "brands").mkdir(parents=True)
        for m in MANIFESTS.values():                 # the CLIs, as empty stand-ins
            script = self.repo / json.loads(m.read_text())["script"]
            script.parent.mkdir(parents=True, exist_ok=True)
            script.write_text("")
        self.brief = "runs/video-teardown/testbrand/t1/deliverable/5-brief.md"
        self.picture = "runs/image-teardown/testbrand/drop1/deliverable/ad-01.png"
        for rel in (self.brief, self.picture):
            (self.repo / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.repo / rel).write_text("x")
        self.out = self.tmp / "lab-out" / "mini-1"
        self.env = {"BRAND": BRAND, "OUT": str(self.out), "PATH": "/usr/bin", "KEEP": "me"}
        self.calls = []

    def tearDown(self):
        shutil.rmtree(str(self.tmp), ignore_errors=True)

    def stub(self, rc=0, make=None):
        """The CLI, stubbed: records the call; `make(cmd)` writes what the CLI would."""
        def run(cmd, env=None):
            self.calls.append((cmd, env))
            if make:
                make(cmd)
            return rc
        return run

    def door(self, which, argv, env=None, run=None, manifest=None):
        return quiet(D.run, manifest or MANIFESTS[which], argv,
                     self.env if env is None else env,
                     run=run or self.stub(), repo=self.repo)

    def script(self, which):
        return str(self.repo / json.loads(MANIFESTS[which].read_text())["script"])

    def refused(self, which, argv, says, env=None, manifest=None):
        rc, text = self.door(which, argv, env=env, manifest=manifest)
        self.assertEqual(rc, 2, text)
        self.assertIn(says, text)
        self.assertEqual(self.calls, [], "nothing may run on a refusal")
        return text


class FiveManifests(Door):
    def test_video_production_maps_to_run_py_start_and_lands_in_out(self):
        def make(cmd):
            root = Path(cmd[cmd.index("--runs-root") + 1])
            run_dir = root / "video-production" / BRAND / "vp-01"
            run_dir.mkdir(parents=True)
            (run_dir / "run.json").write_text("{}")
        rc, text = self.door("video-production",
                             ["--dry_run", "yes", "--format", "song-ad", "--label", "vp-01",
                              "--source", self.brief], run=self.stub(make=make))
        self.assertEqual(rc, 0, text)
        cmd, env = self.calls[0]
        root = cmd[-1]
        self.assertEqual(cmd, [sys.executable, self.script("video-production"), "start",
                               str(self.repo / self.brief), "--brand", BRAND,
                               "--format", "song-ad", "--label", "vp-01", "--dry-run",
                               "--runs-root", root])
        self.assertEqual(Path(root).parent, self.out)
        self.assertTrue(Path(root).name.startswith(".runs-"))
        self.assertTrue((self.out / "vp-01" / "run.json").is_file())
        self.assertFalse(Path(root).exists(), "the empty scaffold is removed")
        self.assertEqual(env["AI_WORKSPACE"], str(self.repo))
        self.assertEqual(env["KEEP"], "me")

    def test_image_teardown_maps_to_chain_py_start(self):
        rc, text = self.door("image-teardown",
                             ["--avatar", "a1", "--count", "2", "--dry_run", "true",
                              "--form", "single", "--picks", "1,3", "--product", "p1",
                              "--route", "ai", "--swipe", "sw1"])
        self.assertEqual(rc, 0, text)
        self.assertEqual(self.calls[0][0],
                         [sys.executable, self.script("image-teardown"), "start",
                          "--brand", BRAND, "--product", "p1", "--avatar", "a1",
                          "--swipe", "sw1", "--route", "ai", "--form", "single",
                          "--count", "2", "--picks", "1,3", "--dry-run"])
        self.assertIn("in this checkout", text)

    def test_image_teardown_optional_flags_left_out_when_not_asked(self):
        rc, text = self.door("image-teardown",
                             ["--avatar", "a1", "--dry_run", "no", "--product", "p1",
                              "--swipe", "sw1"])
        self.assertEqual(rc, 0, text)
        self.assertEqual(self.calls[0][0],
                         [sys.executable, self.script("image-teardown"), "start",
                          "--brand", BRAND, "--product", "p1", "--avatar", "a1",
                          "--swipe", "sw1"])

    def test_image_production_maps_to_make_py_with_out(self):
        rc, text = self.door("image-production",
                             ["--direction", "a man at a bathroom sink, morning light",
                              "--dry_run", "1", "--label", "ip-01", "--purpose", "ad"])
        self.assertEqual(rc, 0, text)
        self.assertEqual(self.calls[0][0],
                         [sys.executable, self.script("image-production"),
                          "--brand", BRAND, "--purpose", "ad",
                          "--direction", "a man at a bathroom sink, morning light",
                          "--label", "ip-01",
                          "--dry-run", "--out", str(self.out / "ip-01")])

    def test_image_edit_maps_to_edit_py_with_picture_and_out(self):
        rc, text = self.door("image-edit",
                             ["--dry_run", "yes", "--fix", "logo", "--label", "ie-01",
                              "--picture", self.picture])
        self.assertEqual(rc, 0, text)
        self.assertEqual(self.calls[0][0],
                         [sys.executable, self.script("image-edit"),
                          str(self.repo / self.picture), "--brand", BRAND,
                          "--fix", "logo", "--dry-run", "--out", str(self.out / "ie-01")])

    def test_image_edit_change_in_words(self):
        rc, text = self.door("image-edit",
                             ["--change", "the tube is in her left hand", "--label", "ie-02",
                              "--picture", self.picture])
        self.assertEqual(rc, 0, text)
        self.assertEqual(self.calls[0][0],
                         [sys.executable, self.script("image-edit"),
                          str(self.repo / self.picture), "--brand", BRAND,
                          "--change", "the tube is in her left hand",
                          "--out", str(self.out / "ie-02")])

    def test_meta_upload_maps_to_build_py_sheet_only(self):
        rc, text = self.door("meta-upload",
                             ["--label", "mu-01", "--lane", "lane1", "--run", "copy-run-7"])
        self.assertEqual(rc, 0, text)
        self.assertEqual(self.calls[0][0],
                         [sys.executable, self.script("meta-upload"),
                          "--brand", BRAND, "--lane", "lane1", "--run", "copy-run-7",
                          "--out", str(self.out / "mu-01")])

    def test_meta_upload_passes_funnel_and_stays_sheet_only(self):
        rc, text = self.door("meta-upload",
                             ["--label", "mu-03", "--lane", "x", "--run", "r",
                              "--funnel", "tof"])
        self.assertEqual(rc, 0, text)
        self.assertEqual(self.calls[0][0],
                         [sys.executable, self.script("meta-upload"),
                          "--brand", BRAND, "--lane", "x", "--run", "r", "--funnel", "tof",
                          "--out", str(self.out / "mu-03")])
        m = D.load(MANIFESTS["meta-upload"])
        self.assertEqual(Path(m["script"]).name, "build.py")
        for word in ("approve", "upload", "live", "active", "handoff"):
            self.assertIn(word, m["refuse"])

    def test_hyphenated_names_read_as_underscored(self):
        rc, text = self.door("image-production",
                             ["--direction", "d", "--dry-run", "yes", "--label", "ip-03",
                              "--purpose", "ad"])
        self.assertEqual(rc, 0, text)
        self.assertIn("--dry-run", self.calls[0][0])

    def test_child_exit_code_is_returned(self):
        rc, _ = self.door("meta-upload", ["--label", "mu-02", "--lane", "l", "--run", "r"],
                          run=self.stub(rc=5))
        self.assertEqual(rc, 5)

    def test_runs_root_with_no_run_folder_says_so_and_cleans_up(self):
        rc, text = self.door("video-production",
                             ["--format", "f", "--label", "vp-02", "--source", self.brief],
                             run=self.stub(rc=1))
        self.assertEqual(rc, 1)
        self.assertIn("made no run folder", text)
        self.assertFalse((self.out / "vp-02").exists())
        self.assertEqual([p.name for p in self.out.iterdir()], [], "no scaffold left behind")


class Refusals(Door):
    def test_missing_brand_or_out(self):
        self.refused("meta-upload", ["--label", "x", "--lane", "l", "--run", "r"], "$BRAND",
                     env={"OUT": str(self.out)})
        self.refused("meta-upload", ["--label", "x", "--lane", "l", "--run", "r"], "$OUT",
                     env={"BRAND": BRAND})

    def test_unknown_argument(self):
        self.refused("image-production", ["--label", "x", "--purpose", "ad", "--model", "m"],
                     "unknown argument(s) --model")

    def test_brand_as_an_argument_is_unknown_and_says_where_it_comes_from(self):
        self.refused("image-production", ["--brand", "other", "--label", "x"],
                     "$BRAND comes from lab-run")

    def test_refused_argument_is_named(self):
        self.refused("image-production", ["--gates", "warn", "--label", "x"],
                     "--gates is refused by this door")
        self.refused("video-production", ["--yes", "1", "--label", "x"],
                     "--yes is refused by this door")

    def test_not_in_pairs(self):
        self.refused("meta-upload", ["--lane"], "pairs")
        self.refused("meta-upload", ["lane", "l"], "is not a --name")

    def test_given_twice(self):
        self.refused("meta-upload", ["--lane", "a", "--lane", "b"], "given twice")

    def test_value_that_would_read_as_a_flag(self):
        self.refused("meta-upload", ["--label", "x", "--lane", "--strict", "--run", "r"],
                     "would read as a flag")

    def test_positional_outside_missing_or_dotdot(self):
        base = ["--format", "f", "--label", "vp-x"]
        self.refused("video-production", base + ["--source", "../outside.md"], "'..' part")
        self.refused("video-production", base + ["--source", "/etc/hosts"], "outside this checkout")
        self.refused("video-production", base + ["--source", "runs/none.md"], "is not there")
        self.refused("video-production", base, "--source is required")

    def test_label_missing_malformed_or_taken(self):
        self.refused("image-edit", ["--fix", "logo", "--picture", self.picture], "--label")
        self.refused("image-edit", ["--fix", "logo", "--label", "../up", "--picture", self.picture],
                     "plain name")
        (self.out / "taken").mkdir(parents=True)
        self.refused("image-edit", ["--fix", "logo", "--label", "taken", "--picture", self.picture],
                     "already exists")

    def test_label_not_taken_where_the_run_names_itself(self):
        self.refused("image-teardown", ["--label", "x", "--product", "p"],
                     "unknown argument(s) --label")

    def test_bool_flag_must_say_yes_or_no(self):
        self.refused("image-production", ["--dry_run", "maybe", "--label", "x"], "say yes or no")

    def test_bad_brand(self):
        self.refused("meta-upload", ["--label", "x"], "plain name",
                     env={"BRAND": "../other", "OUT": str(self.out)})

    def write_manifest(self, which, **change):
        m = json.loads(MANIFESTS[which].read_text())
        m.update(change)
        p = self.tmp / "manifest.json"
        p.write_text(json.dumps(m))
        return p

    def test_deprecated_or_unknown_key_manifest(self):
        self.refused("meta-upload", ["--label", "x"], "deprecated",
                     manifest=self.write_manifest("meta-upload", status="deprecated"))
        self.refused("meta-upload", ["--label", "x"], "unknown key(s) extra",
                     manifest=self.write_manifest("meta-upload", extra=1))

    def test_script_not_in_checkout(self):
        self.refused("meta-upload", ["--label", "x", "--lane", "l", "--run", "r"],
                     "is not in this checkout",
                     manifest=self.write_manifest("meta-upload", script="components/meta-upload/gone.py"))

    def test_nothing_written_on_a_refusal(self):
        self.refused("meta-upload", ["--label", "x", "--approve", "yes"], "refused")
        self.assertFalse(self.out.exists(), "$OUT is not even made on a refusal")


class MetaUploadSheetOnly(Door):
    def test_refuse_list_blocks_approve_upload_live_active(self):
        m = D.load(MANIFESTS["meta-upload"])
        for word in ("approve", "upload", "live", "active"):
            self.assertIn(word, m["refuse"])
        self.assertEqual(Path(m["script"]).name, "build.py")

    def test_never_a_command_naming_approve_or_upload(self):
        base = {"--label": "mu-x", "--lane": "lane1", "--run": "r1"}
        attempts = [
            {"--approve": "yes"}, {"--upload": "yes"}, {"--go_live": "yes"},
            {"--active": "1"}, {"--upload-go": "yes"}, {"--handoff": "h"},
            {"--run": "approve.py"}, {"--run": "components/meta-upload/upload.py"},
            {"--lane": "UPLOAD.PY"}, {"--lane": "--handoff"}, {"--run": "x; upload.py --go"},
            {"--script": "components/meta-upload/approve.py"},
        ]
        for i, extra in enumerate(attempts):
            req = dict(base, **extra)
            req["--label"] = f"mu-{i}"
            self.calls = []
            argv = [t for kv in req.items() for t in kv]
            rc, text = self.door("meta-upload", argv)
            self.assertEqual(rc, 2, f"{extra} should be refused: {text}")
            self.assertEqual(self.calls, [], extra)
        rc, _ = self.door("meta-upload", ["--label", "ok", "--lane", "l", "--run", "r"])
        self.assertEqual(rc, 0)
        for cmd, _env in self.calls:
            self.assertTrue(cmd[1].endswith("components/meta-upload/build.py"))
            for token in cmd:
                for bad in FORBIDDEN:
                    self.assertNotIn(bad, token)

    def test_a_manifest_naming_upload_py_is_refused_at_load(self):
        for script in ("components/meta-upload/upload.py", "components/meta-upload/approve.py"):
            m = json.loads(MANIFESTS["meta-upload"].read_text())
            m["script"] = script
            p = self.tmp / "m.json"
            p.write_text(json.dumps(m))
            (self.repo / script).write_text("")
            self.refused("meta-upload", ["--label", "x", "--lane", "l", "--run", "r"],
                         "named by its own refuse list", manifest=p)


class RealCheckout(unittest.TestCase):
    def test_every_manifest_loads_and_matches_its_cli(self):
        for name, path in MANIFESTS.items():
            m = D.load(path)
            self.assertEqual(m["status"], "draft", name)
            script = REAL / m["script"]
            self.assertTrue(script.is_file(), f"{name}: {script}")
            self.assertEqual(script.parent, path.parent, f"{name}: the manifest sits beside its CLI")
            src = script.read_text()
            flags = list(m["flags"].values()) + list(m["bool_flags"].values()) + [
                m["brand_flag"], m["out"]["flag"], m["out"]["runs_root_flag"]]
            for flag in filter(None, flags):
                self.assertIn(f'"{flag}"', src, f"{name}: {flag} is not in {m['script']}")
            if m["subcommand"]:
                self.assertIn(f'add_parser("{m["subcommand"]}"', src, name)

    def test_every_stub_is_the_two_line_door(self):
        for name, path in MANIFESTS.items():
            stub = path.with_name("lab_entry.py")
            lines = stub.read_text().splitlines()
            self.assertEqual(lines[0], "#!/usr/bin/python3", name)
            self.assertEqual(len(lines), 4, name)
            self.assertIn('with_name("lab_door.json")', lines[-1], name)

    def test_a_real_stub_refuses_without_brand_and_runs_nothing(self):
        env = {k: v for k, v in os.environ.items() if k not in ("BRAND", "OUT")}
        for name, path in MANIFESTS.items():
            r = subprocess.run([sys.executable, str(path.with_name("lab_entry.py")), "--label", "x"],
                               env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 2, f"{name}: {r.stdout}{r.stderr}")
            self.assertIn("$BRAND", r.stdout, name)


class Routes(Door):
    """LD-8 (teardown door routes): one manifest, several routes, picked with
    --command; --route stays image-teardown start's own flag."""

    def routed(self, **change):
        m = json.loads(MANIFESTS["image-teardown"].read_text())
        m.update(change)
        p = self.tmp / "routed.json"
        p.write_text(json.dumps(m))
        return p

    def test_variations_route_maps_to_chain_py_variations(self):
        rc, text = self.door("image-teardown",
                             ["--command", "variations", "--product", "p", "--dry_run", "yes"])
        self.assertEqual(rc, 0, text)
        self.assertEqual(self.calls[0][0],
                         [sys.executable, self.script("image-teardown"), "variations",
                          "--brand", BRAND, "--product", "p", "--dry-run"])

    def test_variations_route_takes_every_flag_it_declares(self):
        rc, text = self.door("image-teardown",
                             ["--command", "variations", "--workers", "3", "--no_name", "yes",
                              "--briefs", "b1,b2", "--drop", "d1", "--batch", "k1"])
        self.assertEqual(rc, 0, text)
        self.assertEqual(self.calls[0][0],
                         [sys.executable, self.script("image-teardown"), "variations",
                          "--brand", BRAND, "--briefs", "b1,b2", "--batch", "k1",
                          "--drop", "d1", "--workers", "3", "--no-name"])

    def test_draft_route_maps_to_chain_py_draft(self):
        rc, text = self.door("image-teardown", ["--command", "draft", "--no_ship", "yes"])
        self.assertEqual(rc, 0, text)
        self.assertEqual(self.calls[0][0],
                         [sys.executable, self.script("image-teardown"), "draft",
                          "--brand", BRAND, "--no-ship"])

    def test_explicit_start_is_the_default(self):
        rc, text = self.door("image-teardown",
                             ["--command", "start", "--avatar", "a1", "--product", "p1",
                              "--swipe", "sw1"])
        self.assertEqual(rc, 0, text)
        self.assertEqual(self.calls[0][0],
                         [sys.executable, self.script("image-teardown"), "start",
                          "--brand", BRAND, "--product", "p1", "--avatar", "a1",
                          "--swipe", "sw1"])

    def test_route_flag_on_the_default_route_passes_through_as_starts_own(self):
        rc, text = self.door("image-teardown",
                             ["--product", "p1", "--route", "ai", "--swipe", "sw1"])
        self.assertEqual(rc, 0, text)
        self.assertEqual(self.calls[0][0],
                         [sys.executable, self.script("image-teardown"), "start",
                          "--brand", BRAND, "--product", "p1", "--swipe", "sw1",
                          "--route", "ai"])
        self.calls = []
        rc, text = self.door("image-teardown",
                             ["--command", "start", "--route", "creator", "--product", "p1"])
        self.assertEqual(rc, 0, text)
        self.assertIn("creator", self.calls[0][0])
        self.assertEqual(self.calls[0][0][2], "start")

    def test_unknown_route_is_refused_naming_it(self):
        text = self.refused("image-teardown", ["--command", "nope", "--product", "p"],
                            "--command 'nope' is not a route of this door")
        for name in ("draft", "start", "variations"):
            self.assertIn(name, text)
        self.refused("image-teardown", ["--command", "ai"], "'ai' is not a route")

    def test_a_routes_own_unknown_argument_is_refused(self):
        self.refused("image-teardown", ["--command", "draft", "--dry_run", "yes"],
                     "unknown argument(s) --dry_run")
        self.refused("image-teardown", ["--command", "variations", "--swipe", "sw1"],
                     "unknown argument(s) --swipe")
        self.refused("image-teardown", ["--command", "draft", "--route", "ai"],
                     "unknown argument(s) --route")

    def test_a_routes_refuse_list_holds(self):
        for route in ("start", "variations", "draft"):
            self.refused("image-teardown", ["--command", route, "--gates", "warn"],
                         "--gates is refused by this door")

    def test_command_given_twice_is_refused(self):
        self.refused("image-teardown", ["--command", "draft", "--command", "start"], "given twice")

    def test_every_single_route_manifest_still_loads_and_takes_no_command(self):
        for name, path in MANIFESTS.items():
            if name == "image-teardown":
                continue
            m = D.load(path)
            self.assertNotIn("routes", m, name)
            self.assertIn("script", m, name)
        self.refused("meta-upload", ["--command", "x", "--label", "mu", "--lane", "l", "--run", "r"],
                     "unknown argument(s) --command")

    def test_teardown_loads_as_three_routes_defaulting_to_start(self):
        m = D.load(MANIFESTS["image-teardown"])
        self.assertEqual(sorted(m["routes"]), ["draft", "start", "variations"])
        self.assertEqual(m["default_route"], "start")
        self.assertEqual(m["subcommand"], "start")
        for name, r in m["routes"].items():
            self.assertEqual(r["subcommand"], name)
            self.assertEqual(r["status"], "draft")
            self.assertEqual(r["brand_flag"], "--brand")
            self.assertIn("gates", r["refuse"])
            self.assertEqual(r["out"], {"flag": None, "runs_root_flag": None, "run_dir": None})
        self.assertNotIn("dry_run", m["routes"]["draft"]["bool_flags"],
                         "draft has no --dry-run: every draft run spends")

    def test_a_manifest_naming_command_is_refused_at_load(self):
        single = json.loads(MANIFESTS["meta-upload"].read_text())
        single["flags"]["command"] = "--command"
        p = self.tmp / "single.json"
        p.write_text(json.dumps(single))
        self.refused("meta-upload", ["--label", "x"], "command is the door's own --command",
                     manifest=p)
        single = json.loads(MANIFESTS["video-production"].read_text())
        single["positionals"] = ["command"]
        p.write_text(json.dumps(single))
        self.refused("video-production", ["--label", "x"], "command is the door's own --command",
                     manifest=p)
        m = json.loads(MANIFESTS["image-teardown"].read_text())
        m["routes"]["draft"]["bool_flags"]["command"] = "--command"
        self.refused("image-teardown", ["--command", "start"], "route draft: command is the door's own",
                     manifest=self.routed(routes=m["routes"]))

    def test_a_bad_routed_manifest_is_refused_at_load(self):
        m = json.loads(MANIFESTS["image-teardown"].read_text())
        self.refused("image-teardown", [], "default_route must name one of its routes",
                     manifest=self.routed(default_route="gone"))
        self.refused("image-teardown", [], "unknown key(s) flags",
                     manifest=self.routed(flags={"x": "--x"}))
        self.refused("image-teardown", [], "routes must map",
                     manifest=self.routed(routes={}))
        routes = json.loads(json.dumps(m["routes"]))
        routes["draft"]["status"] = "approved"
        self.refused("image-teardown", [], "route draft: unknown key(s) status",
                     manifest=self.routed(routes=routes))
        routes = json.loads(json.dumps(m["routes"]))
        routes["draft"]["script"] = "components/meta-upload/build.py"
        self.refused("image-teardown", [], "is not the door's script",
                     manifest=self.routed(routes=routes))
        routes = json.loads(json.dumps(m["routes"]))
        routes["variations"]["bool_flags"]["gates"] = "--gates"
        self.refused("image-teardown", [], "route variations: gates is declared and refused",
                     manifest=self.routed(routes=routes))
        self.refused("image-teardown", [], "deprecated",
                     manifest=self.routed(status="deprecated"))


class RoutesRealCheckout(unittest.TestCase):
    def test_every_route_of_every_manifest_matches_its_cli(self):
        for name, path in MANIFESTS.items():
            loaded = D.load(path)
            for route, m in loaded.get("routes", {name: loaded}).items():
                src = (REAL / m["script"]).read_text()
                flags = list(m["flags"].values()) + list(m["bool_flags"].values()) + [
                    m["brand_flag"], m["out"]["flag"], m["out"]["runs_root_flag"]]
                for flag in filter(None, flags):
                    self.assertIn(f'"{flag}"', src, f"{name}/{route}: {flag}")
                if m["subcommand"]:
                    self.assertIn(f'add_parser("{m["subcommand"]}"', src, f"{name}/{route}")

    def test_no_manifest_flag_or_positional_is_named_command(self):
        for name, path in MANIFESTS.items():
            loaded = D.load(path)
            for route, m in loaded.get("routes", {name: loaded}).items():
                names = list(m["positionals"]) + list(m["flags"]) + list(m["bool_flags"])
                self.assertNotIn("command", names, f"{name}/{route}")


class Ld7Doors(Door):
    """ad-variations `plan` and intake (LD-7 (four more doors)): both CLIs file
    their own runs, so out is all null and the run stays in this checkout."""
    def setUp(self):
        super().setUp()
        for m in LD7_MANIFESTS.values():
            script = self.repo / json.loads(m.read_text())["script"]
            script.parent.mkdir(parents=True, exist_ok=True)
            script.write_text("")
        self.teardown_run = "runs/video-teardown/testbrand/t1"      # a folder, made with the brief

    def ld7(self, which, argv, env=None, run=None):
        return self.door(which, argv, env=env, run=run, manifest=LD7_MANIFESTS[which])

    def ld7_script(self, which):
        return str(self.repo / json.loads(LD7_MANIFESTS[which].read_text())["script"])

    def ld7_refused(self, which, argv, says, env=None):
        return self.refused(which, argv, says, env=env, manifest=LD7_MANIFESTS[which])

    def test_ad_variations_maps_to_run_py_plan(self):
        rc, text = self.ld7("ad-variations",
                            ["--dry_run", "yes", "--k", "2", "--label", "av-01", "--n", "3",
                             "--source", self.teardown_run])
        self.assertEqual(rc, 0, text)
        cmd, env = self.calls[0]
        self.assertEqual(cmd, [sys.executable, self.ld7_script("ad-variations"), "plan",
                               str(self.repo / self.teardown_run), "--brand", BRAND,
                               "--n", "3", "--k", "2", "--label", "av-01", "--dry-run"])
        self.assertTrue(cmd[1].endswith("components/ad-variations/machine/run.py"))
        self.assertIn("in this checkout", text)
        self.assertEqual(env["AI_WORKSPACE"], str(self.repo))

    def test_ad_variations_optional_flags_left_out_when_not_asked(self):
        rc, text = self.ld7("ad-variations", ["--dry_run", "no", "--source", self.teardown_run])
        self.assertEqual(rc, 0, text)
        self.assertEqual(self.calls[0][0],
                         [sys.executable, self.ld7_script("ad-variations"), "plan",
                          str(self.repo / self.teardown_run), "--brand", BRAND])

    def test_ad_variations_refuses_model_rerun_from_and_plan(self):
        base = ["--source", self.teardown_run]
        self.ld7_refused("ad-variations", base + ["--model", "m"], "--model is refused by this door")
        self.ld7_refused("ad-variations", base + ["--rerun_from", "s2"], "--rerun_from is refused")
        self.ld7_refused("ad-variations", base + ["--rerun-from", "s2"], "--rerun_from is refused")
        self.ld7_refused("ad-variations", base + ["--plan", "p.json"], "--plan is refused")

    def test_ad_variations_source_required_and_inside_the_checkout(self):
        self.ld7_refused("ad-variations", ["--n", "3"], "--source is required")
        self.ld7_refused("ad-variations", ["--source", "/etc"], "outside this checkout")
        self.ld7_refused("ad-variations", ["--source", "../x"], "'..' part")
        self.ld7_refused("ad-variations", ["--source", "runs/video-teardown/testbrand/none"],
                         "is not there")

    def test_ad_variations_brand_comes_from_lab_run(self):
        self.ld7_refused("ad-variations", ["--brand", "other", "--source", self.teardown_run],
                         "$BRAND comes from lab-run")

    def test_intake_maps_to_tools_run_py(self):
        rc, text = self.ld7("intake",
                            ["--dry_run", "yes", "--gates", "hold", "--kind", "video",
                             "--label", "in-01", "--limit", "5", "--source", "paid"])
        self.assertEqual(rc, 0, text)
        cmd, _env = self.calls[0]
        self.assertEqual(cmd, [sys.executable, self.ld7_script("intake"), "--brand", BRAND,
                               "--source", "paid", "--kind", "video", "--label", "in-01",
                               "--limit", "5", "--gates", "hold", "--dry-run"])
        self.assertTrue(cmd[1].endswith("components/intake/tools/run.py"))
        self.assertIn("in this checkout", text)

    def test_intake_brand_only_with_dry_run(self):
        rc, text = self.ld7("intake", ["--dry-run", "true"])
        self.assertEqual(rc, 0, text)
        self.assertEqual(self.calls[0][0],
                         [sys.executable, self.ld7_script("intake"), "--brand", BRAND, "--dry-run"])

    def test_intake_refusals(self):
        self.ld7_refused("intake", ["--brand", "other"], "$BRAND comes from lab-run")
        self.ld7_refused("intake", ["--model", "m"], "unknown argument(s) --model")
        self.ld7_refused("intake", ["--dry_run", "maybe"], "say yes or no")
        self.ld7_refused("intake", ["--label", "x"], "$BRAND", env={"OUT": str(self.out)})

    def test_child_exit_code_is_returned(self):
        rc, _ = self.ld7("intake", ["--label", "in-02"], run=self.stub(rc=3))
        self.assertEqual(rc, 3)


class Ld7RealCheckout(unittest.TestCase):
    def test_both_manifests_load_and_match_their_cli(self):
        for name, path in LD7_MANIFESTS.items():
            m = D.load(path)
            self.assertEqual(m["status"], "draft", name)
            self.assertEqual(path.parent, REAL / "components" / name, f"{name}: at the component root")
            script = REAL / m["script"]
            self.assertTrue(script.is_file(), f"{name}: {script}")
            self.assertIn(path.parent, script.parents, f"{name}: the CLI is the component's own")
            self.assertEqual(m["out"], {"flag": None, "runs_root_flag": None, "run_dir": None}, name)
            src = script.read_text()
            flags = list(m["flags"].values()) + list(m["bool_flags"].values()) + [m["brand_flag"]]
            for flag in filter(None, flags):
                self.assertIn(f'"{flag}"', src, f"{name}: {flag} is not in {m['script']}")
            if m["subcommand"]:
                self.assertIn(f'add_parser("{m["subcommand"]}"', src, name)

    def test_ad_variations_refuses_what_its_plan_parser_takes_but_the_door_does_not(self):
        m = D.load(LD7_MANIFESTS["ad-variations"])
        self.assertEqual(sorted(m["refuse"]), ["model", "plan", "rerun_from"])
        self.assertEqual(m["positionals"], ["source"])

    def test_both_stubs_are_the_two_line_door(self):
        door = MANIFESTS["meta-upload"].with_name("lab_entry.py").read_text()
        for name, path in LD7_MANIFESTS.items():
            stub = path.with_name("lab_entry.py")
            self.assertEqual(stub.read_text(), door, name)

    def test_a_real_stub_refuses_without_brand_and_runs_nothing(self):
        env = {k: v for k, v in os.environ.items() if k not in ("BRAND", "OUT")}
        for name, path in LD7_MANIFESTS.items():
            r = subprocess.run([sys.executable, str(path.with_name("lab_entry.py")), "--label", "x"],
                               env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 2, f"{name}: {r.stdout}{r.stderr}")
            self.assertIn("$BRAND", r.stdout, name)


if __name__ == "__main__":
    unittest.main()
