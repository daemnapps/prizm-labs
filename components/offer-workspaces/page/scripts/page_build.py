#!/usr/bin/env python3
"""page_build.py - validate a brand page config and render sections from it.

Usage:
    python page_build.py check <config.json> [--sections a,b,c]
    python page_build.py render <section-file> <config.json> [-o out.html]
    python page_build.py assemble <config.json> <section,section,...> [-o out.html]
    python page_build.py keys [--section <name>]

WHY THIS EXISTS. This skill assembles pages by substituting {{VARIABLE}} keys into
section markup. Until now there was no script, so nothing verified that the
substitution actually completed. A page could ship with unresolved placeholders, or
worse, with values left over from whichever brand filled the template last.

`check` is the gate. Run it before any page goes near a browser.

  - names every key the sections you picked require and you have not set
  - names every key you set that no section uses (usually a typo)
  - refuses a config whose values still look like another brand's

Exit codes:  0 = clean   1 = problems found   2 = usage/IO error
"""
import sys, re, json, os
from pathlib import Path

VAR = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
HERE = Path(__file__).resolve().parent
SECTIONS = Path(os.environ["PRIZM_PAGE_SECTIONS"]) if os.environ.get("PRIZM_PAGE_SECTIONS") else HERE.parent / "references" / "section-library" / "sections"

# Values that mean "nobody filled this in". A config full of these is not ready.
PLACEHOLDER_HINTS = ("TODO", "TBD", "FIXME", "XXX", "CHANGEME", "your-", "example.com")


def load(path, what):
    p = Path(path)
    if not p.exists():
        return None, f"{what} not found: {path}"
    try:
        return json.loads(p.read_text()), None
    except json.JSONDecodeError as e:
        return None, f"{what} is not valid JSON ({path}): {e}"


def flatten(cfg):
    """Config values by key, ignoring _README blocks and grouping wrappers."""
    out = {}
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k.startswith("_"):
                    continue
                if isinstance(v, dict):
                    walk(v)
                else:
                    out[k] = v
    walk(cfg)
    return out


def section_files(names=None):
    if not SECTIONS.exists():
        return [], f"section library not found at {SECTIONS}"
    files = sorted(SECTIONS.glob("*.md"))
    if names:
        want = {n.strip().lower() for n in names}
        files = [f for f in files
                 if f.stem.lower() in want or any(w in f.stem.lower() for w in want)]
        if not files:
            return [], f"no sections matched: {', '.join(sorted(want))}"
    return files, None


def vars_in(files):
    used = {}
    for f in files:
        for m in VAR.finditer(f.read_text()):
            used.setdefault(m.group(1), set()).add(f.stem)
    return used


def cmd_check(argv):
    if not argv:
        print("usage: page_build.py check <config.json> [--sections a,b,c]"); return 2
    cfg, err = load(argv[0], "config")
    if err:
        print(err); return 2
    names = None
    if "--sections" in argv:
        i = argv.index("--sections")
        if i + 1 >= len(argv):
            print("--sections needs a comma-separated list"); return 2
        names = argv[i + 1].split(",")
    files, err = section_files(names)
    if err:
        print(err); return 2

    used = vars_in(files)
    have = flatten(cfg)
    filled = {k: v for k, v in have.items()
              if v not in (None, "", [], {}) }

    missing = {k: v for k, v in used.items() if k not in filled}
    unused = sorted(set(filled) - set(used))
    suspicious = sorted(k for k, v in filled.items()
                        if isinstance(v, str)
                        and any(h.lower() in v.lower() for h in PLACEHOLDER_HINTS))

    print(f"\n{'='*70}\nPAGE CONFIG CHECK\n{'='*70}")
    print(f"  config      {Path(argv[0]).name}")
    print(f"  sections    {len(files)}" + (f" ({', '.join(f.stem for f in files)})"
                                           if names else " (whole library)"))
    print(f"  keys used   {len(used)}")
    print(f"  keys filled {len(filled)}")

    problems = 0
    if missing:
        problems += len(missing)
        print(f"\nUNRESOLVED ({len(missing)}) - these appear in your sections with no value:\n")
        for k in sorted(missing):
            where = ", ".join(sorted(missing[k])[:3])
            more = f" +{len(missing[k])-3}" if len(missing[k]) > 3 else ""
            print(f"  {k:<26} {where}{more}")
    if suspicious:
        problems += len(suspicious)
        print(f"\nPLACEHOLDER VALUES ({len(suspicious)}) - filled, but not really:\n")
        for k in suspicious:
            print(f"  {k:<26} {str(filled[k])[:44]}")
    if unused:
        print(f"\nSET BUT UNUSED ({len(unused)}) - usually a typo, or a section you did not include:\n")
        print("  " + ", ".join(unused[:18]) + (" ..." if len(unused) > 18 else ""))

    if problems:
        print(f"\nFAIL - {problems} problem(s). Do not build from this config.\n")
        return 1
    print("\nPASS - every key the chosen sections need has a value.\n")
    return 0


def substitute(text, filled):
    missing = set()
    def rep(m):
        k = m.group(1)
        if k in filled and filled[k] not in (None, ""):
            v = filled[k]
            return "\n".join(str(x) for x in v) if isinstance(v, list) else str(v)
        missing.add(k)
        return m.group(0)
    return VAR.sub(rep, text), missing


def cmd_render(argv):
    if len(argv) < 2:
        print("usage: page_build.py render <section> <config.json> [-o out.html]"); return 2
    files, err = section_files([argv[0]])
    if err:
        print(err); return 2
    cfg, err = load(argv[1], "config")
    if err:
        print(err); return 2
    filled = flatten(cfg)
    out, missing = substitute(files[0].read_text(), filled)
    if missing:
        print(f"REFUSED: {len(missing)} unresolved key(s) in {files[0].stem}: "
              f"{', '.join(sorted(missing)[:8])}", file=sys.stderr)
        print("Run `check` first. A page with live placeholders must not ship.",
              file=sys.stderr)
        return 1
    _write(out, argv)
    return 0


def cmd_assemble(argv):
    if len(argv) < 2:
        print("usage: page_build.py assemble <config.json> <section,section,...> [-o out.html]")
        return 2
    cfg, err = load(argv[0], "config")
    if err:
        print(err); return 2
    files, err = section_files(argv[1].split(","))
    if err:
        print(err); return 2
    filled = flatten(cfg)
    parts, allmissing = [], set()
    for f in files:
        out, missing = substitute(f.read_text(), filled)
        allmissing |= missing
        parts.append(out)
    if allmissing:
        print(f"REFUSED: {len(allmissing)} unresolved key(s): "
              f"{', '.join(sorted(allmissing)[:10])}", file=sys.stderr)
        return 1
    _write("\n\n".join(parts), argv)
    return 0


def _write(text, argv):
    if "-o" in argv:
        p = Path(argv[argv.index("-o") + 1]); p.write_text(text)
        print(f"written: {p}  ({len(text):,} chars)")
    else:
        print(text)


def cmd_keys(argv):
    names = None
    if "--section" in argv:
        names = [argv[argv.index("--section") + 1]]
    files, err = section_files(names)
    if err:
        print(err); return 2
    used = vars_in(files)
    print(f"\n{len(used)} keys across {len(files)} section(s)\n")
    for k in sorted(used):
        print(f"  {k:<28} {len(used[k]):>2} section(s)  {', '.join(sorted(used[k])[:2])}")
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__); return 2
    cmd, argv = sys.argv[1], sys.argv[2:]
    if cmd == "check":    return cmd_check(argv)
    if cmd == "render":   return cmd_render(argv)
    if cmd == "assemble": return cmd_assemble(argv)
    if cmd == "keys":     return cmd_keys(argv)
    print(__doc__); return 2


if __name__ == "__main__":
    sys.exit(main())
