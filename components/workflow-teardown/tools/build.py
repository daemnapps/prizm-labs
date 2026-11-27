"""Build the page index and the people copy of every recipe.

    python3 components/workflow-teardown/tools/build.py

Reads recipes/*.json and breakdowns/*.json; writes index.json (what the Studio's Higgsfield page shows) and
recipes/<id>.md (the same recipe for people). Writes nothing else. Python 3.9, stdlib only.
"""
import datetime
import glob
import json
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_all(folder):
    out = []
    for f in sorted(glob.glob(os.path.join(HERE, folder, "*.json"))):
        try:
            with open(f) as fh:
                out.append(json.load(fh))
        except ValueError as e:
            print("skipped", os.path.relpath(f, HERE), e)
    return out


def money(x):
    if x is None:
        return ""
    if isinstance(x, dict):
        return "{} · {}".format(x.get("model", ""), x.get("credits", "")).strip(" ·")
    return str(x)


def fence(text):
    return "```\n" + str(text).rstrip() + "\n```\n"


def recipe_md(r):
    L = ["# " + r["name"], "", r.get("makes", ""), ""]
    hf = r.get("higgsfield") or {}
    L += ["Higgsfield original: `{}` · built from {}".format(hf.get("command") or hf.get("workflow") or "",
          ", ".join("`{}`".format(x) for x in hf.get("library", []))), ""]
    p = r.get("price") or {}
    if p:
        L += ["## Price", "", "| | |", "|---|---|"]
        for k in ("higgsfield", "house", "cheap", "basis"):
            if p.get(k):
                L.append("| {} | {} |".format(k, p[k]))
        L.append("")
    L += ["## Inputs", ""]
    for i in r.get("inputs", []):
        L.append("- **{}**{}: {}".format(i.get("name"), "" if i.get("required") else " (optional)", i.get("from")))
    L += ["", "## Steps", ""]
    for s in r.get("steps", []):
        L += ["### {}. {} — `{}`".format(s.get("n"), s.get("name"), s.get("job")), "", s.get("what", ""), "",
              "| | model | credits |", "|---|---|---|"]
        for k in ("hf", "house", "cheap"):
            v = s.get(k)
            if isinstance(v, dict):
                L.append("| {} | {} | {} |".format({"hf": "Higgsfield", "house": "our house", "cheap": "cheapest"}[k],
                                                  v.get("model", ""), v.get("credits", "")))
        L.append("")
        if isinstance(s.get("cheap"), dict) and s["cheap"].get("note"):
            L += ["Cheap swap: " + s["cheap"]["note"] + (" Registry: " + str(s["cheap"].get("registry")) + "."), ""]
        if s.get("local"):
            L += ["On this Mac: `{}`".format(s["local"]), ""]
        if s.get("prompt_hf"):
            L += ["**Higgsfield, word for word**", "", fence(s["prompt_hf"])]
        if s.get("prompt_ours"):
            L += ["**Ours**", "", fence(s["prompt_ours"])]
        if s.get("check"):
            L += ["Check: " + s["check"], ""]
    for key, title in (("checks", "Checks"), ("rules", "Rules")):
        if r.get(key):
            L += ["## " + title, ""] + ["- " + str(x) for x in r[key]] + [""]
    if r.get("formats"):
        L += ["## Formats", "", fence(json.dumps(r["formats"], indent=1, ensure_ascii=False))]
    return "\n".join(L).rstrip() + "\n"


def main():
    recipes = load_all("recipes")
    breakdowns = load_all("breakdowns")
    for r in recipes:
        with open(os.path.join(HERE, "recipes", r["id"] + ".md"), "w") as fh:
            fh.write(recipe_md(r))
    index = {"built": datetime.date.today().isoformat(),
             "about": "Reverse-engineered workflows: the original's steps and prompts word for word, our version, and the cheapest model for each job.",
             "recipes": recipes, "breakdowns": breakdowns}
    with open(os.path.join(HERE, "index.json"), "w") as fh:
        json.dump(index, fh, ensure_ascii=False)
    print("{} recipes, {} breakdowns -> index.json".format(len(recipes), len(breakdowns)))


if __name__ == "__main__":
    main()
