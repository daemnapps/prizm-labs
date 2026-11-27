#!/usr/bin/env python3
"""Research fill — the research system as one repeatable process for any brand.

    python3 components/research-fill/fill.py access --brand <b>             what the brand has granted, and what is missing
    python3 components/research-fill/fill.py status --brand <b> [--avatar a] every step, done or not, per avatar
    python3 components/research-fill/fill.py next   --brand <b> [--avatar a] the one next step and how to run it
    add --json to any of them for the raw result.

The process itself (access list and steps, in order) is process.json. This file only checks
where a brand stands against it. Reads only: it spends nothing, runs nothing and writes nothing.
Key checks say set or missing, never a value. Standard library only.
"""
import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "components" / "keys"))
import loader  # noqa: E402

PROCESS = json.loads((HERE / "process.json").read_text())
MARK = {"done": "✓", "todo": "✗", "blocked": "·", "owner": "◆", "stale": "↻"}


def _json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None


def _filled(value):
    """A template value still holding a <placeholder> or empty counts as not filled."""
    if value in (None, "", [], {}):
        return False
    if isinstance(value, str):
        return "<" not in value and "YYYY" not in value
    if isinstance(value, list):
        return any(_filled(v) for v in value)
    if isinstance(value, dict):
        return any(_filled(v) for k, v in value.items() if k not in ("note", "since", "_what"))
    return bool(value)


class Brand:
    def __init__(self, brand, root=REPO, key=None):
        self.brand = brand
        self.root = Path(root)
        self.folder = self.root / "brands" / brand
        self.runs = self.root / "runs"
        self._key = key or (lambda name: loader.key(name, required=False))
        if not self.folder.is_dir():
            raise SystemExit(f"No brand folder brands/{brand}/. Pull or link it first (components/brand-sync).")

    # --- access ---------------------------------------------------------------
    def _check(self, rule):
        if "any" in rule:
            return any(self._check(r) for r in rule["any"])
        if "all" in rule:
            return all(self._check(r) for r in rule["all"])
        if "key" in rule:
            return bool(self._key(rule["key"]))
        if "brand_json" in rule:
            value = _json(self.folder / "operations" / "brand.json") or {}
            for part in rule["brand_json"].split("."):
                value = value.get(part) if isinstance(value, dict) else None
            return _filled(value)
        if "pulls_flag" in rule:
            value = _json(self.folder / "operations" / "language-pulls.json") or {}
            for part in rule["pulls_flag"].split("."):
                value = value.get(part) if isinstance(value, dict) else None
            return value is True
        if "daily" in rule:
            pulls = _json(self.folder / "operations" / "language-pulls.json") or {}
            return bool((pulls.get("daily") or {}).get("on"))
        if "pulls" in rule:
            pulls = _json(self.folder / "operations" / "language-pulls.json") or {}
            block = pulls.get(rule["pulls"])
            if not _filled(block):
                return False
            if rule["pulls"] == "reviews":
                if block.get("platform") not in ("junip", "judgeme"):
                    return False
                return bool(self._key(block.get("key", ""))) if _filled(block.get("key")) else False
            return True
        return False

    def access(self):
        return [dict(a, granted=self._check(a["check"])) for a in PROCESS["access"]]

    # --- avatars --------------------------------------------------------------
    def avatars(self):
        data = _json(self.folder / "core-avatars" / "avatars.json") or {}
        return [a for a in data.get("avatars", []) if _filled(a.get("id"))]

    def _avatar_folder(self, avatar):
        return self.folder / (avatar.get("folder") or f"core-avatars/{avatar['id']}")

    def bank_lines(self, avatar):
        """Rows in the avatar's customer-language bank, counted by the language layer itself."""
        sys.path.insert(0, str(self.root / "components" / "language-layer"))
        try:
            from language_layer import engine
            return len(engine.load(self.brand, self._avatar_folder(avatar).name, self.root))
        except (Exception, SystemExit):
            return 0

    def rounds(self, avatar):
        base = self.runs / "swipe-organic" / self.brand
        return sorted(p.name for p in base.glob(f"research-{avatar['id']}-*") if (p / "ranking.json").is_file())

    def age_days(self, paths):
        """Days since the newest of these files changed; None when there are none."""
        times = [p.stat().st_mtime for p in paths if p.is_file()]
        return None if not times else int((time.time() - max(times)) // 86400)

    def has_rooms(self, avatar):
        profile = self._avatar_folder(avatar) / "profile.md"
        text = profile.read_text() if profile.is_file() else ""
        if "### rooms" in text.lower():
            return True
        names = {avatar["id"], self._avatar_folder(avatar).name}
        return any(f.parent.name.startswith(tuple(names)) for f in (self.runs / "research" / self.brand).glob("**/rooms-found.json"))

    def profile_todo(self, avatar):
        """What profiles.init says still stands between this avatar's profiles and ads (empty = ready)."""
        try:
            sys.path.insert(0, str(self.root / "components" / "profiles"))
            import profiles  # noqa: E402
            rows = [r for r in profiles.init(self.brand) if r["id"].split("_")[0] == avatar["id"]]
        except (Exception, SystemExit) as err:  # a profile the standard can't read is a todo, not a crash
            return [f"profiles.py could not read it ({str(err)[:80]})"]
        if not rows:
            return ["no profile yet (who.py build)"]
        return [f"{r['id']}: {t}" for r in rows for t in r["todo"]]

    # --- the steps ------------------------------------------------------------
    def steps(self, avatar):
        own_words = any(a["granted"] for a in self.access() if a["need"] == "own-words")
        apify = any(a["granted"] for a in self.access() if a["id"] == "apify")
        out = []
        for s in PROCESS["steps"]:
            kind, detail, age = s["check"], "", None
            if kind == "avatar":
                ok = (self._avatar_folder(avatar) / "profile.md").is_file()
            elif kind == "sources":
                ok = own_words
            elif kind == "bank":
                n = self.bank_lines(avatar)
                ok, detail = n >= s["min"], f"{n} lines (needs {s['min']})"
            elif kind == "rooms":
                ok = self.has_rooms(avatar)
            elif kind == "profile":
                todo = self.profile_todo(avatar)
                ok, detail = not todo, "; ".join(todo[:3])
            elif kind == "rounds":
                names = self.rounds(avatar)
                ok, detail = len(names) >= s["min"], f"{len(names)} ranked round(s)"
                age = self.age_days([self.runs / "swipe-organic" / self.brand / n / "ranking.json" for n in names])
            elif kind == "matrix":
                f = self.runs / "swipe-organic" / self.brand / f"matrix-{avatar['id']}" / "concepts.json"
                ok, age = f.is_file(), self.age_days([f])
            else:
                ok = False
            state = "done" if ok else ("owner" if s.get("owner") else "todo")
            if ok and s.get("refresh_days") and age is not None and age > s["refresh_days"]:
                state, detail = "stale", (detail + "; " if detail else "") + f"newest is {age} days old, refresh every {s['refresh_days']}"
            if state == "todo" and s.get("price") and not apify:
                state, detail = "blocked", "needs the scraping account (access: apify)"
            if state == "todo" and kind == "bank" and not own_words:
                state = "blocked"
                detail = (detail + "; " if detail else "") + "no own-words source connected"
            run = s["run"].replace("<brand>", self.brand).replace("<avatar>", avatar["id"])
            out.append({"id": s["id"], "name": s["name"], "state": state, "detail": detail, "run": run,
                        "fills": s["fills"], "price": bool(s.get("price"))})
        return out


def _next(steps):
    for s in steps:
        if s["state"] in ("todo", "blocked", "stale", "owner"):
            return s
    return None


def main(argv=None, out=sys.stdout, root=REPO, key=None):
    ap = argparse.ArgumentParser(description="Where a brand stands in the research process.")
    ap.add_argument("cmd", choices=["access", "status", "next"])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--avatar", help="one avatar id; default: every avatar in avatars.json")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        b = Brand(a.brand, root=root, key=key)
    except SystemExit as err:
        out.write(f"{err}\n")
        return 2
    if a.cmd == "access":
        rows = b.access()
        if a.json:
            out.write(json.dumps(rows, indent=1) + "\n")
            return 0
        for r in rows:
            out.write(f"{'✓' if r['granted'] else '✗'} {r['name']:22} {r['need']:9}  {'' if r['granted'] else 'grant: ' + r['grant']}\n")
        own = sum(1 for r in rows if r["need"] == "own-words" and r["granted"])
        daily = next((r["granted"] for r in rows if r["id"] == "daily"), False)
        out.write(f"{own} own-words source(s) connected; scraping {'on' if rows[0]['granted'] else 'off'}; daily pull {'on' if daily else 'off'}.\n")
        return 0
    avatars = [x for x in b.avatars() if not a.avatar or x["id"] == a.avatar]
    if not avatars:
        out.write("No named avatar yet. First step: say \"build the profile for <avatar> of %s\".\n" % a.brand)
        return 1
    result = {x["id"]: b.steps(x) for x in avatars}
    if a.json:
        out.write(json.dumps(result if a.cmd == "status" else {k: _next(v) for k, v in result.items()}, indent=1) + "\n")
        return 0
    for avatar, steps in result.items():
        if a.cmd == "status":
            done = sum(1 for s in steps if s["state"] == "done")
            out.write(f"{a.brand} · {avatar}: {done} of {len(steps)} done\n")
            for i, s in enumerate(steps, 1):
                out.write(f"  {MARK[s['state']]} {i}. {s['name']}{'  — ' + s['detail'] if s['detail'] else ''}\n")
        else:
            s = _next(steps)
            if s is None:
                out.write(f"{avatar}: research is full.\n")
            else:
                note = " (shows the price first; spends only on the owner's go)" if s["price"] else ""
                out.write(f"{avatar}: next is {s['name']}{' — ' + s['detail'] if s['detail'] else ''}\n  {s['run']}{note}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
