"""The feedback form's look, read from the brand's own design system — never typed by hand.

Where it looks, first found wins (both under the brand's `brand-identity/`, or the older `identity/`):
  1. design-system/tokens.json   colour tokens by name (a value, or {light, dark}), type families, radius tokens
  2. web-tokens.md               the token table (`| name | `#hex` |`) and its "As CSS custom properties" block
Each form role (ground, ink, accent, …) is matched to the token whose NAME says that role, then to one whose
usage line does. A role nothing matches keeps the engine's neutral default. The logo is the brand's own SVG.

    look_for(brand_dir) -> {"tokens": {...}, "font_body", "font_head", "logo_source", "source": "<file>"}
Brand-agnostic: no brand is named here.
"""
import json
import re
from pathlib import Path

# role -> (names that ARE this role, words in a usage line that point at it)
ROLES = {
    "ground":     (["canvas", "ground", "page", "background", "bg", "surface-bg", "base"], ["ground of every page", "page background", "background"]),
    "card":       (["surface", "card", "surface-card", "panel"], ["cards", "tiles"]),
    "ink":        (["ink", "text", "type", "text-primary", "foreground", "fg"], ["running text", "body text", "all text"]),
    "muted":      (["muted", "text-secondary", "secondary", "subtle", "caption"], ["captions", "small print", "secondary text"]),
    "line":       (["line", "border", "hairline", "rule", "divider"], ["hairline", "border"]),
    "band":       (["deep", "band", "primary", "brand", "brand-primary", "brand-band", "dark"], ["bands", "header", "hero"]),
    "band_ink":   (["ink-on-deep", "on-deep", "on-band", "on-primary", "text-inverse", "inverse"], ["text on the deep", "text on the band", "on dark"]),
    "accent":     (["accent", "highlight", "brand-accent"], ["the one accent", "highlight", "accent"]),
    "cta":        (["cta", "button", "action", "brand-cta"], ["button fill", "call-to-action", "call to action", "primary button"]),
    "cta_ink":    (["cta-ink", "on-cta", "button-ink", "on-accent", "brand-cta-ink"], ["text on a", "button text"]),
}
HEX = re.compile(r"#[0-9A-Fa-f]{3,8}\b")


def _brand_identity(brand_dir):
    for name in ("brand-identity", "identity"):
        d = Path(brand_dir) / name
        if d.is_dir():
            return d
    return None


def _value(v, mode="light"):
    if isinstance(v, dict):
        v = v.get(mode) or v.get("light") or next(iter(v.values()), None)
    return v if isinstance(v, str) and HEX.fullmatch(v.strip()) else None


def _pick(tokens):
    """tokens: [(name, hex, usage)] -> {role: hex}."""
    out, used = {}, set()
    for role, (names, words) in ROLES.items():
        hit = next((t for n in names for t in tokens if t[0].lower() == n and t[1]), None)
        if not hit:
            hit = next((t for t in tokens if t[1] and t[0] not in used and any(w in (t[2] or "").lower() for w in words)), None)
        if hit:
            out[role] = hit[1]
            used.add(hit[0])
    if "cta" not in out and "accent" in out:
        out["cta"] = out["accent"]
    if "cta_ink" not in out and "cta" in out:
        cta = next((t for t in tokens if t[1] == out["cta"]), None)
        ink = next((t for t in tokens if cta and t[0].lower() == cta[0].lower() + "-ink"), None)
        if ink:
            out["cta_ink"] = ink[1]
    if "picked" not in out and "band" in out:
        out["picked"], out["picked_ink"] = out["band"], out.get("band_ink", out.get("ground"))
    if "cta_line" not in out and "line" in out:
        out["cta_line"] = out.get("cta", out["line"])
    return out


def _from_json(path):
    d = json.loads(path.read_text())
    color = d.get("color") or {}
    toks = [(t.get("name", ""), _value(t.get("value")), t.get("usage", "")) for t in color.get("tokens") or []]
    look = {"tokens": _pick(toks)}
    fam = ((d.get("type") or {}).get("families") or {})
    body = fam.get("sans") or fam.get("body") or fam.get("text")
    head = fam.get("display") or fam.get("heading") or body
    if body:
        look["font_body"] = body
    if head:
        look["font_head"] = head
    radius = {t.get("name", ""): t.get("value") for t in (d.get("radius") or {}).get("tokens") or []}
    r = next((v for k, v in radius.items() if "button" in k or "card" in k), None) or next(iter(radius.values()), None)
    if r:
        look["tokens"]["radius"] = r
    return look


def _from_md(path):
    text = path.read_text()
    toks = []
    for m in re.finditer(r"^\|\s*\**([A-Za-z][A-Za-z0-9 _-]*?)\**\s*\|\s*`(#[0-9A-Fa-f]{3,8})`[^|]*\|\s*([^|\n]*)", text, re.M):
        if m.group(1).strip().lower() != "open":
            toks.append((m.group(1).strip().lower().replace(" ", "-"), m.group(2), m.group(3)))
    for m in re.finditer(r"--brand--color--([a-z-]+)\s*:\s*(#[0-9A-Fa-f]{3,8})\s*;\s*(/\*\s*open)?", text):
        if not m.group(3):
            toks.append((m.group(1), m.group(2), ""))
    look = {"tokens": _pick(toks)}
    for role, key in (("display", "font_head"), ("body", "font_body")):
        m = re.search(r"--brand--font--" + role + r"\s*:\s*([^;]+);", text)
        if m and "open" not in m.group(1):
            look[key] = m.group(1).strip()
    return look


def logo(identity):
    svgs = sorted(identity.glob("*logo*.svg")) or sorted(identity.glob("*.svg"))
    return svgs[0] if svgs else None


def look_for(brand_dir, root=None):
    """The look read off the brand's design system; {} when it has none yet."""
    ident = _brand_identity(brand_dir)
    if not ident:
        return {}
    look = {}
    for rel, reader in (("design-system/tokens.json", _from_json), ("web-tokens.md", _from_md)):
        p = ident / rel
        if p.is_file():
            try:
                found = reader(p)
            except (OSError, ValueError):
                continue
            if found.get("tokens"):
                look = found
                look["source"] = str(p.relative_to(root)) if root and p.is_relative_to(root) else str(p)
                break
    lg = logo(ident)
    if lg:
        look["logo_source"] = str(lg.relative_to(root)) if root and lg.is_relative_to(root) else str(lg)
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
