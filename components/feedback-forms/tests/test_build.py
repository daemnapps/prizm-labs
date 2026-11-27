#!/usr/bin/env python3
"""feedback-forms — config checks, the compiled page config, previews, the
campaign-page-kit package and the engine's event body. No network, no key;
temp folders only (the real brand configs are read, never written).

    python3 -m unittest discover -s components/feedback-forms/tests
"""
import io, json, re, shutil, subprocess, sys, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

COMP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(COMP))
import build as B  # noqa: E402

BRANDS = B.brands() or ["_TEMPLATE"]   # a fresh copy has no brand yet: the starter template stands in


class RealConfigs(unittest.TestCase):
    def test_there_are_brand_configs(self):
        self.assertTrue(BRANDS)

    def test_every_brand_config_is_sound(self):
        for b in BRANDS:
            st, qs = B.load(b)
            self.assertEqual(B.check(st, qs), [], b)

    def test_wording_cites_the_language_bank(self):
        for b in BRANDS:
            _, qs = B.load(b)
            if not qs.get("language_pass"):
                continue
            for sid, st in qs["stages"].items():
                cited = [q for q in st["questions"] if q.get("language_used")]
                self.assertTrue(cited, f"{b}/{sid}: no question cites a bank row")
                self.assertIn("language_used", st["email"], f"{b}/{sid}: the email records no bank rows")
                for q in st["questions"]:
                    for o in q.get("options_language") or []:
                        self.assertIn("language_used", o)

    def test_stage_ids_make_standard_source_ids(self):
        for b in BRANDS:
            st, _ = B.load(b)
            for s in st["stages"]:
                name = b if not b.startswith("_") else "template"
                self.assertRegex(f"survey_{name}_feedback-{s['stage']}", r"^survey_[a-z0-9-]+_[a-z0-9-]+$")

    def test_page_config_carries_no_email_copy_or_triggers(self):
        for b in BRANDS:
            st, qs = B.load(b)
            cfg = B.runtime(st, qs)
            flat = json.dumps(cfg)
            self.assertNotIn("subject", flat)
            self.assertNotIn("flow_filters", flat)
            self.assertNotIn("private_key", flat)
            self.assertEqual(set(cfg["stages"]), set(qs["stages"]))
            self.assertTrue(cfg["klaviyo"]["public_id"])
            self.assertNotIn("language_", flat)          # bank row ids stay out of the page
            self.assertNotIn('"was"', flat)


class Check(unittest.TestCase):
    def good(self):
        st = {"klaviyo": {"public_id": "P", "metric": "M"}, "form": {"link": "x?stage={stage}"},
              "stages": [{"stage": "s-one", "lane": "customer"}]}
        qs = {"brand": "b", "default_stage": "s-one", "stages": {"s-one": {
            "questions": [{"id": f"q{i}", "n": i, "type": "text", "text": "T?", "areas": ["product"], "yields": ["x"]} for i in range(5)],
            "email": {"subject": "s", "preview": "p", "body": ["b"], "button": "go"}}}}
        return st, qs

    def test_good_passes(self):
        self.assertEqual(B.check(*self.good()), [])

    def test_catches_what_breaks_a_form(self):
        st, qs = self.good()
        q = qs["stages"]["s-one"]["questions"]
        q[1]["areas"] = ["sales"]
        q[2]["type"] = "dropdown"
        q[3]["show_if"] = {"q": "nope", "in": ["x"]}
        q[4]["n"] = 0
        st["stages"].append({"stage": "Bad Stage", "lane": "vip"})
        bad = " | ".join(B.check(st, qs))
        for want in ("unknown business area 'sales'", "type must be", "show_if points at 'nope'", "number n used twice",
                     "lowercase words", "lane must be", "has no questions"):
            self.assertIn(want, bad)


class Outputs(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_previews_are_self_contained(self):
        b = BRANDS[0]
        made = B.write_previews(b, self.tmp)
        _, qs = B.load(b)
        self.assertEqual(len(made), len(qs["stages"]) + 1)
        page = (self.tmp / f"{qs['default_stage']}.html").read_text()
        self.assertNotRegex(page, r"<script[^>]+src=")          # nothing loaded from anywhere
        self.assertIn('"mode": "preview"', page)
        self.assertIn('"mode": "local-test"', (self.tmp / "_send-test.html").read_text())

    def test_cpk_package(self):
        b = BRANDS[0]
        files = B.write_cpk(b, self.tmp)
        self.assertEqual(files, ["_layouts/base-feedback.html", "assets/config.js", "assets/css/feedback.css",
                                 "assets/js/feedback-config.js", "assets/js/feedback.js", "index.html"])
        idx = (self.tmp / "index.html").read_text()
        st, _ = B.load(b)
        self.assertIn(f"permalink: /{st['form']['slug']}/", idx)
        layout = (self.tmp / "_layouts/base-feedback.html").read_text()
        self.assertIn("noindex", layout)
        self.assertIn("no-referrer", layout)
        self.assertNotIn("analytics-head", layout.replace("analytics partials", ""))
        self.assertNotRegex((self.tmp / "assets/js/feedback-config.js").read_text(), r"pk_[A-Za-z0-9]{20,}")

    def test_install_sheet(self):
        for b in BRANDS:
            md = B.install_md(b)
            st, qs = B.load(b)
            for s in st["stages"]:
                self.assertIn(s["klaviyo"]["flow_name"], md)
                self.assertIn(st["form"]["link"].replace("{stage}", s["stage"]), md)
            self.assertIn("Draft", md)

    def fixture(self):
        """A temp workspace carrying one real brand's two config files."""
        b = BRANDS[0]
        ops = self.tmp / "brands" / b / "operations"
        ops.mkdir(parents=True)
        for name in ("feedback-stages.json", "feedback-questions.json"):
            shutil.copy(B.ops(b) / name, ops / name)
        return b

    def brand_files(self):
        return sorted(str(p.relative_to(self.tmp)) for p in (self.tmp / "brands").rglob("*"))

    def test_install_files_under_runs(self):
        b = self.fixture()
        before = self.brand_files()
        p = B.write_install(b, root=self.tmp)
        self.assertEqual(p, self.tmp / "runs/feedback-forms" / b / "install/deliverable/feedback-klaviyo-install.md")
        self.assertTrue(p.is_file())
        self.assertEqual(self.brand_files(), before)

    def test_main_all_writes_nothing_under_brands(self):
        b = self.fixture()
        before = self.brand_files()
        with mock.patch.object(B, "WORKSPACE", self.tmp), redirect_stdout(io.StringIO()):
            self.assertEqual(B.main(["all", "--brand", b]), 0)
        self.assertEqual(self.brand_files(), before)
        self.assertTrue(B.install_path(b, root=self.tmp).is_file())
        self.assertTrue((self.tmp / "runs/feedback-forms" / b / "preview").is_dir())


class Docs(unittest.TestCase):
    def test_page_renders_to_runs_system(self):
        sys.path.insert(0, str(COMP / "docs"))
        import make_page as M
        self.assertEqual(M.OUT, B.WORKSPACE / "runs" / "feedback-forms" / "_system")
        m = M.mirror()
        self.assertIn("/install/deliverable/feedback-klaviyo-install.md", m)
        self.assertNotIn("operations/feedback-klaviyo-install.md", m)


@unittest.skipUnless(shutil.which("node"), "node not installed")
class Engine(unittest.TestCase):
    def test_event_body(self):
        js = r"""
const E = require(process.argv[1]);
const cfg = {brand: "b", form_version: "v1", klaviyo: {metric: "Submitted Feedback"}, known: {s: {orders: 1}},
             stages: {s: {label: "S", questions: []}}};
const qs = [{id: "a", n: 1, type: "scale", text: "How likely?", areas: ["marketing"]},
            {id: "b", n: 2, type: "choice", text: "Where?", areas: ["marketing"]},
            {id: "c", n: 3, type: "text", text: "Why?"},
            {id: "d", n: 4, type: "text", text: "Skipped?"}];
const ans = {a: {answer: 9}, b: {answer: "Other", other: "barber"}, c: {answer: "It works"}, d: {answer: ""}};
const body = E.buildEvent(cfg, "s", {email: "x@y.z", flow: "F", test: false}, ans, qs,
                          {page: "https://h/p/", anon: "anon", id: "U", time: "T"});
const vis = [E.visible({show_if: {q: "b", in: ["Other"]}}, ans), E.visible({show_if: {q: "b", not_in: ["Other"]}}, ans),
             E.visible({show_if: {q: "zz", not_in: ["No"]}}, ans)];
const p = E.readParams("?stage=S&e=a%40b.c&_kx=K&fid=F&test=1", false);
console.log(JSON.stringify({body, vis, p}));
"""
        out = subprocess.run(["node", "-e", js, str(COMP / "engine" / "feedback.js")], capture_output=True, text=True, check=True)
        d = json.loads(out.stdout)
        a = d["body"]["data"]["attributes"]
        self.assertEqual(a["metric"]["data"]["attributes"]["name"], "Submitted Feedback")
        self.assertEqual(a["profile"]["data"]["attributes"], {"email": "x@y.z"})
        self.assertEqual(a["unique_id"], "U")
        p = a["properties"]
        self.assertEqual([x["id"] for x in p["answers"]], ["a", "b", "c"])     # empty answers are not sent
        self.assertEqual((p["q_b"], p["answered"], p["known"], p["test"], p["flow_id"]), ("Other: barber", 3, {"orders": 1}, False, "F"))
        self.assertEqual(d["vis"], [True, False, False])
        self.assertEqual(d["p"], {"stage": "s", "email": "a@b.c", "kx": "K", "flow": "F", "message": None, "test": True})


class Hygiene(unittest.TestCase):
    def test_no_brand_name_in_the_engine_or_builder(self):
        names = [b for b in BRANDS]
        py = [f for f in sorted(COMP.rglob("*.py")) if (COMP / "tests") not in f.parents]
        for f in py + [COMP / "engine" / "feedback.js", COMP / "engine" / "feedback.css"]:
            text = f.read_text().lower()
            for n in names:
                self.assertNotIn(n, text, f"{n} named in {f.name}")


if __name__ == "__main__":
    unittest.main()
