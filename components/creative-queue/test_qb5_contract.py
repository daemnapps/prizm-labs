"""QB-5 (production contract): the adapter manifest validator, contract.py.

A valid adapter.json passes; an unknown word, `go`, a lab argv[0] and a kind outside the naming standard's types each
fail with the field named; `find` lists the fixtures. Stdlib only, no network. Run from the repo root:
    python3 components/creative-queue/test_qb5_contract.py
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))
import contract  # noqa: E402

FIX = HERE / "test_qb5_fixtures"
REPO = contract._repo()


def cli(*args):
    p = subprocess.run([sys.executable, str(HERE / "contract.py")] + list(args), cwd=str(REPO),
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return p.returncode, p.stdout, p.stderr


class Check(unittest.TestCase):
    def test_valid_passes(self):
        code, out, _ = cli("check", str(FIX / "valid" / "adapter.json"))
        self.assertEqual(code, 0, out)
        self.assertIn("ok:", out)
        self.assertEqual(contract.check(json.loads((FIX / "valid" / "adapter.json").read_text())), [])

    def test_the_email_adapter_passes(self):
        code, out, _ = cli("check", "tools/email-production/adapter/adapter.json")
        self.assertEqual(code, 0, out)

    def test_unknown_word_fails_naming_words(self):
        code, out, _ = cli("check", str(FIX / "unknown-word" / "adapter.json"))
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("words:"), out)
        self.assertIn("sparkle", out)

    def test_go_is_refused_even_when_listed(self):
        code, out, _ = cli("check", str(FIX / "go-word" / "adapter.json"))
        self.assertEqual(code, 1)
        lines = out.strip().splitlines()
        self.assertTrue(any(ln.startswith("words:") and "'go' is refused" in ln for ln in lines), out)
        self.assertTrue(any(ln.startswith("kind_words:") and "'go' is refused" in ln for ln in lines), out)

    def test_every_refused_word_fails(self):
        base = json.loads((FIX / "valid" / "adapter.json").read_text())
        for w in ("go", "schedule", "send", "approve"):
            m = dict(base, words=["ok", w])
            got = contract.check(m)
            self.assertTrue(any(p.startswith("words:") and "refused" in p for p in got), (w, got))

    def test_lab_argv_fails_naming_the_verb(self):
        code, out, _ = cli("check", str(FIX / "lab-argv" / "adapter.json"))
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("apply:"), out)
        self.assertIn("lab code", out)

    def test_argv_outside_components_or_missing_fails(self):
        base = json.loads((FIX / "valid" / "adapter.json").read_text())
        for argv, word in ((["platform/x.py"], "under components/"), (["/abs/components/x.py"], "repo-relative"),
                           (["components/../lab/x.py"], "repo-relative"), (["components/nope/nothing.py"], "not on disk"),
                           ([], "non-empty")):
            got = contract.check(dict(base, detail=argv))
            self.assertTrue(any(p.startswith("detail:") and word in p for p in got), (argv, got))

    def test_kind_outside_naming_types_fails_naming_kind(self):
        code, out, _ = cli("check", str(FIX / "bad-kind" / "adapter.json"))
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("kind:"), out)
        self.assertIn("image-ad", out)          # the naming standard's own word for "static", as a hint

    def test_kinds_are_the_naming_standards(self):
        d = json.loads((REPO / "components" / "naming" / "stages.json").read_text())
        self.assertEqual(sorted(contract.kinds()), sorted(t["id"] for t in d["types"]))

    def test_missing_field_and_bad_file(self):
        m = json.loads((FIX / "valid" / "adapter.json").read_text())
        del m["report"]
        self.assertIn("report: missing", contract.check(m))
        with tempfile.TemporaryDirectory() as t:
            f = Path(t) / "adapter.json"
            f.write_text("{not json")
            code, out, _ = cli("check", str(f))
            self.assertEqual(code, 1)
            self.assertTrue(out.startswith("file:"), out)

    def test_load_and_command(self):
        m = contract.load(FIX / "valid" / "adapter.json")
        argv = contract.command(m, "apply", ["x", "-", "ok", "--by", "the team"])
        self.assertEqual(argv[0], sys.executable)
        self.assertEqual(argv[1], str(REPO / "components" / "creative-queue" / "contract.py"))
        self.assertEqual(argv[2:], ["apply", "x", "-", "ok", "--by", "the team"])
        with self.assertRaises(ValueError):
            contract.load(FIX / "go-word" / "adapter.json")

    def test_kill_signal_warns_never_fails(self):
        m = json.loads((FIX / "valid" / "adapter.json").read_text())
        m["kind_words"] = {w: "x" for w in ("a1", "a2", "a3", "a4")}
        m["words"] = ["ok", "a1", "a2", "a3", "a4"]
        self.assertEqual(contract.check(m), [])
        self.assertTrue(contract.warnings(m))


class TryVerb(unittest.TestCase):
    """LD-83 (picture try first): an optional `try` verb beside apply, with its try_words."""

    def base(self):
        return json.loads((FIX / "valid" / "adapter.json").read_text())

    def test_a_manifest_with_try_and_try_words_validates(self):
        m = dict(self.base(), **{"try": ["components/creative-queue/contract.py", "try"], "try_words": ["picture"]})
        self.assertEqual(contract.check(m), [])

    def test_try_words_outside_words_or_refused_fail(self):
        m = dict(self.base(), **{"try": ["components/creative-queue/contract.py", "try"]})
        for tw, why in ((["sparkle"], "not in words"), (["go"], "refused"), (["send"], "refused"), ([], "non-empty"),
                        ("picture", "non-empty")):
            got = contract.check(dict(m, try_words=tw))
            self.assertTrue(any(p.startswith("try_words:") and why in p for p in got), (tw, got))
        got = contract.check(dict(self.base(), try_words=["picture"]))
        self.assertTrue(any(p.startswith("try_words:") and "without a `try` verb" in p for p in got), got)

    def test_try_argv_is_checked_like_the_others(self):
        got = contract.check(dict(self.base(), **{"try": ["lab/engineer/x.py"], "try_words": ["picture"]}))
        self.assertTrue(any(p.startswith("try:") and "lab code" in p for p in got), got)

    def test_go_and_send_stay_refused_as_change_words_with_try(self):
        m = dict(self.base(), **{"try": ["components/creative-queue/contract.py", "try"], "try_words": ["picture"]})
        for w in ("go", "send"):
            got = contract.check(dict(m, words=["ok", "picture", w]))
            self.assertTrue(any(p.startswith("words:") and "refused" in p for p in got), (w, got))
        self.assertNotIn("try", contract.REFUSED)
        self.assertEqual(contract.VERBS, ("report", "detail", "apply"))

    def test_command_builds_the_try_argv_only_when_declared(self):
        m = dict(self.base(), **{"try": ["components/creative-queue/contract.py", "try"], "try_words": ["picture"]})
        argv = contract.command(m, "try", ["x", "1", "picture", "0: warmer", "--by", "the team"])
        self.assertEqual(argv[:2], [sys.executable, str(REPO / "components" / "creative-queue" / "contract.py")])
        self.assertEqual(argv[2:], ["try", "x", "1", "picture", "0: warmer", "--by", "the team"])
        with self.assertRaises(ValueError) as c:
            contract.command(self.base(), "try", [])
        self.assertIn("report, detail, apply", str(c.exception))
        self.assertEqual(contract.check(self.base()), [])                       # a manifest without try: unchanged

    def test_the_real_email_adapter_declares_try(self):
        m = contract.load(REPO / "tools" / "email-production" / "adapter" / "adapter.json")
        self.assertEqual(m["try"], ["tools/email-production/adapter/adapter.py", "try"])
        self.assertEqual(m["try_words"], ["picture"])


class Find(unittest.TestCase):
    def test_find_lists_fixtures(self):
        code, out, _ = cli("find", "--root", str(FIX / "find-root"))
        self.assertEqual(code, 0)
        self.assertEqual(out.split(), ["components/alpha/adapter.json", "components/beta/adapter/adapter.json"])

    def test_find_in_the_repo_has_the_email_adapter_and_no_fixture(self):
        got = contract.find()
        self.assertIn("tools/email-production/adapter/adapter.json", got)
        self.assertFalse([p for p in got if "test_qb5_fixtures" in p], got)


if __name__ == "__main__":
    unittest.main()
