"""This tool's questions to the element library (components/elements).

    import email_elements as EE
    EE.type_problem(brand, "founder-note")   # None, or why that email type is refused
    EE.layout("simple")                      # the template/email row, or Unknown
    EE.picked(brand, type, layout)           # what run.json records

A calendar send's `type` IS an email format. It is a real one when the element
library lists it (`format/email`) OR the brand's own `email-sms/email-types.json`
does — a brand may add types of its own. Unknown in both is refused with the
real ids named, never forced into the nearest one.
"""
import json
import sys
from pathlib import Path

if "paths" not in sys.modules:             # a caller may have taken this folder OFF the path on purpose
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # (its email.py shadows Python's `email`)
from paths import WORKSPACE, component                        # noqa: E402

sys.path.insert(0, str(component("elements", "machine")))
import elements as E                                          # noqa: E402

Unknown = E.Unknown


def brand_types(brand, workspace=None):
    f = Path(workspace or WORKSPACE) / "brands" / brand / "email-sms" / "email-types.json"
    try:
        return [t["key"] for t in json.loads(f.read_text()).get("types", []) if t.get("key")]
    except (OSError, ValueError):
        return []


def type_source(brand, type_, workspace=None):
    """'library', 'brand', or None."""
    if not type_:
        return None
    try:
        E.get("format", "email", type_)
        return "library"
    except Unknown:
        pass
    return "brand" if type_ in brand_types(brand, workspace) else None


def type_problem(brand, type_, workspace=None):
    if type_source(brand, type_, workspace):
        return None
    lib = [r["id"] for r in E.rows("format", "email")]
    own = [k for k in brand_types(brand, workspace) if k not in lib]
    return (f"`{type_}` is not an email type — not in the element library (format/email) "
            f"and not in brands/{brand}/email-sms/email-types.json. Real ones: " + ", ".join(lib)
            + (f" · this brand's own: {', '.join(own)}" if own else ""))


def layout(id_="simple"):
    return E.get("template", "email", id_)


def picked(brand, type_, layout_id=None, workspace=None):
    out = {}
    if type_:
        out["format/email"] = {"id": type_, "from": type_source(brand, type_, workspace) or "UNKNOWN"}
    if layout_id:
        out["template/email"] = {"id": layout_id, "from": "library"}
    return out
