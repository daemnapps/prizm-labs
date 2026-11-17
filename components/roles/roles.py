#!/usr/bin/env python3
"""Roles: who owns what, and what each role's agent runs.

    python3 components/roles/roles.py check                 # is the role file true?
    python3 components/roles/roles.py list                  # every role and its number
    python3 components/roles/roles.py resolve <name>        # which role an existing name means
    python3 components/roles/roles.py card <role> [--brand <brand>]    # one role, in full
    python3 components/roles/roles.py agent <role> [--brand <brand>]   # the brief the role's agent starts from
    python3 components/roles/roles.py brief <role> --brand <brand> [--month YYYY-MM]   # this month's brief for the holder
    python3 components/roles/roles.py money --brand <brand>  # the brand's cost-per-purchase lines, from its own numbers
    python3 components/roles/roles.py template              # rewrite brands/_TEMPLATE/roles.json from the role file
    python3 components/roles/roles.py export                # roles + coverage as JSON (for a page)

The truth is roles.json beside this file. It is brand-agnostic. Who holds a role,
the targets and any grant for a brand live in brands/<brand>/roles.json. Reads
only; the one thing it writes is the template, and only on `template`.
"""
import argparse
import datetime
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
ROLES = HERE / "roles.json"
TEMPLATE = ROOT / "brands" / "_TEMPLATE" / "roles.json"
HANDOFF_ROLES = ROOT / "components" / "handoff-standard" / "skill" / "roles.json"
STAGES = ROOT / "components" / "naming" / "stages.json"
PARTS = ROOT / "components" / "system" / "components.json"
NEEDED = ["id", "name", "layer", "reason", "number", "knowledge", "application", "taste", "authority", "tripwires", "loop"]
LISTS = ["workflows", "also_called", "handoffs", "calls"]          # must exist, may be empty
ID = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def load():
    """The role file, with each role's workflows read from the one parts list.

    A component names its role once, in components/system/components.json; nothing is listed twice.
    """
    data = json.loads(ROLES.read_text())
    parts = json.loads(PARTS.read_text())["components"] if PARTS.exists() else []
    for r in data["roles"]:
        r["workflows"] = [{"job": (p["stage"] or p["workflow"]).replace("-", " ").capitalize(), "tool": p["path"],
                           "agent": p["does"], "stages": p.get("steps", [])} for p in parts if p["role"] == r["id"]]
    return data


def norm(path):
    """One name per tool: tools/x and components/x are the same folder."""
    p = path.strip().strip("`").rstrip("/")
    parts = p.split("/")
    if parts[0] == "tools" and (ROOT / "components" / "/".join(parts[1:])).exists():
        return "components/" + "/".join(parts[1:])
    return p


def listed_tools():
    """Every folder TOOLS.md lists, with its job."""
    out = {}
    for line in (ROOT / "TOOLS.md").read_text().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 3 or cells[0] == "Job" or set(cells[0]) <= set("-"):
            continue
        for folder in re.findall(r"`([^`]+)`", cells[2]):
            out[norm(folder)] = {"job": cells[0], "tool": cells[1]}
    return out


def names(data):
    """Every name that means a role: its id, its title and its other names."""
    table = {}
    for r in data["roles"]:
        for n in [r["id"], r["name"]] + r.get("also_called", []):
            table.setdefault(n.lower().replace(" ", "-"), []).append(r["id"])
    return table


def resolve(data, name):
    hit = sorted(set(names(data).get(name.strip().lower().replace(" ", "-").replace("_", "-"), [])))
    return hit[0] if len(hit) == 1 else None


def coverage(data):
    roles = data["roles"]
    ids = {r["id"] for r in roles}
    gate_ids = {g["id"] for g in data["model"]["calls"]["list"]}
    problems, owners, numbers, handoff_owner = [], {}, {}, {}
    for r in roles:
        if not ID.match(r.get("id", "")):
            problems.append(f"{r.get('id', '?')}: a role id is lowercase with dashes")
        for f in NEEDED:
            if not r.get(f):
                problems.append(f"{r.get('id', '?')}: '{f}' is missing or empty")
        for f in LISTS:
            if not isinstance(r.get(f), list):
                problems.append(f"{r.get('id', '?')}: '{f}' must be a list")
        n = r.get("number", {}).get("name", "")
        if n in numbers:
            problems.append(f"number '{n}' has two owners: {numbers[n]} and {r['id']}")
        numbers[n] = r["id"]
        if r.get("reports_to") and r["reports_to"] not in ids:
            problems.append(f"{r['id']}: reports to unknown role '{r['reports_to']}'")
        for f in r.get("loop", {}).get("feeds", []):
            if f not in ids:
                problems.append(f"{r['id']}: feeds unknown role '{f}'")
        if r.get("authority", {}).get("level") not in (1, 2, 3, 4):
            problems.append(f"{r['id']}: authority level must be 1-4")
        for g in r.get("calls", []):
            if g.get("call") not in gate_ids:
                problems.append(f"{r['id']}: unknown call '{g.get('call')}'")
        for h in r.get("handoffs", []):
            if h in handoff_owner:
                problems.append(f"hand-off '{h}' is claimed by two roles: {handoff_owner[h]} and {r['id']}")
            handoff_owner[h] = r["id"]
        for w in r.get("workflows", []):
            t = norm(w["tool"])
            if not (ROOT / t).exists():
                problems.append(f"{r['id']}: workflow folder not found: {w['tool']}")
            if t in owners:
                problems.append(f"{t} has two owners: {owners[t]} and {r['id']}")
            owners[t] = r["id"]
    for n, who in names(data).items():
        if len(set(who)) > 1:
            problems.append(f"the name '{n}' means two roles: {', '.join(sorted(set(who)))}")
    for x in data["model"].get("money", {}).get("equation", []) + data["model"].get("money", {}).get("levers", []):
        if x["role"] not in ids:
            problems.append(f"money: '{x.get('term') or x.get('name')}' names unknown role '{x['role']}'")
    for s in data["model"].get("stops_today", []):
        if s["role"] not in ids:
            problems.append(f"stop '{s['stop']}' names unknown role '{s['role']}'")

    # the names already in the toolkit must each land on one role
    matched = []
    if HANDOFF_ROLES.exists():
        for h in json.loads(HANDOFF_ROLES.read_text()).get("roles", {}):
            if h in handoff_owner:
                matched.append({"name": h, "from": "hand-off standard", "role": handoff_owner[h]})
            else:
                problems.append(f"hand-off role '{h}' is not claimed by any role")
        for h in handoff_owner:
            if h not in json.loads(HANDOFF_ROLES.read_text()).get("roles", {}):
                problems.append(f"{handoff_owner[h]}: hand-off '{h}' is not in the hand-off standard")
    if STAGES.exists():
        for who in sorted({s.get("who") for s in json.loads(STAGES.read_text()).get("stages", []) if s.get("who")}):
            got = resolve(data, who)
            if got:
                matched.append({"name": who, "from": "stage list", "role": got})
            else:
                problems.append(f"stage owner '{who}' in components/naming/stages.json does not resolve to a role")
    for r in roles:
        for a in r.get("also_called", []):
            if not any(x["name"] == a for x in matched):
                matched.append({"name": a, "from": "also called", "role": r["id"]})

    listed = listed_tools()
    unowned = sorted(t for t in listed if t not in owners)
    for t in unowned:
        problems.append(f"no role owns {t} ({listed[t]['tool']})")
    comp = ROOT / "components"
    all_components = sorted(p.name for p in comp.iterdir() if p.is_dir() and not p.name.startswith(".")) if comp.exists() else []
    owned_names = {t.split("/")[1] for t in owners if t.startswith("components/")}
    return {
        "problems": problems,
        "listed_tools": len(listed),
        "listed_tools_owned": len(listed) - len(unowned),
        "roles": len(roles),
        "numbers": len(numbers),
        "roles_without_machine": [r["id"] for r in roles if not r.get("workflows") and r["id"] != "owner"],
        "draft_numbers": [r["id"] for r in roles if r["number"].get("basis") == "draft"],
        "components_total": len(all_components),
        "components_without_role": [c for c in all_components if c not in owned_names],
        "matched": matched,
        "roles_never_asking_owner": [r["id"] for r in roles if not r.get("calls") and r["id"] != "owner"
                                     and not any(s["role"] == r["id"] for s in data["model"].get("stops_today", []))],
        "roles_free_after_yes": sorted({s["role"] for s in data["model"].get("stops_today", []) if s["proposed"] == "holder"
                                        and not next(x for x in roles if x["id"] == s["role"]).get("calls")}),
    }


def role(data, rid):
    got = resolve(data, rid)
    for r in data["roles"]:
        if r["id"] == (got or rid):
            return r
    sys.exit(f"No role '{rid}'. Roles: " + ", ".join(r["id"] for r in data["roles"]))


def brand_file(brand):
    p = ROOT / "brands" / brand / "roles.json"
    if not p.exists():
        sys.exit(f"brands/{brand}/roles.json is not there yet. Copy brands/_TEMPLATE/roles.json into the brand folder and fill it.")
    return json.loads(p.read_text())


def target(assign, key):
    v = (assign.get("targets") or {}).get(key)
    return "not set" if v in (None, "") else str(v)


def held_by(assign):
    h = [x for x in (assign.get("holders") or []) if x]
    return ", ".join(h) if h else "nobody yet"


def card_md(data, r, assign=None):
    lv = {a["level"]: a for a in data["model"]["authority"]}[r["authority"]["level"]]
    gate_name = {g["id"]: g["name"] for g in data["model"]["calls"]["list"]}
    lead = next((x["name"] for x in data["roles"] if x["id"] == r.get("reports_to")), "")
    L = [f"# {r['name']}", "", f"`{r['id']}`" + (f" · also called: {', '.join(r['also_called'])}" if r.get("also_called") else ""), "",
         f"**Why it exists:** {r['reason']}", ""]
    if assign is not None:
        L += [f"**Held by:** {held_by(assign)}", ""]
    n = r["number"]
    L += [f"**Its number:** {n['name']} ({n['reads_as']})" + (f" · target: {target(assign, n['target_key'])}" if assign is not None else "")]
    for c in r.get("counts", []):
        L.append(f"- {c['name']} per {c['per']}" + (f" · target: {target(assign, c['target_key'])}" if assign is not None else ""))
    L += ["", "**What it knows:**"]
    L += [f"- Ask the knowledge base: {q}" for q in r["knowledge"]["ask"]]
    L += ["- Brand folder: " + ", ".join(r["knowledge"]["brand_files"])]
    L += ["", "**What the work looks like:**"]
    L += [f"- {a['output']} · {a['cadence']} · {a['standard']}" for a in r["application"]]
    L += ["", "**What its agent runs:**"]
    if r["workflows"]:
        for w in r["workflows"]:
            st = f" · stages: {', '.join(w['stages'])}" if w.get("stages") else ""
            L.append(f"- {w['job']}: `{w['tool']}` · {w['agent']}{st}")
    else:
        L.append("- No workflow built yet. The work is done by hand until one exists.")
    if r.get("handoffs"):
        L.append("- Work arrives as a hand-off: " + ", ".join(f"`{h}`" for h in r["handoffs"]))
    L += ["", "**Calls that stay with a person:**"] + [f"- {t}" for t in r["taste"]]
    L += ["", f"**Authority:** level {lv['level']}, {lv['name']} ({lv['scope']})"]
    L += [f"- Decides alone: {d}" for d in r["authority"]["decides"]]
    L += [f"- Goes to its lead{(' (' + lead + ')') if lead else ''}: {d}" for d in r["authority"]["sends_up"]]
    L += ["", "**The owner's calls it reaches:**"]
    if r["calls"]:
        for g in r["calls"]:
            granted = assign is not None and (assign.get("grants") or {}).get(g["call"]) is True
            L.append(f"- {gate_name[g['call']]}: {g['at']}" + (" · granted to this role" if granted else ""))
    else:
        L.append("- None.")
    pending = [s for s in data["model"].get("stops_today", []) if s["role"] == r["id"] and s["proposed"] == "holder"]
    if pending:
        L += ["", "**Still stops for the owner today (moves to the holder on his yes):**"]
        L += [f"- {s['stop']} ({s['where']})" for s in pending]
    L += ["", "**The owner steps in when:**"] + [f"- {t}" for t in r["tripwires"]]
    lp = r["loop"]
    L += ["", f"**The loop:** reads {lp['reads'].lower()} → changes {lp['changes'].lower()}"
          + (f" → feeds {', '.join(lp['feeds'])}" if lp.get("feeds") else "")]
    return "\n".join(L) + "\n"


def cmd_check(_a):
    data = load()
    c = coverage(data)
    print(f"{c['roles']} roles · {c['numbers']} numbers, one owner each · "
          f"{c['listed_tools_owned']}/{c['listed_tools']} listed tools owned · "
          f"{len(c['matched'])} existing names matched")
    print(f"Roles that never stop for the owner: {len(c['roles_never_asking_owner'])} of {c['roles'] - 1}"
          f" (+{len(c['roles_free_after_yes'])} once their approvals move to the holder)")
    if c["roles_without_machine"]:
        print("Roles with no workflow yet: " + ", ".join(c["roles_without_machine"]))
    if c["draft_numbers"]:
        print("Numbers still a draft: " + ", ".join(c["draft_numbers"]))
    print(f"Parts not under a role yet: {len(c['components_without_role'])} of {c['components_total']}")
    if c["problems"]:
        print("\nFIX:")
        for p in c["problems"]:
            print(" - " + p)
        sys.exit(1)
    print("OK")


def cmd_list(_a):
    for r in load()["roles"]:
        print(f"{r['id']:<22} {r['number']['name']:<34} {len(r['workflows'])} workflows · {len(r['calls'])} calls")


def cmd_resolve(a):
    data = load()
    got = resolve(data, a.name)
    if not got:
        sys.exit(f"'{a.name}' is not a role name here. Roles: " + ", ".join(r["id"] for r in data["roles"]))
    print(got)


def cmd_card(a):
    data = load()
    r = role(data, a.role)
    assign = (brand_file(a.brand).get("assign") or {}).get(r["id"], {}) if a.brand else None
    print(card_md(data, r, assign))


def cmd_agent(a):
    data = load()
    r = role(data, a.role)
    assign = (brand_file(a.brand).get("assign") or {}).get(r["id"], {}) if a.brand else None
    brand = a.brand or "{brand}"
    gate_name = {g["id"]: g["name"].lower() for g in data["model"]["calls"]["list"]}
    stops = "; ".join(f"{gate_name[g['call']]} ({g['at'].lower()})" for g in r["calls"])
    L = [f"You are the {r['name']} agent (`agent:{r['id']}`) for {brand}. You run this role's workflows from start to finish.",
         "A person holds the role; you do the work. After a hand-off you run everything and ask nobody, except where this brief says to stop.", "",
         card_md(data, r, assign),
         "## How you work",
         f"- Read brands/{brand}/ first. Fill every blank from the brand folder, never from an example.",
         "- Before a judgment call, ask the knowledge base the questions above and follow what it returns.",
         "- Run each workflow by its own README. Start a sub-agent per stage where stages are listed; pass a stage on only when its check passes.",
         "- Fix a failed check yourself once. If the same stage fails twice, stop and report it: that is a trip-wire.",
         "- Log the day's count. Report the number against its target every week.",
         "- Anything under 'Goes to its lead' goes to that role as: " + ", ".join(data["model"]["proposal"]) + ".",
         ("- Stop and ask the owner only at: " + stops + ". A call the brand file grants to this role is yours to make."
          if stops else "- This role reaches none of the owner's calls."),
         "- Where the card lists a stop that is still the owner's today, keep that stop until the tool that holds it is changed.",
         "- Name every file, folder and hand-off by the naming rules: the role, never the person."]
    print("\n".join(L))


def cmd_brief(a):
    data = load()
    r = role(data, a.role)
    assign = (brand_file(a.brand).get("assign") or {}).get(r["id"], {})
    month = a.month or datetime.date.today().strftime("%Y-%m")
    n = r["number"]
    gate_name = {g["id"]: g["name"] for g in data["model"]["calls"]["list"]}
    lead = next((x["name"] for x in data["roles"] if x["id"] == r.get("reports_to")), "nobody")
    L = [f"# {r['name']} · brief for {month}", "",
         f"Held by: {held_by(assign)} · reports to: {lead}", "",
         "## What changed this month", assign.get("changed_this_month") or "Nothing written yet.", "",
         "## Your numbers", "| Number | Target |", "|---|---|",
         f"| {n['name']} | {target(assign, n['target_key'])} |"]
    L += [f"| {c['name']} per {c['per']} | {target(assign, c['target_key'])} |" for c in r.get("counts", [])]
    L += ["", "## What you deliver", "| Output | How often | Standard |", "|---|---|---|"]
    L += [f"| {x['output']} | {x['cadence']} | {x['standard']} |" for x in r["application"]]
    L += ["", "## Your calls", *[f"- {t}" for t in r["taste"]],
          "", "## You decide alone", *[f"- {t}" for t in r["authority"]["decides"]],
          "", "## Your agent runs", *([f"- {w['agent']} (`{w['tool']}`)" for w in r["workflows"]] or ["- Nothing built yet"]),
          "", "## The owner's calls you reach", *([f"- {gate_name[g['call']]}: {g['at']}" for g in r["calls"]] or ["- None"]),
          *[f"- Today, still: {s['stop']} ({s['where']})" for s in data["model"].get("stops_today", []) if s["role"] == r["id"] and s["proposed"] == "holder"],
          "", "## The owner steps in when", *[f"- {t}" for t in r["tripwires"]]]
    print("\n".join(L))


def money_lines(inputs):
    """Breakeven and target cost per purchase from a brand's own numbers; None when a number is missing."""
    try:
        ov, buf, cpo, pt = (float(inputs[k]) for k in ("order_value", "buffer", "cost_per_order", "profit_target"))
    except (KeyError, TypeError, ValueError):
        return None
    breakeven = ov * (1 - buf) - cpo
    return {"breakeven_cost_per_purchase": round(breakeven, 2), "target_cost_per_purchase": round(breakeven - pt * ov, 2)}


def cmd_money(a):
    data = load()
    m = data["model"]["money"]
    got = money_lines(brand_file(a.brand).get("money") or {})
    names = {r["id"]: r["name"] for r in data["roles"]}
    print(" ".join(f"{x['sign']} {x['term']} ({names[x['role']]})" for x in m["equation"]))
    if not got:
        sys.exit("Fill 'money' in the brand's roles.json first: " + ", ".join(i["key"] for i in m["inputs"]))
    for f in m["formulas"]:
        print(f"{f['name']}: {got[f['key']]}  ({f['is']})")


def cmd_template(_a):
    data = load()
    out = {
        "about": "Who holds each role for this brand, this brand's targets, and any call the owner has granted. The roles themselves are in components/roles/roles.json and never change per brand. A holder is a person's short id or agent:<name>; the first holder answers for the role's number. Leave a target empty until there is a real number for it. A grant is the owner's own act: only the owner turns one to true.",
        "money": {i["key"]: None for i in data["model"]["money"]["inputs"]},
        "assign": {},
    }
    for r in data["roles"]:
        keys = [r["number"]["target_key"]] + [c["target_key"] for c in r.get("counts", [])]
        row = {"holders": [], "targets": {k: None for k in keys}, "spend_cap": None, "token_budget": None}
        if r.get("calls"):
            row["grants"] = {g["call"]: False for g in r["calls"]}
        row["changed_this_month"] = ""
        out["assign"][r["id"]] = row
    TEMPLATE.write_text(json.dumps(out, indent=1) + "\n")
    print(f"Wrote {TEMPLATE.relative_to(ROOT)}")


def cmd_export(_a):
    data = load()
    data["coverage"] = coverage(data)
    print(json.dumps(data, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check").set_defaults(fn=cmd_check)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    p = sub.add_parser("resolve"); p.add_argument("name"); p.set_defaults(fn=cmd_resolve)
    p = sub.add_parser("card"); p.add_argument("role"); p.add_argument("--brand"); p.set_defaults(fn=cmd_card)
    p = sub.add_parser("agent"); p.add_argument("role"); p.add_argument("--brand"); p.set_defaults(fn=cmd_agent)
    p = sub.add_parser("brief"); p.add_argument("role"); p.add_argument("--brand", required=True); p.add_argument("--month"); p.set_defaults(fn=cmd_brief)
    p = sub.add_parser("money"); p.add_argument("--brand", required=True); p.set_defaults(fn=cmd_money)
    sub.add_parser("template").set_defaults(fn=cmd_template)
    sub.add_parser("export").set_defaults(fn=cmd_export)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
