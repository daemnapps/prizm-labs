"""Brand context for one run — read ONLY from brands/<brand>/ (workspace rule 7,
components rule 9). Every file is optional: a brand that lacks one gets
"(not on file for this brand)" in the prompt, and the run records which files
it read, so a missing file is visible rather than silent.

Nothing here names a brand. The avatar comes from the teardown's own audience
read (stage 1b), never a default.
"""
import json
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
_SHIM = next((d / "tools" / "copywriter" / "machine" for d in Path(__file__).resolve().parents
              if (d / "tools" / "copywriter" / "machine" / "language.py").is_file()), None)


def level_of(text):
    """A doctrine awareness id out of a slot's value ("`problem-aware` — …"), or None."""
    t = str(text or "").strip().strip("`").lower()
    t = t.split()[0].strip("`.,;:") if t else ""
    return t if t in LEVELS else None


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
            t = self.file(f"products/{handle}.md", 2500)
            if t:
                out.append(f"--- products/{handle}.md ---\n{t}")
        return "\n".join(out)

    def avatars(self):
        if not self.avatar:
            return MISSING
        base = self.bp.brand_path(self.brand, "core-avatars", self.avatar, root=self.brands)
        out = []
        prof = self.file(f"core-avatars/{self.avatar}/profile.md", 5000)
        out.append(f"=== core avatar: {self.avatar} (profile.md) ===\n{prof or MISSING}")
        subs = sorted((base / "sub-avatars").glob("*.md")) if (base / "sub-avatars").is_dir() else []
        for s in subs:
            t = _read(s, 900)
            self.read_files.append(self.rel(s))
            out.append(f"--- sub-avatar {s.stem} ---\n{t}")
        return "\n\n".join(out)

    def language(self):
        """Verbatim customer lines for the run's avatar — the only words a new line may use.

        Queried through the language layer, the call the picture chain and the video hook step make (the owner,
        2026-10-27: "awareness levels and verbatims and spice are the foundation of what we're doing here"): the
        avatar's rows, never-used first plus a proven slice, spoken at the ad's awareness level first — hooks,
        injection and spice. It used to read the raw bank files ranked by likes. A failed or empty query is said,
        on stderr and in the slot; it never widens to every avatar's rows."""
        if not self.avatar:
            return MISSING
        lang = self.bp.brand_path(self.brand, "core-avatars", self.avatar, "language", root=self.brands)
        if lang.is_dir():
            self.read_files += [self.rel(f) for f in sorted(lang.rglob("*.json")) if "used" not in f.relative_to(lang).parts]
        shim = next((d for d in (self.repo / "tools" / "copywriter" / "machine", _SHIM)
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
        rules = self.file(f"core-avatars/{self.avatar}/language/rules.md", 4000)
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
