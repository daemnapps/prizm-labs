"""QB-6 (content queue page): the content-queue page family holds together.

content-queue.sources.json passes serve.py's own checks (argv[0] a component's script, no runs folders, no needs) and
its /data/queue answers JSON through the kit's Sources; the page's JavaScript parses (js-parse.test.mjs exits 0 with
content-queue.html among the templates, and its script compiles on its own); check.py on the template exits 0; the
page is tab-ready (one #cq-root section, CSS under .cq, data only from /data/queue) and its requests never name a
--root. Stdlib only, no network, no Chrome, no git. Run from the repo root:
    python3 components/page-features/kit/test_qb6_content_queue.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import serve  # noqa: E402  kit/serve.py

ROOT = serve.ROOT
TPL = os.path.join(ROOT, serve.TEMPLATES)
PAGE = os.path.join(TPL, "content-queue.html")
FEATURES = os.path.join(TPL, "content-queue.features.json")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class Sources(unittest.TestCase):
    def test_declared_as_the_card_says(self):
        decl = serve.sources("content-queue")
        self.assertEqual(sorted(k for k in decl if not k.startswith("_")), ["queue", "runs", "statics", "videos"])   # QB-9, QB-11
        # QB-7 (content queue Monday): view.py also reads the email line's cards and deadlines, so both are watched
        self.assertEqual(decl["queue"], {"argv": ["components/creative-queue/view.py"], "cache_s": 300,
                                         "watch": ["runs/queue/index.json", "runs/queue-shadow/decisions/*/*.jsonl",
                                                   "runs/email-production/*/*/klaviyo/card.json",
                                                   "runs/email-production/*/deadlines.json",
                                                   "runs/queue-shadow/observations/*.json",
                                                   # the Calendar view's emails to write (2026-11-05)
                                                   "runs/marketing-calendar/*/*/slots.json",
                                                   "runs/marketing-calendar/*/*/review.json",
                                                   "runs/email-production/*/*/deliverable/email.json"],
                                         "viewer": True})   # the page server's person: who may move an email (2026-11-06)
        self.assertEqual(serve.runs_prefixes(decl), ["creative-queue/statics/"])   # QB-9: the statics pictures only
        self.assertEqual(decl["statics"], {"argv": ["components/creative-queue/statics.py", "list"], "cache_s": 300,
                                           "watch": ["runs/creative-queue/statics/*/*/done.json",
                                                     # the last good list and a failed refresh (2026-11-02): the next
                                                     # ask after a background refresh gets the new list
                                                     "runs/creative-queue/statics/last.json",
                                                     "runs/creative-queue/statics/refresh-error.json"]})
        self.assertEqual(serve.preflight(decl), [])                # no needs
        self.assertEqual(serve.family_of(PAGE), "content-queue")

    def test_serve_accepts_the_source_and_runs_only_its_component(self):
        decl = serve.sources("content-queue")
        seen = []
        src = serve.Sources(decl, root=ROOT, runner=lambda argv: seen.append(argv) or "{}")
        self.assertEqual(src.get("queue"), "{}")
        self.assertEqual(seen, [["components/creative-queue/view.py"]])
        self.assertEqual(len(src.stamp("queue")), 2)
        with self.assertRaises(serve.BadParameter):
            src.get("queue", {"root": "runs/queue"})                 # takes no parameters at all

    def test_the_real_door_answers_json_with_video_read_only(self):
        out = serve.Sources(serve.sources("content-queue"), root=ROOT).get("queue")
        d = json.loads(out)
        for k in ("owner_built", "owner_age_h", "shadow_root", "people", "stages", "rows"):
            self.assertIn(k, d)
        # QB-7 (content queue Monday): video is back, read only; emails are the email line's, read only
        for r in d["rows"]:
            if r["type"] == "video-ad":
                self.assertEqual(r["read_only"], "video", r["id"])
            if r["type"] == "email":
                self.assertEqual(r["read_only"], "email", r["id"])


class Page(unittest.TestCase):
    def test_js_parses_with_content_queue_counted(self):
        node = shutil.which("node")
        self.assertTrue(node, "node is not on PATH")
        p = subprocess.run([node, os.path.join(TPL, "js-parse.test.mjs")], cwd=ROOT, capture_output=True, text=True,
                           timeout=300)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        files = len([f for f in os.listdir(TPL) if f.endswith((".html", ".js"))])
        self.assertIn("— %d file(s)" % files, p.stdout)              # every template, content-queue.html included
        self.assertTrue(os.path.isfile(PAGE))
        # PF-15 (direct by default): one page script besides the component-owned act.js block (kit/act.js)
        one = ("const fs=require('fs'),vm=require('vm');const t=fs.readFileSync(process.argv[1],'utf8');"
               "const m=[...t.matchAll(/<script(\\s[^>]*)?>([\\s\\S]*?)<\\/script>/g)]"
               ".filter(x=>!/id=\"pf-(act|due)\"/.test(x[1]||''));"
               "if(m.length!==1)throw new Error('expected one script block, got '+m.length);"
               "new vm.Script(m[0][2],{filename:'content-queue.html'});")
        p = subprocess.run([node, "-e", one, PAGE], capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_check_py_exits_0(self):
        p = subprocess.run([sys.executable, "-B", os.path.join(ROOT, "components", "page-features", "check.py"),
                            "--features", FEATURES, PAGE], cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(json.loads(read(FEATURES))["owner"], "email_lead")

    def test_tab_ready_and_never_names_a_root(self):
        text = read(PAGE)
        self.assertEqual(len(re.findall(r'<section id="cq-root" class="cq">', text)), 1)
        body = text.split("<body", 1)[1]
        self.assertTrue(body.split(">", 1)[1].lstrip().startswith('<section id="cq-root" class="cq">'))
        self.assertTrue(body.rstrip().endswith("</section>\n</body>\n</html>"))
        css = re.findall(r"<style>([\s\S]*?)</style>", text)
        self.assertEqual(len(css), 1)
        rules = re.sub(r"/\*[\s\S]*?\*/", "", css[0])          # a comment is not a selector (its commas split nothing)
        for rule in re.findall(r"([^{}]+)\{[^{}]*\}", re.sub(r"@media[^{]*\{", "", rules)):
            for sel in rule.split(","):
                self.assertIn(".cq", sel, "CSS not under .cq: %s" % sel.strip())
        script = re.findall(r"<script>([\s\S]*?)</script>", text)[0].strip()
        self.assertTrue(script.startswith("(function () {") and script.endswith("})();"))   # one IIFE, no globals
        # data only from /data/queue; the one other call is PF-13 (direct buttons)'s POST /act to the kit,
        # made by kit/act.js's pfAct since PF-15 (direct by default)
        # plus one read-only page check, "/p/<viewer>/emails.html": does this person have their own emails page,
        # so the emails link opens editor's own (e8a4704ece, email_lead 2026-11-10); a GET of a page file, never data
        self.assertEqual(sorted(re.findall(r"fetch\(\s*\"([^\"]+)\"", script)),
                         ["/data/queue", "/data/statics", "/data/videos", "/p/"])   # QB-9, QB-11
        self.assertIn('fetch("/p/" + viewer() + "/emails.html", {cache: "no-store"})', script)
        self.assertIn('window.pfAct(body.n, body, {family: "content-queue"', script)
        self.assertNotIn("--root", script)
        self.assertNotIn("runs/queue/", script)
        self.assertIn('"python3 components/creative-queue/cq.py"', script)


if __name__ == "__main__":
    unittest.main()
