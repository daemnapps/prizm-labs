"""Brand context for one run — read ONLY from brands/<brand>/ (workspace rule 7,
components rule 9). Every file is optional: a brand that lacks one gets
"(not on file for this brand)" in the prompt, and the run records which files
it read, so a missing file is visible rather than silent.

Nothing here names a brand. The avatar comes from the teardown's own audience
read (stage 1b), never a default.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

MISSING = "(not on file for this brand)"
LEVELS = ("most-aware", "product-aware", "solution-aware", "problem-aware", "unaware")
# What a variation's new lines draw on, per language-layer stage (the copywriter's stage map, its public
# `language.for_stage`): hooks for new openings, stickers and captions; injection for the swapped-in problem words;
# spice for the room's own register.
LANGUAGE_STAGES = (("hooks", 25), ("injection", 20), ("spice", 15))
# the copywriter's language door, in the checkout this file sits in — found, never by counting folders
_SHIM = next((d / "components" / "copywriter" / "machine" for d in Path(__file__).resolve().parents
              if (d / "components" / "copywriter" / "machine" / "language.py").is_file()), None)


def _folder(brand, avatar):
    """The avatar's folder as the brand keeps it, from a profile id, a new name or an old name (naming/PEOPLE.md)."""
    try:
        import importlib.util
        f = next(d / "naming" / "people.py" for d in Path(__file__).resolve().parents if d.name == "components")
        spec = importlib.util.spec_from_file_location("naming_people", f)
        people = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(people)
        return people.folders(brand, avatar)[0] or avatar
    except Exception:                                  # noqa: BLE001  without the door the name stands as given
        return avatar


def level_of(text):
    """A doctrine awareness id out of a slot's value ("`problem-aware` — …"), or None."""
    t = str(text or "").strip().strip("`").lower()
    t = t.split()[0].strip("`.,;:") if t else ""
    return t if t in LEVELS else None


def who():
    """creative-strategist `machine/who.py` (its public surface): the one read of who an ad is for, loaded once by path."""
    import importlib.util
    name = "creative_strategist_who"
    if name not in sys.modules:
        was = list(sys.path)
        f = next(d / "components/creative-strategist/machine/who.py" for d in Path(__file__).resolve().parents if (d / "components" / "creative-strategist").is_dir())
        spec = importlib.util.spec_from_file_location(name, str(f))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        sys.path[:] = was + [x for x in sys.path if x not in was]     # appended: this machine's own modules keep every name
        sys.modules[name] = m
    return sys.modules[name]


def who_args(brand, avatar, sub=None, demographic=None, what=None):
    """(brand, avatar, sub, demographic, what) ready for who.block / who.stamp, or None when the avatar is not on file.
    A sub-avatar that is not on file is said, and the step is written to the whole avatar."""
    H = who()
    if not (brand and avatar) or not (H.avatar_dir(brand, avatar) / "profile.md").is_file():
        return None
    s = re.split(r"[\s,(]", str(sub or "").strip().strip("`"))[0]
    if s.lower() in ("none", "core", "null", "-"):
        s = ""
    try:
        H.resolve(brand, avatar, s)
    except SystemExit as e:
        print(f"  ! {e}: written to the whole avatar", file=sys.stderr)
        s = ""
    return brand, avatar, s, demographic or None, {k: v for k, v in (what or {}).items() if v}


def who_text(args):
    """who.block with no prompt slot in it, or ""."""
    return re.sub(r"\{([a-z_]+)\}", r"(\1)", who().block(*args)) if args else ""


def aim_of(rec):
    """(sub, demographic, what) a parent run or an ask carries: its `aim`, else its own keys (an ask's `strategy`, its
    `sub_avatar`; a teardown run's 1b read). Nothing is filled in."""
    rec = rec if isinstance(rec, dict) else {}
    a, s = rec.get("aim") or {}, rec.get("strategy") or {}
    aud = rec.get("audience") if isinstance(rec.get("audience"), dict) else {}
    what = {k: a.get(k) or s.get(k) for k in ("desire", "awareness", "stage", "leads_with", "doubt", "claim")}
    lv = re.search(r"\b(%s)\b" % "|".join(LEVELS), str(what["awareness"] or "").lower())
    what["awareness"] = lv.group(1) if lv else None
    return (a.get("sub") or rec.get("sub_avatar") or aud.get("_sub_avatar"), a.get("demographic") or rec.get("demographic"),
            {k: v for k, v in what.items() if v})


def _read(p, limit=None):
    p = Path(p)
    if not p.is_file():
        return None
    t = p.read_text(errors="replace")
    return t if not limit or len(t) <= limit else t[:limit] + f"\n… [cut at {limit:,} of {len(t):,} characters — full file: {p}]"


def _json(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


class BrandContext:
    def __init__(self, repo, brand, avatar=None, awareness=None):
        self.repo, self.brand, self.avatar = Path(repo), brand, avatar
        self.awareness = level_of(awareness)
        self.sub, self.demographic, self.what = None, None, {}     # set by speak_to()
        sys.path.append(str(self.repo / "components" / "brandpath"))
        import brandpath as BP  # noqa: E402
        self.bp, self.brands = BP, self.repo / "brands"
        self.home = BP.brand_root(brand, root=self.brands)
        self.read_files = []

    def rel(self, p):
        return str(Path(p).relative_to(self.repo))

    def file(self, rel, limit=None):
        # today's spelling of a brand file, resolved to where the folder plan
        # keeps it now (identity-anchors.md -> brand-identity/identity-anchors.md);
        # a path the plan does not know stays brands/<brand>/<rel>
        sys.path.append(str(self.repo / "components" / "brandpath"))
        import brandpath as BP  # noqa: E402
        p = BP.resolve_rel(self.brand, rel, root=self.repo / "brands")
        t = _read(p, limit)
        if t is not None:
            self.read_files.append(self.rel(p))
        return t

    def product_rel(self, name, default):
        """`products/<catalog id>.md` (or `<id>/product.md`) for any name of a product, relative to the
        brand folder; `default` when the brand has no file for it. One product name (2026-11-19)."""
        naming = str(Path(__file__).resolve().parents[2] / "naming")   # the sibling component, beside this code
        if naming not in sys.path:
            sys.path.append(naming)
        import names  # noqa: E402
        f = names.product_file(self.brand, name, root=self.repo)
        return str(f.relative_to(self.home)) if f and f.is_relative_to(self.home) else default

    def speak_to(self, sub=None, demographic=None, what=None):
        """Who the variations speak to (the parent run's own), for `avatars()`. -> who.stamp's answer, or {}."""
        self.sub, self.demographic, self.what = sub, demographic, dict({"awareness": self.awareness}, **(what or {}))
        args = who_args(self.brand, self.avatar, sub, demographic, self.what)
        st = who().stamp(*args) if args else {}
        self.awareness = level_of(st.get("awareness")) or self.awareness      # the language rows follow the same level
        return st

    # ------------------------------------------------------------------
    def rules(self):
        """Position, story and likeness rules — the NEVER lists live in these."""
        parts = []
        for rel, lim in (("position.md", 12000), ("story.md", 9000), ("identity-anchors.md", 7000)):
            t = self.file(rel, lim)
            parts.append(f"=== brands/{self.brand}/{rel} ===\n{t if t is not None else MISSING}")
        c = self.file("compliance.json")
        parts.append(f"=== brands/{self.brand}/compliance.json ===\n{c if c is not None else MISSING}")
        return "\n\n".join(parts)

    def products(self):
        heroes = self.bp.brand_path(self.brand, "products", "heroes.json", root=self.brands)
        h = _json(heroes)
        if not h:
            return MISSING
        self.read_files.append(self.rel(heroes))
        out = [f"Heroes (the SKUs an ad may point at first): {', '.join(h.get('heroes') or [])}"]
        if h.get("hero_rule"):
            out.append(f"Rule: {h['hero_rule']}")
        if h.get("never"):
            out.append(f"Never: {h['never']}")
        sell = h.get("sellable") or []
        if sell:
            out.append("Sellable: " + "; ".join(f"{s.get('title')} ({s.get('handle')})" for s in sell))
        for handle in h.get("heroes") or []:
            rel = self.product_rel(handle, f"products/{handle}.md")   # one product name (2026-11-19)
            t = self.file(rel, 2500)
            if t:
                out.append(f"--- {rel} ---\n{t}")
        return "\n".join(out)

    def avatars(self):
        if not self.avatar:
            return MISSING
        folder = _folder(self.brand, self.avatar)
        base = self.bp.brand_path(self.brand, "core-avatars", folder, root=self.brands)
        out = []
        prof = self.file(f"core-avatars/{folder}/profile.md", 5000)
        out.append(f"=== core avatar: {self.avatar} (profile.md) ===\n{prof or MISSING}")
        args = who_args(self.brand, self.avatar, self.sub, self.demographic, self.what or {"awareness": self.awareness})
        if args:
            out.append(who_text(args))              # who.py: the named sub-avatar's card, words, doubts and claim
        subs = sorted((base / "sub-avatars").glob("*.md")) if (base / "sub-avatars").is_dir() else []
        if args and args[2]:                        # a sub-avatar is named: that one, and no other person's situation
            key = re.sub(r"^sub-\d+-", "", args[2])
            subs = [s for s in subs if re.sub(r"^sub-\d+-", "", s.stem) == key]
        for s in subs:
            self.read_files.append(self.rel(s))
            out.append(f"--- sub-avatar {s.stem} ---\n{_read(s)}")      # whole: a card cut mid-line is half a person
        return "\n\n".join(out)

    def language(self):
        """Verbatim customer lines for the run's avatar — the only words a new line may use.

        Queried through the language layer, the call the picture chain and the video hook step make (owner,
        2026-10-27: "awareness levels and verbatims and spice are the foundation of what we're doing here"): the
        avatar's rows, never-used first plus a proven slice, spoken at the ad's awareness level first — hooks,
        injection and spice. It used to read the raw bank files ranked by likes. A failed or empty query is said,
        on stderr and in the slot; it never widens to every avatar's rows."""
        if not self.avatar:
            return MISSING
        folder = _folder(self.brand, self.avatar)
        lang = self.bp.brand_path(self.brand, "core-avatars", folder, "language", root=self.brands)
        if lang.is_dir():
            self.read_files += [self.rel(f) for f in sorted(lang.rglob("*.json")) if "used" not in f.relative_to(lang).parts]
        shim = next((d for d in (self.repo / "components" / "copywriter" / "machine", _SHIM)
                     if d is not None and (d / "language.py").is_file()), None)
        level = self.awareness or "any level"
        if shim is None:
            print("  ! language: the copywriter's language door is not on this checkout", file=sys.stderr)
            return "(the language layer could not be reached — write no new line; never invent a quote)"
        # its own process: the shim's folder has a paths.py of its own, which would shadow a caller's in-process
        code = ("import sys, json; sys.path.insert(0, sys.argv[1]); import language as L; a = json.loads(sys.argv[2]); "
                "print(json.dumps({s: L.for_stage(a['brand'], s, a['avatar'], None, None, n, a['root'], used='fresh', "
                "awareness=a['level']) for s, n in a['stages']}))")
        arg = json.dumps({"brand": self.brand, "avatar": self.avatar, "level": self.awareness,
                          "root": str(self.repo), "stages": LANGUAGE_STAGES})
        try:
            r = subprocess.run([sys.executable, "-c", code, str(shim), arg], capture_output=True, text=True, timeout=180)
            got = json.loads(r.stdout) if r.returncode == 0 else None
            if got is None:
                raise RuntimeError(((r.stderr or "").strip().splitlines() or ["no output"])[-1][:200])
        except Exception as e:                       # noqa: BLE001  said out loud, never a quiet empty slot
            print(f"  ! language: the language layer failed for {self.avatar} ({type(e).__name__}: {e})", file=sys.stderr)
            return (f"(the language layer FAILED for {self.avatar}: {e} — write no new line from memory; "
                    "never invent a quote)")
        out, empty = [], []
        for stage, _n in LANGUAGE_STAGES:
            txt = got.get(stage) or ""
            if "no rows matched" in txt or not txt.strip():
                empty.append(stage)
                out.append(f"=== {stage}: NO ROWS for {self.avatar} at {level} ===")
            else:
                out.append(txt.strip())
        if empty:
            print(f"  ! language: no rows for {self.avatar} · {level} · {', '.join(empty)}", file=sys.stderr)
        rules = self.file(f"core-avatars/{folder}/language/rules.md", 4000)
        head = f"=== language rules ===\n{rules}\n\n" if rules else ""
        return head + "\n\n".join(out)

    def cast(self):
        # resolved through the folder plan as file() is (ai-cast/casting/roster.json
        # -> ai-elements/characters/casting/roster.json)
        sys.path.append(str(self.repo / "components" / "brandpath"))
        import brandpath as BP  # noqa: E402
        for rel in ("ai-cast/casting/roster.json", "casting/roster.json"):
            p = BP.resolve_rel(self.brand, rel, root=self.repo / "brands")
            d = _json(p)
            if d:
                self.read_files.append(self.rel(p))
                people = d.get("people") or []
                rows = [f"- {p.get('name')} ({p.get('id')}), {p.get('age')} — {p.get('reads') or ''}; {p.get('hair') or ''}; "
                        f"covers: {p.get('covers') or p.get('sub_avatar') or p.get('sub') or '—'}" for p in people]
                return f"{d.get('_what', '')}\nRule: {d.get('_rule', '')}\n" + "\n".join(rows)
        return MISSING

    def funnels(self):
        t = self.file("funnels/README.md", 3000)
        return t or MISSING
