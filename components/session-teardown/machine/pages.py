"""The page under test, read from the page list manifest (components/naming/pages.json) — never its internals."""
import json
from urllib.parse import urlparse

from run_kit import paths


def load():
    return json.loads(paths.component("naming", "pages.json").read_text())


def page(page_id, data=None):
    data = data or load()
    p = (data.get("pages") or {}).get(page_id)
    if not p:
        raise KeyError("page %s is not in the page list" % page_id)
    ctl = [v for v in p.get("versions", []) if v.get("control")]
    if len(ctl) != 1:
        raise ValueError("page %s has %d control versions; it needs exactly one" % (page_id, len(ctl)))
    c = ctl[0]
    return {"page_id": page_id, "brand": p["brand"], "place": p["place"], "step": p["step"], "kind": p.get("kind"),
            "url": p["url"], "product": p.get("product"), "avatar": p.get("avatar"), "angle": p.get("angle"),
            "control": {"version": c["version"], "path": urlparse(c["url"]).path, "offer": str(c.get("offer") or ""),
                        "url": c["url"]},
            "running_test": any((t.get("state") or t.get("status")) == "live" for t in p.get("tests", []))}
