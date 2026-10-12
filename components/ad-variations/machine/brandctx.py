"""Brand context for one run — read ONLY from brands/<brand>/ (workspace rule 7,
components rule 9). Every file is optional: a brand that lacks one gets
"(not on file for this brand)" in the prompt, and the run records which files
it read, so a missing file is visible rather than silent.

Nothing here names a brand. The avatar comes from the teardown's own audience
read (stage 1b), never a default.
"""
import json
import sys
from pathlib import Path

MISSING = "(not on file for this brand)"


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
    def __init__(self, repo, brand, avatar=None):
        self.repo, self.brand, self.avatar = Path(repo), brand, avatar
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

    def language(self, limit=60):
        """Verbatim customer lines for the run's avatar — the only words a new line may use."""
        if not self.avatar:
            return MISSING
        lang = self.bp.brand_path(self.brand, "core-avatars", self.avatar, "language", root=self.brands)
        lines = []
        for f in sorted(lang.glob("*.json")) if lang.is_dir() else []:
            d = _json(f) or {}
            ents = d.get("entries") if isinstance(d, dict) else d if isinstance(d, list) else []
            if not ents:
                continue
            self.read_files.append(self.rel(f))
            ents = [e for e in ents if isinstance(e, dict) and e.get("text") and len(e["text"]) > 18
                    and e.get("status", "active") == "active"]
            ents.sort(key=lambda e: -((e.get("signal") or {}).get("likes") or (e.get("signal") or {}).get("count") or 0))
            for e in ents[: limit // 2]:
                lines.append(f"- “{e['text'][:220]}” — {e.get('use') or '—'} · {e.get('sub') or 'no sub'} · {e.get('id')}")
        rules = self.file(f"core-avatars/{self.avatar}/language/rules.md", 4000)
        head = f"=== language rules ===\n{rules}\n\n" if rules else ""
        return head + ("=== verbatim lines (a sample; the bank is larger) ===\n" + "\n".join(lines[:limit]) if lines else MISSING)

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
