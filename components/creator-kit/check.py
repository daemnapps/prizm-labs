#!/usr/bin/env python3
"""Is this computer ready to run the creator line? Keys, brand folders and the skills, in plain lines.

    python3 components/creator-kit/check.py

Reads components/creator-kit/kit.json. Never prints a key, only "set" or "missing". Exit 0 when the needed keys
and at least one brand folder are in place. Standard library only.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "components" / "keys"))
import loader  # noqa: E402


def report(repo=REPO):
    kit = json.loads((HERE / "kit.json").read_text())
    keys = {name: bool(loader.lookup(name)) for group in kit["keys"].values() for name in group}
    brands = sorted(p.name for p in (repo / "brands").iterdir()
                    if p.is_dir() and not p.name.startswith(("_", "."))) if (repo / "brands").is_dir() else []
    skills = {s["skill"]: (repo / ".claude" / "skills" / s["skill"] / "SKILL.md").is_file() for s in kit["loop"]}
    ready = all(keys[k] for k in kit["keys"]["needed"]) and bool(brands) and all(skills.values())
    return {"kit": kit, "keys": keys, "brands": brands, "skills": skills, "ready": ready}


def main():
    r = report()
    kit = r["kit"]
    print("Creator kit check\n")
    for group, label in (("needed", "Needed"), ("helpful", "Helpful")):
        print(label + ":")
        for name, why in kit["keys"][group].items():
            print(f"  {'✓' if r['keys'][name] else '✗'} {name}: {why}")
    print("\nBrand folders: " + (", ".join(r["brands"]) or "none yet: link the brand folder you were given (setup page, step 1)"))
    missing = [s for s, ok in r["skills"].items() if not ok]
    print("Skills: " + ("all here" if not missing else "missing " + ", ".join(missing)))
    print("\n" + ("Ready. Say what you want, e.g. \"" + kit["loop"][0]["say"] + "\"." if r["ready"] else
                  "Not ready yet: open the setup page (python3 components/onboarding/serve.py) for the ✗ keys and the brand folder."))
    return 0 if r["ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
