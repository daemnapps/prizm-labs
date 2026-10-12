#!/usr/bin/env python3
"""The simple email: the copy machine's words in one fixed shape, pictures
made by GPT, and — on --push — a DRAFT campaign in the brand's Klaviyo.

    python3 simple_email.py <run>  --brand brand-b            # pictures + the email
    python3 simple_email.py <run>  --brand brand-b --push     # ...and a Klaviyo draft
    python3 simple_email.py <run>  --brand brand-b --no-images   # layout only, no spend

the owner, 2026-09-19: "we're just going to focus on not doing fully design-based
email templates and just using what we had before as our baseline… the logo at
the top, headline for the email, an image that describes the headline with
relevance, the copy. If another image needs to go in there, towards the
bottom, it can. Maybe there's an offer… and then you just put a button in."

WHERE EACH PART COMES FROM
- the words: stage 8 of the email chain writes them into this shape, as a
  fenced `EMAIL` block (prompts/stage8-build-v2-damon.md)
- the look: `brands/<brand>/email-sms/simple.json`, read off the brand's own last
  sent email — this engine names no brand, colour or font
- the pictures: GPT Image through the video machine's direct OpenAI door, the
  model named in its providers registry; the offer picture is made FROM the
  real product photo when the brand has one on file
- the send: a Klaviyo DRAFT. This tool has no send call and never will —
  scheduling is a person's act, in Klaviyo.

WHERE IT FILES (runs/README.md, 2026-09-17)
- the email and its record: runs/email-production/<brand>/<label>/deliverable/
- the pictures (media): Shared Assets/runs/email-production/<brand>/<label>/
"""
import argparse
import datetime
import html
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
import drive_reach as DR  # noqa: E402

from paths import HERE, WORKSPACE, component

# This folder's own email.py shadows Python's `email` package, which the
# picture door needs (urllib -> http.client -> email.parser). Nothing below
# imports from this folder again, so take it off the path.
sys.path = [p for p in sys.path if Path(p or ".").resolve() != HERE]
# The checks and the hold are the shared ones (components/quality-checks); the
# layout is asked of the element library (components/elements, template/email).
sys.path.insert(0, str(component("marketing-chain-checks")))
sys.path.insert(0, str(HERE / "machine"))
import marketing_chain_checks as Q                                  # noqa: E402
from marketing_chain_checks import rulings as R                     # noqa: E402
import email_elements as EE                                 # noqa: E402
sys.path.append(str(component("brandpath")))   # appended, never ahead of this machine
import brandpath as BP                                      # noqa: E402


def logo_file(brand, rel):
    """The brand's logo, found through the folder map — a look file may still
    name the pre-v6 folder (identity/ → brand-identity/, 957c585c6)."""
    return BP.resolve_rel(brand, rel, root=WORKSPACE / "brands")

MACHINE = "email-production"
LAYOUT = "simple"                       # the one email template (template/email in the element library)
_NO_DRIVE_TOLD = set()


def drive_media(brand, label):
    """Where this email's pictures are made and looked for: (how, folder).

    SI-38 (email Drive reach), decided by drive_reach.route(): "api" — the
    run's own media/ folder, filed to Shared Assets by id (a key wins over a
    mount); "mount" — Shared Assets/runs/email-production/<brand>/<label>/
    on the mount, as before; "none" — the run's own media/ folder, said once
    on stderr. Never a made-up Drive path."""
    local = WORKSPACE / "runs" / MACHINE / brand / label / "media"   # gitignored media
    try:
        how = DR.route()
        sa = DR.mount() if how == "mount" else None
        if how == "mount" and sa is None:
            raise DR.NoDrive(DR.NO_DRIVE)
    except DR.NoDrive as e:
        if not _NO_DRIVE_TOLD:
            _NO_DRIVE_TOLD.add(True)
            print(f"pictures: the Drive is not reached — {e}", file=sys.stderr)
        return "none", local
    if how == "api":
        return "api", local
    return "mount", sa / "runs" / MACHINE / brand / label


KLAVIYO = "https://a.klaviyo.com/api"
REVISION = "2025-07-15"
# The picture model is the registry's; only the frame changes. The video
# machine's default is a tall 9:16 frame at its top quality — an email hero is
# wide, and a month of heroes at the top tier is spend nobody sees at 600px.
EMAIL_IMAGE = {"size": "1536x1024", "quality": "high"}


# --------------------------------------------------------------------- read

def the_email(run_dir):
    text = (run_dir / "stage8--blocks.md").read_text()
    m = re.search(r"```EMAIL\s*\n(.*?)```", text, re.S)
    if not m:
        sys.exit(f"{run_dir.name}: stage 8 wrote no EMAIL block — this run was built "
                 "in the old block layout. Rebuild it:  python3 email.py <source> … "
                 "--rerun-from stage8")
    try:
        return json.loads(m.group(1))
    except ValueError as e:
        sys.exit(f"{run_dir.name}: the EMAIL block is not valid JSON ({e})")


def look(brand):
    f = WORKSPACE / "brands" / brand / "email-sms" / "simple.json"
    if not f.is_file():
        sys.exit(f"no brands/{brand}/email-sms/simple.json — the brand's look for the "
                 "simple email is not on file yet")
    return json.loads(f.read_text())


def product_photo(brand, key):
    """The real product photo, when the brand keeps one — as a file per
    product under products/<key>/images/, or named by key in products/images/."""
    if not key:
        return None
    root = WORKSPACE / "brands" / brand / "products"
    pics = [p for p in (root / key / "images").glob("*")
            if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")]
    pics += [p for p in (root / "images").glob(f"{key}*")
             if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")]
    rank = ("packshot", "cutout", "-00", "hero")
    pics.sort(key=lambda p: next((i for i, r in enumerate(rank) if r in p.name), 9))
    return pics[0] if pics else drive_product_photo(brand, key)


def drive_product_photo(brand, key):
    """The packshot on the Drive, where a brand's product pictures live (media
    never sits in git). Shared Assets/brands/<brand>/products/<catalog id>/packshot/,
    sets under products/bundles/<set>/packshot/. The folder is named by catalog
    id, which is not always the store handle (`wash` → `daily-face-wash`,
    `the-vitals-set` → `vitals-set`), so a folder matches when one name's words
    contain the other's. Two folders matching equally is no answer: the picture
    is then made without a reference, as before, rather than from a guess.

    A folder listing, so the mount only: on the API route, or with no Drive,
    there is no packshot here (by id it is brandpath#2's)."""
    try:
        if DR.route() != "mount":
            return None
    except DR.NoDrive:
        return None
    sa = DR.mount()
    if sa is None:
        return None
    base = sa / "brands" / brand / "products"
    try:
        if not base.is_dir():
            return None
        stop = {"the", "bundle", "and"}
        words = lambda s: {w for w in re.split(r"[-_\s]+", s.lower()) if w and w not in stop}
        want = words(key)
        dirs = [d for d in base.iterdir() if d.is_dir() and not d.name.startswith("_") and d.name != "bundles"]
        dirs += [d for d in (base / "bundles").glob("*") if d.is_dir()]
        exact = [d for d in dirs if words(d.name) == want]
        near = [d for d in dirs if words(d.name) <= want or want <= words(d.name)]
        found = exact or near
        if len(found) != 1:
            return None
        pics = [p for p in (found[0] / "packshot").glob("*")
                if p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")]
        order = ("_packshot_front", "hero", "_packshot_", "lockup", "packshot")
        pics.sort(key=lambda p: next((i for i, r in enumerate(order) if r in p.name.lower()), 9))
        return pics[0] if pics else None
    except OSError:
        return None


# ----------------------------------------------------------------- pictures

def openai_door():
    # the video machine left lab/ai-video-production for
    # tools/video-production; the old reach found nothing and every
    # email died at its pictures (2026-09-23)
    f = component("video-production", "machine", "direct_openai.py")
    spec = importlib.util.spec_from_file_location("direct_openai", f)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    base = mod.cfg()
    mod.cfg = lambda: {**base, "params": {**(base.get("params") or {}), **EMAIL_IMAGE}}
    return mod


def make_pictures(email, brand, media_dir):
    door = openai_door()
    media_dir.mkdir(parents=True, exist_ok=True)
    made = {}
    jobs = [("hero", email.get("hero"), None)]
    offer_img = (email.get("offer") or {}).get("image")
    if offer_img:
        jobs.append(("offer", offer_img, product_photo(brand, offer_img.get("product"))))
    for name, spec, ref in jobs:
        if not spec or not spec.get("prompt"):
            continue
        out = media_dir / f"{name}.png"
        prompt = (spec["prompt"] + "\n\nA wide photograph for the top of an email. "
                  "No words, letters, numbers or logos anywhere in the image.")
        if ref:
            prompt += ("\n\nThe product in the reference image must appear exactly as "
                       "it is — same pack, same colours, same label. Do not redraw it.")
        print(f"  picture: {name}" + (f" (from {ref.name})" if ref else "") + " …")
        door.generate(prompt, [ref] if ref else [], out)
        made[name] = web_copy(out)
    return made


def web_copy(png):
    """The picture as the email carries it: 1200px wide (2x a 600px email),
    JPEG. A 3MB PNG at the top of an email is a slow first screen on a phone."""
    jpg = png.with_suffix(".jpg")
    if not jpg.is_file() or jpg.stat().st_mtime < png.stat().st_mtime:
        subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "82",
                        "--resampleWidth", "1200", str(png), "--out", str(jpg)],
                       capture_output=True, check=True)
    return jpg


def inline(path):
    """A picture inside the preview itself, so the page opens anywhere."""
    import base64
    return "data:image/jpeg;base64," + base64.b64encode(Path(path).read_bytes()).decode()


# ------------------------------------------------------------------- render

def para(text):
    t = html.escape(text.strip())
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    return t.replace("\n", "<br>")


def render(email, lk, pictures, logo_src):
    c, f = lk["colors"], lk["fonts"]
    body = f"font-family:{f['body']};font-size:{lk.get('body_size', 16)}px;line-height:1.5;color:{c['text']};"

    def img(src, alt):
        return (f'<tr><td style="padding:0 0 24px 0;"><img src="{src}" alt="{html.escape(alt or "")}" '
                f'width="600" style="display:block;width:100%;max-width:600px;height:auto;border:0;"></td></tr>')

    rows = [f'<tr><td align="center" style="padding:24px 0;"><a href="{lk["logo"].get("link", "#")}">'
            f'<img src="{logo_src}" alt="{html.escape(lk["logo"]["alt"])}" width="{lk["logo"]["width"]}" '
            f'style="display:block;width:{lk["logo"]["width"]}px;height:auto;border:0;"></a></td></tr>']
    rows.append(f'<tr><td style="padding:0 32px 20px 32px;font-family:{f["headline"]};'
                f'font-size:{lk.get("headline_size", 24)}px;line-height:1.15;color:{c["text"]};">'
                f'{para(email["headline"])}</td></tr>')
    if pictures.get("hero"):
        rows.append(img(pictures["hero"], email["hero"].get("alt")))
    copy = []
    if lk.get("greeting"):
        copy.append(f'<p style="margin:0 0 16px 0;">{lk["greeting"]}</p>')
    copy += [f'<p style="margin:0 0 16px 0;">{para(p)}</p>' for p in email.get("body", []) if p.strip()]
    rows.append(f'<tr><td style="padding:0 32px 8px 32px;{body}">{"".join(copy)}</td></tr>')
    offer = email.get("offer")
    if offer:
        if pictures.get("offer"):
            rows.append(img(pictures["offer"], (offer.get("image") or {}).get("alt")))
        rows.append(f'<tr><td style="padding:0 32px 8px 32px;{body}font-weight:600;">'
                    f'{para(offer["line"])}</td></tr>')
    b = email["button"]
    rows.append(f'<tr><td align="center" style="padding:16px 32px 32px 32px;">'
                f'<a href="{html.escape(b["link"])}" style="display:inline-block;background:{c["button"]};'
                f'color:{c["button_text"]};font-family:{f["body"]};font-size:16px;text-decoration:none;'
                f'padding:15px 28px;border-radius:{lk.get("button_radius", 4)}px;">{html.escape(b["label"])}</a></td></tr>')
    if lk.get("signoff"):
        rows.append(f'<tr><td style="padding:0 32px 32px 32px;{body}">'
                    + "<br>".join(html.escape(s) for s in lk["signoff"]) + "</td></tr>")
    foot = f"font-family:{f['body']};font-size:12px;line-height:1.6;color:{c['muted']};"
    rows.append(f'<tr><td align="center" style="padding:24px 32px;{foot}">'
                + (f"{html.escape(lk['tagline'])}<br><br>" if lk.get("tagline") else "")
                + 'No longer find value in our emails? <a href="{% unsubscribe_link %}" '
                  f'style="color:{c["muted"]};">Unsubscribe</a><br>'
                  "{{ organization.name }} · {{ organization.full_address }}</td></tr>")
    return (f'<!DOCTYPE html><html><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"></head>'
            f'<body style="margin:0;padding:0;background:{c["page"]};">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="background:{c["page"]};"><tr><td align="center" style="padding:24px 8px;">'
            f'<table role="presentation" width="600" cellpadding="0" cellspacing="0" '
            f'style="width:100%;max-width:600px;background:{c["card"]};">'
            + "".join(rows) + "</table></td></tr></table></body></html>\n")


# ---------------------------------------------------------------- the check

def finished_text(email, with_link=False):
    """The words a reader will see, in one string."""
    parts = [email.get("headline", ""), *email.get("body", []),
             (email.get("offer") or {}).get("line", ""),
             (email.get("button") or {}).get("label", "")]
    if with_link:
        parts.append((email.get("button") or {}).get("link", ""))
    return " ".join(parts)


def price_check(email, brand, run_dir):
    """EVERY PRICE IN THE EMAIL IS ONE THE BANK SELLS TODAY (2026-09-19).

    The first email through this tool sold two of a set at a real price for a
    size the store had switched off and then removed. The product file lists
    every size ever made; the offer bank lists only what is live. The writer
    took the number from the product file and then told us, in its own notes,
    it was "verbatim from the offer bank". A prompt saying "prices verbatim
    from the bank" is a request; this is the check. A price that is not in the
    send's own offer block does not reach Klaviyo.

    The check itself is the shared one (components/quality-checks, 2026-09-20,
    which was lifted from here); this finds the send's offer and its bank entry.
    """
    try:
        offer = json.loads((run_dir / "run.json").read_text()).get("assignment", {}).get("offer")
    except (OSError, ValueError):
        offer = None
    text = finished_text(email)
    if not Q.prices_in(text):
        return []
    if not offer or offer == "none":
        return Q.price_check(text, "", None)
    bank = (WORKSPACE / "brands" / brand / "products" / "offer-bank.md").read_text()
    block = Q.offer_block(bank, offer)
    if not block:
        # an offer the bank does not hold sells no price at all — every price fails
        block = f"## {offer} — (not in the offer bank)"
    return Q.price_check(text, block, offer)


def delivery_items(email, brand, run_dir, pick=0):
    """Everything that holds an email back from Klaviyo: prices, the chain's
    own check step (8c — product facts, chopped thoughts, typos), unfilled
    notes. All three are the shared checks; the gate is `delivery`. Each
    problem is an item with an id a person can rule on (HE-1 (fact rulings),
    2026-10-01); its `text` is the problem string, unchanged. `pick` is the
    subject pair that will be SENT — the one gated (SI-151 (picked subject
    gated))."""
    def it(kind, text, quote=None):
        return Q.item("delivery", kind, text, quote)
    problems = [it("price", p) for p in price_check(email, brand, run_dir)]
    chk = run_dir / "stage8c--check.md"
    if chk.is_file():
        problems += [dict(i, text=i["text"] + " — look at stage8c--check.md")
                     if i["kind"] == "check-unreadable" else i
                     for i in Q.check_items(chk.read_text(), "delivery")]
    else:
        problems.append(it("unchecked", "this email was never checked (no step 8c) — rerun it from stage8"))
    # A hole the writer marked is honest in the working copy and a defect in
    # the finished email: the first rewrite with customer language shipped a
    # "[UNFILLED: the handoff…]" note inside the body (2026-09-19).
    finished = finished_text(email, with_link=True)
    notes = "\n".join(re.findall(r"\[[^\[\]]*UNFILLED[^\[\]]*\]", finished))
    problems += [it("unfilled", p, notes) for p in Q.unfilled_check(finished)]
    # the two lines a reader sees in the inbox before anything else — the pair
    # that will be SENT, never pair 0 standing in for it (SI-151 (picked
    # subject gated)): --pick 1 used to gate pair 0 and push pair 1 unread
    subs = email.get("subjects") or []
    if not 0 <= pick < len(subs):
        problems.append(it("subject", f"pick {pick} is not in the subject set (0..{len(subs) - 1})"))
    else:
        problems += [it("subject", f"subject pair {pick}: {p}") for p in Q.subject_check(subs[pick])]
    # A PARTNER'S PRODUCT is checked against the partner's own roster entry
    # (2026-09-21): their real link is present, no link nobody put on the
    # roster, and no earnings claim on a traffic-only arrangement. The run
    # names the partner; the roster is the only thing that describes them.
    # A DRAFT IS NOT A PRODUCT, AND EVERY EMAIL ENDS SOMEWHERE A READER CAN BUY
    # (the owner, 2026-09-21). Both read the brand's own catalogue; neither names a
    # product here.
    sys.path.append(str(HERE / "machine"))
    import brand_facts as BF
    cat = BF.catalogue(brand, WORKSPACE)
    problems += [it("draft-product", p) for p in Q.draft_product_check(finished, cat["never"])]

    run = json.loads((run_dir / "run.json").read_text())
    key = (run.get("assignment") or {}).get("affiliate")
    partner = Q.partner_on_file(WORKSPACE / "brands" / brand, key) if key else None
    if key:
        if not partner:
            problems.append(it("partner", f"this send features partner `{key}`, who is not active on "
                                          f"{brand}'s roster — nothing is invented in their place"))
        else:
            problems += [it("partner", p) for p in
                         Q.partner_check(finished, partner, own_domains=own_domains(brand))]
    btn = email.get("button") or {}
    # every page the brand declares for a product (`url`, `url_leads` …) is a destination
    problems += [it("money-path", p) for p in
                 Q.money_path_check(btn.get("link"),
                                    [v for x in cat["sellable"] for k, v in x.items()
                                     if (k == "url" or k.startswith("url_")) and v],
                                    label=btn.get("label", ""),
                                    extra_ok=[partner["link"]] if partner else [])]
    return problems


def delivery_split(email, brand, run_dir, pick=0):
    """(kept, cleared): the delivery items, less the ones a person's standing
    ruling clears (marketing_chain_checks.rulings, read from this WORKSPACE)."""
    return R.split(delivery_items(email, brand, run_dir, pick), brand, Path(run_dir).name, WORKSPACE)


def delivery_problems(email, brand, run_dir, pick=0):
    """The problems still holding the email back, as strings — the gate's
    reading, and klaviyo_upload's when it re-runs the gate."""
    return [i["text"] for i in delivery_split(email, brand, run_dir, pick)[0]]


def own_domains(brand):
    """Our own web addresses, read off the brand's own files — never typed here."""
    import re as _re
    out = set()
    for rel in ("email-sms/machine.json", "email-sms/simple.json"):
        f = WORKSPACE / "brands" / brand / rel
        if f.is_file():
            for u in _re.findall(r"https?://([^/\s\"']+)", f.read_text()):
                out.add(u.lower())
    return out


# ------------------------------------------------------------------ klaviyo


def _shared_keys():
    """The repo's one key loader (components/keys/loader.py): the environment,
    then the repo's .env, then — quietly — the owner's personal fallbacks."""
    import importlib.util
    import sys as _sys
    from pathlib import Path as _Path
    mod = _sys.modules.get("shared_keys_loader")
    if mod is None:
        path = next(p / "components" / "keys" / "loader.py"
                    for p in _Path(__file__).resolve().parents
                    if (p / "components" / "keys" / "loader.py").is_file())
        spec = importlib.util.spec_from_file_location("shared_keys_loader", str(path))
        mod = importlib.util.module_from_spec(spec)
        _sys.modules["shared_keys_loader"] = mod
        try:
            spec.loader.exec_module(mod)
        except Exception:
            _sys.modules.pop("shared_keys_loader", None)
            raise
    return mod


def kl_key(lk):
    k = _shared_keys().lookup(lk.get("klaviyo_key") or "")
    if not k:
        sys.exit(f"no {lk.get('klaviyo_key')} set (add it to .env) — this brand's Klaviyo is not "
                 "connected, so the email is built but not pushed")
    return k


def kl(method, path, key, payload=None, form=None):
    cmd = ["curl", "-sS", "-g", "--max-time", "120", "-X", method,
           "-H", f"Authorization: Klaviyo-API-Key {key}", "-H", f"revision: {REVISION}",
           "-H", "accept: application/vnd.api+json"]
    if form:
        for k2, v in form.items():
            cmd += ["-F", f"{k2}={v}"]
    elif payload is not None:
        cmd += ["-H", "Content-Type: application/vnd.api+json", "-d", json.dumps(payload)]
    r = subprocess.run(cmd + [f"{KLAVIYO}/{path}"], capture_output=True, text=True)
    out = json.loads(r.stdout) if r.stdout.strip() else {}
    if "errors" in out:
        e = out["errors"][0]
        sys.exit(f"Klaviyo refused {path}: {e.get('status')} {e.get('detail', e)}"[:400])
    return out


def upload(key, path, name):
    out = kl("POST", "image-upload", key, form={"file": f"@{path}", "name": name})
    return out["data"]["attributes"]["image_url"]


def the_slot(brand, label):
    """The calendar's send this email was written for — its segment decides
    who the draft goes to. Never guessed: no slot, no push. Read AS REVIEWED
    (SI-151 (picked subject gated), machine/reviewed_plan.py): the reviewer's
    date and segment edits are the send, a cut send is None, and a review.json
    that cannot be read is None too — never the plan as first written."""
    sid = re.sub(r"--.*$", "", label)
    sid = sid[len(brand) + 1:] if sid.startswith(brand + "-") else sid
    # the month's one home: runs/marketing-calendar/<brand>/<YYYY-MM>/, newest
    # first (SI-22 (calendar months home), 2026-10-07) — in the workspace, then
    # in this checkout's own root, FOUND by walking up (as calendar_tool found
    # the old component runs/), so a run copied into another workspace still
    # finds the calendar it was written for
    homes = [WORKSPACE / "runs" / "marketing-calendar" / brand]
    repo = next((d for d in HERE.parents if (d / "runs" / "marketing-calendar").is_dir()), None)
    if repo is not None:
        homes.append(repo / "runs" / "marketing-calendar" / brand)
    dirs, seen = [], set()
    for home in homes:
        if not home.is_dir() or home.resolve() in seen:
            continue
        seen.add(home.resolve())
        dirs += sorted((d for d in home.glob("*") if d.is_dir()), reverse=True)
    import reviewed_plan as RP
    for d in dirs:
        try:
            if json.loads((d / "run.json").read_text()).get("brand") != brand:
                continue
            slots = json.loads((d / "slots.json").read_text())
        except (OSError, ValueError):
            continue
        if not any(s.get("id") == sid for s in slots):
            continue
        # this month planned the send: what the reviewer made of it decides,
        # and an older month is never read in its place
        try:
            s = next((s for s in RP.reviewed(d, slots) if s.get("id") == sid), None)
        except (RP.ReviewUnreadable, ImportError) as e:
            print(f"{label}: the review layer is unreadable — {e}", file=sys.stderr)
            return None
        if s is None:
            print(f"{label}: {sid} was cut by the reviewer ({d / 'review.json'})", file=sys.stderr)
        return s
    return None


def send_strategy(lk, slot):
    """The calendar's day, at the brand's send hour, in EACH RECIPIENT'S OWN
    time zone (the owner, 2026-09-19: "scheduling the emails for recipient time
    zone based off of our data"). The hour is the brand's, read from its
    simple.json with the evidence beside it. Setting the time is not
    scheduling: the draft carries it, and a person still presses Schedule."""
    st = lk.get("send_time") or {}
    if not st.get("local") or not slot.get("date"):
        sys.exit("no send time — add send_time.local to the brand's simple.json")
    # the API revision in use (2025-07-15) takes `datetime` + `options` on the
    # strategy itself; the older `options_static` shape is refused
    # `send_past_recipients_immediately` exists only on a local send — Klaviyo
    # refuses it on one fixed time for everyone (400, NonLocalStaticSend)
    local = bool(st.get("recipient_time_zone", True))
    options = {"is_local": local}
    if local:
        options["send_past_recipients_immediately"] = False
    return {"method": "static",
            "datetime": f"{slot['date']}T{st['local']}:00+00:00",
            "options": options}


def audience(brand, slot):
    """The slot's segment names and their Klaviyo ids, from the brand's own
    audience matrix. Returns (names, ids, missing names)."""
    matrix = json.loads((WORKSPACE / "brands" / brand / "email-sms/audience-matrix.json").read_text())
    ids = {s["name"]: s.get("id") for s in matrix["segments"]}
    names = slot.get("segments") or [slot["segment"]]
    return names, [ids.get(n) for n in names], [n for n in names if not ids.get(n)]


def push(email, lk, brand, label, pictures, pick, out_dir):
    # the pick first, before the Keychain or any upload (SI-151 (picked
    # subject gated)): a negative pick used to pass and send pair -1
    subs = email.get("subjects") or []
    if not 0 <= pick < len(subs):
        sys.exit(f"pick {pick} not in the subject set (0..{len(subs) - 1})")
    key = kl_key(lk)
    slot = the_slot(brand, label)
    if not slot:
        sys.exit(f"no calendar send named {label} for {brand} — the audience comes from "
                 "the plan, never guessed")
    names, seg, missing = audience(brand, slot)
    if missing:
        sys.exit(f"segment(s) {names} have no Klaviyo id in the audience matrix")

    cache = out_dir / "hosted.json"
    hosted = json.loads(cache.read_text()) if cache.is_file() else {}
    for n, p in pictures.items():
        if n not in hosted:
            hosted[n] = upload(key, p, f"{brand}-{label}-{n}")
    cache.write_text(json.dumps(hosted, indent=1) + "\n")
    logo = lk["logo"].get("url") or upload(key, logo_file(brand, lk["logo"]["file"]),
                                           f"{brand}-logo")
    doc = render(email, lk, hosted, logo)
    (out_dir / "email.html").write_text(doc)

    rec = create_draft(key, doc, email, lk, brand, label, slot, names, seg, pick,
                       send_strategy(lk, slot))
    (out_dir / "pushed.json").write_text(json.dumps(rec, indent=1) + "\n")
    return rec


def campaign_name(slot, subject, names):
    """What a person reads in Klaviyo's campaign list (the brand editor, 2026-10-01):
    send date | product | subject | audience — sortable by date and readable
    at a glance, in the same order as the brand's earlier hand-made names."""
    y, m, d = (slot.get("date") or "").split("-") if slot.get("date") else ("", "", "")
    when = f"{m}/{d}/{y}" if y else "no date"
    product = str(slot.get("product") or "")
    if product.lower() in ("", "none", "null"):      # a send about no one product
        product = slot.get("category") or "no product"
    product = product.replace("-", " ").title()
    who = ", ".join(re.sub(r"^Core \| ", "", n) for n in (names or [])) or "no audience"
    return f"{when} | {product} | {subject} | {who}"


def create_draft(key, doc, email, lk, brand, label, slot, names, seg, pick, strategy):
    """Template + DRAFT campaign + the template assigned to its message. No
    send call: a campaign only leaves Klaviyo through a send job, which this
    never creates. `strategy` None leaves the send time unset (Klaviyo's own
    default) — used when the plan's day has already passed."""
    subs = email.get("subjects") or []
    subject, preview = subs[pick]["subject"], subs[pick].get("preview", "")
    frm = lk.get("from") or {}
    if not frm.get("email"):
        sys.exit("no from-address in simple.json — fill it in before pushing")
    tpl = kl("POST", "templates", key, {"data": {"type": "template", "attributes": {
        "name": f"{brand} · {label} · simple", "editor_type": "CODE", "html": doc}}})
    attrs = {
        "name": campaign_name(slot, subject, names),
        "audiences": {"included": seg, "excluded": []},
        "campaign-messages": {"data": [{"type": "campaign-message", "attributes": {
            "definition": {"channel": "email", "label": label, "content": {
                "subject": subject, "preview_text": preview,
                "from_email": frm["email"], "from_label": frm.get("label") or brand}}}}]}}
    if strategy:
        attrs["send_strategy"] = strategy
    camp = kl("POST", "campaigns", key, {"data": {"type": "campaign", "attributes": attrs}})
    camp_id = camp["data"]["id"]
    msg_id = camp["data"]["relationships"]["campaign-messages"]["data"][0]["id"]
    kl("POST", "campaign-message-assign-template", key, {"data": {
        "type": "campaign-message", "id": msg_id,
        "relationships": {"template": {"data": {"type": "template", "id": tpl["data"]["id"]}}}}})
    return {"campaign_id": camp_id, "template_id": tpl["data"]["id"], "message_id": msg_id,
            "campaign_name": attrs["name"], "subject": subject,
            "preview": preview, "segments": names, "segment_ids": seg, "send_date": slot.get("date"),
            "send_time": (lk.get("send_time") or {}).get("local") if strategy else None,
            "recipient_time_zone": bool(strategy),
            "pushed_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "status": "DRAFT — schedule it in Klaviyo yourself"}


# --------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("run_dir")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--no-images", action="store_true", help="lay it out without making pictures")
    ap.add_argument("--push", action="store_true", help="create a Klaviyo DRAFT")
    ap.add_argument("--pick", type=int, default=0, help="subject pair (0 = the control)")
    a = ap.parse_args()
    run_dir = Path(a.run_dir).resolve()
    label = run_dir.name
    # THE ELEMENTS GATE: the layout is a real template, or nothing is built
    try:
        EE.layout(LAYOUT)
    except EE.Unknown as e:
        sys.exit(f"HELD at the elements gate — {e.args[0]}")
    email, lk = the_email(run_dir), look(a.brand)

    out_dir = WORKSPACE / "runs" / MACHINE / a.brand / label / "deliverable"
    how, media = drive_media(a.brand, label)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "email.json").write_text(json.dumps(email, indent=1, ensure_ascii=False) + "\n")

    pictures = {}
    if not a.no_images:
        where = ["runs", MACHINE, a.brand, label]
        if how == "api":            # made before, on another machine: read them back by id
            try:
                for n in ("hero", "offer"):
                    DR.get(where, f"{n}.png", media)
            except Exception as e:
                print(f"  pictures: could not read them back from the Drive "
                      f"({type(e).__name__}: {e}) — making them")
        have = {n: web_copy(media / f"{n}.png") for n in ("hero", "offer")
                if (media / f"{n}.png").is_file()}
        pictures = have or make_pictures(email, a.brand, media)
        if how == "api" and not have and pictures:
            _, placed, note = DR.put([media / f"{n}.png" for n in pictures]
                                     + [Path(p) for p in pictures.values()], where)
            print(f"  pictures: {len(placed)} file(s) to Shared Assets/runs/{MACHINE}/"
                  f"{a.brand}/{label}/ through the Drive API" + (f" — {note}" if note else ""))
        if how == "none":
            print(f"  pictures: kept in {media} only — the Drive was not reached")
    if lk["logo"].get("url"):
        logo = lk["logo"]["url"]
    else:
        import base64
        lf = logo_file(a.brand, lk["logo"]["file"])
        # an SVG's media type is image/svg+xml — "image/svg" renders nothing
        mt = {"svg": "svg+xml", "jpg": "jpeg"}.get(lf.suffix.lstrip('.').lower(),
                                                  lf.suffix.lstrip('.').lower())
        logo = f"data:image/{mt};base64," + base64.b64encode(lf.read_bytes()).decode()
    preview = render(email, lk, {n: inline(p) for n, p in pictures.items()}, logo)
    (out_dir / "preview.html").write_text(preview)
    print(f"email: {out_dir / 'preview.html'}")
    # which elements this email was built from, kept in the run's own record
    rj = run_dir / "run.json"
    if rj.is_file():
        try:
            state = json.loads(rj.read_text())
            picked = dict(state.get("elements") or {})
            picked["template/email"] = {"id": LAYOUT, "from": "library"}
            if picked != state.get("elements"):
                state["elements"] = picked
                rj.write_text(json.dumps(state, indent=2) + "\n")
        except ValueError:
            pass
    # THE DELIVERY GATE. check.json is the shared, gate-keyed shape
    # ({"delivery": {"result", "problems"}}); the old {"prices": "FAIL"} shape
    # blamed prices for every kind of failure.
    cj = out_dir / "check.json"
    if cj.is_file():
        try:
            old = json.loads(cj.read_text())
        except ValueError:
            old = {}
        kept = {k: v for k, v in old.items() if k in {g[0] for g in Q.GATES}}
        if kept != old:
            cj.write_text(json.dumps(kept, indent=1, ensure_ascii=False) + "\n")
    # A person's standing ruling clears a problem (HE-1 (fact rulings)); what
    # it cleared is written beside the rest in check.json, never dropped silently.
    kept, cleared = delivery_split(email, a.brand, run_dir, a.pick)
    for c in cleared:
        print(f"cleared by {c['by']}'s {c['ruling']} ruling: {c['id']}")
    try:
        Q.hold("delivery", [i["text"] for i in kept], out_dir, items=kept, cleared=cleared)
    except Q.Held as held:
        sys.exit("HELD — not sent to Klaviyo:\n  " + "\n  ".join(held.problems))
    if a.push:
        rec = push(email, lk, a.brand, label, pictures, a.pick, out_dir)
        print(f"Klaviyo DRAFT {rec['campaign_id']} · “{rec['subject']}” · "
              f"{', '.join(rec['segments'])} · set for {rec['send_date']} {rec['send_time']} "
              "recipient time — press Schedule in Klaviyo")


if __name__ == "__main__":
    main()
