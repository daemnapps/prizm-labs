"""Portable kits (LD-2 (portable video kits); fixes video-edit-dry-1, kit srcs that were one
Mac's /Users/… paths): a kit names its media relative to the kit, the repo or Shared Assets,
and gather() finds each form again — or leaves a ref it cannot find for the gate to name.
The workspace and the Drive mount are patched to temp folders; nothing renders.

    python3 tools/video-edit/tests/test_portable_kit.py
"""
import contextlib
import errno
import io
import json
import shutil
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from stat import S_ISREG

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
import kit_paths as KP  # noqa: E402
import kit_from_run as K  # noqa: E402
import run as R  # noqa: E402


def touch(p: Path) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x")
    return p


def srcs(kit: dict) -> list:
    out = [r["src"] for r in [kit.get("voice"), kit.get("music"), *(kit.get("sfx") or []), *(kit.get("room_tone") or [])]
           if isinstance(r, dict) and r.get("src")]
    for c in kit.get("clips") or []:
        out.append(c["src"])
        if (c.get("voice") or {}).get("src"):
            out.append(c["voice"]["src"])
    return out


class Patched(unittest.TestCase):
    """A workspace at <tmp>/ws and a Drive mount at <tmp>/drive/Shared Assets."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.ws = self.tmp / "ws"
        (self.ws / "components").mkdir(parents=True)
        (self.ws / "brands").mkdir()
        self.shared = self.tmp / "drive" / "Shared Assets"
        self.shared.mkdir(parents=True)
        self.kit = self.ws / "runs" / "video-edit" / "b" / "l" / "kit"
        self.kit.mkdir(parents=True)
        keep = (KP.repo, KP.mount)
        KP.repo = lambda: self.ws
        KP.mount = lambda: self.shared

        def restore():
            KP.repo, KP.mount = keep
            shutil.rmtree(str(self.tmp), ignore_errors=True)
        self.addCleanup(restore)
        self.asked = []                                                       # labels the Drive API was asked for
        keep_readable = KP.READABLE
        KP.READABLE = self.no_drive                                           # offline: no test reaches the Drive (LD-15 (kit reads by API))
        self.addCleanup(setattr, KP, "READABLE", keep_readable)

    def no_drive(self, label):
        self.asked.append(label)
        raise KP.R.NoDrive(f"{label}: not on the Drive (test)")

    def quiet(self, fn, *a):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            got = fn(*a)
        return got, out.getvalue()


class Portable(Patched):
    def test_kit_relative_when_under_the_kit(self):
        f = touch(self.kit / "media" / "S1.mp4")
        self.assertEqual(KP.portable(f, self.kit), "media/S1.mp4")

    def test_repo_relative_when_under_the_workspace(self):
        f = touch(self.ws / "runs" / "video-production" / "b" / "l" / "media" / "S1.mp4")
        self.assertEqual(KP.portable(f, self.kit), "runs/video-production/b/l/media/S1.mp4")
        self.assertEqual(KP.portable(f, None), "runs/video-production/b/l/media/S1.mp4")   # no kit folder known yet

    def test_shared_assets_when_under_the_mount(self):
        f = touch(self.shared / "banks" / "music" / "m1.mp3")
        self.assertEqual(KP.portable(f, self.kit), "Shared Assets/banks/music/m1.mp3")

    def test_a_file_the_key_fetched_is_stored_as_its_label(self):
        # 2026-10-20 (lead 088): the edit run on the mini wrote the API cache path into the kit
        f = touch(self.tmp / "T" / "upright-drive" / "Shared Assets" / "banks" / "sfx" / "click.mp3")
        got, text = self.quiet(KP.portable, f, self.kit)
        self.assertEqual(got, "Shared Assets/banks/sfx/click.mp3")
        self.assertNotIn("WARN", text)
        cache = self.tmp / "reach-cache"
        with mock.patch.object(KP.R, "cache_root", lambda: cache):
            g = touch(cache / "banks" / "sfx" / "pop.mp3")
            self.assertEqual(KP.portable(g, self.kit), "Shared Assets/banks/sfx/pop.mp3")

    def test_absolute_only_as_a_last_resort_and_warned(self):
        f = touch(self.tmp / "someones-mac" / "S1.mp4")
        got, text = self.quiet(KP.portable, f, self.kit)
        self.assertEqual(got, str(f))
        self.assertTrue(got.startswith("/"))
        self.assertIn("WARN", text)
        self.assertIn(str(f), text)

    def test_no_mount_and_no_workspace_is_absolute(self):
        KP.repo, KP.mount = (lambda: None), (lambda: None)
        # KEYS ONLY (the team 2026-10-20, rule 069): a file whose path has a Shared Assets part is stored as
        # its label even with no mount here — never this machine's path
        f = touch(self.shared / "banks" / "x.mp3")
        got, text = self.quiet(KP.portable, f, None)
        self.assertEqual(got, "Shared Assets/banks/x.mp3")
        self.assertNotIn("WARN", text)
        # a file with no Shared Assets part and nothing else to hang off is still absolute, and warned
        g = touch(self.tmp / "someones-mac" / "x.mp3")
        got, text = self.quiet(KP.portable, g, None)
        self.assertEqual(got, str(g))
        self.assertIn("WARN", text)


class Resolve(Patched):
    def test_each_form_is_found(self):
        k = touch(self.kit / "media" / "S1.mp4")
        r = touch(self.ws / "runs" / "video-production" / "b" / "l" / "vo" / "S2.mp3")
        s = touch(self.shared / "banks" / "sfx" / "ding.wav")
        a = touch(self.tmp / "elsewhere" / "old.mp4")
        self.assertEqual(KP.resolve("media/S1.mp4", self.kit), k)
        self.assertEqual(KP.resolve("runs/video-production/b/l/vo/S2.mp3", self.kit), r)
        self.assertEqual(KP.resolve("Shared Assets/banks/sfx/ding.wav", self.kit), s)
        self.assertEqual(KP.resolve(str(a), self.kit), a)                      # absolute → kept
        for got in (KP.resolve("media/S1.mp4", self.kit), KP.resolve("Shared Assets/banks/sfx/ding.wav", self.kit)):
            self.assertTrue(got.is_absolute())

    def test_the_kit_wins_over_the_repo(self):
        k = touch(self.kit / "media" / "S1.mp4")
        touch(self.ws / "media" / "S1.mp4")
        self.assertEqual(KP.resolve("media/S1.mp4", self.kit), k)

    def test_a_missing_file_is_none(self):
        for ref in ("media/gone.mp4", "runs/video-production/b/l/gone.mp4", "Shared Assets/gone.wav",
                    str(self.tmp / "gone.mp4"), "", None):
            self.assertIsNone(KP.resolve(ref, self.kit), ref)

    def test_shared_assets_with_no_mount_is_none(self):
        touch(self.shared / "banks" / "sfx" / "ding.wav")
        KP.mount = lambda: None
        self.assertIsNone(KP.resolve("Shared Assets/banks/sfx/ding.wav", self.kit))


class ResolveForeign(Patched):
    """LD-13 (old kits remap): an old kit's absolute src from another Mac is found again by its suffix."""
    DRIVE = "~/Library/CloudStorage/GoogleDrive-x/Shared drives/Shared Assets"
    CHECKOUT = "~/Projects/workspace"

    def test_a_foreign_shared_assets_path_resolves_to_this_mount(self):
        s = touch(self.shared / "banks" / "a.wav")
        got = KP.resolve(f"{self.DRIVE}/banks/a.wav", self.kit)
        self.assertEqual(got, s)
        self.assertTrue(got.is_absolute())

    def test_a_foreign_checkout_path_resolves_to_this_repo(self):
        r = touch(self.ws / "runs" / "v" / "x.mp4")
        got = KP.resolve(f"{self.CHECKOUT}/runs/v/x.mp4", self.kit)
        self.assertEqual(got, r)
        self.assertTrue(got.is_absolute())

    def test_each_repo_top_folder_is_an_anchor(self):
        for top in ("runs", "components", "brands", "lab", "new-workflow-design"):
            f = touch(self.ws / top / "v" / "x.mp4")
            self.assertEqual(KP.resolve(f"{self.CHECKOUT}/{top}/v/x.mp4", self.kit), f, top)

    def test_a_foreign_path_that_exists_nowhere_is_none(self):
        for ref in (f"{self.DRIVE}/banks/gone.wav", f"{self.CHECKOUT}/runs/v/gone.mp4",
                    "~/Desktop/ding.wav", f"{self.DRIVE}"):
            self.assertIsNone(KP.resolve(ref, self.kit), ref)

    def test_an_existing_absolute_path_is_kept(self):
        a = touch(self.tmp / "elsewhere" / "runs" / "v" / "x.mp4")
        touch(self.ws / "runs" / "v" / "x.mp4")                              # a remap target exists too
        self.assertEqual(KP.resolve(str(a), self.kit), a)

    def test_the_mount_is_tried_before_the_repo(self):
        s = touch(self.shared / "runs" / "v" / "x.mp4")
        touch(self.ws / "runs" / "v" / "x.mp4")
        self.assertEqual(KP.resolve(f"{self.DRIVE}/runs/v/x.mp4", self.kit), s)

    def test_the_repo_is_tried_when_the_mount_misses(self):
        r = touch(self.ws / "runs" / "v" / "x.mp4")
        self.assertEqual(KP.resolve(f"{self.DRIVE}/runs/v/x.mp4", self.kit), r)

    def test_the_last_shared_assets_and_the_first_top_folder_count(self):
        s = touch(self.shared / "banks" / "a.wav")
        self.assertEqual(KP.resolve(f"/Volumes/Shared Assets/old/{self.DRIVE}/banks/a.wav", self.kit), s)
        r = touch(self.ws / "runs" / "lab" / "x.mp4")
        self.assertEqual(KP.resolve(f"{self.CHECKOUT}/runs/lab/x.mp4", self.kit), r)

    def test_no_mount_and_no_workspace_is_none(self):
        touch(self.shared / "banks" / "a.wav")
        touch(self.ws / "runs" / "v" / "x.mp4")
        KP.repo, KP.mount = (lambda: None), (lambda: None)
        self.assertIsNone(KP.resolve(f"{self.DRIVE}/banks/a.wav", self.kit))
        self.assertIsNone(KP.resolve(f"{self.CHECKOUT}/runs/v/x.mp4", self.kit))

    def test_an_old_kit_with_foreign_srcs_gathers_them_here(self):
        s = touch(self.shared / "banks" / "sfx" / "ding.wav")
        c = touch(self.ws / "runs" / "video-production" / "b" / "l" / "media" / "S1.mp4")
        (self.kit / "edit-kit.json").write_text(json.dumps({
            "clips": [{"id": "S1", "src": f"{self.CHECKOUT}/runs/video-production/b/l/media/S1.mp4",
                       "roll": "a", "talks": True, "approved": True}],
            "sfx": [{"id": "sfx1", "src": f"{self.DRIVE}/banks/sfx/ding.wav"}]}))
        kit, red = R.gather(self.kit)
        self.assertEqual(red, [])
        self.assertEqual(srcs(kit), [str(s), str(c)])


class ResolveByApi(Patched):
    """LD-15 (kit reads by API): with no mount (a launchd job on the mini), a `Shared Assets` src is
    read through gdrive-creator `reach.readable()` on its `Shared Assets/…` label — a fake here."""
    DRIVE = ResolveForeign.DRIVE

    def setUp(self):
        super().setUp()
        KP.mount = lambda: None
        self.cache = self.tmp / "api-cache"

    def fake_reach(self, label):
        self.asked.append(label)
        return touch(self.cache.joinpath(*Path(label).parts))

    def test_a_portable_src_reads_through_the_api(self):
        KP.READABLE = self.fake_reach
        got = KP.resolve("Shared Assets/banks/sfx/a.wav", self.kit)
        self.assertEqual(got, self.cache / "Shared Assets" / "banks" / "sfx" / "a.wav")
        self.assertTrue(got.is_absolute())
        self.assertEqual(self.asked, ["Shared Assets/banks/sfx/a.wav"])

    def test_an_old_absolute_src_reads_through_the_api_by_its_label(self):
        KP.READABLE = self.fake_reach
        got = KP.resolve(f"{self.DRIVE}/banks/a.wav", self.kit)
        self.assertEqual(got, self.cache / "Shared Assets" / "banks" / "a.wav")
        self.assertEqual(self.asked, ["Shared Assets/banks/a.wav"])           # the label, never the foreign path

    def test_the_last_shared_assets_names_the_label(self):
        KP.READABLE = self.fake_reach
        KP.resolve(f"/Volumes/Shared Assets/old/{self.DRIVE}/banks/a.wav", self.kit)
        self.assertEqual(self.asked, ["Shared Assets/banks/a.wav"])

    def test_no_drive_is_none(self):
        self.assertIsNone(KP.resolve("Shared Assets/banks/sfx/a.wav", self.kit))
        self.assertIsNone(KP.resolve(f"{self.DRIVE}/banks/a.wav", self.kit))
        self.assertEqual(self.asked, ["Shared Assets/banks/sfx/a.wav", "Shared Assets/banks/a.wav"])

    def test_no_key_is_none(self):
        def no_key(label):
            raise SystemExit("GDRIVE_SA_KEY is not set")
        KP.READABLE = no_key
        self.assertIsNone(KP.resolve("Shared Assets/banks/sfx/a.wav", self.kit))
        self.assertIsNone(KP.resolve(f"{self.DRIVE}/banks/a.wav", self.kit))

    def test_an_os_error_is_none(self):
        def broken(label):
            raise OSError("disk")
        KP.READABLE = broken
        self.assertIsNone(KP.resolve("Shared Assets/banks/sfx/a.wav", self.kit))

    def test_a_folder_is_none(self):
        def folder(label):
            d = self.cache.joinpath(*Path(label).parts)
            d.mkdir(parents=True)
            return d
        KP.READABLE = folder
        self.assertIsNone(KP.resolve("Shared Assets/banks/sfx", self.kit))

    def test_a_mount_file_wins_and_the_api_is_never_asked(self):
        KP.mount = lambda: self.shared
        KP.READABLE = self.fake_reach
        s = touch(self.shared / "banks" / "sfx" / "a.wav")
        a = touch(self.shared / "banks" / "a.wav")
        self.assertEqual(KP.resolve("Shared Assets/banks/sfx/a.wav", self.kit), s)
        self.assertEqual(KP.resolve(f"{self.DRIVE}/banks/a.wav", self.kit), a)
        self.assertEqual(self.asked, [])

    def test_a_kit_or_repo_file_wins_and_the_api_is_never_asked(self):
        KP.READABLE = self.fake_reach
        k = touch(self.kit / "Shared Assets" / "banks" / "a.wav")
        self.assertEqual(KP.resolve("Shared Assets/banks/a.wav", self.kit), k)
        r = touch(self.ws / "runs" / "v" / "x.mp4")
        self.assertEqual(KP.resolve(f"{self.DRIVE}/runs/v/x.mp4", self.kit), r)
        self.assertEqual(self.asked, [])

    def test_a_src_with_no_shared_assets_never_asks(self):
        KP.READABLE = self.fake_reach
        for ref in ("media/gone.mp4", "runs/v/gone.mp4", "~/Desktop/ding.wav",
                    f"{self.DRIVE}"):
            self.assertIsNone(KP.resolve(ref, self.kit), ref)
        self.assertEqual(self.asked, [])

    def test_gather_reads_the_banks_in_memory_and_leaves_the_kit_as_written(self):
        KP.READABLE = self.fake_reach
        touch(self.kit / "media" / "S1.mp4")
        kit_json = {"clips": [{"id": "S1", "src": "media/S1.mp4", "roll": "a", "talks": True, "approved": True}],
                    "music": {"src": "Shared Assets/banks/music/m1.mp3"},
                    "sfx": [{"id": "sfx1", "src": f"{self.DRIVE}/banks/sfx/ding.wav"}]}
        (self.kit / "edit-kit.json").write_text(json.dumps(kit_json))
        kit, red = R.gather(self.kit)
        self.assertEqual(red, [])
        self.assertEqual(kit["music"]["src"], str(self.cache / "Shared Assets" / "banks" / "music" / "m1.mp3"))
        self.assertEqual(kit["sfx"][0]["src"], str(self.cache / "Shared Assets" / "banks" / "sfx" / "ding.wav"))
        self.assertEqual(json.loads((self.kit / "edit-kit.json").read_text()), kit_json)   # never written into the kit


class ResolveMountDeadlock(Patched):
    """LD-24 (kit mount deadlock): a Drive for desktop placeholder answers a stat with EDEADLK
    ("Resource deadlock avoided"), which pathlib's is_file() does not swallow. resolve() takes
    it as "not here" and goes on to the Drive API — never an exception out of gather."""
    DRIVE = ResolveForeign.DRIVE

    def setUp(self):
        super().setUp()
        self.cache = self.tmp / "api-cache"
        touch(self.shared / "banks" / "a.wav")                                # a placeholder: listed on the mount, unreadable
        touch(self.shared / "banks" / "sfx" / "a.wav")
        real_stat, real_is_file = Path.stat, Path.is_file
        mount = str(self.shared)

        def stat(path, *a, **k):
            if str(path).startswith(mount):
                raise OSError(errno.EDEADLK, "Resource deadlock avoided", str(path))
            return real_stat(path, *a, **k)

        def is_file(path):                                                    # pathlib 3.9's own is_file (the mini's): newer
            try:                                                              # interpreters skip Path.stat, so it is pinned here
                return S_ISREG(path.stat().st_mode)
            except OSError as e:
                if e.errno not in (errno.ENOENT, errno.ENOTDIR, errno.EBADF, errno.ELOOP):
                    raise
                return False
            except ValueError:
                return False
        Path.stat, Path.is_file = stat, is_file
        self.addCleanup(setattr, Path, "stat", real_stat)
        self.addCleanup(setattr, Path, "is_file", real_is_file)

    def fake_reach(self, label):
        self.asked.append(label)
        return touch(self.cache.joinpath(*Path(label).parts))

    def test_the_simulated_placeholder_raises_through_pathlib(self):
        with self.assertRaises(OSError) as e:
            (self.shared / "banks" / "a.wav").is_file()
        self.assertEqual(e.exception.errno, errno.EDEADLK)

    def test_a_foreign_src_on_a_deadlocked_mount_reads_through_the_api(self):
        KP.READABLE = self.fake_reach
        got = KP.resolve(f"{self.DRIVE}/banks/a.wav", self.kit)
        self.assertEqual(got, self.cache / "Shared Assets" / "banks" / "a.wav")
        self.assertTrue(got.is_absolute())
        self.assertTrue(got.is_file())
        self.assertEqual(self.asked, ["Shared Assets/banks/a.wav"])

    def test_a_foreign_src_on_a_deadlocked_mount_with_no_drive_is_none(self):
        self.assertIsNone(KP.resolve(f"{self.DRIVE}/banks/a.wav", self.kit))
        self.assertEqual(self.asked, ["Shared Assets/banks/a.wav"])

    def test_a_portable_src_on_a_deadlocked_mount_reads_through_the_api(self):
        KP.READABLE = self.fake_reach
        got = KP.resolve("Shared Assets/banks/sfx/a.wav", self.kit)
        self.assertEqual(got, self.cache / "Shared Assets" / "banks" / "sfx" / "a.wav")
        self.assertTrue(got.is_absolute())
        self.assertTrue(got.is_file())
        self.assertEqual(self.asked, ["Shared Assets/banks/sfx/a.wav"])

    def test_a_portable_src_on_a_deadlocked_mount_with_no_drive_is_none(self):
        self.assertIsNone(KP.resolve("Shared Assets/banks/sfx/a.wav", self.kit))
        self.assertEqual(self.asked, ["Shared Assets/banks/sfx/a.wav"])

    def test_an_absolute_src_on_this_deadlocked_mount_reads_through_the_api(self):
        KP.READABLE = self.fake_reach
        got = KP.resolve(str(self.shared / "banks" / "a.wav"), self.kit)
        self.assertEqual(got, self.cache / "Shared Assets" / "banks" / "a.wav")
        self.assertEqual(self.asked, ["Shared Assets/banks/a.wav"])
        self.asked.clear()
        KP.READABLE = self.no_drive
        self.assertIsNone(KP.resolve(str(self.shared / "banks" / "a.wav"), self.kit))
        self.assertEqual(self.asked, ["Shared Assets/banks/a.wav"])

    def test_a_deadlocked_mount_still_lets_the_repo_win(self):
        KP.READABLE = self.fake_reach
        touch(self.shared / "runs" / "v" / "x.mp4")
        r = touch(self.ws / "runs" / "v" / "x.mp4")
        self.assertEqual(KP.resolve(f"{self.DRIVE}/runs/v/x.mp4", self.kit), r)
        self.assertEqual(self.asked, [])

    def test_gather_on_a_deadlocked_mount_reads_the_banks_by_api(self):
        KP.READABLE = self.fake_reach
        touch(self.kit / "media" / "S1.mp4")
        (self.kit / "edit-kit.json").write_text(json.dumps({
            "clips": [{"id": "S1", "src": "media/S1.mp4", "roll": "a", "talks": True, "approved": True}],
            "music": {"src": "Shared Assets/banks/sfx/a.wav"},
            "sfx": [{"id": "sfx1", "src": f"{self.DRIVE}/banks/a.wav"}]}))
        kit, red = R.gather(self.kit)
        self.assertEqual(red, [])
        self.assertEqual(kit["music"]["src"], str(self.cache / "Shared Assets" / "banks" / "sfx" / "a.wav"))
        self.assertEqual(kit["sfx"][0]["src"], str(self.cache / "Shared Assets" / "banks" / "a.wav"))


class BuildWritesPortableRefs(Patched):
    def production_run(self) -> Path:
        vm = self.ws / "runs" / "video-production" / "b" / "vm-01"
        for f in ("media/S1.mp4", "media/S2.mp4", "vo/S2.mp3", "media/S3-PLATE.png", "vo/S3.mp3", "tone.wav"):
            touch(vm / f)
        touch(self.shared / "banks" / "music" / "m1.mp3")
        touch(self.shared / "banks" / "sfx" / "ding.wav")
        ok = {"verdict": "PASS"}
        (vm / "verdicts.json").write_text(json.dumps({s: {"motion": ok, "director": ok, "parity": ok} for s in ("S1", "S2")}))
        (vm / "run.json").write_text(json.dumps({"brand": "b", "label": "l"}))
        (vm / "plan.json").write_text(json.dumps({"scenes": [
            {"id": "S1", "type": "A", "to_camera": True, "opens": True},
            {"id": "S2", "type": "B"},
            {"id": "S3", "kind": "card", "card": {"lines": ["3 WEEKS"]}}],
            "music": {"bank_id": "m1", "file": str(self.shared / "banks" / "music" / "m1.mp3")},
            "sfx": [{"cue": "ding", "bank_id": "d1", "file": str(self.shared / "banks" / "sfx" / "ding.wav")},
                    {"cue": "room-tone-kitchen", "bank_id": "room-tone-kitchen", "file": "tone.wav"}]}))
        return vm

    def test_no_src_starts_with_a_slash(self):
        vm = self.production_run()
        (kit, notes), text = self.quiet(K.build, vm)
        got = srcs(kit)
        self.assertEqual(len(got), 8, got)                                    # 3 clips, 2 voice slices, music, sfx, room tone
        self.assertEqual([s for s in got if s.startswith("/")], [])
        self.assertNotIn("WARN", text)
        by = {c["id"]: c for c in kit["clips"]}
        self.assertEqual(by["S1"]["src"], "runs/video-production/b/vm-01/media/S1.mp4")
        self.assertEqual(by["S2"]["voice"]["src"], "runs/video-production/b/vm-01/vo/S2.mp3")
        self.assertEqual(kit["music"]["src"], "Shared Assets/banks/music/m1.mp3")
        self.assertEqual(kit["sfx"][0]["src"], "Shared Assets/banks/sfx/ding.wav")
        self.assertEqual(kit["room_tone"][0]["src"], "runs/video-production/b/vm-01/tone.wav")

    def test_the_written_kit_gathers_with_every_src_found(self):
        vm = self.production_run()
        (kit, _), _ = self.quiet(K.build, vm)
        R.write(self.kit / "edit-kit.json", kit)
        got, red = R.gather(self.kit)
        self.assertEqual(red, [])
        for s in srcs(got):
            self.assertTrue(Path(s).is_absolute(), s)
            self.assertTrue(Path(s).is_file(), s)


class Gather(Patched):
    def kit_file(self, kit: dict) -> None:
        (self.kit / "edit-kit.json").write_text(json.dumps(kit))

    def test_relative_srcs_yield_rows_whose_src_exists(self):
        touch(self.kit / "media" / "S1.mp4")
        touch(self.ws / "runs" / "video-production" / "b" / "l" / "media" / "S2.mp4")
        touch(self.ws / "runs" / "video-production" / "b" / "l" / "vo" / "S2.mp3")
        touch(self.shared / "banks" / "music" / "m1.mp3")
        touch(self.shared / "banks" / "sfx" / "ding.wav")
        touch(self.kit / "tone.wav")
        self.kit_file({"clips": [
            {"id": "S1", "src": "media/S1.mp4", "roll": "a", "talks": True, "approved": True},
            {"id": "S2", "src": "runs/video-production/b/l/media/S2.mp4", "roll": "b", "talks": False, "approved": True,
             "voice": {"src": "runs/video-production/b/l/vo/S2.mp3"}}],
            "music": {"src": "Shared Assets/banks/music/m1.mp3"},
            "sfx": [{"id": "sfx1", "src": "Shared Assets/banks/sfx/ding.wav"}],
            "room_tone": [{"src": "tone.wav"}]})
        kit, red = R.gather(self.kit)
        self.assertEqual(red, [])
        got = srcs(kit)
        self.assertEqual(len(got), 6)
        for s in got:
            self.assertTrue(Path(s).is_absolute(), s)
            self.assertTrue(Path(s).exists(), s)
        on_disk = json.loads((self.kit / "edit-kit.json").read_text())
        self.assertEqual(on_disk["clips"][0]["src"], "media/S1.mp4")          # resolved in memory only

    def test_a_ref_not_on_this_machine_stays_as_written_for_the_gate(self):
        touch(self.kit / "media" / "S1.mp4")
        self.kit_file({"clips": [{"id": "S1", "src": "media/S1.mp4", "roll": "a", "talks": True, "approved": True}],
                       "music": {"src": "Shared Assets/banks/music/only-on-one-drive.mp3"},
                       "sfx": [{"id": "sfx1", "src": "~/Desktop/ding.wav"}]})
        kit, red = R.gather(self.kit)
        self.assertEqual(red, [])
        self.assertEqual(kit["music"]["src"], "Shared Assets/banks/music/only-on-one-drive.mp3")
        self.assertEqual(kit["sfx"][0]["src"], "~/Desktop/ding.wav")
        self.assertTrue(Path(kit["clips"][0]["src"]).is_file())

    def test_an_old_kit_with_absolute_srcs_still_gathers(self):
        old = self.tmp / "someones-mac" / "runs" / "video-production" / "b" / "l"
        a, b, v = touch(old / "media" / "S1.mp4"), touch(old / "media" / "S2.mp4"), touch(old / "vo" / "S2.mp3")
        self.kit_file({"clips": [
            {"id": "S1", "src": str(a), "roll": "a", "talks": True, "approved": True},
            {"id": "S2", "src": str(b), "roll": "b", "talks": False, "approved": True, "voice": {"src": str(v)}}]})
        kit, red = R.gather(self.kit)
        self.assertEqual(red, [])
        self.assertEqual(srcs(kit), [str(a), str(b), str(v)])


if __name__ == "__main__":
    unittest.main()
