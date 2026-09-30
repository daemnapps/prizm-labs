#!/usr/bin/env python3
"""The doctrine's declared test.

    python3 components/marketing-doctrine/test_doctrine.py

No pytest, no network, no dependency — it runs wherever python3 runs. It
proves the things that would quietly rot: the counts are the counts, the
section list is Damon's nine plus the six added on the 2026-09-18 ask and
nothing coined, every line pointer is inside
the book, the slices on disk are what the JSON renders, and the pronoun gate
is green on everything this component ships.
"""

import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True      # a test run leaves no __pycache__ behind

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import lint_prompts          # noqa: E402
import render                # noqa: E402

BOOK_LINES = 6407

# Damon's own nine, in the order Damon lists them. This is the spine and it
# never reorders.
DAMON_SECTION_IDS = [
    "hook", "problem", "failed-solutions", "root-cause", "unique-mechanism",
    "solution", "product", "offer", "call-to-action",
]
# The six a fundamental direct-response reading said the nine were missing,
# added 2026-09-18 on Damon's ask — each carries an `added` line in the JSON so
# any of them can be struck without archaeology.
ADDED_SECTION_IDS = [
    "identification", "agitation", "proof", "transformation", "objections",
    "urgency",
]
SECTION_IDS = DAMON_SECTION_IDS + ADDED_SECTION_IDS
TECHNIQUE_IDS = [
    "intensification", "identification", "gradualization", "redefinition",
    "mechanization", "concentration", "camouflage",
]
AWARENESS_IDS = [
    "most-aware", "product-aware", "solution-aware", "problem-aware", "unaware",
]
SLICE_NAMES = [name for name, _ in render.RENDERERS]

# The taste and delivery dials (Damon's ruling, 2026-09-18). Declared here so
# a value quietly disappearing is a failing test rather than a thinner prompt.
DIAL_IDS = ["humor", "delivery_style", "register", "pacing",
            "reference_world", "avoid"]
DIAL_VALUES = {
    "humor": ["none", "dry", "wry", "self-deprecating", "observational",
              "absurd", "broad"],
    "delivery_style": ["deadpan", "confessional", "teacher-explainer", "rant",
                       "storyteller", "hype", "plain-testimonial",
                       "deadly-sincere", "understatement", "interview-consult",
                       "reaction-duet", "hands-and-voiceover"],
    "register": ["staccato-urgent", "plain-flat", "warm-unhurried", "clinical",
                 "playful", "intimate-low"],
    "pacing": ["fast-open-slow-body", "escalating", "one-breath",
               "beat-and-pause", "list-stack"],
    "reference_world": ["laugh-at", "trust", "watch", "quote", "look", "sound"],
    "avoid": ["cringe-register", "ad-voice-tells"],
}
TASTE_RQ_IDS = {"RQ-17", "RQ-18", "RQ-19", "RQ-20", "RQ-21"}
# The spoken pass (Damon's ruling, 2026-09-19: "humans don't use em dashes
# when speaking"). Declared here so a level, a rule or a mark quietly
# disappearing is a failing test rather than a paragraph read as prose.
SPOKEN_RQ_IDS = {"RQ-22", "RQ-23", "RQ-24"}
SPOKEN_LEVELS = ["0 plain", "1 conversational", "2 casual", "3 slang", "4 in-group"]
SPOKEN_RULES = ["no-em-dash", "no-semicolon", "no-parenthesis", "ellipsis-is-the-breath",
                "one-idea-per-sentence", "fragments-allowed", "contractions-on",
                "pause-is-punctuation", "direct-address", "questions-to-the-viewer",
                "restart-once", "fillers-at-the-start"]
SPOKEN_MARKS = [",", ".", "?", "!", "...", "\u2014", "\u2013", ";", "(", "[tag]"]
PROFILE_SLOTS = {"age", "gender", "skin tone / ethnicity", "region", "language"}

_FAILURES = []


def check(label, ok, detail=""):
    if ok:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s%s" % (label, (" — " + detail) if detail else ""))
        _FAILURES.append(label)


def section(title):
    print("\n%s" % title)


def main():
    section("1. frameworks.json parses")
    try:
        data = json.loads((HERE / "frameworks.json").read_text())
        check("json parses", True)
    except Exception as exc:                      # noqa: BLE001
        check("json parses", False, str(exc))
        print("\nFAILED: 1 (cannot continue without the JSON)")
        return 1

    section("2. counts and ids")
    levels = data["awareness"]["levels"]
    stages = data["sophistication"]["stages"]
    techs = data["techniques"]
    secs = data["sections"]
    check("5 awareness levels", len(levels) == 5, "got %d" % len(levels))
    check("awareness ids are the five, in order",
          [l["id"] for l in levels] == AWARENESS_IDS, str([l["id"] for l in levels]))
    check("every level carries must / must_not / where_the_ad_may_begin",
          all(l.get("must") and l.get("must_not") and l.get("where_the_ad_may_begin")
              for l in levels))
    check("5 sophistication stages", len(stages) == 5, "got %d" % len(stages))
    check("every stage carries market_has_heard / lead_with",
          all(s.get("market_has_heard") and s.get("lead_with") for s in stages))
    check("category reset rule present", bool(data["sophistication"].get("category_reset")))
    check("7 techniques", len(techs) == 7, "got %d" % len(techs))
    check("technique ids are the seven",
          [t["id"] for t in techs] == TECHNIQUE_IDS, str([t["id"] for t in techs]))
    check("every technique carries definition / sub_methods / when / owning_stage /"
          " research_question / scene_shape",
          all(t.get("definition") and t.get("sub_methods") and t.get("when")
              and t.get("owning_stage") and t.get("research_question")
              and t.get("scene_shape") for t in techs))
    check("intensification enumerates 13 ways",
          len(techs[0]["sub_methods"]) == 13, "got %d" % len(techs[0]["sub_methods"]))
    sec_ids = [s["id"] for s in secs]
    check("%d sections" % len(SECTION_IDS), len(secs) == len(SECTION_IDS),
          "got %d" % len(secs))
    check("Damon's nine are present, in that order",
          [i for i in sec_ids if i in DAMON_SECTION_IDS] == DAMON_SECTION_IDS,
          str(sec_ids))
    check("the six added on that ask are present",
          [i for i in sec_ids if i in ADDED_SECTION_IDS] == ADDED_SECTION_IDS,
          str(sec_ids))
    check("no section outside those two lists",
          sorted(sec_ids) == sorted(SECTION_IDS),
          str(sorted(set(sec_ids) - set(SECTION_IDS))))
    check("every added section says when and why it was added",
          all(s.get("added") for s in secs if s["id"] in ADDED_SECTION_IDS))
    check("none of the original nine carries an added line",
          not any(s.get("added") for s in secs if s["id"] in DAMON_SECTION_IDS))
    check("every section names real techniques",
          all(t in TECHNIQUE_IDS for s in secs for t in s["techniques"]))
    check("every section names real awareness levels",
          all(lv in AWARENESS_IDS + ["every level"]
              for s in secs
              for key in ("needed_at", "usually_skipped_at")
              for lv in (s.get("awareness", {}).get(key) or [])))
    check("every crosswalk row names real sections",
          all(x in sec_ids for row in data["frameworks_crosswalk"]["rows"]
              for x in row["sections"]))
    check("desire carries the three dimensions",
          len(data["desire"]["dimensions"]) == 3)
    check("desire carries the physical-vs-functional rule",
          bool(data["desire"]["physical_vs_functional"]["rule"]))
    rqs = data["research_questions"]
    check("research questions present", len(rqs) >= 1, "got %d" % len(rqs))
    check("research question ids unique", len(set(q["id"] for q in rqs)) == len(rqs))
    check("every research question carries question / framework / tags / stages",
          all(q.get("question") and q.get("framework") and q.get("tags")
              and q.get("stages") for q in rqs))

    section("3. every line pointer is inside the book (1-%d)" % BOOK_LINES)
    bad = []
    for path in [HERE / "frameworks.json", HERE / "delivery.json",
                 HERE / "SCHWARTZ.md"] + \
                [HERE / "slices" / n for n in SLICE_NAMES]:
        if not path.exists():
            continue
        for m in re.finditer(r"L(\d+)", path.read_text()):
            n = int(m.group(1))
            if not 1 <= n <= BOOK_LINES:
                bad.append("%s:L%d" % (path.name, n))
    check("all L-pointers in range", not bad, ", ".join(bad[:5]))
    refs = re.findall(r'"ref"', (HERE / "frameworks.json").read_text())
    check("rows carry refs", len(refs) >= 50, "got %d" % len(refs))

    section("4. render is idempotent")
    first = render.render_all()
    second = render.render_all()
    check("two renders agree", first == second)
    check("every named slice is rendered",
          sorted(first) == sorted(SLICE_NAMES), str(sorted(first)))
    stale = [n for n in SLICE_NAMES
             if not (HERE / "slices" / n).exists()
             or (HERE / "slices" / n).read_text() != first[n]]
    check("slices on disk match the JSON", not stale, ", ".join(stale))
    check("render.py --check agrees", render.main(["--check"]) == 0)
    check("each slice stands alone (names its own bound variable)",
          all("Bound as `{" in first[n] for n in SLICE_NAMES))

    section("5. the pronoun gate is green on what this component ships")
    targets = [HERE / "SCHWARTZ.md", HERE / "README.md"] + \
              [HERE / "slices" / n for n in SLICE_NAMES]
    targets = [t for t in targets if t.exists()]
    found, unreadable = lint_prompts.check([str(t) for t in targets])
    check("no gendered pronoun in %d file(s)" % len(targets), found == 0 and unreadable == 0,
          "%d finding(s)" % found)
    check("the linter catches one when it is there",
          lint_prompts.findings_in_text("the viewer sees her own face") == [(1, 17, "her")])
    check("the linter exempts a fenced block",
          lint_prompts.findings_in_text("```\nher\n```") == [])
    check("the linter exempts quoted speech",
          lint_prompts.findings_in_text('the speaker said "her skin"') == [])

    section("6. ad-frameworks.json — the second door's own file")
    ad_path = HERE / "ad-frameworks.json"
    if not ad_path.exists():
        check("ad-frameworks.json exists", False, "not built yet")
    else:
        ad = json.loads(ad_path.read_text())
        rows = ad["frameworks"]
        crosswalk_names = {row["framework"] for row in data["frameworks_crosswalk"]["rows"]}
        check("every crosswalk row has a matching ad-frameworks row",
              crosswalk_names <= {r["name"] for r in rows},
              str(crosswalk_names - {r["name"] for r in rows}))
        check("every row's sections are real section ids",
              all(s["id"] in sec_ids for r in rows for s in r["sections"]))
        check("every row's techniques are real technique ids",
              all(s["technique"] in TECHNIQUE_IDS for r in rows for s in r["sections"]))
        check("every row's awareness entry/exit are real levels",
              all(r["awareness"]["entry"] in AWARENESS_IDS
                  and r["awareness"]["exit"] in AWARENESS_IDS for r in rows))
        check("every row declares status seed or proven",
              all(r["status"] in ("seed", "proven") for r in rows))
        check("every row ids are unique",
              len({r["id"] for r in rows}) == len(rows))
        check("no row's source claims 'proven' work without Damon's status",
              all(r["status"] == "proven" or not r["source"].startswith("proven")
                  for r in rows))
        check("ad-frameworks.md is bound as {ad_frameworks}",
              "{ad_frameworks}" in (HERE / "slices" / "ad-frameworks.md").read_text()
              if (HERE / "slices" / "ad-frameworks.md").exists() else False)

    section("7. delivery.json — the taste and delivery dials")
    del_path = HERE / "delivery.json"
    if not del_path.exists():
        check("delivery.json exists", False, "not built yet")
    else:
        dl = json.loads(del_path.read_text())
        dials = {d_["id"]: d_ for d_ in dl["dials"]}
        check("the six dials are present, in order",
              [d_["id"] for d_ in dl["dials"]] == DIAL_IDS,
              str([d_["id"] for d_ in dl["dials"]]))
        for dial_id, want in DIAL_VALUES.items():
            got = [v["id"] for v in dials.get(dial_id, {}).get("values", [])]
            check("`%s` carries its declared values" % dial_id, got == want, str(got))
        check("every dial states its own rule and receipt rule",
              all(d_.get("rule") and d_.get("receipt_rule") for d_ in dl["dials"]))
        check("the receipt rule and the never-a-voice rule are both stated",
              bool(dl.get("rule")) and bool(dl.get("voice_rule")))
        vals = [(d_["id"], v) for d_ in dl["dials"] for v in d_["values"]]
        check("every value says what it is, when it fits, its risk and its receipt",
              all(v.get("what") and v.get("when") and v.get("risk")
                  and v.get("receipt") and v.get("source") for _, v in vals),
              str([f"{d}.{v['id']}" for d, v in vals
                   if not (v.get("what") and v.get("when") and v.get("risk")
                           and v.get("receipt") and v.get("source"))]))
        check("every value names real awareness levels",
              all(x in AWARENESS_IDS for _, v in vals for x in v["fits"]["awareness"]),
              str(sorted({x for _, v in vals for x in v["fits"]["awareness"]}
                         - set(AWARENESS_IDS))))
        check("every value names real sections",
              all(x in SECTION_IDS for _, v in vals for x in v["fits"]["sections"]),
              str(sorted({x for _, v in vals for x in v["fits"]["sections"]}
                         - set(SECTION_IDS))))
        fmts = {"any"}
        if (HERE / "ad-frameworks.json").exists():
            for f_ in json.loads((HERE / "ad-frameworks.json").read_text())["frameworks"]:
                fmts |= set(f_["formats_fit"])
        check("every value names formats the ad-framework rows also use",
              all(x in fmts for _, v in vals for x in v["fits"]["formats"]),
              str(sorted({x for _, v in vals for x in v["fits"]["formats"]} - fmts)))
        check("every delivery style names a real technique it serves",
              all(v.get("serves") in TECHNIQUE_IDS
                  for d_, v in vals if d_ == "delivery_style"),
              str([v["id"] for d_, v in vals
                   if d_ == "delivery_style" and v.get("serves") not in TECHNIQUE_IDS]))
        check("every delivery style names camera, rhythm and pace",
              all(v.get("camera") and v.get("rhythm") and v.get("pace")
                  for d_, v in vals if d_ == "delivery_style"))
        refd = [(d_, v) for d_, v in vals if v.get("ref")]
        check("a schwartz-sourced value carries a ref, a craft one does not",
              all(v["source"] != "craft" for _, v in refd)
              and all(v.get("ref") for _, v in vals if v["source"] != "craft"),
              str([f"{d}.{v['id']} ({v['source']})" for d, v in vals
                   if bool(v.get("ref")) != (v["source"] != "craft")]))
        check("some value is schwartz-sourced", bool(refd), "none refd")
        check("the humor rule keeps humor off the proof and offer beats",
              "proof" in dials["humor"]["rule"] and "offer" in dials["humor"]["rule"])
        check("the reference-world rule says a reference is never a voice",
              "voice" in dials["reference_world"]["rule"]
              and "cloned" in dials["reference_world"]["rule"])
        check("delivery.md is bound as {delivery}",
              "{delivery}" in (HERE / "slices" / "delivery.md").read_text()
              if (HERE / "slices" / "delivery.md").exists() else False)
        rq_ids = {q["id"] for q in data["research_questions"]}
        check("the five taste questions are in the bank",
              TASTE_RQ_IDS <= rq_ids, str(sorted(TASTE_RQ_IDS - rq_ids)))
        taste_qs = [q for q in data["research_questions"] if q["id"] in TASTE_RQ_IDS]
        check("every taste question names a dial as its framework",
              all(q["framework"].startswith("delivery.")
                  and q["framework"].split(".", 1)[1] in dials for q in taste_qs),
              str([q["framework"] for q in taste_qs]))
        check("the taste questions use the two new language tags",
              {"taste", "cringe"} <= {t_ for q in taste_qs for t_ in q["tags"]})

    section("the position gate — every brand's position.md has the template's shape (2026-09-19)")
    import lint_position      # noqa: E402
    brands = sorted(p for p in [*(HERE.parent.parent / "brands").glob("*/position.md"),
                                         *(HERE.parent.parent / "brands").glob("*/brand-identity/position.md")]
                    if not p.relative_to(HERE.parent.parent / "brands").parts[0].startswith("_"))
    check("brands/_TEMPLATE/brand-identity/position.md exists and is brand-agnostic",
          lint_position.TEMPLATE.is_file()
          and not lint_position.check(lint_position.TEMPLATE, is_template=True),
          str(lint_position.check(lint_position.TEMPLATE, is_template=True)
              if lint_position.TEMPLATE.is_file() else "missing"))
    check("the template's fourteen slots are the ones the prompts read",
          {"LINE", "SPINE", "PROBLEM WORD", "MECHANISM", "MECHANISM NAME", "DISPLACES",
           "MARKET STAGE", "STAGE WHY", "LEADS WITH", "NEVER", "confirmed by"}
          <= set(lint_position.SLOTS))
    check("every brand has a position.md", bool(brands), "no brand has one")
    for b in brands:
        fs = lint_position.check(b)
        check("%s/position.md matches the template" % b.parent.name, not fs, "; ".join(fs))

    section("the story gate — every brand's story.md has the template's shape (2026-09-19)")
    import lint_story         # noqa: E402
    stories = sorted(p for p in [*(HERE.parent.parent / "brands").glob("*/story.md"),
                                          *(HERE.parent.parent / "brands").glob("*/brand-identity/story.md")]
                     if not p.relative_to(HERE.parent.parent / "brands").parts[0].startswith("_"))
    check("brands/_TEMPLATE/brand-identity/story.md exists and is brand-agnostic",
          lint_story.TEMPLATE.is_file()
          and not lint_story.check(lint_story.TEMPLATE, is_template=True),
          str(lint_story.check(lint_story.TEMPLATE, is_template=True)
              if lint_story.TEMPLATE.is_file() else "missing"))
    for s in stories:
        fs = lint_story.check(s)
        check("%s/story.md matches the template" % s.parent.name, not fs, "; ".join(fs))

    section("8. spoken.json — the rules of spoken copy")
    sp_path = HERE / "spoken.json"
    if not sp_path.exists():
        check("spoken.json exists", False, "not built yet")
    else:
        sp = json.loads(sp_path.read_text())
        check("the ruling, the measurement and the receipt rule are stated",
              bool(sp.get("added")) and bool(sp.get("measured")) and bool(sp.get("rule"))
              and bool(sp.get("voiceprint_rule")))
        rules = sp["written_vs_spoken"]
        check("the written-vs-spoken table carries every declared rule, in order",
              [r["id"] for r in rules] == SPOKEN_RULES, str([r["id"] for r in rules]))
        check("every rule says written / spoken / why and carries at least one URL receipt",
              all(r.get("written") and r.get("spoken") and r.get("why")
                  and r.get("receipts") and all(x.get("url", "").startswith("http")
                                                for x in r["receipts"]) for r in rules),
              str([r["id"] for r in rules if not r.get("receipts")]))
        levels = sp["levels"]
        check("the five colloquialism levels, in order",
              [l["label"] for l in levels] == SPOKEN_LEVELS, str([l["label"] for l in levels]))
        check("every level says what it allows (contractions · fillers · markers · slang · in-words), a pattern, fits and a receipt rule",
              all(set(l["allows"]) == {"contractions", "fillers", "discourse_markers", "slang", "in_words"}
                  and l.get("pattern") and l.get("fits") and l.get("receipt_rule") and l.get("source")
                  for l in levels))
        check("level 3 and 4 are receipted to rows, never invented",
              all("row" in l["receipt_rule"].lower() and ("quoted" in l["receipt_rule"].lower()
                  or "quotes" in l["receipt_rule"].lower())
                  for l in levels if l["id"] in ("3", "4")))
        check("level 4 never sits on a claim",
              "proof" in levels[4]["receipt_rule"] and "offer" in levels[4]["receipt_rule"])
        check("every level names real sections",
              all(x in SECTION_IDS for l in levels for x in l["fits"]["sections"]),
              str(sorted({x for l in levels for x in l["fits"]["sections"]} - set(SECTION_IDS))))
        check("every level names real registers",
              all(x in DIAL_VALUES["register"] for l in levels for x in l["fits"]["registers"]))
        check("every level names real delivery styles",
              all(x in DIAL_VALUES["delivery_style"] for l in levels for x in l["fits"]["delivery_styles"]))
        recipes = sp["register_recipes"]["recipes"]
        check("a register recipe for every delivery style the dials carry, and no other",
              sorted(r["delivery_style"] for r in recipes) == sorted(DIAL_VALUES["delivery_style"]),
              str(sorted(r["delivery_style"] for r in recipes)))
        check("every recipe names sentence length, fillers, markers, pause density, questions, restart, levels, wpm and voice settings",
              all(r.get("sentence_length") and isinstance(r.get("fillers"), list)
                  and isinstance(r.get("markers"), list) and r.get("pause_density")
                  and r.get("questions") and isinstance(r.get("restart"), bool)
                  and r.get("levels") and r.get("wpm") and r.get("voice_settings")
                  and r.get("source") for r in recipes))
        check("every recipe's levels are declared levels",
              all(x in [l["id"] for l in levels] for r in recipes for x in r["levels"]))

        def inside(rng, lo, hi):
            return lo <= rng[0] <= rng[1] <= hi
        check("every recipe's voice settings sit inside the model's own limits (stability/style 0–1, speed 0.7–1.2)",
              all(inside(r["voice_settings"]["stability"], 0, 1)
                  and inside(r["voice_settings"]["style"], 0, 1)
                  and inside(r["voice_settings"]["speed"], 0.7, 1.2) for r in recipes))
        check("the settings doc and the wpm doc are cited",
              sp["register_recipes"]["settings_doc"].startswith("http")
              and sp["register_recipes"]["wpm_doc"].startswith("http"))
        pm = sp["punctuation_map"]
        marks = [m["mark"] for m in pm["marks"]]
        check("the punctuation map is for eleven_multilingual_v2 and says why",
              pm["model"] == "eleven_multilingual_v2" and "stitching" in pm["model_why"])
        check("the map covers comma, full stop, question, exclamation, ellipsis, both dashes, semicolon, parenthesis and the bracketed tag",
              all(m in marks for m in SPOKEN_MARKS), str(sorted(set(SPOKEN_MARKS) - set(marks))))
        check("the map says what the break tag does and whether v2 is named",
              any(m["mark"].startswith("<break") and "v3" in m["does"] for m in pm["marks"]))
        check("every mark says what it does, what the take does and cites a source",
              all(m.get("does") and m.get("take", {}).get("action") in ("keep", "replace")
                  and m.get("source") for m in pm["marks"]))
        check("every replaced mark carries a regex pattern the take can run",
              all(re.compile(m["take"]["pattern"]) for m in pm["marks"]
                  if m["take"]["action"] == "replace"))
        check("the dash, the semicolon, the parenthesis and the tag are replaced; the comma, the full stop and the ellipsis (the breath) are kept",
              all(m["take"]["action"] == "replace" for m in pm["marks"]
                  if m["mark"] in ("\u2014", "\u2013", ";", "(", "[tag]"))
              and all(m["take"]["action"] == "keep" for m in pm["marks"] if m["mark"] in (",", ".", "?", "...", "…")))
        bands = sp["demographic_bands"]["bands"]
        check("every demographic band is keyed to a profile slot the demographics block carries",
              all(b["profile_slot"] in PROFILE_SLOTS for b in bands),
              str([b["profile_slot"] for b in bands if b["profile_slot"] not in PROFILE_SLOTS]))
        check("every band's markers are researched: each band carries markers, URL sources, levels and a measured line",
              all(b.get("markers_researched") and b.get("sources")
                  and all(s.startswith("http") for s in b["sources"])
                  and b.get("levels_available") and b.get("measured") for b in bands))
        check("the bands rule says a band is an option keyed to the profile, never an assumption",
              "never" in sp["demographic_bands"]["rule"] and "profile" in sp["demographic_bands"]["rule"])
        check("the bands point at the brand's own measured creators",
              "VOICEPRINTS.md" in sp["demographic_bands"]["our_creators"])
        rq_ids = {q["id"] for q in data["research_questions"]}
        check("the three spoken questions are in the bank",
              SPOKEN_RQ_IDS <= rq_ids, str(sorted(SPOKEN_RQ_IDS - rq_ids)))
        sqs = [q for q in data["research_questions"] if q["id"] in SPOKEN_RQ_IDS]
        check("every spoken question names the levels as its framework",
              all(q["framework"] == "spoken.levels" for q in sqs))
        check("the spoken questions carry in-word · subculture · community-voice · taste between them",
              {"in-word", "subculture", "community-voice", "taste"} <= {t_ for q in sqs for t_ in q["tags"]})
        check("every spoken question feeds the spice pass",
              all("4g-spice" in q["stages"] for q in sqs))
        check("spoken.md is bound as {spoken}",
              "{spoken}" in (HERE / "slices" / "spoken.md").read_text()
              if (HERE / "slices" / "spoken.md").exists() else False)
        check("spoken.md carries no em-dash inside a SPOKEN example",
              not re.search(r"\| `\w[\w-]*` \| [^|]*\| [^|]*\u2014", (HERE / "slices" / "spoken.md").read_text().split("## 2.")[0].split("|---|---|---|---|---|")[-1])
              if (HERE / "slices" / "spoken.md").exists() else False)

    print("")
    if _FAILURES:
        print("FAILED: %d" % len(_FAILURES))
        for f in _FAILURES:
            print("  - %s" % f)
        return 1
    print("PASSED: all checks green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
