"""My Feeds export — the rules that must never quietly break.

    python3 -m pytest components/swipe-organic/test_feedsexport.py
"""
import ast, os, re, subprocess, sys

# Our own names and the competitors the public page names are private: the guard
# reads them from the environment (packs.py). Stand-ins for the test, reloaded so
# a guard imported earlier in the session picks them up.
os.environ.setdefault("PRIZM_OUR_NAMES", "brand-a|brand-b|ourcompany")
os.environ.setdefault("PRIZM_SHOWN_COMPETITORS", r"competitor\s?one|competitor\s?two")


def _fresh():
    import importlib
    import packs, feedsexport
    importlib.reload(packs)
    return packs, importlib.reload(feedsexport)
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = (HERE / "feedsexport.py").read_text()


def test_never_imports_apify():
    """The export reads records only. It must not import apify.py — not
    directly, and not through anything it imports at load."""
    tree = ast.parse(SRC)
    names = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    names |= {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert not any(re.match(r"apify", n or "") for n in names)
    code = ("import sys; sys.path.insert(0, %r); import feedsexport; "
            "assert not any(m == 'apify' or m.startswith('apify.') for m in sys.modules), "
            "[m for m in sys.modules if 'apify' in m]" % str(HERE))
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=str(HERE))
    assert r.returncode == 0, r.stderr


def test_scan_refuses_ours_and_never_public_things():
    sys.path.insert(0, str(HERE))
    _, F = _fresh()
    for bad in ("brand-b--avatar-one", "brand-a--avatar-four", "ourcompany", "/Users/someone", "act_123456", "meta_page_id",
                "app.adplexity.io/storage/x.jpg", "prompts-as-sent", "damon--saves",
                "customer-base.md", "x.cloudfront.net/face.png", "APIFY_TOKEN"):
        assert F.dirty(bad), bad
    assert F.dirty("ad 123456789012345", {"123456789012345"})
    for ok in ("Competitor One", "Competitor Two", "Competitor Three", "TikTok · 1.2M views"):
        assert not F.dirty(ok), ok
    # the owner, 1 Oct 2026: our brand NAMES show on My Feeds (he wants to see
    # them). Read from brands/, never typed into the exporter.
    for ok in ("Brand B", "Brand A", "a Brand B customer"):
        assert not F.dirty(ok), ok
    assert "brand-b" in F.OUR_BRANDS and "brand-a" in F.OUR_BRANDS


def test_export_writes_no_brand_keyed_ids():
    sys.path.insert(0, str(HERE))
    import feedsexport as F
    assert F.public_id("brand-b--avatar-one") == "avatar-one"
    assert F.public_id("damon--my-saves") == "my-saves"
    assert not F.dirty(F.public_id("damon--saves"))


def test_guard_allows_public_competitors_only_when_asked(tmp_path):
    sys.path.insert(0, str(HERE))
    packs, _ = _fresh()
    (tmp_path / "a.json").write_text('{"brand": "Competitor One"}')
    assert packs.guard(tmp_path)                          # packs still name nobody
    assert not packs.guard(tmp_path, allow_competitors=True)
    (tmp_path / "b.json").write_text('{"brand": "brand-b"}')
    assert packs.guard(tmp_path, allow_competitors=True)  # our own names: always refused
