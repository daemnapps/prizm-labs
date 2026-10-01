#!/usr/bin/env python3
"""What a brand has on file that touches an idea — read at run time, from
`brands/<brand>/`, and from nowhere else.

    brand_context.py <brand> [avatar]      print what would be read, and what is missing

Nothing here knows any brand. It reads the same files every chain reads —
the position, the story, the avatar's card, the offer bank, the angles, the
objections — and asks the shared language layer
(`components/language-layer`) for the customer's own words. A file that is not
there is SAID to be not there: the prompt is told, the dry run prints it, and
the brief is told it may not lean on it.

An avatar, a sub-avatar, an angle and an offer are LOOKED UP. One that is not
on file is refused, with the ones that are on file named.
"""
import json
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
import paths as P                                             # noqa: E402

CAP = 40_000                                                   # chars of any one file a prompt is shown

# Which kinds of customer words the round-out and the brief look for. This is
# this chain's own definition (the language layer ships no map of its own).
STAGE_USE = {
    "round-out": ["problem-language", "self-descriptor", "identity", "tried-and-failed",
                  "why-bought", "objection", "result-language", "post-use-feeling"],
}


class NotOnFile(Exception):
    """Something asked for by name that the brand's files do not hold."""


def brand_dir(brand):
    return P.BRANDS / brand


def _read(path, cap=CAP):
    text = path.read_text(errors="replace").strip()
    if len(text) > cap:
        return text[:cap] + f"\n\n(shown: the first {cap:,} of {len(text):,} characters of {P.rel(path)})"
    return text


def _file(brand, *parts, old=None):
    """(text, note) — the file's words, or a plain statement that it is not on file.
    `old` is the path the file had before the v6 folder names; read when the new one is absent."""
    f = brand_dir(brand).joinpath(*parts)
    if f.is_file():
        return _read(f), None
    if old and brand_dir(brand).joinpath(*old).is_file():
        return _read(brand_dir(brand).joinpath(*old)), None
    return f"(not on file: {P.rel(f)} — nothing may be claimed from it)", P.rel(f)


# ------------------------------------------------------------------ looked up, never coined

def avatars(brand):
    """Every core avatar the brand has: a folder under core-avatars/ holding a profile.md."""
    root = brand_dir(brand) / "core-avatars"
    if not root.is_dir():
        return []
    return sorted(d.name for d in root.iterdir() if d.is_dir() and (d / "profile.md").is_file())


def subs(brand, avatar):
    d = brand_dir(brand) / "core-avatars" / avatar / "sub-avatars"
    out = {}
    for f in sorted(d.glob("*.md")) if d.is_dir() else []:
        out[re.sub(r"^sub-\d+-", "", f.stem)] = f
    return out


def angles(brand):
    f = brand_dir(brand) / "strategy" / "angles.json"
    if not f.is_file():
        return []
    try:
        doc = json.loads(f.read_text())
    except ValueError:
        return []
    rows = doc.get("angles") if isinstance(doc, dict) else doc
    return [r for r in (rows or []) if isinstance(r, dict) and r.get("id")]


def offer_bank(brand):
    f = brand_dir(brand) / "offers" / "offer-bank.md"
    return f.read_text(errors="replace") if f.is_file() else ""


def offer_keys(brand):
    return re.findall(r"^## ([a-z0-9][a-z0-9-]*) —", offer_bank(brand), re.M)


def check_avatar(brand, avatar):
    have = avatars(brand)
    if avatar not in have:
        raise NotOnFile(f"`{avatar}` is not an avatar this brand has on file — the ones there are: "
                        f"{', '.join(have) or '(no core-avatars folder)'}")
    return avatar


def check_sub(brand, avatar, sub):
    have = subs(brand, avatar)
    key = re.sub(r"^sub-\d+-", "", sub or "")
    if key not in have:
        raise NotOnFile(f"`{sub}` is not a sub-avatar under `{avatar}` — the ones there are: "
                        f"{', '.join(sorted(have)) or '(none)'}")
    return key


def check_angle(brand, angle):
    rows = angles(brand)
    for r in rows:
        if r["id"] == angle:
            return r
    raise NotOnFile(f"`{angle}` is not an angle in this brand's strategy/angles.json — the ones there are: "
                    f"{', '.join(r['id'] for r in rows) or '(no angles on file)'}")


def check_offer(brand, offer):
    have = offer_keys(brand)
    if offer not in have:
        raise NotOnFile(f"`{offer}` is not an offer in this brand's offer bank — the ones there are: "
                        f"{', '.join(have) or '(no offer bank on file)'}")
    return offer


# ------------------------------------------------------------------ what a prompt is shown

def avatar_menu(brand):
    """Every avatar with the opening of its card — what the round-out chooses
    from when nobody pinned one."""
    out = []
    for a in avatars(brand):
        text = (brand_dir(brand) / "core-avatars" / a / "profile.md").read_text(errors="replace")
        body = re.sub(r"^---.*?\n---", "", text, flags=re.S)
        body = re.sub(r"^#.*$", "", body, flags=re.M)
        gist = re.sub(r"\s+", " ", body).strip()[:320]
        out.append(f"- `{a}` — {gist}")
    return "\n".join(out) or "(this brand has no avatars on file)"


def avatar_card(brand, avatar, sub=None):
    if not avatar:
        return "(no avatar chosen yet — see the avatar menu)"
    text, _ = _file(brand, "core-avatars", avatar, "profile.md")
    out = [f"--- {avatar} ---", text]
    if sub:
        f = subs(brand, avatar).get(sub)
        if f:
            out += [f"--- sub-avatar: {sub} ---", _read(f)]
    return "\n\n".join(out)


def angle_menu(brand, avatar=None):
    rows = [r for r in angles(brand) if r.get("status", "active") not in ("removed", "retired")]
    if avatar:
        rows = [r for r in rows if r.get("avatar") in (avatar, None, "", "all")] or rows
    if not rows:
        return "(no angles on file for this brand)"
    return "\n".join(f"- `{r['id']}` — {r.get('name') or ''}: {re.sub(chr(10), ' ', str(r.get('what') or ''))[:260]}"
                     for r in rows)


def customer_words(brand, avatar, limit=40):
    """The customer's own words, asked of the shared language layer — the same
    component every sibling chain reads them through."""
    try:
        if str(P.LANGUAGE) not in sys.path:
            sys.path.append(str(P.LANGUAGE))
        from language_layer import engine
        text = engine.for_stage(brand, "round-out", avatar=avatar or None, limit=limit, root=P.REPO,
                                stage_use=STAGE_USE, widen="once", title="The customer's own words")
        if re.search(r"_0 rows", text or "") or not (text or "").strip():
            return "(no customer language on file for this avatar — no line may be presented as a customer's words)"
        return text
    except Exception as e:                                     # the layer is called, never depended on to exist
        return f"(the language layer could not be read: {type(e).__name__} — no line may be presented as a customer's words)"


def gather(brand, avatar=None, sub=None):
    """Every block a prompt binds, plus the list of what is not on file."""
    missing = []
    blocks = {}
    # story and position live in brand-identity/ (v6); a brand not moved yet has them at the top
    for name, parts, old in (("position", ("brand-identity", "position.md"), ("position.md",)),
                             ("story", ("brand-identity", "story.md"), ("story.md",)),
                             ("offers", ("offers", "offer-bank.md"), None),
                             ("objections", ("core-avatars", "objection-bank.md"), None)):
        blocks[name], miss = _file(brand, *parts, old=old)
        if miss:
            missing.append(miss)
    blocks["avatar_menu"] = avatar_menu(brand)
    blocks["avatar_card"] = avatar_card(brand, avatar, sub)
    blocks["angles"] = angle_menu(brand, avatar)
    blocks["customer_language"] = customer_words(brand, avatar)
    return blocks, missing


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    b, m = gather(sys.argv[1], *(sys.argv[2:3]))
    for k, v in b.items():
        print(f"{k:<18} {len(v):>7,} chars")
    for x in m:
        print("not on file:", x)
