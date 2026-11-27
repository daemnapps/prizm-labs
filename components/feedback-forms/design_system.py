"""The feedback form's look, read from the brand's design system by the standard names — never guessed.

First choice is the brand's design system file, `email-sms/design-system.json` — the same file the email design
engine renders every email with (components/email-production/design/), so the form looks like the email that links
to it. Its keys are the same for every brand: tokens canvas · surface · ink · muted · line · band · band_ink · accent ·
button · button_ink, fonts display/body with their fallbacks, and the logo. Each form role reads exactly one key.

Without that file the fallback standard is the web token table every brand keeps (`brand-identity/web-tokens.md`, the same table
components/page-production reads): `| token-name | `value` | where it came from |`. Each form role reads exactly one
standard token. A token the brand has not declared is NOT inferred from other names or colours: the form keeps the
engine's neutral value for that role and the role is listed in `missing`, so a person adds the token (measured off
the brand's live site) instead of anyone assuming it.

A `design-system/tokens.json` counts only when it carries a `"web_tokens"` map in the same standard names.

    look_for(brand_dir, root) -> {"tokens": {...}, "font_body", "font_head", "head_transform", "logo_source",
                                  "source": "<file>", "missing": ["brand-cta", ...]}
Brand-agnostic: no brand is named here.
"""
import json
import re
from pathlib import Path

# form role -> the standard token it reads (in order; the first one the brand declares wins)
ROLE_TOKENS = {
    "ground":     ("surface-alt", "surface-bg"),     # the page behind the form: the brand's tinted ground if it has one
    "card":       ("surface-card",),
    "ink":        ("text-primary",),
    "muted":      ("text-secondary",),
    "line":       ("border",),
    "band":       ("brand-band", "brand-primary-dark"),
    "band_ink":   ("text-inverse",),
    "accent":     ("brand-accent",),
    "cta":        ("brand-cta", "brand-primary"),
    "cta_ink":    ("brand-cta-ink",),
    "cta_line":   ("brand-cta-border", "brand-cta"),
    "picked":     ("brand-band", "brand-primary-dark"),
    "picked_ink": ("text-inverse",),
    "radius":     ("button-radius", "radius"),
    "chip_radius": ("button-radius", "radius"),
}
TEXT_TOKENS = {"font_head": ("font-heading",), "font_body": ("font-body",), "head_transform": ("heading-case",)}
REQUIRED = ("surface-bg", "text-primary", "brand-band", "text-inverse", "brand-cta", "brand-cta-ink", "font-heading", "font-body")
ROW = re.compile(r"^\|\s*([a-z][a-z0-9-]+)\s*\|\s*`([^`]+)`", re.M)


def _identity(brand_dir):
    for name in ("brand-identity", "identity"):
        d = Path(brand_dir) / name
        if d.is_dir():
            return d
    return None


def standard_tokens(ident):
    """{token-name: value} from web-tokens.md (or tokens.json › web_tokens), and the file it came from."""
    tj = ident / "design-system" / "tokens.json"
    if tj.is_file():
        try:
            wt = json.loads(tj.read_text()).get("web_tokens")
            if isinstance(wt, dict) and wt:
                return {k: str(v) for k, v in wt.items()}, tj
        except (OSError, ValueError):
            pass
    md = ident / "web-tokens.md"
    if md.is_file():
        found = {m.group(1): m.group(2).strip() for m in ROW.finditer(md.read_text())}
        if found:
            return found, md
    return {}, None


def logo(ident, on_dark=True):
    svgs = sorted(ident.glob("*logo*.svg"))
    light = [p for p in svgs if re.search(r"white|light|cream|-dt\b|_light", p.stem, re.I)]
    pick = (light or svgs) if on_dark else ([p for p in svgs if p not in light] or svgs)
    return pick[0] if pick else None


def _rel(p, root):
    try:
        return str(p.relative_to(root)) if root else str(p)
    except ValueError:
        return str(p)


DS_ROLES = {"ground": "canvas", "card": "surface", "ink": "ink", "muted": "muted", "line": "line", "band": "band",
            "band_ink": "band_ink", "accent": "accent", "cta": "button", "cta_ink": "button_ink", "cta_line": "button",
            "picked": "band", "picked_ink": "band_ink"}
DS_REQUIRED = ("canvas", "ink", "band", "band_ink", "button", "button_ink")


def from_design_system(brand_dir, root=None):
    """The look from email-sms/design-system.json, or None when the brand has none."""
    p = Path(brand_dir) / "email-sms" / "design-system.json"
    if not p.is_file():
        return None
    try:
        d = json.loads(p.read_text())
    except (OSError, ValueError):
        return None
    t = d.get("tokens") or {}
    look = {"tokens": {role: t[key] for role, key in DS_ROLES.items() if t.get(key)}}
    if t.get("radius"):
        look["tokens"]["radius"] = look["tokens"]["chip_radius"] = t["radius"]
    fonts = d.get("fonts") or {}
    for key, face in (("font_head", "display"), ("font_body", "body")):
        f = fonts.get(face) or {}
        if f.get("family"):
            look[key] = f"'{f['family']}', " + (f.get("fallback") or "sans-serif")
    lg = (d.get("logo") or {}).get("file") or ""
    if lg.startswith("brand:"):
        lp = Path(brand_dir) / lg[len("brand:"):]
        if lp.is_file():
            look["logo_source"] = _rel(lp, root)
    if (d.get("logo") or {}).get("alt"):
        look["logo_alt"] = d["logo"]["alt"]
    look["missing"] = [k for k in DS_REQUIRED if not t.get(k)]
    look["source"] = _rel(p, root)
    return look


def look_for(brand_dir, root=None):
    found = from_design_system(brand_dir, root)
    if found:
        return found
    ident = _identity(brand_dir)
    if not ident:
        return {"missing": list(REQUIRED)}
    std, src = standard_tokens(ident)
    look = {"tokens": {}}
    for role, names in ROLE_TOKENS.items():
        v = next((std[n] for n in names if std.get(n)), None)
        if v:
            look["tokens"][role] = v
    for key, names in TEXT_TOKENS.items():
        v = next((std[n] for n in names if std.get(n)), None)
        if v and not v.startswith("http"):
            look[key] = v if key != "font_head" or "," in v else v + ", system-ui, sans-serif"
            if key == "font_body" and "," not in v:
                look[key] = v + ", system-ui, sans-serif"
    look["missing"] = [n for n in REQUIRED if not std.get(n)]
    if src:
        look["source"] = _rel(src, root)
    lg = logo(ident, on_dark=bool(look["tokens"].get("band")))
    if lg:
        look["logo_source"] = _rel(lg, root)
    return look


def resolve(questions, brand_dir, root=None):
    """questions["look"] with the design system filled in. Values typed in the brand's file win."""
    typed = dict(questions.get("look") or {})
    if typed.get("tokens") and typed.get("from") != "design-system":
        return typed
    ds = look_for(brand_dir, root)
    merged = {**ds, **{k: v for k, v in typed.items() if k not in ("from", "note", "tokens")}}
    merged["tokens"] = {**ds.get("tokens", {}), **(typed.get("tokens") or {})}
    return merged
