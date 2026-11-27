#!/usr/bin/env python3
"""Feedback forms — build a brand's form, its previews and its Klaviyo install
sheet from the brand's own config. Brand-agnostic: every word, colour and
trigger comes from

    brands/<brand>/operations/feedback-stages.json     who gets it, when, what we already know
    brands/<brand>/operations/feedback-questions.json  the questions, the look, the emails

    python3 components/feedback-forms/build.py check   --brand B     # the config is sound
    python3 components/feedback-forms/build.py preview --brand B     # runs/feedback-forms/<B>/preview/<stage>.html
    python3 components/feedback-forms/build.py install --brand B     # runs/feedback-forms/<B>/install/deliverable/feedback-klaviyo-install.md
    python3 components/feedback-forms/build.py cpk --brand B --dest <campaign src folder>
                                                                    # the page for the brand's campaign-page-kit repo
    python3 components/feedback-forms/build.py all                   # check + preview + install, every brand with a config

The page it builds sends ONE Klaviyo Client API event per submission (metric
"Submitted Feedback", the brand's PUBLIC company id — no secret anywhere); the
research gatherer's `feedback` mode reads those events back into the language
bank. No network, no key: this file only reads config and writes files.
"""
import argparse
import base64
import datetime as dt
import html
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = Path(os.environ.get("AI_WORKSPACE") or HERE.parents[1])
ENGINE_JS = HERE / "engine" / "feedback.js"
ENGINE_CSS = HERE / "engine" / "feedback.css"
# The tracking standard's email tags (components/funnel-tracking, email_url), through its
# public surface: every flow email's button link carries them (owner, 2026-10-12).
sys.path.append(str(HERE.parent / "funnel-tracking" / "machine"))
sys.path.insert(0, str(HERE))
import design_system as DS  # noqa: E402
import standard as TRACKING  # noqa: E402
TYPES = ("choice", "multi", "scale", "text")
AREAS = ("marketing", "product", "operations", "customer-service", "customer-experience", "website")
LANES = ("lead", "prospect", "customer", "churned")
# What a question carries for the people who write it, never for the page:
# its old wording, and the language-bank rows it was written from.
PAGE_DROPS = ("from_old", "was", "was_options", "language_used", "options_language", "language_query", "language_note")
TOKEN_VARS = ("band", "band_ink", "ground", "card", "ink", "muted", "line", "accent", "accent_2",
              "cta", "cta_ink", "cta_line", "picked", "picked_ink", "radius", "chip_radius")


def ops(brand, root=None):
    return (root or WORKSPACE) / "brands" / brand / "operations"


def load(brand, root=None):
    """The brand's stages and questions; the look is filled in from its design system (design_system.py)."""
    d = ops(brand, root)
    stages = json.loads((d / "feedback-stages.json").read_text())
    questions = json.loads((d / "feedback-questions.json").read_text())
    questions["look"] = DS.resolve(questions, d.parent, root or WORKSPACE)
    return stages, questions


def brands(root=None):
    return sorted(p.parent.parent.name for p in ((root or WORKSPACE) / "brands").glob("*/operations/feedback-questions.json")
                  if not p.parent.parent.name.startswith("_"))


# ---------------------------------------------------------------- check

def check(stages, questions):
    """Problems with a brand's config, as plain sentences. [] = sound."""
    bad = []
    st_ids = [s["stage"] for s in stages.get("stages", [])]
    q_stages = questions.get("stages", {})
    if len(set(st_ids)) != len(st_ids):
        bad.append("a stage is listed twice in feedback-stages.json")
    for s in st_ids:
        if s not in q_stages:
            bad.append(f"stage {s!r} has no questions in feedback-questions.json")
    for s in q_stages:
        if s not in st_ids:
            bad.append(f"stage {s!r} has questions but no trigger in feedback-stages.json")
    if questions.get("default_stage") not in q_stages:
        bad.append("default_stage is not one of the stages")
    if not re.match(r"^[a-z0-9-]+$", questions.get("brand", "")):
        bad.append("brand must be a lowercase slug")
    kl = stages.get("klaviyo") or {}
    if not kl.get("public_id") or not kl.get("metric"):
        bad.append("klaviyo.public_id and klaviyo.metric are required")
    for s in stages.get("stages", []):
        if s.get("lane") not in LANES:
            bad.append(f"{s['stage']}: lane must be one of {', '.join(LANES)}")
        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", s["stage"]):
            bad.append(f"{s['stage']}: a stage id is lowercase words joined by '-' (it becomes part of the source id)")
        if s.get("status") == "blocked" and not s.get("blocked_by"):
            bad.append(f"{s['stage']}: blocked, but blocked_by does not say why")
        if "{stage}" not in (stages.get("form") or {}).get("link", "{stage}"):
            bad.append("form.link must carry {stage}")
    for sid, st in q_stages.items():
        ids, ns = set(), set()
        qs = st.get("questions") or []
        if not qs:
            bad.append(f"{sid}: no questions")
        base = [q for q in qs if not q.get("show_if")]
        if not 4 <= len(base) <= 9:
            bad.append(f"{sid}: {len(base)} always-shown questions (keep it to 4–9)")
        for q in qs:
            where = f"{sid}/{q.get('id')}"
            if q.get("id") in ids:
                bad.append(f"{where}: id used twice")
            ids.add(q.get("id"))
            if q.get("n") in ns:
                bad.append(f"{where}: number n used twice")
            ns.add(q.get("n"))
            if q.get("type") not in TYPES:
                bad.append(f"{where}: type must be one of {', '.join(TYPES)}")
            if q.get("type") in ("choice", "multi") and not q.get("options"):
                bad.append(f"{where}: a choice needs options")
            if q.get("type") == "scale" and not (isinstance(q.get("min"), int) and isinstance(q.get("max"), int)):
                bad.append(f"{where}: a scale needs integer min and max")
            if not q.get("text"):
                bad.append(f"{where}: no question text")
            for a in q.get("areas") or []:
                if a not in AREAS:
                    bad.append(f"{where}: unknown business area {a!r}")
            if not q.get("areas"):
                bad.append(f"{where}: tag at least one business area")
            if not q.get("yields"):
                bad.append(f"{where}: name what the answers yield (bank tags)")
            ol = q.get("options_language")
            if ol is not None and [x.get("option") for x in ol] != list(q.get("options") or []):
                bad.append(f"{where}: options_language does not line up with options")
            c = q.get("show_if")
            if c and c.get("q") not in ids:
                bad.append(f"{where}: show_if points at {c.get('q')!r}, which is not an earlier question")
        em = st.get("email") or {}
        for k in ("subject", "preview", "body", "button"):
            if not em.get(k):
                bad.append(f"{sid}: email.{k} is missing")
    return bad


# ---------------------------------------------------------------- the runtime config

def runtime(stages, questions, mode="live"):
    """What the page needs — and nothing it doesn't (no emails, no triggers)."""
    known = {s["stage"]: dict(s.get("known") or {}, lane=s["lane"]) for s in stages["stages"]}
    labels = {s["stage"]: s.get("label") for s in stages["stages"]}
    out = {
        "brand": questions["brand"], "label": questions.get("label") or questions["brand"],
        "form_version": questions["form_version"], "default_stage": questions["default_stage"],
        "klaviyo": {"public_id": stages["klaviyo"]["public_id"], "metric": stages["klaviyo"]["metric"],
                    "revision": stages["klaviyo"].get("client_revision", "2025-10-15")},
        "look": {k: v for k, v in (questions.get("look") or {}).items() if k in ("logo", "logo_alt")},
        "copy": questions.get("copy") or {}, "thanks": questions.get("thanks") or {},
        "reward": {k: (questions.get("reward") or {}).get(k) for k in ("line", "code")},
        "known": known, "mode": mode,
        "stages": {sid: {"label": labels.get(sid) or sid, "title": st.get("title"), "intro": st.get("intro"),
                         "questions": [{k: v for k, v in q.items() if k not in PAGE_DROPS} for q in st["questions"]]}
                   for sid, st in questions["stages"].items()},
    }
    return out


def brand_css(questions, font_prefix="../", fonts=True):
    """The brand's custom properties (and its font faces) for .fb[data-brand]."""
    look = questions.get("look") or {}
    t = look.get("tokens") or {}
    b = questions["brand"]
    lines = []
    for f in (look.get("font_face") or []) if fonts else []:
        src = f["src"][len("assets/"):] if f["src"].startswith("assets/") else f["src"]
        lines.append(f"@font-face {{ font-family: '{f['family']}'; font-weight: {f.get('weight', 400)}; "
                     f"font-style: normal; font-display: swap; src: url('{font_prefix}{src}') format('woff2'); }}")
    props = [f"--fb-{k.replace('_', '-')}: {t[k]};" for k in TOKEN_VARS if t.get(k)]
    props += [f"--fb-font-body: {look['font_body']};"] if look.get("font_body") else []
    props += [f"--fb-font-head: {look['font_head']};"] if look.get("font_head") else []
    props += [f"--fb-head-transform: {look['head_transform']};"] if look.get("head_transform") else []
    lines.append(f".fb[data-brand=\"{b}\"] {{ " + " ".join(props) + " }")
    lines.append(f"html, body {{ margin: 0; min-height: 100%; background: {t.get('ground', '#fff')}; }}")
    lines.append("[data-feedback-root] { min-height: 100vh; min-height: 100dvh; }")
    return "\n".join(lines) + "\n"


def logo_data_uri(questions, root=None):
    src = (questions.get("look") or {}).get("logo_source")
    if not src:
        return None
    p = (root or WORKSPACE) / src
    if not p.is_file():
        return None
    return "data:image/svg+xml;base64," + base64.b64encode(p.read_bytes()).decode()


def js_config(cfg):
    return "window.FEEDBACK_CONFIG = " + json.dumps(cfg, indent=1, ensure_ascii=False).replace("</", "<\\/") + ";\n"


# ---------------------------------------------------------------- outputs

PREVIEW = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>{title}</title>
<style>
{css}
{brand_css}
</style>
</head>
<body>
<div data-feedback-root></div>
<script>
// Preview: the stage in the file name opens unless ?stage= says otherwise.
(function () {{
  var p = new URLSearchParams(location.search);
  if (!p.get("stage")) {{ p.set("stage", {stage}); try {{ history.replaceState(null, "", location.pathname + "?" + p.toString()); }} catch (e) {{}} }}
}})();
{config}
window.FEEDBACK_CONFIG.look.logo = {logo};
</script>
<script>
{engine}
</script>
</body>
</html>
"""


def preview_html(stages, questions, stage, mode="preview", root=None):
    """One self-contained page (engine, look and config inline; brand fonts
    fall back to the system face) — opens from disk, no server."""
    cfg = runtime(stages, questions, mode)
    return PREVIEW.format(
        title=html.escape(f"{cfg['label']} feedback · {stage} · {mode}"),
        css=ENGINE_CSS.read_text(), brand_css=brand_css(questions, fonts=False),
        config=js_config(cfg), logo=json.dumps(logo_data_uri(questions, root)),
        engine=ENGINE_JS.read_text(), stage=json.dumps(stage))


def write_previews(brand, out=None, root=None):
    stages, questions = load(brand, root)
    out = Path(out) if out else (root or WORKSPACE) / "runs" / "feedback-forms" / brand / "preview"
    out.mkdir(parents=True, exist_ok=True)
    made = []
    for sid in questions["stages"]:
        f = out / f"{sid}.html"
        f.write_text(preview_html(stages, questions, sid, "preview", root))
        made.append(f)
    # the one page that really sends: a test=true event, for the end-to-end proof
    f = out / "_send-test.html"
    f.write_text(preview_html(stages, questions, questions["default_stage"], "local-test", root))
    made.append(f)
    return made


CPK_INDEX = """---
page_layout: base-feedback.html
# the kit accepts product | checkout | upsell | receipt; a content page uses `product`
page_type: product
permalink: /{slug}/
title: "{title}"
og_description: "{desc}"
styles:
  - css/feedback.css
scripts:
  - js/feedback-config.js
  - js/feedback.js

# ---------------------------------------------------------------------------
# FEEDBACK FORM — one page, every customer stage (?stage=<stage>).
# GENERATED by ai-workspace components/feedback-forms/build.py from
# brands/{brand}/operations/feedback-questions.json + feedback-stages.json.
# The questions and the look live in that config; the behaviour in
# assets/js/feedback.js (engine copy). Edit the source and rebuild.
#
# The email link: https://<this host>/{slug}/?stage=<stage>&e={{{{ email|urlencode }}}}
# Stages: {stage_list}
# On submit: one Klaviyo Client API event "Submitted Feedback" with the
# brand's PUBLIC company id ({public_id}). No secret key, no ad pixels, no
# Campaign Cart SDK on this page — the email in the link must never reach
# an ad platform, so the analytics partials are not included here.
# ---------------------------------------------------------------------------
---
<div data-feedback-root data-logo="{{{{ '{logo}' | campaign_asset }}}}"></div>
<noscript><p style="padding:24px;font-family:system-ui,sans-serif">This form needs JavaScript switched on.</p></noscript>
"""

CPK_LAYOUT = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="robots" content="noindex, nofollow">
  <meta name="referrer" content="no-referrer">
  <title>{{{{ title }}}}</title>
  {{% if og_description %}}<meta name="description" content="{{{{ og_description }}}}">{{% endif %}}
  <meta property="og:title" content="{{{{ title }}}}">
  {{% if og_description %}}<meta property="og:description" content="{{{{ og_description }}}}">{{% endif %}}
  <meta property="og:site_name" content="{label}">
  {{%- comment -%}}
    Feedback form layout. No Campaign Cart SDK, no analytics partials, no
    third-party requests except the Klaviyo Client API on submit: the page URL
    carries the customer's email (?e=), so nothing that reports page URLs
    (pixels, tag managers) may load here. `no-referrer` keeps the URL out of
    any outbound request's Referer header. GENERATED by ai-workspace
    components/feedback-forms/build.py.
  {{%- endcomment -%}}
  <link rel="icon" href="{favicon}">
  {{% for style in styles %}}
  <link rel="stylesheet" href="{{{{ style | campaign_asset }}}}">
  {{% endfor %}}
</head>
<body>
  {{{{ content }}}}
  {{% for script in scripts %}}
  <script src="{{{{ script | campaign_asset }}}}" defer></script>
  {{% endfor %}}
</body>
</html>
"""

CPK_CONFIG_JS = """// {label} feedback form — a content page: no cart, no checkout, so the
// Campaign Cart SDK is not loaded by its layout (base-feedback.html). This file
// exists because the repo smoke-check expects every campaign to carry one.
// The form's own settings are in js/feedback-config.js (generated).
window.nextConfig = {{
  apiKey: '',
  storeName: '{label}',
  debug: false
}};
"""

FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' "
           "height='32' rx='6' fill='{c}'/%3E%3C/svg%3E")


def write_cpk(brand, dest, root=None):
    """The campaign's source folder for the brand's campaign-page-kit repo.
    Writes the page, its layout, the engine copy and the compiled config;
    leaves the logo, fonts and anything else already there alone."""
    stages, questions = load(brand, root)
    form = stages["form"]
    dest = Path(dest)
    cfg = runtime(stages, questions, "live")
    look = questions.get("look") or {}
    logo = (look.get("logo") or "")[len("assets/"):] if (look.get("logo") or "").startswith("assets/") else look.get("logo", "")
    files = {
        "index.html": CPK_INDEX.format(slug=form["slug"], brand=brand, title=f"{cfg['label']} — Feedback",
                                       desc=f"Tell {cfg['label']} how it's going. A few quick questions.",
                                       stage_list=", ".join(questions["stages"]), public_id=cfg["klaviyo"]["public_id"],
                                       logo=logo),
        "_layouts/base-feedback.html": CPK_LAYOUT.format(label=cfg["label"],
                                                         favicon=FAVICON.format(c=(look.get("tokens") or {}).get("band", "#111").replace("#", "%23"))),
        "assets/config.js": CPK_CONFIG_JS.format(label=cfg["label"]),
        "assets/js/feedback-config.js": "// GENERATED by ai-workspace components/feedback-forms/build.py from\n"
                                        f"// brands/{brand}/operations/feedback-questions.json + feedback-stages.json. Do not edit here.\n"
                                        + js_config(cfg),
        "assets/js/feedback.js": ENGINE_JS.read_text(),
        "assets/css/feedback.css": ENGINE_CSS.read_text() + "\n/* ---- " + cfg["label"] + " (generated from its config) ---- */\n"
                                   + brand_css(questions, font_prefix="../"),
    }
    for rel, text in files.items():
        p = dest / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return sorted(files)


# ---------------------------------------------------------------- the Klaviyo install sheet

def kill_list(brand, root=None):
    p = (root or WORKSPACE) / "runs" / "feedback-forms" / brand / "kill-list.json"
    try:
        return {f"{k['flow_id']}/{k['message_id']}": k for k in json.loads(p.read_text()).get("messages", [])}
    except Exception:
        return {}


def install_md(brand, root=None):
    stages, questions = load(brand, root)
    kl, form, em = stages["klaviyo"], stages["form"], stages.get("email") or {}
    kills = kill_list(brand, root)
    label = questions.get("label") or brand
    try:
        pr = json.loads(((root or WORKSPACE) / "runs" / "feedback-forms" / "_system" / "status.json").read_text())["brands"][brand].get("pr")
    except Exception:
        pr = None
    L = [f"# {label} — feedback flows: Klaviyo install sheet", "",
         f"_Generated {dt.date.today().isoformat()} by `components/feedback-forms/build.py install --brand {brand}` from "
         f"`brands/{brand}/operations/feedback-stages.json` + `feedback-questions.json`. Edit those, rebuild this._", "",
         "**Who does this: email_lead.** Build every flow below in Klaviyo and leave it in **Draft** (or Manual). "
         "Nothing goes live until owner says go. Existing flows are not touched by this sheet — the kill list at the "
         "bottom says what each new flow would replace, for owner to decide.", "",
         "## Before you start", "",
         f"- Klaviyo account: public id `{kl['public_id']}`.",
         f"- The form: **{form['url']}** (one page, every stage; `?stage=` picks the questions). It goes live when the "
         f"`{form['slug']}` campaign pull request on `{form['repo']}` is merged" + (f" ({pr})." if pr else "."),
         f"- Every answer arrives in Klaviyo as one event, metric **\"{kl['metric']}\"**, on the profile that got the email. "
         "The metric appears in the account after the first real submission — it is not something to create.",
         f"- From: **{em.get('from_label', '')}** ({em.get('from_email', '')}).",
         f"- Email style: {em.get('style', '')}",
         f"- Reward: {em.get('reward', '')}",
         f"- The button link, per stage (copy it exactly): `{form['link']}` — with `{{stage}}` filled in below.",
         f"- {form.get('link_note', '')}", "",
         "## Build steps (same for every flow)", "",
         "1. Flows → Create flow → Build your own → name it exactly as below.",
         "2. Trigger: the metric named below (pick the one whose integration matches). Add the trigger filter if one is listed.",
         "3. Flow filters: add each one listed.",
         "4. Add a Time Delay: the wait listed.",
         "5. Add an Email: from name/address above, the subject and preview text below, a text-based email with the "
         "body paragraphs below, one button with the button text and the link below, then the standard footer "
         "(`{% unsubscribe %}` · `{{ organization.name }} {{ organization.full_address }}`).",
         "6. Leave the email and the flow in **Draft**. Tell owner it is built.", ""]
    for s in stages["stages"]:
        sid = s["stage"]
        q = questions["stages"][sid]
        e = q["email"]
        k = s["klaviyo"]
        t = k["trigger"]
        # utm_campaign = the flow's name, utm_content = <stage>.button (the flow's one message)
        link = TRACKING.tag_email_link(form["link"].replace("{stage}", sid), k["flow_name"], sid, "button")
        n_base = len([x for x in q["questions"] if not x.get("show_if")])
        L += [f"## {k['flow_name']}", "",
              f"**{s['label']}** · answers file into the **{s['lane']}** lane · {n_base} questions"
              + (f" (+{len(q['questions']) - n_base} follow-up)" if len(q["questions"]) > n_base else ""), ""]
        if s.get("status") == "blocked":
            L += [f"> **BLOCKED — don't build yet.** {s['blocked_by']}", ""]
        L += ["| | |", "|---|---|",
              f"| Flow name | `{k['flow_name']}` |",
              f"| Trigger | {t['metric']} ({t.get('integration', '')}"
              + (f", metric id `{t['metric_id']}`" if t.get("metric_id") else "") + ") |",
              f"| Trigger filter | {'; '.join(k.get('trigger_filters') or []) or '—'} |",
              f"| Flow filters | {'<br>'.join(k.get('flow_filters') or []) or '—'} |",
              f"| Wait | {k['wait']} — {k.get('why_the_wait', '')} |",
              f"| Subject | {e['subject']} |",
              f"| Preview text | {e['preview']} |",
              f"| Button text | {e['button']} |",
              f"| Button link | `{link}` |", "",
              "Email body:", ""]
        for para in e["body"]:
            L.append(f"> {para}")
            L.append(">")
        L.append(f"> **[{e['button']}]({link})**")
        L.append(">")
        for para in e.get("after") or []:
            L.append(f"> {para}")
            L.append(">")
        if L[-1] == ">":
            L.pop()
        L.append("")
        if s.get("replaces"):
            L.append("Would replace (owner decides; nothing is switched off by this sheet):")
            for r in s["replaces"]:
                kk = kills.get(r)
                L.append(f"- {kk['flow_name']} › {kk['message_name']} ({kk['state']}) — `{r}`" if kk else f"- `{r}`")
            L.append("")
    L += ["## Kill list (read-only — for owner)", ""]
    if kills:
        L += ["Every existing flow email in this account that links to an old Google Form, read from the Klaviyo API "
              "on the date in `runs/feedback-forms/" + brand + "/kill-list.json`. Nothing here has been changed.", "",
              "| Flow | Flow state | Email | Email state | Links to | Replaced by |", "|---|---|---|---|---|---|"]
        for key, kk in kills.items():
            L.append(f"| {kk['flow_name']} (`{kk['flow_id']}`) | {kk['flow_status']} | {kk['message_name']} (`{kk['message_id']}`) "
                     f"| {kk['state']} | {kk['form']} | {kk.get('replaced_by') or '—'} |")
    else:
        L.append("No kill list on file for this brand (no Klaviyo private key to read its flows with).")
    L.append("")
    return "\n".join(L)


INSTALL_LABEL = "install"


def install_path(brand, root=None, label=INSTALL_LABEL):
    """Where the install sheet lands: the run folder's deliverable/, under a
    stable label rebuilt in place (like preview/). Never brands/ (K2)."""
    return (root or WORKSPACE) / "runs" / "feedback-forms" / brand / label / "deliverable" / "feedback-klaviyo-install.md"


def write_install(brand, root=None, label=INSTALL_LABEL):
    p = install_path(brand, root, label)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(install_md(brand, root))
    return p


# ---------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(prog="build.py")
    ap.add_argument("what", choices=("check", "preview", "install", "cpk", "all"))
    ap.add_argument("--brand", action="append")
    ap.add_argument("--dest", help="cpk: the campaign's src folder in a campaign-page-kit checkout")
    ap.add_argument("--out", help="preview: where the preview pages go")
    ap.add_argument("--label", default=INSTALL_LABEL,
                    help="install: the run label under runs/feedback-forms/<brand>/ (default %(default)s)")
    a = ap.parse_args(argv)
    todo = a.brand or brands()
    rc = 0
    for b in todo:
        stages, questions = load(b)
        bad = check(stages, questions)
        if bad:
            rc = 1
            print(f"{b}: {len(bad)} problem(s)")
            for x in bad:
                print(f"  - {x}")
            continue
        print(f"{b}: config sound — {len(questions['stages'])} stages, "
              f"{sum(len(s['questions']) for s in questions['stages'].values())} questions")
        if a.what in ("preview", "all"):
            for f in write_previews(b, a.out):
                print(f"  preview {f.relative_to(WORKSPACE) if WORKSPACE in f.parents else f}")
        if a.what in ("install", "all"):
            print(f"  install sheet {write_install(b, label=a.label).relative_to(WORKSPACE)}")
        if a.what == "cpk":
            if not a.dest:
                print("  cpk needs --dest <campaign src folder>")
                return 2
            for f in write_cpk(b, a.dest):
                print(f"  wrote {f}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
