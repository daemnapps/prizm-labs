#!/usr/bin/env python3
"""The bank tools write PROPOSALS under runs/, never into brands/ — and the
research gatherer's apply step is what writes them (O5: `brands/` is
read-only to machines; the gatherer is the one carved-out writer).
Fixture trees only: no model call, no network, no key.

    python3 -m unittest discover -s tests          # from tools/language-layer
"""
import contextlib, hashlib, io, json, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_tools import COMP, E, Roots, bank, tool  # noqa: E402

from language_layer import proposal as P  # noqa: E402


def gather_apply(prop, root):
    """Apply through the research gatherer's CLI (`gather.py apply`) — its
    contract surface, the same way the tools hand off. Returns applied.json."""
    rc = quiet(P.hand_off, prop, root)
    assert rc == 0, f"gather.py apply exited {rc}"
    return json.loads((Path(prop).parent / "applied.json").read_text())


def snapshot(root):
    """Every file under brands/, by content — to prove a tool wrote nothing there."""
    b = Path(root) / "brands"
    return {p.relative_to(root).as_posix(): hashlib.sha1(p.read_bytes()).hexdigest()
            for p in sorted(b.rglob("*")) if p.is_file()}


class Tree:
    """A fixture bank, with the engine's root probe and workspace on it."""
    def __init__(self, rows=None, files=None):
        self.rows, self.files = rows, files or {}

    def __enter__(self):
        self.t = tempfile.TemporaryDirectory()
        self.root = Path(self.t.name)
        self.lang = bank(self.t.name, rows=self.rows)
        for name, rows in self.files.items():
            (self.lang / name).parent.mkdir(parents=True, exist_ok=True)
            (self.lang / name).write_text(json.dumps({"entries": rows}, indent=1) + "\n")
        self.saved = (list(E._ROOTS), E.WORKSPACE)
        E.configure(roots=[lambda: self.root], workspace=self.root)
        return self

    def __exit__(self, *a):
        E.configure(roots=self.saved[0], workspace=self.saved[1])
        self.t.cleanup()

    def entries(self, name="prospects.json"):
        return json.loads((self.lang / name).read_text())["entries"]


def quiet(fn, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        out = fn(*a)
    sys.stdout.flush()
    return out


class LabelApply(unittest.TestCase):
    def test_label_writes_a_proposal_and_the_gatherer_applies_it(self):
        m = tool("label")
        fake = lambda rows, brand, model, batch=20: {  # noqa: E731
            r["id"]: {"id": r["id"], "awareness": "problem-aware", "sophistication": "none",
                      "lane_words": "prospect", "why": "fixture"} for r in rows}
        real, m.label = m.label, fake
        try:
            with Tree() as t:
                before = snapshot(t.root)
                rc = quiet(m.main, ["apply", "--brand", "fx", "--propose-only"])
                self.assertEqual(rc, 0)
                self.assertEqual(snapshot(t.root), before, "label.py wrote into brands/")
                props = sorted((t.root / "runs" / "language-layer" / "fx").glob("label-*/proposal.json"))
                self.assertEqual(len(props), 1)
                prop = json.loads(props[0].read_text())
                self.assertEqual(prop["kind"], "language-bank-proposal")
                self.assertEqual(len(prop["rows"]), 2)
                self.assertTrue((props[0].parent / "proposal.md").is_file())
                rep = gather_apply(props[0], t.root)
                self.assertEqual(rep["applied"], 2)
                got = t.entries()
                self.assertEqual({e["awareness"]["level"] for e in got}, {"problem-aware"})
                self.assertEqual({e["awareness"]["model"] for e in got}, {m.MODEL})
                self.assertTrue((props[0].parent / "applied.json").is_file())
                # a new run starts a new folder; the applied one is never resumed
                quiet(m.main, ["apply", "--brand", "fx", "--propose-only"])
                self.assertEqual(len(list((t.root / "runs" / "language-layer" / "fx").glob("label-*"))), 2)
        finally:
            m.label = real

    def test_one_command_labels_and_applies_through_the_gatherer(self):
        m = tool("label")
        rows = [dict(id="language_fx_a1_lead_0001", text="need", source=dict(
            name="Instagram ad comment", type="comment", ref="https://www.instagram.com/p/x/c/1"),
            origin="external")]
        with Tree(files={"leads.json": rows}) as t:
            rc = quiet(m.main, ["origin", "--brand", "fx", "--where", "ad comment"])
            self.assertEqual(rc, 0)
            self.assertEqual(t.entries("leads.json")[0]["origin"], "internal")

    def test_default_model_is_the_registry_id(self):
        m = tool("label")
        reg = json.loads((COMP.parent.parent / "components" / "models" / "models.json").read_text())["models"]
        self.assertIn(m.MODEL, {x["id"] for x in reg})


class OriginRule(unittest.TestCase):
    def test_any_ad_comment_is_internal(self):
        m = tool("label")
        for name in ("Instagram ad comment", "Facebook ad comment — Evergreen", "ad comment — VSL"):
            self.assertEqual(m.origin_of({"source": {"type": "comment", "name": name,
                                                      "ref": "https://www.facebook.com/reel/1"}}, "fx"),
                             "internal", name)
        self.assertEqual(m.origin_of({"source": {"type": "comment", "name": "creator post",
                                                  "ref": "https://www.tiktok.com/@other/video/1"}}, "fx"),
                         "external")


class RenameAndSources(unittest.TestCase):
    def test_rename_is_a_proposal_until_applied(self):
        with Tree() as t:
            before = snapshot(t.root)
            rc = quiet(tool("rename_ids").main, ["--brand", "fx", "--propose-only"])
            self.assertEqual(rc, 0)
            self.assertEqual(snapshot(t.root), before)
            prop = next((t.root / "runs" / "language-layer" / "fx").glob("rename-*/proposal.json"))
            gather_apply(prop, t.root)
            self.assertEqual(sorted(e["id"] for e in t.entries()),
                             ["language_fx_a1_prospect_0001", "language_fx_a1_prospect_0002"])

    def test_sources_and_registry_are_a_proposal_until_applied(self):
        with Tree() as t:
            before = snapshot(t.root)
            quiet(tool("map_sources").main, ["--brand", "fx", "--propose-only"])
            self.assertEqual(snapshot(t.root), before)
            prop = next((t.root / "runs" / "language-layer" / "fx").glob("sources-*/proposal.json"))
            gather_apply(prop, t.root)
            reg = json.loads((t.root / "brands" / "fx" / "core-avatars" / "language-sources.json").read_text())
            self.assertEqual({s["id"] for s in reg["sources"]},
                             {"survey_fx_fx", "post_tiktok_some-creator_7312345678901234567"})
            self.assertEqual({e["source"]["id"] for e in t.entries()},
                             {"survey_fx_fx", "post_tiktok_some-creator_7312345678901234567"})


class KeywordCta(unittest.TestCase):
    def test_short_repeated_lead_comments_are_tagged(self):
        src = dict(name="Facebook ad comment — ad", type="comment", id="post_facebook_fx_1",
                   ref="https://www.facebook.com/reel/1")
        leads = [dict(id=f"language_fx_a1_lead_000{i}", text=t, use="product-request", source=dict(src))
                 for i, t in enumerate(["Recipe", "recipe!", "Recipe please", "where do I buy this long sentence here"], 1)]
        leads.append(dict(id="language_fx_a1_lead_0009", text="link?", source=dict(src, id="post_facebook_fx_2")))
        with Tree(files={"leads.json": leads}) as t:
            m = tool("keyword_cta")
            hits = m.find("fx")
            self.assertEqual(sorted(e["id"] for _, _, e, _ in hits),
                             ["language_fx_a1_lead_0001", "language_fx_a1_lead_0002"])
            quiet(m.main, ["--brand", "fx"])
            got = {e["id"]: e.get("use") for e in t.entries("leads.json")}
            self.assertEqual(got["language_fx_a1_lead_0001"], ["product-request", "keyword-cta"])
            self.assertEqual(got["language_fx_a1_lead_0003"], "product-request")   # said once: not a repeat
            self.assertIsNone(got["language_fx_a1_lead_0009"])                     # once per source


if __name__ == "__main__":
    unittest.main()
