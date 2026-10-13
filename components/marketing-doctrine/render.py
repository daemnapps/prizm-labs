#!/usr/bin/env python3
"""Render every slice in slices/ from frameworks.json.

    python3 components/marketing-doctrine/render.py [--check]

frameworks.json is the truth. The slices are what a prompt binds, one block
at a time, so a stage pays for the doctrine it uses and nothing else. Never
hand-edit a slice: edit the JSON and run this.

--check renders into memory and exits 1 if anything on disk differs (the
idempotence gate the test suite uses).
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
JSON_PATH = HERE / "frameworks.json"
SLICES = HERE / "slices"

HEAD = (
    "<!-- rendered from components/marketing-doctrine/frameworks.json by "
    "render.py — do not hand-edit -->"
)


def _ref(value):
    """A ref is one pointer or several; print them the same way every time."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return " ".join("[%s]" % r for r in value)
    return "[%s]" % value


def _lines(*parts):
    return "\n".join(parts)


def _open(title, var, blurb):
    return _lines(
        HEAD,
        "",
        "# %s" % title,
        "",
        "Bound as `{%s}`. Source: the doctrine component; refs are line pointers"
        " into the book, for verification only." % var,
        "",
        blurb,
        "",
    )


def desire(d):
    b = d["desire"]
    out = [_open("Desire — the one the ad runs on", "desire_dimensions", b["rule"] + " " + _ref(b["ref"]))]
    out.append("## The three dimensions — a lead desire must win all three\n")
    out.append("| Dimension | What it measures | The test | Ref |")
    out.append("|---|---|---|---|")
    for dim in b["dimensions"]:
        out.append("| %s | %s | %s | %s |" % (dim["name"], dim["measures"], dim["test"], _ref(dim["ref"])))
    out.append("")
    out.append("**One desire leads.** %s %s\n" % (b["lead_desire_rule"]["rule"], _ref(b["lead_desire_rule"]["ref"])))
    out.append("## Physical vs functional product\n")
    out.append("%s %s\n" % (b["physical_vs_functional"]["rule"], _ref(b["physical_vs_functional"]["ref"])))
    out.append("Physical facts are allowed back in for exactly five jobs:\n")
    for job in b["physical_vs_functional"]["physical_facts_may"]:
        out.append("- %s" % job)
    out.append("")
    out.append("**Dominant trait.** %s %s\n" % (b["dominant_trait"]["rule"], _ref(b["dominant_trait"]["ref"])))
    out.append("## Where desire comes from\n")
    for src in b["sources_of_desire"]:
        out.append("- **%s** — %s %s" % (src["id"], src["what"], _ref(src["ref"])))
    out.append("")
    out.append("Owning stages: %s\n" % ", ".join(b["owning_stage"]))
    return "\n".join(out)


def awareness(d):
    b = d["awareness"]
    out = [_open("Awareness — the five levels", "awareness_levels", b["rule"] + " " + _ref(b["ref"]))]
    for lv in b["levels"]:
        out.append("## %d. %s (`%s`)\n" % (lv["level"], lv["name"], lv["id"]))
        out.append("- **Knows:** %s" % lv["knows"])
        out.append("- **Must:** %s" % "; ".join(lv["must"]))
        if "the_seven_jobs" in lv:
            out.append("  - the seven jobs: %s" % ", ".join(lv["the_seven_jobs"]))
        out.append("- **Must NOT:** %s" % "; ".join(lv["must_not"]))
        out.append("- **Where the ad may begin:** %s" % lv["where_the_ad_may_begin"])
        out.append("- Ref: %s\n" % _ref(lv["ref"]))
    out.append("**Entry is not destination.** %s %s\n" % (b["entry_exit_rule"]["rule"], _ref(b["entry_exit_rule"]["ref"])))
    out.append("**The opening line.** %s %s\n" % (b["headline_rule"]["rule"], _ref(b["headline_rule"]["ref"])))
    out.append("**Dramatising it is a separate craft.** %s %s\n" % (
        b["headline_rule"]["verbalization"]["rule"], _ref(b["headline_rule"]["verbalization"]["ref"])))
    out.append("Owning stages: %s\n" % ", ".join(b["owning_stage"]))
    return "\n".join(out)


def sophistication(d):
    b = d["sophistication"]
    out = [_open("Sophistication — the five stages", "sophistication_stages", b["rule"] + " " + _ref(b["ref"]))]
    out.append("| Stage | The market has already heard | The ad must lead with | Ref |")
    out.append("|---|---|---|---|")
    for st in b["stages"]:
        out.append("| %d. %s (`%s`) | %s | %s | %s |" % (
            st["stage"], st["name"], st["id"], st["market_has_heard"], st["lead_with"], _ref(st["ref"])))
    out.append("")
    out.append("**Category reset.** %s %s\n" % (b["category_reset"]["rule"], _ref(b["category_reset"]["ref"])))
    out.append("Owning stages: %s\n" % ", ".join(b["owning_stage"]))
    return "\n".join(out)


def techniques(d):
    out = [_open(
        "The seven techniques", "techniques",
        "Body copy works three levers: desire (what is wanted), identification (roles"
        " and self-image), belief (what is already accepted). These seven are how all"
        " three get built. [L2166-2240]")]
    for t in d["techniques"]:
        out.append("## %s (`%s`) %s\n" % (t["name"], t["id"], _ref(t["ref"])))
        out.append("%s\n" % t["definition"])
        out.append("Sub-methods:\n")
        for s in t["sub_methods"]:
            out.append("%d. %s %s" % (s["n"], s["what"], _ref(s["ref"])))
        out.append("")
        if "method" in t:
            out.append("Method:\n")
            for s in t["method"]:
                out.append("%d. %s %s" % (s["n"], s["what"], _ref(s["ref"])))
            out.append("")
        if "rule" in t:
            out.append("**Rule.** %s\n" % t["rule"])
        if "campaign_level" in t:
            out.append("**Across a campaign.** %s %s\n" % (
                t["campaign_level"]["rule"], _ref(t["campaign_level"]["ref"])))
        if "price_cut_rule" in t:
            out.append("**A price cut needs its own mechanism.** %s %s\n" % (
                t["price_cut_rule"]["rule"], _ref(t["price_cut_rule"]["ref"])))
        out.append("- **When:** %s" % t["when"])
        out.append("- **Owning stage:** %s" % ", ".join(t["owning_stage"]))
        out.append("- **Research question:** %s" % t["research_question"])
        out.append("- **Scene shape:** %s\n" % t["scene_shape"])
    return "\n".join(out)


def sections(d):
    r = d["sections_rule"]
    out = [_open(
        "The sections — a vocabulary, not a sequence", "sections",
        r["rule"] + " " + _ref(r["ref"]))]
    out.append("**Awareness decides the sections.** " + r["awareness_rule"])
    out.append("")
    out.append("The list is the list — never one it does not carry, never a renamed one. Each names the techniques that build it and the levels that call for it.")
    out.append("")
    out.append("| Section | Id | What it does | Techniques | Needed at | Usually skipped at | Ref |")
    out.append("|---|---|---|---|---|---|---|")
    for s in d["sections"]:
        a = s.get("awareness", {})
        need = ", ".join(a.get("needed_at", []))
        if a.get("note"):
            need += " — " + a["note"]
        out.append("| %s | `%s` | %s | %s | %s | %s | %s |" % (
            s["name"], s["id"], s["what"], ", ".join(s["techniques"]),
            need, ", ".join(a.get("usually_skipped_at", [])) or "—", _ref(s["ref"])))
    out.append("")
    added = [s for s in d["sections"] if s.get("added")]
    if added:
        out.append("_Added %s: %s._" % (
            added[0]["added"], ", ".join("`%s`" % s["id"] for s in added)))
        out.append("")
    c = d["frameworks_crosswalk"]
    out.append("## How the common frameworks read into the vocabulary")
    out.append("")
    out.append(c["rule"])
    out.append("")
    out.append("| Framework the asset follows | Its parts, as section ids |")
    out.append("|---|---|")
    for row in c["rows"]:
        out.append("| %s | %s |" % (row["framework"], " → ".join("`%s`" % x for x in row["sections"])))
    out.append("")
    return "\n".join(out)


def mood(d):
    b = d["mood"]
    out = [_open("Mood", "mood", b["definition"] + " " + _ref(b["ref"]))]
    for r in b["rules"]:
        out.append("- **%s** — %s %s" % (r["id"], r["rule"], _ref(r["ref"])))
    out.append("")
    out.append("- **Owning stage:** %s" % ", ".join(b["owning_stage"]))
    out.append("- **Research question:** %s" % b["research_question"])
    out.append("- **Scene shape:** %s\n" % b["scene_shape"])
    return "\n".join(out)


def verification(d):
    b = d["verification"]
    out = [_open("Verification — where proof lands", "verification", b["definition"] + " " + _ref(b["ref"]))]
    out.append("Three things, related and NOT the same:\n")
    for t in b["three_distinct_things"]:
        out.append("- **%s** — %s %s" % (t["id"], t["what"], _ref(t["ref"])))
    out.append("")
    for r in b["rules"]:
        out.append("- **%s** — %s %s" % (r["id"], r["rule"], _ref(r["ref"])))
    out.append("")
    out.append("- **Owning stage:** %s" % ", ".join(b["owning_stage"]))
    out.append("- **Research question:** %s" % b["research_question"])
    out.append("- **Scene shape:** %s\n" % b["scene_shape"])
    return "\n".join(out)


def offer_close(d):
    b = d["offer_close"]
    out = [_open("Offer and close", "offer_close", b["what"] + " " + _ref(b["ref"]))]
    for r in b["rules"]:
        out.append("- **%s** — %s %s" % (r["id"], r["rule"], _ref(r["ref"])))
    out.append("")
    out.append("Owning stage: %s\n" % ", ".join(b["owning_stage"]))
    return "\n".join(out)


def research_questions(d):
    out = [_open(
        "The research question bank", "research_questions",
        "A judgment call that cannot be answered from evidence is a research question,"
        " not a guess. Each row names the tags that answer it in the language bank and"
        " the stages it feeds. A finding is a direction, never a finished line.")]
    out.append("| Id | Question | Framework | Tags | Feeds | Ref |")
    out.append("|---|---|---|---|---|---|")
    for q in d["research_questions"]:
        out.append("| %s | %s | %s | %s | %s | %s |" % (
            q["id"], q["question"], q["framework"],
            ", ".join("`%s`" % t for t in q["tags"]),
            ", ".join(q["stages"]), _ref(q["ref"])))
    out.append("")
    return "\n".join(out)


DELIVERY_JSON_PATH = HERE / "delivery.json"


def delivery(d):
    """Taste and delivery — components/marketing-doctrine/delivery.json, a
    sibling of frameworks.json like ad-frameworks.json. `d` (frameworks.json)
    is read only to flag a section, awareness level or technique a dial names
    that the doctrine no longer carries; the slice's content comes from
    DELIVERY_JSON_PATH."""
    b = json.loads(DELIVERY_JSON_PATH.read_text())
    known_sec = {s["id"] for s in d.get("sections", [])}
    known_aw = {l["id"] for l in d.get("awareness", {}).get("levels", [])}
    known_tech = {t["id"] for t in d.get("techniques", [])}

    def flag(ids, known):
        return ", ".join("`%s`%s" % (x, "" if x in known else " \u26a0") for x in ids) or "\u2014"

    out = [_open("Taste and delivery \u2014 the dials", "delivery", b["what"])]
    out.append("**The receipt rule.** %s\n" % b["rule"])
    out.append("**Never a voice.** %s\n" % b["voice_rule"])
    out.append("| Dial | What it sets | Values |")
    out.append("|---|---|---|")
    for dl in b["dials"]:
        out.append("| **%s** (`%s`) | %s | %s |" % (
            dl["name"], dl["id"], dl["what"],
            " \u00b7 ".join("`%s`" % v["id"] for v in dl["values"])))
    out.append("")
    for dl in b["dials"]:
        out.append(("## %s (`%s`) %s" % (dl["name"], dl["id"],
                     _ref(dl.get("ref")))).rstrip() + "\n")
        out.append("%s\n" % dl["what"])
        out.append("**Rule.** %s\n" % dl["rule"])
        out.append("**Receipt.** %s\n" % dl["receipt_rule"])
        if dl.get("ref_why"):
            out.append("_Why that pointer:_ %s\n" % dl["ref_why"])
        for v in dl["values"]:
            out.append(("### `%s` %s" % (v["id"],
                         _ref(v.get("ref")))).rstrip() + "\n")
            out.append("- **What it is:** %s" % v["what"])
            if v.get("camera"):
                out.append("- **Camera:** %s" % v["camera"])
            if v.get("rhythm"):
                out.append("- **Line rhythm:** %s" % v["rhythm"])
            if v.get("pace"):
                out.append("- **Pace:** %s" % v["pace"])
            if v.get("serves"):
                out.append("- **Technique it serves:** `%s`%s" % (
                    v["serves"], "" if v["serves"] in known_tech else " \u26a0"))
            out.append("- **When it fits:** %s" % v["when"])
            out.append("  - levels: %s" % flag(v["fits"]["awareness"], known_aw))
            out.append("  - sections: %s" % flag(v["fits"]["sections"], known_sec))
            out.append("  - formats: %s" % ", ".join("`%s`" % x for x in v["fits"]["formats"]))
            out.append("- **Risk:** %s" % v["risk"])
            out.append("- **Receipt it needs:** %s" % v["receipt"])
            out.append("- **Source:** %s\n" % v["source"])
    return "\n".join(out)


AD_JSON_PATH = HERE / "ad-frameworks.json"


def ad_frameworks(d):
    """The second door's own file — components/marketing-doctrine/ad-frameworks.json,
    a sibling of frameworks.json rather than a key inside it. `d` (frameworks.json)
    is read only to flag a section id ad-frameworks.json carries that the doctrine
    no longer does; the slice's own content comes from AD_JSON_PATH."""
    a = json.loads(AD_JSON_PATH.read_text())
    known = {s["id"] for s in d.get("sections", [])}
    out = [_open("Ad frameworks — the second door", "ad_frameworks", a["what"])]
    out.append(a["rule"])
    out.append("")
    out.append("**Status.** " + " ".join(
        "**%s** — %s." % (k, v) for k, v in a["status_values"].items()))
    out.append("")
    out.append("**Promotion.** %s" % a["promote_rule"])
    out.append("")
    out.append("| Framework | Status | Sections (technique) | Awareness | "
                "Sophistication | Formats it fits | Source |")
    out.append("|---|---|---|---|---|---|---|")
    for f in a["frameworks"]:
        secs = ", ".join("`%s` (%s)%s" % (s["id"], s["technique"],
                          "" if s["id"] in known else " ⚠")
                          for s in f["sections"])
        out.append("| %s (`%s`) | %s | %s | `%s`→`%s` | %s | %s | %s |" % (
            f["name"], f["id"], f["status"], secs,
            f["awareness"]["entry"], f["awareness"]["exit"],
            ", ".join(f["sophistication"]), ", ".join(f["formats_fit"]),
            f["source"]))
    out.append("")
    for f in a["frameworks"]:
        out.append("## %s (`%s`)\n" % (f["name"], f["id"]))
        out.append("%s\n" % f["what"])
        out.append("| # | Section | Technique | Scene shape |")
        out.append("|---|---|---|---|")
        for i, s in enumerate(f["sections"], 1):
            flag = "" if s["id"] in known else " — ⚠ not a section frameworks.json carries"
            out.append("| %d | `%s`%s | %s | %s |" % (i, s["id"], flag, s["technique"], s["shape"]))
        out.append("")
        out.append("- **Ref:** %s\n" % _ref(f.get("ref")))
    return "\n".join(out)


SPOKEN_JSON_PATH = HERE / "spoken.json"


def spoken(d):
    """Spoken copy — components/marketing-doctrine/spoken.json, a sibling of
    delivery.json. `d` (frameworks.json) is read to flag a section the levels
    name that the doctrine no longer carries and to print the three spoken
    research questions; delivery.json is read to flag a delivery style a
    recipe names that the dials no longer carry."""
    b = json.loads(SPOKEN_JSON_PATH.read_text())
    known_sec = {s["id"] for s in d.get("sections", [])}
    styles = set()
    if DELIVERY_JSON_PATH.exists():
        for dl in json.loads(DELIVERY_JSON_PATH.read_text())["dials"]:
            if dl["id"] == "delivery_style":
                styles = {v["id"] for v in dl["values"]}

    def flag(ids, known):
        return ", ".join("`%s`%s" % (x, "" if x in known else " \u26a0") for x in ids) or "\u2014"

    def links(rows):
        return "; ".join("[%s](%s)" % (r.get("note") or r["url"], r["url"]) for r in rows)

    out = [_open("Spoken copy \u2014 written for the mouth", "spoken", b["what"])]
    out.append("**Measured.** %s\n" % b["measured"])
    out.append("**The rule.** %s\n" % b["rule"])
    out.append("**Our creators outrank the web.** %s\n" % b["voiceprint_rule"])

    t = b.get("the_thought") or {}
    if t:
        out.append("## 0. The unit is the thought, not the sentence\n")
        out.append("**Ruled.** %s\n" % t["ruled"])
        out.append("%s\n" % t["rule"])
        ref = t.get("reference") or {}
        out.append("| | |\n|---|---|")
        out.append("| The prose | %s |" % ref.get("prose", ""))
        out.append("| Chopped (wrong) | %s |" % ref.get("chopped_wrong", ""))
        out.append("| **Spoken (right)** | **%s** |" % ref.get("spoken_right", ""))
        out.append("| Why | %s |\n" % ref.get("why", ""))
        out.append("| Mark | What it is in speech |\n|---|---|")
        for k, v in (t.get("marks") or {}).items():
            out.append("| `%s` | %s |" % (k, v))
        out.append("")
        out.append("**Measured.** %s\n" % t.get("measured", ""))
        out.append("**The test.** %s\n" % t.get("test", ""))
        vs = b.get("voice_settings_ruled") or {}
        if vs:
            out.append("**The read Damon chose (%s).** stability %s · similarity %s · style %s · speed %s · speaker boost %s. %s\n" % (
                vs.get("ruled", ""), vs.get("stability"), vs.get("similarity_boost"), vs.get("style"),
                vs.get("speed"), "off" if not vs.get("use_speaker_boost") else "on", vs.get("note", "")))
    out.append("## 1. Written vs spoken \u2014 the rules of spoken copy\n")
    out.append("| Rule | Written | Spoken | Why | Receipt |")
    out.append("|---|---|---|---|---|")
    for r in b["written_vs_spoken"]:
        out.append("| `%s` | %s | %s | %s | %s |" % (
            r["id"], r["written"], r["spoken"], r["why"], links(r["receipts"])))
    out.append("")

    out.append("## 2. Colloquialism levels \u2014 the dial\n")
    out.append("| Level | What it is | Contractions | Fillers | Discourse markers | Slang | In-words |")
    out.append("|---|---|---|---|---|---|---|")
    for lv in b["levels"]:
        a = lv["allows"]
        out.append("| **%s** | %s | %s | %s | %s | %s | %s |" % (
            lv["label"], lv["what"], a["contractions"], a["fillers"],
            a["discourse_markers"], a["slang"], a["in_words"]))
    out.append("")
    for lv in b["levels"]:
        out.append("### `%s`\n" % lv["label"])
        out.append("- **Pattern:** %s" % lv["pattern"])
        out.append("- **Fits:** registers %s \u00b7 delivery styles %s \u00b7 sections %s" % (
            ", ".join("`%s`" % x for x in lv["fits"]["registers"]),
            flag(lv["fits"]["delivery_styles"], styles),
            flag(lv["fits"]["sections"], known_sec)))
        out.append("- **Receipt rule:** %s" % lv["receipt_rule"])
        out.append("- **Source:** %s\n" % lv["source"])

    rr = b["register_recipes"]
    out.append("## 3. Register recipes \u2014 per delivery style\n")
    out.append("%s\n" % rr["what"])
    out.append("**Voice settings.** %s Doc: %s\n" % (rr["settings_note"], rr["settings_doc"]))
    out.append("**Words per minute.** %s Doc: %s\n" % (rr["wpm_note"], rr["wpm_doc"]))
    out.append("| Delivery style | Sentence length | Fillers | Markers | Pause density | Questions | Restart | Levels | WPM | stability | style | speed | Source |")
    out.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rr["recipes"]:
        vs = r["voice_settings"]
        out.append("| %s | %s | %s | %s | %s | %s | %s | %s | %d\u2013%d | %.2f\u2013%.2f | %.2f\u2013%.2f | %.2f\u2013%.2f | %s |" % (
            flag([r["delivery_style"]], styles), r["sentence_length"],
            ", ".join(r["fillers"]) or "none", ", ".join(r["markers"]) or "none",
            r["pause_density"], r["questions"], "once" if r["restart"] else "no",
            ", ".join(r["levels"]), r["wpm"][0], r["wpm"][1],
            vs["stability"][0], vs["stability"][1], vs["style"][0], vs["style"][1],
            vs["speed"][0], vs["speed"][1],
            r["source"] if r["source"] != "craft" else "craft \u2014 " + r["source_note"]))
    out.append("")

    pm = b["punctuation_map"]
    out.append("## 4. The voice-model punctuation map \u2014 `%s`\n" % pm["model"])
    out.append("%s\n" % pm["what"])
    out.append("**Why this model.** %s\n" % pm["model_why"])
    out.append("Doc: %s\n" % pm["doc"])
    out.append("| Mark | Name | What it does on the model | The take | Write it? | Source |")
    out.append("|---|---|---|---|---|---|")
    for m in pm["marks"]:
        take = m["take"]
        tk = "keep" if take["action"] == "keep" else "replace with `%s`" % take.get("with", "")
        mark = m["mark"].replace("|", "\\|")
        out.append("| `%s` | %s | %s | %s | %s | %s |" % (
            mark, m["name"], m["does"], tk, m["write_it"], m["source"]))
    out.append("")
    sm = pm["settings_map"]
    out.append("**The settings, in one line each** (doc: %s): " % sm["doc"] + " \u00b7 ".join(
        "`%s` \u2014 %s" % (k, v) for k, v in sm.items() if k != "doc") + "\n")

    db = b["demographic_bands"]
    out.append("## 5. Demographic bands \u2014 options keyed to the profile\n")
    out.append("%s\n" % db["what"])
    out.append("**Rule.** %s\n" % db["rule"])
    out.append("**Our creators.** %s\n" % db["our_creators"])
    for band in db["bands"]:
        out.append("### `%s` \u2014 profile slot `%s`: %s\n" % (band["id"], band["profile_slot"], band["band"]))
        for mk in band["markers_researched"]:
            out.append("- %s" % mk)
        out.append("- **Levels available:** %s" % ", ".join("`%s`" % x for x in band["levels_available"]))
        out.append("- **Measured:** %s" % band["measured"])
        out.append("- **Sources:** %s\n" % " \u00b7 ".join(band["sources"]))

    qs = [q for q in d.get("research_questions", []) if q["framework"].startswith("spoken.")]
    if qs:
        out.append("## 6. The spoken research questions \u2014 what the gatherer fills\n")
        out.append("| Id | Question | Tags | Feeds |")
        out.append("|---|---|---|---|")
        for q in qs:
            out.append("| %s | %s | %s | %s |" % (
                q["id"], q["question"], ", ".join("`%s`" % x for x in q["tags"]), ", ".join(q["stages"])))
        out.append("")
    return "\n".join(out)


EMOTION_JSON_PATH = HERE / "emotion.json"


def emotion(d):
    """The emotional map — components/marketing-doctrine/emotion.json, a
    sibling of delivery.json. `d` (frameworks.json) is read only to flag a
    section or awareness level a feeling names that the doctrine no longer
    carries; ad-frameworks.json to flag an arc's framework that is gone."""
    b = json.loads(EMOTION_JSON_PATH.read_text())
    known_sec = {s["id"] for s in d.get("sections", [])}
    known_aw = {l["id"] for l in d.get("awareness", {}).get("levels", [])}
    known_fw = set()
    if AD_JSON_PATH.exists():
        known_fw = {f["id"] for f in json.loads(AD_JSON_PATH.read_text())["frameworks"]}
    rec = {r["id"]: r for r in b["receipts"]}

    def flag(ids, known):
        return ", ".join("`%s`%s" % (x, "" if x in known else " \u26a0") for x in ids) or "\u2014"

    def src(row):
        return ("%s %s" % (row["source"], _ref(row.get("ref")))).rstrip()

    out = [_open("The emotional map \u2014 what each beat makes the viewer feel", "emotion", b["what"])]
    out.append("**Read off the swipe.** %s\n" % b["rule"])
    out.append("**Shown, never said.** %s\n" % b["show_rule"])
    out.append("## 1. The rules\n")
    for r in b["rules"]:
        out.append("- **%s** \u2014 %s _(%s)_" % (r["id"], r["rule"], src(r)))
    out.append("")
    out.append("## 2. The five points every map names\n")
    for p_ in b["points"]:
        out.append("- **%s** (`%s`) \u2014 %s %s _(%s)_" % (p_["name"], p_["id"], p_["what"], p_["rule"], src(p_)))
    out.append("")
    out.append("## 3. The feelings \u2014 the only words a beat's feeling is spelled in\n")
    out.append("| Feeling | Valence | What the viewer feels | What on screen makes it |")
    out.append("|---|---|---|---|")
    for f in b["feelings"]:
        out.append("| `%s` | %s | %s | %s |" % (f["id"], f["valence"], f["what"], f["on_screen"]))
    out.append("")
    for f in b["feelings"]:
        out.append(("### `%s` %s" % (f["id"], _ref(f.get("ref")))).rstrip() + "\n")
        out.append("- **Fits:** sections %s \u00b7 levels %s" % (
            flag(f["fits"]["sections"], known_sec), flag(f["fits"]["awareness"], known_aw)))
        out.append("- **Risk:** %s" % f["risk"])
        out.append("- **Source:** %s\n" % f["source"])
    out.append("## 4. Intensity\n")
    for i in b["intensity"]:
        out.append("- **%d** \u2014 %s" % (i["level"], i["what"]))
    out.append("")
    out.append("## 5. The arcs \u2014 the shape of the whole piece\n")
    for a in b["arcs"]:
        out.append("- **%s** (`%s`) \u2014 %s %s Frameworks: %s. _(%s)_" % (
            a["name"], a["id"], a["shape"] + ".", a["what"], flag(a["frameworks"], known_fw), a["source"]))
    out.append("")
    out.append("## 6. What carries a feeling \u2014 the director's levers\n")
    for c in b["carriers"]:
        out.append("- **%s** (`%s`) \u2014 %s" % (c["name"], c["id"], c["what"]))
    out.append("")
    out.append("## 7. The map, exactly as a stage prints it\n")
    out.append("```\n%s\n```\n" % b["map_format"])
    out.append("## 8. Receipts\n")
    for r in b["receipts"]:
        out.append("- `%s` \u2014 %s %s" % (r["id"], r["cite"], r["what"]))
    used = {x.split("\u2014", 1)[1].strip() for x in
            [row["source"] for row in b["feelings"] + b["points"] + b["arcs"] + b["rules"]]
            if x.startswith("research")}
    missing = sorted(used - set(rec))
    if missing:
        out.append("\n\u26a0 cited but not in receipts: %s" % ", ".join(missing))
    return "\n".join(out)


TELLS_JSON_PATH = HERE / "tells.json"


def tells(d):
    """The tells — components/marketing-doctrine/tells.json: what gives work
    away as machine-made, channel by channel. `hard` rows are the patterns
    tells.py runs; `judge` rows are read against this list by a person or a
    judge prompt."""
    b = json.loads(TELLS_JSON_PATH.read_text())
    out = [_open("The tells \u2014 what makes work read as machine-made", "tells", b["what"])]
    out.append("**The master rule.** %s\n" % b["master_rule"])
    out.append("**How a tell is held.** %s\n" % b["hold_rule"])
    out.append("**Why it matters.** %s _(%s)_\n" % (b["why_it_matters"]["rule"], b["why_it_matters"]["source"]))
    for ch in b["channels"]:
        rows = [t for t in b["tells"] if t["channel"] == ch["id"]]
        out.append("## %s \u2014 %s\n" % (ch["name"], ch["what"]))
        for t in rows:
            out.append("### %s \u00b7 %s (%s)\n" % (t["id"], t["name"],
                       "machine-checked" if t["check"] == "hard" else "judged"))
            out.append("- **Spot it:** %s" % t["spot"])
            out.append("- **Why it reads as machine:** %s" % t["why"])
            out.append("- **Instead:** %s" % t["fix"])
            out.append("- **Source:** %s\n" % t["source"])
    out.append("## Receipts\n")
    for r in b["receipts"]:
        out.append("- `%s` \u2014 %s %s %s" % (r["id"], r["cite"], r["url"], r["what"]))
    return "\n".join(out)


RENDERERS = [
    ("desire.md", desire),
    ("awareness.md", awareness),
    ("sophistication.md", sophistication),
    ("techniques.md", techniques),
    ("sections.md", sections),
    ("mood.md", mood),
    ("verification.md", verification),
    ("offer-close.md", offer_close),
    ("research-questions.md", research_questions),
    ("ad-frameworks.md", ad_frameworks),
    ("delivery.md", delivery),
    ("spoken.md", spoken),
    ("emotion.md", emotion),
    ("tells.md", tells),
]


def render_all():
    """-> {filename: text}. Pure: reads the JSON, writes nothing."""
    data = json.loads(JSON_PATH.read_text())
    out = {}
    for name, fn in RENDERERS:
        text = fn(data).rstrip("\n") + "\n"
        out[name] = text
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="render the doctrine slices")
    ap.add_argument("--check", action="store_true",
                    help="render in memory and fail if the files on disk differ")
    args = ap.parse_args(argv)
    rendered = render_all()
    if args.check:
        bad = []
        for name, text in rendered.items():
            path = SLICES / name
            if not path.exists() or path.read_text() != text:
                bad.append(name)
        for name in bad:
            print("stale: slices/%s" % name)
        if bad:
            return 1
        print("slices are current (%d)" % len(rendered))
        return 0
    SLICES.mkdir(exist_ok=True)
    for name, text in rendered.items():
        (SLICES / name).write_text(text)
    print("rendered %d slices into %s" % (len(rendered), SLICES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
