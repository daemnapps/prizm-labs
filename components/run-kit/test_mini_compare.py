#!/usr/bin/env python3
"""mini-compare (mini_compare.py, LD-41 (mini-compare false REDs)), checked against
one temp-dir git fixture repo — components/<x>/ files, the mini's key list and a
platform/data/mini-inventory/index.json — with `main([<x>, "--detail"])` run in it
and its report captured. Each of the five false shapes prints no RED; its real
counterpart, and every check that was there before, still prints RED. No real
repo, remote or network is touched (origin/main is a local ref set at the
fixture commit).

LD-42 (full check default): every run checks every file; a RED in committed code
is ALREADY IN THE CODE (its lines only with --detail), the same RED in a file you
changed — uncommitted, untracked, or not on origin/main — is NEW; `--full` changes
nothing; no component named prints one line per component, worst first.

LD-43 (new static checks): per check one fixture that fires and a near-miss that
does not; a gitignored .venv/ or work/ written after the commit is neither a
local name nor the component's code; brandpath's drive_index.py is DELIBERATE.

LD-43b (narrow new checks): the first real run's false shapes — a hashed file size,
the builtin hash(), a local URL printed, linked or returned — print no RED; their
true twins (a hashed path, a URL the code connects to) do; one line per file:line.

LD-44b (trace narrowing): a child under another interpreter (a venv in /tmp) opening
its own prefix is not RED; its probe for a missing ~/.toolrc is counted, not RED;
its open of an existing ~/secret.txt still is.

    /usr/bin/python3 components/run-kit/test_mini_compare.py
"""
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mini_compare as M    # noqa: E402

GIT_ENV = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
           "GIT_TERMINAL_PROMPT": "0"}

FILES = {
    # the mini's key list and installed list
    "platform/workers/mini-worker/job_env.py":
        'JOB_ENV = {"lab-run": ["ANTHROPIC_API_KEY"]}\n'
        'VENDOR_KEYS = ["ANTHROPIC_API_KEY", "SHOPIFY_TOKEN"]\n',
    "platform/data/mini-inventory/index.json":
        json.dumps({"as_of": "20261020T000000Z", "python": {"packages": [{"name": "requests"}]}}),
    # fix 1: tracked modules and a tracked package outside components/
    "platform/workers/mini-worker/clone_root.py": "ROOT = None\n",
    "new-workflow-design/builds/atlas/tools/triage_rederive.py": "X = 1\n",
    "platform/lib/sharedpkg/__init__.py": "",
    "components/inrepo/run.py":
        "import job_env\nimport clone_root\nimport triage_rederive\nimport sharedpkg\n",
    "components/notinrepo/run.py":
        "import nopkg_ld41\nimport untracked_mod\nimport requests\n",
    # fix 2: guarded imports
    "components/guarded/run.py":
        "try:\n    import optmod_a\nexcept ImportError:\n    optmod_a = None\n"
        "try:\n    import optmod_b\nexcept (OSError, ModuleNotFoundError):\n    pass\n"
        "try:\n    from optmod_c import thing\nexcept Exception:\n    pass\n"
        "try:\n    import optmod_d\nexcept:\n    pass\n",
    "components/unguarded/run.py":
        "def key():\n    import optmod_e\n    return optmod_e.key('X')\n"
        "try:\n    import optmod_f\nexcept KeyError:\n    pass\n"
        "try:\n    def later():\n        import optmod_h\nexcept ImportError:\n    pass\n",
    "components/mixed/a.py": "try:\n    import optmod_g\nexcept ImportError:\n    pass\n",
    "components/mixed/b.py": "import optmod_g\n",
    # fix 3: guarded sentinels
    "components/sentinel/drive_index.py": "def mount():\n    return None\n",
    "components/sentinel/run.py":
        "from pathlib import Path\nimport drive_index\n"
        "SA = Path(drive_index.mount() or Path.home() / \"Library/CloudStorage/no-shared-assets-mount\")\n"
        "DRIVE = (Path(drive_index.mount() or Path.home() / \"Library/CloudStorage/elsewhere\")\n"
        "         / \"components/x\")\n"
        "NO_MOUNT = Path.home() / \"Library\" / \"CloudStorage\" / \"no-shared-assets-mount\"\n",
    "components/homepath/run.py":
        "import os\nfrom pathlib import Path\n"
        "PROJECTS = Path.home() / \"Projects\"\n"
        "NAME = os.environ.get(\"X_DIR\")\n"
        "A = NAME or Path.home() / \"Desktop\"\n"
        "B = Path.home() / \"Downloads\" or os.getcwd()\n",
    # fix 4: the keys component's own fallbacks
    "components/keys/loader.py":
        "import os\nimport nopkg_keys\n"
        "MANAGED = \"~/.workflow-worker.env\"\n"
        "KEY_FILE = \"~/.upright-keys.env\"\n"
        "T = os.environ.get(\"SHOPIFY_TOKEN\")\n",
    "components/keys/merge.py": "DEFAULT_OUT = \"~/upright-keys.master.env\"\n",
    "components/keys/other.py": "OTHER = \"~/.other.env\"\n",
    "components/notkeys/loader.py": "KEY_FILE = \"~/.upright-keys.env\"\n",
    # fix 5: regex strings
    "components/regex/run.py":
        "import re\n"
        "LEAK = re.compile(r\"/Users/|api[_-]?key\", re.I)\n"
        "HIT = re.search(\"~/secret\", \"text\")\n",
    "components/regexreal/run.py":
        "import re\n"
        "OUT = \"~/Desktop\"\n"
        "NEW = re.sub(\"x\", \"~/Desktop/out\", \"y\")\n",
    # the checks that were there before
    "components/py310/run.py": "def f(x):\n    match x:\n        case 1:\n            return 1\n",
    "components/hints/run.py": "def f(a: int | None) -> str:\n    return ''\n",
    "components/keyread/run.py":
        "import os\nA = os.environ.get(\"SHOPIFY_TOKEN\")\nB = os.environ.get(\"ANTHROPIC_API_KEY\")\n",
    "components/shadow/calendar.py": "X = 1\n",
    # LD-42 (full check default): the same RED shape, committed and on origin/main …
    "components/split/old.py": "OUT = \"~/Desktop\"\n",
    "components/split/edited.py": "X = 1\n",
    ".gitignore": "__pycache__/\n",
    # LD-43 (new static checks) item 0: the shared Drive-folder finder is DELIBERATE
    "components/brandpath/drive_index.py":
        "import pathlib\n"
        "def accounts():\n"
        "    cloud = pathlib.Path.home() / \"Library\" / \"CloudStorage\"\n"
        "    return sorted(m for m in cloud.glob(\"GoogleDrive-*\") if m.is_dir())\n"
        "ATTR = \"com.google.drivefs.item-id#S\"\n",
    # item 0b: an ignored .venv's packages and an ignored work/'s modules are not local
    "components/venvpkg/.gitignore": ".venv/\n",
    "components/venvpkg/run.py": "import numpy\n",
    "components/workpy/.gitignore": "work/\n",
    "components/workpy/run.py": "import helper_ld43\n",
    # 1: data only on one machine; an ignored folder no code names stays AMBER
    "components/onemachine/.gitignore": "work/\nmodels/\n",
    "components/onemachine/prompts/a.md": "x\n",
    "components/onemachine/run.py":
        "import os\nfrom pathlib import Path\n"
        "HERE = Path(__file__).resolve().parent\n"
        "WORK = HERE / \"work\"\n"                                                  # 4 RED
        "MODEL = os.path.join(os.path.dirname(__file__), \"models\", \"m.bin\")\n"  # 5 RED
        "PROMPT = HERE / \"prompts\" / \"a.md\"\n"                                 # 6 tracked
        "OUT = Path(__file__).parents[2] / \"runs\" / \"onemachine\"\n",           # 7 not ignored
    "components/unnamed/.gitignore": "cache/\n",
    "components/unnamed/run.py": "X = 1\n",
    # 2: local services — LD-43b (narrow new checks): only a URL the code connects to
    "components/service/run.py":
        "\"\"\"Serves on http://localhost:8800 when run by hand.\"\"\"\n"   # 1 a docstring
        "URL = urllib.request.urlopen(\"http://127.0.0.1:8420/api\")\n"     # 2 RED
        "HOST = http.client.HTTPConnection(\"localhost:8797\")\n"           # 3 RED
        "BIND = (\"127.0.0.1\", 8820)\n"                                    # 4 a bare host
        "FILE = urllib.request.urlopen(\"file://localhost/tmp/x\")\n"       # 5 a file URL
        "import http.client, urllib.request\n",                             # last, so the lines above keep their numbers
    # 3: Drive-app-only features
    "components/drivefs/run.py":
        "\"\"\"Reads com.google.drivefs xattrs by hand.\"\"\"\n"            # 1 a docstring
        "import os\nimport drive_index\n"
        "ATTR = \"com.google.drivefs.item-id#S\"\n"                         # 4 RED
        "A = list(os.walk(\"/Volumes/x/Library/CloudStorage/GoogleDrive\"))\n"   # 5 RED
        "root = drive_index.mount()\n"
        "B = list(os.walk(root))\n"                                         # 7 RED
        "C = list(os.walk(\"runs/drivefs\"))\n",                            # 8 not Drive
    # 4: ids from hashing a path
    # LD-43b (narrow new checks): 4 and 6 narrowed to true twins — str() of a bare `p`
    # and the builtin hash() no longer fire; hash(path) moved to components/narrowed/
    "components/hashpath/run.py":
        "import hashlib, os\nfrom pathlib import Path\n"
        "def ids(p, path, data, rel):\n"
        "    a = hashlib.sha1(str(path).encode()).hexdigest()\n"            # 4 RED
        "    b = hashlib.sha256(p.resolve().as_posix().encode())\n"         # 5 RED
        "    c = hashlib.md5(os.fspath(Path(data)).encode())\n"             # 6 RED
        "    d = hashlib.sha1(data.encode())\n"                             # 7 not a path
        "    e = hashlib.sha256(Path(path).read_bytes())\n"                 # 8 the contents
        "    f = hashlib.sha1(str(p.relative_to(rel)).encode())\n"          # 9 a relative path
        "    g = hashlib.sha1(str(\"const\").encode())\n"                   # 10 a constant
        "    return a, b, c, d, e, f, g\n",
    # 5: output inside the component (O4 (output under runs))
    "components/writeinside/prompt.md": "x\n",
    "components/writeinside/run.py":
        "import shutil\nfrom pathlib import Path\n"
        "HERE = Path(__file__).resolve().parent\n"
        "ROOT = HERE.parents[1]\n"
        "(HERE / \"out\").mkdir(exist_ok=True)\n"                          # 5 RED
        "(HERE / \"page.html\").write_text(\"x\")\n"                       # 6 RED
        "with open(HERE / \"log.txt\", \"a\") as fh:\n"                    # 7 RED
        "    fh.write(\"x\")\n"
        "shutil.copy(\"a.txt\", HERE / \"copy.txt\")\n"                    # 9 RED
        "(ROOT / \"runs\" / \"writeinside\").mkdir(parents=True, exist_ok=True)\n"   # 10 runs/
        "with open(HERE / \"prompt.md\") as fh:\n"                         # 11 a read
        "    fh.read()\n"
        "shutil.copy(HERE / \"prompt.md\", ROOT / \"runs\" / \"p.md\")\n",  # 13 into runs/
    # 6: a swallowed Drive / index error (AMBER only)
    "components/swallow/run.py":
        "import drive_index\n"
        "def a():\n"
        "    try:\n"                                                        # 3 AMBER
        "        return drive_index.rows(\"b\")\n"
        "    except OSError:\n"
        "        return []\n"
        "def b():\n"
        "    try:\n"                                                        # 8 re-raises
        "        return drive_index.mount()\n"
        "    except OSError:\n"
        "        raise\n"
        "def c(lst, x):\n"
        "    try:\n"                                                        # 13 list.index
        "        return lst.index(x)\n"
        "    except ValueError:\n"
        "        return None\n"
        "def d():\n"
        "    try:\n"                                                        # 18 AMBER
        "        reach_drive()\n"
        "    except Exception:\n"
        "        pass\n",
    # LD-43b (narrow new checks): the false shapes the lead read on the first real run,
    # none of which fires, and each one's true twin, which does
    "components/narrowed/run.py":
        "import hashlib, os, subprocess\n"
        "from pathlib import Path\n"
        "from urllib.request import urlopen\n"
        "import requests\n"
        "TMP = \"tmp\"\n"
        "BASE = \"http://localhost:8795\"\n"
        "def shapes(v, head, tmp, src, path, resize, crop, label, port):\n"
        "    a = hashlib.sha1(head + str(v.stat().st_size).encode())\n"           # 8 a .stat() field
        "    b = tmp / f\"smooth-{abs(hash(str(src))) % 10**8}.mp4\"\n"           # 9 builtin hash
        "    c = os.path.join(TMP, f\"{abs(hash((path, resize, crop)))}.jpg\")\n"  # 10 builtin hash
        "    d = hash(path)\n"                                                    # 11 builtin hash
        "    print(f\"serving on http://localhost:{port}\")\n"                    # 12 a print
        "    e = '<a href=\"http://127.0.0.1:8777/runs/{label}/x\">open</a>'.format(label=label)\n"  # 13 HTML
        "    return \"http://localhost:8820/x\"\n"                                # 14 a returned value
        "def twins(path):\n"
        "    a = hashlib.sha1(str(path).encode())\n"                              # 16 RED
        "    b = urlopen(\"http://localhost:8880/x\")\n"                          # 17 RED
        "    c = requests.get(BASE + \"/approve\")\n"                             # 18 RED, BASE followed
        "    d = subprocess.run([\"curl\", \"-s\", \"http://127.0.0.1:8797/x\"])\n"   # 19 RED
        "    return a, b, c, d\n",
    # one finding per file:line: a write into an ignored folder is "output inside the
    # component" only; a read from it is "data only on one machine" only
    "components/writeignored/.gitignore": "work/\n",
    "components/writeignored/run.py":
        "from pathlib import Path\n"
        "HERE = Path(__file__).resolve().parent\n"
        "(HERE / \"work\" / \"out.json\").write_text(\"x\")\n"                   # 3 a write
        "open(HERE / \"work\" / \"in.json\").read()\n",                          # 4 a read
}
SPLIT_RED = "OUT = \"~/Desktop\"\n"
# … committed but not on origin/main, edited and not committed, and never added
UNPUSHED = {"components/split/unpushed.py": SPLIT_RED}
EDITED = {"components/split/edited.py": SPLIT_RED}
UNTRACKED = {"lab/scratch/untracked_mod.py": "X = 1\n", "components/split/fresh.py": SPLIT_RED,
             # LD-43 (new static checks): a new check's RED in a file you changed is NEW
             "components/service/fresh.py":
                 "import urllib.request; urllib.request.urlopen(\"http://localhost:9000/x\")\n"}
# written after the commit into folders the fixture's .gitignore files ignore
IGNORED = {
    "components/venvpkg/.venv/lib/python3.9/site-packages/numpy/__init__.py": "",
    "components/workpy/work/helper_ld43.py": SPLIT_RED,
    "components/onemachine/work/data.json": "{}\n",
    "components/unnamed/cache/x.json": "{}\n",
}
IGNORED_NUMPY = "components/venvpkg/.venv/lib/python3.9/site-packages/numpy/__init__.py"


def split_red(name):
    return "a path on this machine only (components/split/%s.py:1): %s" % (name, SPLIT_RED.strip())


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def sh(repo, *args):
    p = subprocess.run(["git", "-c", "core.hooksPath=" + os.devnull, "-c", "commit.gpgsign=false"]
                       + list(args), cwd=str(repo), capture_output=True, text=True,
                       env=dict(os.environ, **GIT_ENV))
    if p.returncode != 0:
        raise AssertionError("git {0}: {1}".format(" ".join(args), p.stderr))
    return p.stdout


class MiniCompare(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="mini-compare-"))
        cls.repo = cls.tmp / "repo"
        sh(cls.tmp, "init", "-q", str(cls.repo))
        sh(cls.repo, "config", "user.email", "alice@example.com")
        sh(cls.repo, "config", "user.name", "alice")
        for rel, text in FILES.items():
            write(cls.repo / rel, text)
        sh(cls.repo, "add", "--", "components", "platform", "new-workflow-design", ".gitignore")
        sh(cls.repo, "commit", "-q", "-m", "fixture")
        sh(cls.repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        for rel, text in UNPUSHED.items():
            write(cls.repo / rel, text)
        sh(cls.repo, "add", "--", *UNPUSHED)
        sh(cls.repo, "commit", "-q", "-m", "not pushed")
        for rel, text in list(EDITED.items()) + list(UNTRACKED.items()) + list(IGNORED.items()):
            write(cls.repo / rel, text)
        cls.saved_env = {k: os.environ.get(k) for k in GIT_ENV}
        os.environ.update(GIT_ENV)

    @classmethod
    def tearDownClass(cls):
        for k, v in cls.saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(str(cls.tmp), ignore_errors=True)

    def run_main(self, *argv):
        """main(argv) in the fixture repo; everything it prints."""
        M._LOCAL, M._DRIFT = None, None
        buf, cwd = io.StringIO(), os.getcwd()
        os.chdir(str(self.repo))
        try:
            with contextlib.redirect_stdout(buf):
                code = M.main(list(argv))
        finally:
            os.chdir(cwd)
        self.assertEqual(code, 0)
        return buf.getvalue()

    def report(self, component, flags=("--detail",)):
        """main([component, *flags]) — by default --detail, so REDs already in the
        committed code print their lines too; that component's section."""
        m = re.search(r"^== %s — .*?(?=^== |\Z)" % re.escape(component),
                      self.run_main(component, *flags), re.M | re.S)
        return m.group(0) if m else ""

    def reds(self, component):
        return [l.strip() for l in self.report(component).splitlines() if l.strip().startswith("RED")]

    # fix 1 — in-repo modules are not packages
    def test_tracked_modules_anywhere_in_the_repo_are_local(self):
        self.assertEqual(self.reds("inrepo"), [])

    def test_a_missing_or_untracked_module_is_still_red(self):
        reds = self.reds("notinrepo")
        self.assertTrue(any("package nopkg_ld41 — not in the mini's installed list" in r for r in reds), reds)
        self.assertTrue(any("package untracked_mod — not in the mini's installed list" in r for r in reds), reds)
        self.assertFalse(any("requests" in r for r in reds), reds)   # on the mini's list

    # fix 2 — guarded imports
    def test_an_import_in_a_guarding_try_is_optional(self):
        text = self.report("guarded")
        self.assertNotIn("RED", text)
        for n in ("optmod_a", "optmod_b", "optmod_c", "optmod_d"):
            self.assertRegex(text, r"\?\s+package %s — optional" % n)

    def test_an_unguarded_import_is_still_red(self):
        reds = self.reds("unguarded")
        for n in ("optmod_e", "optmod_f", "optmod_h"):   # in a def; KeyError handler; def inside the try
            self.assertTrue(any("package %s — not in the mini's installed list" % n in r for r in reds), (n, reds))

    def test_a_name_imported_unguarded_anywhere_is_red(self):
        reds = self.reds("mixed")
        self.assertTrue(any("package optmod_g — not in the mini's installed list" in r for r in reds), reds)

    # fix 3 — guarded sentinels
    def test_a_fallback_after_call_or_and_the_no_mount_sentinel_are_not_red(self):
        text = self.report("sentinel")
        self.assertNotIn("RED", text)
        self.assertIn("guarded fallback: 3 (components/sentinel/run.py:3, components/sentinel/run.py:4, "
                      "components/sentinel/run.py:6)", text)

    def test_a_home_path_outside_a_call_or_is_still_red(self):
        reds = self.reds("homepath")
        for ln in (3, 5, 6):   # bare; `name or …`; home path as the FIRST operand
            self.assertTrue(any("components/homepath/run.py:%d)" % ln in r for r in reds), (ln, reds))
        self.assertNotIn("guarded fallback", self.report("homepath"))

    # fix 4 — the keys component's own fallbacks
    def test_the_keys_files_print_one_deliberate_line_each(self):
        text = self.report("keys")
        self.assertIn("deliberate: 2 — " + M.DELIBERATE["components/keys/loader.py"], text)
        self.assertIn("deliberate: 1 — " + M.DELIBERATE["components/keys/merge.py"], text)
        reds = [l for l in text.splitlines() if "RED" in l]
        self.assertFalse(any("a path on this machine only (components/keys/loader.py" in r for r in reds), reds)
        self.assertFalse(any("a path on this machine only (components/keys/merge.py" in r for r in reds), reds)
        # key reads and packages in a DELIBERATE file are still checked; other files still RED
        self.assertTrue(any("components/keys/loader.py reads SHOPIFY_TOKEN" in r for r in reds), reds)
        self.assertTrue(any("package nopkg_keys" in r for r in reds), reds)
        self.assertTrue(any("(components/keys/other.py:1)" in r for r in reds), reds)

    def test_deliberate_is_exactly_the_two_keys_files_and_the_drive_finder(self):
        self.assertEqual(sorted(M.DELIBERATE), ["components/brandpath/drive_index.py",
                                                "components/keys/loader.py", "components/keys/merge.py"])

    def test_a_home_path_in_a_file_not_in_deliberate_is_still_red(self):
        reds = self.reds("notkeys")
        self.assertTrue(any("(components/notkeys/loader.py:1)" in r for r in reds), reds)

    # fix 5 — regex strings
    def test_a_pattern_passed_to_re_is_not_a_path(self):
        self.assertNotIn("RED", self.report("regex"))

    def test_a_path_string_not_passed_first_to_re_is_still_red(self):
        reds = self.reds("regexreal")
        for ln in (2, 3):   # a plain constant; re.sub's replacement, not its pattern
            self.assertTrue(any("components/regexreal/run.py:%d)" % ln in r for r in reds), (ln, reds))

    # the checks that were there before
    def test_a_39_compile_error_is_red(self):
        reds = self.reds("py310")
        self.assertTrue(any(r.startswith("RED    breaks on the mini's Python 3.9.6: components/py310/run.py — ")
                            for r in reds), reds)

    def test_an_x_or_y_hint_is_red(self):
        reds = self.reds("hints")
        self.assertTrue(any("components/hints/run.py:1 — an `X | Y` type hint" in r for r in reds), reds)

    def test_a_key_the_mini_does_not_hand_out_is_red(self):
        reds = self.reds("keyread")
        self.assertTrue(any("components/keyread/run.py reads SHOPIFY_TOKEN" in r for r in reds), reds)
        self.assertFalse(any("ANTHROPIC_API_KEY" in r for r in reds), reds)

    def test_a_stdlib_named_file_is_red(self):
        reds = self.reds("shadow")
        self.assertTrue(any("shadows the standard library: components/shadow/calendar.py hides "
                            "Python's own `calendar` module" in r for r in reds), reds)

    # LD-42 (full check default) — what you changed, split from what was already there
    def findings(self, component):
        M._LOCAL, M._DRIFT = None, None
        cwd = os.getcwd()
        out = M.findings(self.repo, component)   # called from OUTSIDE the fixture repo
        self.assertEqual(os.getcwd(), cwd)
        return out

    def test_findings_returns_the_five_keys_as_lists_of_lines(self):
        f = self.findings("split")
        self.assertEqual(sorted(f), ["amber", "new_red", "notes", "old_red", "unchecked"])
        for k, v in f.items():
            self.assertTrue(isinstance(v, list) and all(isinstance(x, str) for x in v), (k, v))

    def test_a_committed_red_is_old_and_the_same_red_in_a_change_is_new(self):
        f = self.findings("split")
        self.assertEqual(f["old_red"], [split_red("old")])
        # edited and not committed; untracked; committed but not on origin/main
        self.assertEqual(f["new_red"], [split_red("edited"), split_red("fresh"), split_red("unpushed")])
        self.assertEqual(self.findings("py310")["new_red"], [])
        self.assertEqual(len(self.findings("py310")["old_red"]), 1)

    def test_already_in_the_code_prints_its_count_and_its_lines_only_with_detail(self):
        text = self.report("split", ())
        self.assertIn("\n  ALREADY IN THE CODE: 1 RED\n", text)
        self.assertNotIn(split_red("old"), text)
        for name in ("edited", "fresh", "unpushed"):   # NEW REDs always print, before the count
            self.assertLess(text.index("  RED    " + split_red(name)), text.index("ALREADY IN THE CODE"))
        detail = self.report("split", ("--detail",))
        self.assertIn("  ALREADY IN THE CODE: 1 RED\n  RED    " + split_red("old") + "\n", detail)
        self.assertIn("WON'T RUN THE SAME", self.report("py310", ()))   # the verdict counts old REDs too

    def test_full_changes_nothing(self):
        for c in ("split", "shadow", "keys"):
            self.assertEqual(self.run_main(c), self.run_main(c, "--full"), c)
        self.assertEqual(self.run_main(), self.run_main("--full"))

    def test_no_component_named_lists_one_line_each_worst_first(self):
        text = self.run_main()
        rows = re.findall(r"^(\S+)  new (\d+)  already (\d+)  amber (\d+)$", text, re.M)
        names = [r[0] for r in rows]
        self.assertEqual(rows[0], ("split", "3", "1", "3"))
        self.assertEqual(rows, sorted(rows, key=lambda r: (-int(r[1]), -int(r[2]), r[0])))
        self.assertIn(("py310", "0", "1", "0"), rows)
        self.assertLess(names.index("keys"), names.index("hints"))   # 3 already before 1
        self.assertLess(names.index("homepath"), names.index("keys"))   # a tie goes by name
        self.assertLess(names.index("hints"), names.index("keyread"))
        self.assertNotIn("inrepo", names)   # clean: only with --all
        self.assertNotIn("\n== ", text)     # no sections without --detail
        self.assertIn("inrepo  new 0  already 0  amber 0", self.run_main("--all"))
        detail = self.run_main("--detail")
        self.assertIn("== split — WON'T RUN THE SAME", detail)
        self.assertIn("  RED    " + split_red("old"), detail)

    # LD-43 (new static checks)
    def lines_of(self, component, word):
        return [l.strip() for l in self.report(component).splitlines() if l.strip().startswith(word)]

    def has(self, lines, text):
        return any(text in l for l in lines)

    # item 0 — the Drive-folder finder's own CloudStorage lines are a note, not REDs
    def test_the_drive_finder_prints_one_deliberate_line(self):
        text = self.report("brandpath")
        self.assertNotIn("RED", text)
        self.assertIn("deliberate: 3 — " + M.DELIBERATE["components/brandpath/drive_index.py"], text)

    # item 0b — gitignored folders are neither local names nor the component's code
    def test_a_package_in_an_ignored_venv_is_still_red(self):
        self.assertTrue((self.repo / IGNORED_NUMPY).is_file())
        reds = self.reds("venvpkg")
        self.assertTrue(self.has(reds, "package numpy — not in the mini's installed list"), reds)

    def test_a_module_only_in_an_ignored_folder_is_red_and_not_scanned(self):
        reds = self.reds("workpy")
        self.assertTrue(self.has(reds, "package helper_ld43 — not in the mini's installed list"), reds)
        self.assertFalse(self.has(reds, "components/workpy/work/"), reds)

    # 1 — data only on one machine
    def test_a_path_from_the_component_into_an_ignored_folder_is_red(self):
        reds = self.reds("onemachine")
        for ln, folder in ((4, "work"), (5, "models")):
            self.assertIn("RED    data only on one machine (components/onemachine/run.py:%d): builds a path into "
                          "components/onemachine/%s, which git ignores — a mini run's fresh checkout does not "
                          "have it" % (ln, folder), reds)
        for ln in (6, 7):   # a tracked file; a folder git does not ignore
            self.assertFalse(self.has(reds, "components/onemachine/run.py:%d)" % ln), (ln, reds))
        self.assertTrue(self.has(self.lines_of("onemachine", "AMBER"), "components/onemachine/work/"))

    def test_an_ignored_folder_no_code_names_stays_amber(self):
        self.assertEqual(self.reds("unnamed"), [])
        self.assertTrue(self.has(self.lines_of("unnamed", "AMBER"),
                                 "ignored folders/files that exist only here (a mini run is a fresh checkout): "
                                 "components/unnamed/cache/"))

    # 2 — local services
    def test_a_local_service_url_or_port_is_red(self):
        reds = self.reds("service")
        self.assertIn("RED    a local service (components/service/run.py:2): http://127.0.0.1 — a mini run "
                      "reaches only what listens on the mini", reds)
        self.assertTrue(self.has(reds, "a local service (components/service/run.py:3): localhost:8797"), reds)
        for ln in (1, 4, 5):   # a docstring; a bare host with no port; a file:// URL
            self.assertFalse(self.has(reds, "components/service/run.py:%d)" % ln), (ln, reds))

    def test_a_new_checks_red_in_a_file_you_changed_is_new(self):
        f = self.findings("service")
        self.assertEqual(f["new_red"], ["a local service (components/service/fresh.py:1): http://localhost — "
                                        "a mini run reaches only what listens on the mini"])
        self.assertEqual(len(f["old_red"]), 2)

    # 3 — Drive-app-only features
    def test_a_drive_app_only_feature_is_red(self):
        reds = [r for r in self.reds("drivefs") if "Drive-app-only" in r]
        self.assertEqual([re.search(r"run\.py:(\d+)", r).group(1) for r in reds], ["4", "5", "7"], reds)
        self.assertTrue(self.has(reds, "(components/drivefs/run.py:4): com.google.drivefs — "), reds)
        self.assertTrue(self.has(reds, "(components/drivefs/run.py:7): os.walk over the Drive for desktop folder"),
                        reds)

    # 4 — ids from hashing a path
    def test_an_id_from_hashing_a_path_is_red(self):
        reds = [r for r in self.reds("hashpath") if "an id from hashing a path" in r]
        self.assertEqual([re.search(r"run\.py:(\d+)", r).group(1) for r in reds], ["4", "5", "6"], reds)

    # 5 — output inside the component
    def test_output_inside_the_component_is_red(self):
        reds = [r for r in self.reds("writeinside") if "output inside the component" in r]
        self.assertEqual(sorted(int(re.search(r"run\.py:(\d+)", r).group(1)) for r in reds), [5, 6, 7, 9], reds)
        self.assertTrue(self.has(reds, "(components/writeinside/run.py:6): writes components/writeinside/page.html"
                                       " — output goes under runs/"), reds)

    # 6 — a swallowed Drive / index error: AMBER, never RED
    def test_a_try_that_swallows_a_drive_error_is_amber_only(self):
        self.assertEqual(self.reds("swallow"), [])
        amber = self.lines_of("swallow", "AMBER")
        for ln in (3, 18):
            self.assertTrue(self.has(amber, "a swallowed error (components/swallow/run.py:%d)" % ln), (ln, amber))
        for ln in (8, 13):   # the handler re-raises; list.index is not an index lookup
            self.assertFalse(self.has(amber, "components/swallow/run.py:%d)" % ln), (ln, amber))

    # LD-43b (narrow new checks) — the first real run's false shapes, and their true twins
    def test_the_first_runs_false_shapes_no_longer_fire(self):
        reds = self.reds("narrowed")
        for ln in range(8, 15):   # a .stat() field; builtin hash() x3; a print; an HTML link; a return
            self.assertFalse(self.has(reds, "components/narrowed/run.py:%d)" % ln), (ln, reds))

    def test_their_true_twins_are_still_red(self):
        reds = self.reds("narrowed")
        self.assertEqual(reds, [
            "RED    an id from hashing a path (components/narrowed/run.py:16): the same file hashes to another "
            "id in a mini run's checkout, which sits in another folder",
            "RED    a local service (components/narrowed/run.py:17): http://localhost — a mini run reaches "
            "only what listens on the mini",
            "RED    a local service (components/narrowed/run.py:18): http://localhost — a mini run reaches "
            "only what listens on the mini",
            "RED    a local service (components/narrowed/run.py:19): http://127.0.0.1 — a mini run reaches "
            "only what listens on the mini"])

    def test_a_write_into_an_ignored_folder_is_one_line(self):
        reds = self.reds("writeignored")
        self.assertEqual([r for r in reds if "components/writeignored/run.py:3)" in r],
                         ["RED    output inside the component (components/writeignored/run.py:3): writes "
                          "components/writeignored/work/out.json — output goes under runs/<machine>/<brand>/"
                          "<label>/, never inside a component (O4 (output under runs))"])
        self.assertEqual([r for r in reds if "components/writeignored/run.py:4)" in r],
                         ["RED    data only on one machine (components/writeignored/run.py:4): builds a path into "
                          "components/writeignored/work, which git ignores — a mini run's fresh checkout does "
                          "not have it"])
        self.assertEqual(len(reds), 2, reds)


# LD-44 (dry-run trace): a second fixture repo — one grant row whose door has a dry run,
# one whose door has none — with run-kit's real lab_door.py copied in, so the stub runs
# exactly as a mini lab run's does. Every run is local; nothing reaches a network.
FALLBACK_LINE = 9
# LD-44b (trace narrowing): what a child under ANOTHER interpreter does — the yt-dlp shape:
# its own prefix's files, a probe for a config file that is not there, a real home file
OTHER_PY_CHILD = ("import os, sys\n"
                  "print('child prefix ' + os.path.realpath(sys.prefix))\n"
                  "open(os.path.join(sys.prefix, 'own-prefix.txt')).read()\n"
                  "try:\n"
                  "    open(os.path.join(os.environ['HOME'], '.toolrc'))\n"
                  "except OSError:\n"
                  "    pass\n"
                  "open(os.path.join(os.environ['HOME'], 'secret.txt')).read()\n")
TRACE_FILES = {
    "team/dispatch-grants.json": json.dumps({"components": [
        {"component": "tracer", "owner": "alice", "filers": ["*"], "script": "components/tracer/lab_entry.py"},
        {"component": "nodry", "owner": "alice", "filers": ["*"], "script": "components/nodry/lab_entry.py"},
    ]}),
    "platform/workers/mini-worker/job_env.py":
        'JOB_ENV = {"lab-run": ["LD44_ALLOWED_TOKEN"]}\nVENDOR_KEYS = ["LD44_VENDOR_NAME"]\n',
    "brands/fixture/README.md": "a fixture brand folder\n",
    "components/run-kit/run_kit/__init__.py": "",
    "components/tracer/lab_door.json": json.dumps({
        "status": "draft", "script": "components/tracer/cli.py", "subcommand": None, "positionals": [],
        "flags": {"mode": "--mode", "label": "--label"}, "bool_flags": {"dry_run": "--dry-run"},
        "brand_flag": "--brand", "out": {"flag": "--out", "runs_root_flag": None, "run_dir": None},
        "refuse": []}),
    # the tools/video-teardown/machine/keys.py shape: the environment first; the
    # Path.home() fallback (line 9) is a static RED a run that has the variable never reaches
    "components/tracer/cli.py":
        "import argparse, os, subprocess, sys, time\n"                       # 1
        "from pathlib import Path\n"                                         # 2
        "\n"                                                                 # 3
        "\n"                                                                 # 4
        "def fixture_dir():\n"                                               # 5
        "    v = os.environ.get(\"LD44_FIXTURE_DIR\")\n"                     # 6
        "    if v:\n"                                                        # 7
        "        return Path(v)\n"                                           # 8
        "    return Path.home() / \".ld44-fixture-fallback\"\n"              # 9 the fallback
        "\n"
        "\n"
        "def main():\n"
        "    ap = argparse.ArgumentParser()\n"
        "    for f in (\"--brand\", \"--mode\", \"--label\", \"--out\"):\n"
        "        ap.add_argument(f)\n"
        "    ap.add_argument(\"--dry-run\", action=\"store_true\")\n"
        "    a = ap.parse_args()\n"
        "    if not a.dry_run:\n"
        "        print(\"NOT A DRY RUN\")\n"
        "        return 3\n"
        "    Path(a.out).mkdir(parents=True, exist_ok=True)\n"
        "    if a.mode == \"home\":\n"
        "        open(os.path.join(os.environ[\"HOME\"], \"secret.txt\")).read()\n"
        "    elif a.mode == \"env\":\n"
        "        os.listdir(str(fixture_dir()))\n"
        "    elif a.mode == \"child\":\n"
        "        subprocess.run([sys.executable, \"-c\", \"import os; open(os.path.join(os.environ['HOME'], "
        "'child.txt')).read()\"], check=True)\n"
        "    elif a.mode == \"otherpy\":\n"
        + "        subprocess.run([os.environ[\"LD44B_PYTHON\"], \"-c\", %r], check=True)\n" % OTHER_PY_CHILD +
        "    elif a.mode == \"keys\":\n"
        "        for n in (\"LD44_SECRET_TOKEN\", \"LD44_VENDOR_NAME\", \"LD44_ALLOWED_TOKEN\", \"LD44_PLAIN\"):\n"
        "            print(\"%s=%s\" % (n, \"present\" if n in os.environ else \"absent\"))\n"
        "    elif a.mode == \"sleep\":\n"
        "        time.sleep(60)\n"
        "    print(\"dry run done, no model call\")\n"
        "    return 0\n"
        "\n"
        "\n"
        "sys.exit(main())\n",
    "components/nodry/lab_door.json": json.dumps({
        "status": "draft", "script": "components/nodry/cli.py", "subcommand": None, "positionals": [],
        "flags": {"label": "--label"}, "bool_flags": {}, "brand_flag": "--brand",
        "out": {"flag": "--out", "runs_root_flag": None, "run_dir": None}, "refuse": []}),
    "components/nodry/cli.py":
        "import os\nopen(os.path.join(os.environ[\"HOME\"], \"nodry-ran.txt\"), \"w\").write(\"ran\")\n",
}
# the stub a grant row names, the shape of tools/video-teardown/machine/lab_entry.py
STUB = ("#!/usr/bin/python3\n"
        "import os, sys, pathlib\n"
        "sys.path.append(next(str(d / \"components\" / \"run-kit\") for d in pathlib.Path(__file__).resolve()"
        ".parents if (d / \"components\" / \"run-kit\").is_dir()))\n"
        "from run_kit import lab_door; sys.exit(lab_door.run(pathlib.Path(__file__).with_name(\"lab_door.json\"), "
        "sys.argv[1:], os.environ))\n")
FALLBACK_RED = ("a path on this machine only (components/tracer/cli.py:%d): return Path.home() / "
                "\".ld44-fixture-fallback\"" % FALLBACK_LINE)


class DryRunTrace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="mini-compare-trace-test-"))
        cls.repo = cls.tmp / "repo"
        sh(cls.tmp, "init", "-q", str(cls.repo))
        sh(cls.repo, "config", "user.email", "alice@example.com")
        sh(cls.repo, "config", "user.name", "alice")
        for rel, text in TRACE_FILES.items():
            write(cls.repo / rel, text)
        for c in ("tracer", "nodry"):
            write(cls.repo / "components" / c / "lab_entry.py", STUB)
        write(cls.repo / "components/run-kit/run_kit/lab_door.py",
              (HERE / "run_kit" / "lab_door.py").read_text())
        sh(cls.repo, "add", "-A")
        sh(cls.repo, "commit", "-q", "-m", "fixture")
        sh(cls.repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        # a HOME for the child outside every allowed root (the temp folder is one), never the real home
        cls.home = Path(tempfile.mkdtemp(prefix="ld44-home-", dir="/tmp" if os.path.isdir("/tmp") else None))
        for name in ("secret.txt", "child.txt"):
            (cls.home / name).write_text("x\n")
        # LD-44b (trace narrowing): another interpreter path — a venv, its python a symlink
        # to sys.executable — whose prefix sits outside every allowed root, as Homebrew's does
        cls.prefix_dir = Path(tempfile.mkdtemp(prefix="ld44b-prefix-", dir="/tmp" if os.path.isdir("/tmp") else None))
        cls.prefix = cls.prefix_dir / "py"
        subprocess.run([sys.executable, "-m", "venv", "--without-pip", "--symlinks", str(cls.prefix)],
                       check=True, capture_output=True)
        (cls.prefix / "own-prefix.txt").write_text("x\n")
        cls.other_py_trace = None
        cls.saved_env = {k: os.environ.get(k) for k in list(GIT_ENV) + ["HOME", "LD44B_PYTHON"]}
        os.environ.update(GIT_ENV)
        os.environ["HOME"] = str(cls.home)
        os.environ["LD44B_PYTHON"] = str(cls.prefix / "bin" / "python3")

    @classmethod
    def tearDownClass(cls):
        for k, v in cls.saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(str(cls.tmp), ignore_errors=True)
        shutil.rmtree(str(cls.home), ignore_errors=True)
        shutil.rmtree(str(cls.prefix_dir), ignore_errors=True)

    def trace(self, mode, component="tracer", **kw):
        M._LOCAL, M._DRIFT = None, None
        return M.trace(self.repo, component, None, {"mode": mode}, **kw)

    def findings(self, t):
        M._LOCAL, M._DRIFT = None, None
        return M.findings(self.repo, "tracer", trace=t)

    def test_the_child_home_is_outside_every_allowed_root(self):
        roots = M.allowed_roots(self.repo, self.tmp / "out", self.tmp / "base")
        self.assertFalse(M._inside(str(self.home / "secret.txt"), roots), roots)
        self.assertTrue(M._inside(str(self.repo / "components"), roots))

    def test_a_dry_run_that_opens_a_home_file_is_red(self):
        t = self.trace("home")
        self.assertEqual(t["exit"], 0, t["output"])
        secret = str(self.home / "secret.txt")
        self.assertIn(secret, t["opened"])
        f = self.findings(t)
        self.assertIn("the dry run opened " + secret, f["trace_red"])
        self.assertEqual(sorted(f), ["amber", "new_red", "notes", "old_red", "trace_red", "unchecked"])

    def test_an_environment_first_fallback_never_reached_is_downgraded(self):
        with mock_env(LD44_FIXTURE_DIR=str(self.repo / "components" / "tracer")):
            t = self.trace("env")
        self.assertEqual(t["exit"], 0, t["output"])
        self.assertEqual(t["opened"], [], t["opened"])
        self.assertIn("components/tracer/cli.py:6", t["reached"])          # the environment read ran
        self.assertNotIn("components/tracer/cli.py:%d" % FALLBACK_LINE, t["reached"])
        static = self.findings(None)
        self.assertIn(FALLBACK_RED, static["new_red"] + static["old_red"])  # RED without the trace
        f = self.findings(t)
        self.assertEqual(f["trace_red"], [])
        self.assertNotIn(FALLBACK_RED, f["new_red"] + f["old_red"])
        self.assertIn("fallback — not reached in the dry run: " + FALLBACK_RED, f["amber"])

    def test_a_reached_path_red_stays_red(self):
        t = {"opened": [], "reached": {"components/tracer/cli.py:%d" % FALLBACK_LINE}, "exit": 0}
        f = self.findings(t)
        self.assertIn(FALLBACK_RED, f["new_red"] + f["old_red"])
        self.assertFalse(any(a.startswith("fallback — not reached") for a in f["amber"]), f["amber"])

    def test_an_open_inside_a_child_process_is_caught(self):
        t = self.trace("child")
        self.assertEqual(t["exit"], 0, t["output"])
        self.assertIn(str(self.home / "child.txt"), t["opened"])

    # LD-44b (trace narrowing): one run of the other-interpreter child, read by three tests
    def other_py(self):
        if DryRunTrace.other_py_trace is None:
            DryRunTrace.other_py_trace = self.trace("otherpy")
        t = DryRunTrace.other_py_trace
        self.assertEqual(t["exit"], 0, t["output"])
        self.assertIn("child prefix " + os.path.realpath(str(self.prefix)), t["output"])   # it ran there
        return t

    def test_a_childs_own_interpreter_prefix_is_not_red(self):
        own = str(self.prefix / "own-prefix.txt")
        roots = M.allowed_roots(self.repo, self.tmp / "out", self.tmp / "base")
        self.assertFalse(M._inside(own, roots), roots)   # the parent's roots alone would call it RED
        t = self.other_py()
        self.assertNotIn(own, t["opened"] + t["absent"])
        self.assertFalse(any(p.startswith(os.path.realpath(str(self.prefix)) + os.sep) or
                             p.startswith(str(self.prefix) + os.sep) for p in t["opened"]), t["opened"])
        self.assertNotIn("the dry run opened " + own, self.findings(t)["trace_red"])

    def test_a_probe_for_a_missing_file_is_counted_not_red(self):
        toolrc = str(self.home / ".toolrc")
        self.assertFalse(os.path.lexists(toolrc))
        t = self.other_py()
        self.assertIn(toolrc, t["absent"])
        self.assertNotIn(toolrc, t["opened"])
        f = self.findings(t)
        self.assertNotIn("the dry run opened " + toolrc, f["trace_red"])
        line = [n for n in f["notes"] if n.startswith("dry run traced:")]
        self.assertEqual(len(line), 1, f["notes"])
        self.assertTrue(line[0].endswith("probed, absent here: %d" % len(t["absent"])), line)

    def test_an_existing_home_file_opened_by_that_child_is_still_red(self):
        secret = str(self.home / "secret.txt")
        t = self.other_py()
        self.assertIn(secret, t["opened"])
        self.assertIn("the dry run opened " + secret, self.findings(t)["trace_red"])

    def test_a_key_shaped_name_outside_the_ceiling_is_absent_in_the_child(self):
        with mock_env(LD44_SECRET_TOKEN="s", LD44_VENDOR_NAME="v", LD44_ALLOWED_TOKEN="a", LD44_PLAIN="p"):
            t = self.trace("keys")
        out = "\n".join(t["output"])
        for line in ("LD44_SECRET_TOKEN=absent", "LD44_VENDOR_NAME=absent",
                     "LD44_ALLOWED_TOKEN=present", "LD44_PLAIN=present"):
            self.assertIn(line, out)

    def test_the_door_runs_as_the_worker_does(self):
        plan = M.trace_plan(self.repo, "tracer", None, {"mode": "env"})
        self.assertEqual(plan["argv"], [M.MINI_PY, str(self.repo.resolve() / "components/tracer/lab_entry.py"),
                                        "--dry_run", "yes", "--label", "trace", "--mode", "env"])
        self.assertEqual(plan["brand"], "fixture")
        with self.assertRaises(Exception) as e:
            M.trace_plan(self.repo, "tracer", None, {"mode": "env", "dry_run": "no"})
        self.assertIn("dry_run=yes", str(e.exception))

    def test_a_door_without_dry_run_is_refused_and_nothing_runs(self):
        with self.assertRaises(Exception) as e:
            self.trace("x", component="nodry")
        self.assertEqual(str(e.exception), "no dry run door: the trace is skipped")
        self.assertFalse((self.home / "nodry-ran.txt").exists())
        code, text = self.run_main("nodry", "--trace")
        self.assertEqual((code, text), (2, "mini-compare --trace: no dry run door: the trace is skipped\n"))
        self.assertFalse((self.home / "nodry-ran.txt").exists())

    def test_a_component_with_no_grant_row_is_refused(self):
        code, text = self.run_main("tracer-not-a-row", "--trace")
        self.assertEqual(code, 2)
        self.assertEqual(len(text.splitlines()), 1, text)
        self.assertIn("is not a component row", text)

    def test_a_dry_run_past_its_timeout_is_killed_and_red(self):
        t = self.trace("sleep", timeout=2)
        self.assertTrue(t["timed_out"])
        self.assertEqual(t["exit"], 124)
        self.assertIn("the dry run did not finish in 2 s", self.findings(t)["trace_red"])

    def test_the_cli_prints_the_run_and_the_downgrade(self):
        with mock_env(LD44_FIXTURE_DIR=str(self.repo / "components" / "tracer")):
            code, text = self.run_main("tracer", "--trace", "mode=env")
        self.assertEqual(code, 0, text)
        self.assertIn("  | dry run done, no model call", text)
        self.assertIn("  AMBER  fallback — not reached in the dry run: " + FALLBACK_RED, text)
        self.assertNotIn("RED    " + FALLBACK_RED, text)
        self.assertNotIn("the dry run opened", text)

    def run_main(self, *argv):
        M._LOCAL, M._DRIFT = None, None
        buf, cwd = io.StringIO(), os.getcwd()
        os.chdir(str(self.repo))
        try:
            with contextlib.redirect_stdout(buf):
                code = M.main(list(argv))
        finally:
            os.chdir(cwd)
        return code, buf.getvalue()


@contextlib.contextmanager
def mock_env(**values):
    saved = {k: os.environ.get(k) for k in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


if __name__ == "__main__":
    unittest.main()
