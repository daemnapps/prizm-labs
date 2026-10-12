#!/usr/bin/env python3
"""The brief generator: one slot in, the document production consumes out.

    python3 brief.py results/compose-2026-09            # every slot
    python3 brief.py results/compose-2026-09 sep-03     # one slot

Deterministic — no model calls. A slot is already fully specified (that is
what a slot IS); this collects what the slot points at into one page and
writes the exact chain command that produces the email. Production never has
to open anything else.
"""
import argparse
import json
import sys
from pathlib import Path


def _json_or(path, default):
    """A brand file that is not there yet reads as empty — a brand with no
    history is a brand, not an error (Brand A, 2026-09-09)."""
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, ValueError):
        return default


def _text_or(path, default=""):
    try:
        return path.read_text()
    except FileNotFoundError:
        return default

from paths import HERE, WORKSPACE, component, run_home
sys.path.append(str(component("brandpath")))   # appended, never ahead of this machine
import brandpath as BP                                # noqa: E402


def moment_context(brand_root, occasion):
    """If the occasion names a calendar moment, carry its evidence along."""
    try:
        d = json.loads(BP.brand_path(brand_root.name, "strategy", "moments.json", root=brand_root.parent).read_text())
    except OSError:
        return None
    for av, block in d["avatars"].items():
        for m in block["moments"]:
            if m["key"] in (occasion or ""):
                lines = [f"`{m['key']}` · {m['stream']} · {m['window']} · "
                         f"evidence: {m['evidence']} · avatar: {av}"]
                if m.get("sent"):
                    lines.append("Already sent against it: " + " / ".join(m["sent"]))
                if m.get("note"):
                    lines.append(m["note"])
                return "\n".join(lines)
    return None


def spent_ground(brand_root, slot):
    """Every sent subject of this slot's type — the ground it may not reuse."""
    cl = _json_or(brand_root / "email-sms/classified.json", [])
    rows = [r for r in cl if r.get("type") == slot.get("type")]
    if not rows:
        return "(nothing of this type has ever been sent — the ground is clear)"
    return "\n".join(f"- {r['sent']} · “{r['subject']}”" for r in rows)


def offer_for(slot, brand, avatar):
    """The offer THIS VERSION may carry.

    A slot carries one offer; a send carries one version per avatar; and an
    offer belongs to one lane. Those three facts collided — a bundle send to
    Core | One-Time Customer assigned `volume-tiers` (avatar-one's) and then
    wrote a avatar-two version of it, which the bank refuses outright.

    A version whose lane the offer does not belong to carries NO offer. It
    earns instead. That is the honest answer: the alternative is either
    refusing to write the version at all, or letting one lane quote another
    lane's price, and the bank's own standing rule is one lane per offer.
    """
    o = slot.get("offer") or "none"
    if o == "none" or not avatar or avatar in ("mixed", "none"):
        return o
    try:
        sys.path.insert(0, str(HERE))
        import offers as OFFERS
        row = next((r for r in OFFERS.parse(brand) if r["key"] == o), None)
        if row and row.get("lane") and row["lane"] != avatar:
            return "none"
    except Exception:
        pass
    return o


def occasion_of(slot, brand):
    """The moment in words the writer can use, not the filing key.

    RULED 2026-09-10 (the owner: "this literally has nothing to do with football").
    A slot scheduled on `nfl-season` used to hand the chain the string
    "nfl-season" — and only to triage and the brief header at that. The brand's
    own moments file already says what the moment is, when its window runs and
    why it lands for this audience; that is what the copy needs."""
    occ = (slot.get("occasion") or "").strip()
    if not occ or occ.startswith("recorded problem") or occ.startswith("HELD OPEN"):
        return occ
    f = BP.brand_path(brand, "strategy", "moments.json", root=WORKSPACE / "brands")
    if not f.is_file():
        return occ
    found = {}

    def walk(o):
        if isinstance(o, dict):
            if o.get("key") == occ:
                found.update(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(json.loads(f.read_text()))
    if not found:
        return occ
    bits = [occ]
    if found.get("window"):
        bits.append(f"it runs {found['window']}")
    if found.get("note"):
        bits.append(found["note"].rstrip("."))
    return " — ".join(bits)



def partner_rule(slot, brand):
    """The partner's own record, as a rule the writer cannot miss.

    An affiliate send used to carry its partner only in prose — the occasion
    and the angle — so the real product name, the real tracked link and the
    terms of the arrangement never reached the stage that writes a word, and a
    writer could invent any of the three. Ruled 2026-09-21 after an
    `affiliate-feature` was reported to the owner as having no partner while the partner
    had been on the roster since 2026-09-02. The roster is the only source;
    nothing here is invented, and a slot naming a partner that is not active
    returns a refusal rather than a guess.
    """
    key = slot.get("affiliate")
    if not key:
        return ""
    f = WORKSPACE / "brands" / brand / "email-sms" / "affiliates.json"
    roster = _json_or(f, {}).get("affiliates", [])
    a = next((x for x in roster if x.get("key") == key
              and x.get("status", "active") == "active"), None)
    if not a:
        live = ", ".join(x["key"] for x in roster if x.get("status", "active") == "active")
        raise SystemExit(f"{slot['id']}: partner `{key}` is not active in "
                         f"{f} — on file: {live or 'none'}")
    lines = [f"THIS EMAIL FEATURES A PARTNER'S PRODUCT, NOT OURS: {a['name']}.",
             f"The only link for it is {a['link']} — never write another, and never "
             "shorten, prettify or invent one.",
             f"Why it belongs here: {a.get('blurb', '').strip()}",
             "It is theirs. Never describe it as ours, never imply we make it, and "
             "never put our guarantee on it."]
    if "traffic" in (a.get("commission") or "").lower():
        lines.append("The arrangement is traffic-only: NO commission, earnings, "
                     "payout or 'we get paid' claim appears anywhere in this email.")
    return " ".join(lines)


def chain_command(slot, brand, avatar=None, angle=None, label=None):
    """One chain run. A slot with variants calls this once per variant — each
    variant is its own email, addressed through its own avatar, carrying the
    specific argument the cells stage picked for it (--angle). A single-voice
    slot calls it once with no variant."""
    src = slot.get("source", "")
    if not src or src.startswith("[UNFILLED"):
        return ("[UNFILLED: no source fits — pick a swipe before this runs. "
                "The chain takes one: python3 email.py <source> ...]")
    parts = [f"python3 email.py ../brands/{brand}/email-sms/sends/{src}",
             f"--brand {brand}"]
    av = avatar if avatar is not None else slot.get("avatar")
    if av and av not in ("none", "mixed"):
        parts.append(f"--avatar {av}")
    for flag in ("product",):
        v = slot.get(flag)
        if v and v != "none":
            parts.append(f"--{flag} {v}")
    # "no offer" is a DECISION the calendar made, and the chain has to be told
    # it — silence used to mean "pick from the whole bank" (the owner, 2026-09-10)
    parts.append(f"--offer {offer_for(slot, brand, av)}")
    parts.append(f"--label {label or slot['id']}")
    parts.append(f'--source-reference "{slot["id"]}: {slot.get("occasion", "")}"')
    # the moment and the send day are FACTS THE COPY OBEYS, not filing labels
    # (RULED 2026-09-10 — a football slot came out with no football in it
    # because the occasion reached triage and the brief header and nothing else)
    if slot.get("occasion"):
        parts.append(f'--occasion "{occasion_of(slot, brand)}"')
    if slot.get("date"):
        parts.append(f'--send-date {slot["date"]}')
    research = run_home(brand, f'research-{slot["date"][:7]}') / f'{slot["id"]}.md'
    parts.append(f'--research {research}')
    if angle:
        parts.append(f'--angle "{angle}"')
    return " \\\n    ".join(parts)


def chain_argv(slot, brand, avatar=None, angle=None, label=None, brand_root=None,
               note=None):
    """Same run as chain_command, as a real argv list — no shell quoting to
    get wrong on an angle sentence full of punctuation."""
    src = slot.get("source", "")
    if not src or src.startswith("[UNFILLED"):
        return None
    # the brand tree is wherever paths.py says it is — never a relative
    # guess from this folder (the lab copy of brands/ moved 2026-09-02)
    # A slot may be written off ANOTHER brand's email — a brand with no library
    # of its own borrows shapes, declared in its own email/format-sources.json
    # (2026-09-14). The source lives with the brand it came from; the send is
    # still this brand's, so only the path moves.
    src_brand = slot.get("source_brand") or brand
    argv = [sys.executable, "email.py",
            str(WORKSPACE / "brands" / src_brand / "email-sms" / "sends" / src),
            "--brand", brand]
    av = avatar if avatar is not None else slot.get("avatar")
    if av and av not in ("none", "mixed"):
        argv += ["--avatar", av]
    for flag in ("product",):
        v = slot.get(flag)
        if v and v != "none":
            argv += [f"--{flag}", v]
    argv += ["--offer", offer_for(slot, brand, avatar)]
    # who receives it — the writer reads its funnel stage from this
    if slot.get("segment"):
        argv += ["--segment", slot["segment"]]
    argv += ["--label", label or slot["id"]]
    # the send's type IS an email format (components/elements, format/email);
    # the chain checks it before any step runs and records it in run.json
    if slot.get("type"):
        argv += ["--type", slot["type"]]
    argv += ["--source-reference", f'{slot["id"]}: {slot.get("occasion", "")}']
    if slot.get("occasion"):
        argv += ["--occasion", occasion_of(slot, brand)]
    if slot.get("date"):
        argv += ["--send-date", slot["date"]]
        # every send gets its week researched, not just the ones on a moment
        argv += ["--research", str(run_home(brand, f'research-{slot["date"][:7]}') / f'{slot["id"]}.md')]
    if angle:
        argv += ["--angle", angle]
    # what a human wrote on the review board before triggering this send,
    # with the partner's own record ahead of it when the slot names one
    if slot.get("affiliate"):
        argv += ["--affiliate", slot["affiliate"]]
    note = " ".join(x for x in (partner_rule(slot, brand), (note or "").strip()) if x)
    if note:
        argv += ["--note", note]
    if brand_root:
        argv += ["--brand-root", str(brand_root)]
    return argv


def label_prefix(run_dir, brand):
    """`<brand>-` when the month's runs carry the brand in their label, else "".
    A month at its home (runs/marketing-calendar/<brand>/<YYYY-MM>/) or a
    legacy `calendar-YYYY-MM-<brand>` folder is branded; a legacy unbranded
    `calendar-YYYY-MM` folder is not, so its old labels stay stable."""
    run_dir = Path(run_dir)
    if run_dir.parent.name == brand or run_dir.name.endswith("-" + brand):
        return brand + "-"
    return ""


def variant_runs(slot, brand):
    """(avatar, angle, label) for every chain run this slot needs — one per
    variant if the cells stage split this segment into an A/B test, else one
    plain run through the slot's own avatar."""
    variants = slot.get("variants") or []
    if not variants:
        return [(slot.get("avatar"), None, slot["id"])]
    if len(variants) == 1:
        v = variants[0]
        return [(v.get("avatar"), v.get("angle"), slot["id"])]
    return [(v.get("avatar"), v.get("angle"), f"{slot['id']}--{v.get('avatar')}")
            for v in variants]


def build_brief(slot, brand, brand_root):
    b = [f"# {slot['id']} — {slot.get('type')} · {slot.get('date')}", ""]
    b += ["The slot, fully specified. Production opens this page and nothing else.", ""]
    b += ["## The slot", ""]
    order = ("date", "hour", "local", "segment", "avatar", "sub_avatar",
             "category", "type", "role", "occasion", "product", "offer",
             "follows", "then")
    for k in order:
        v = slot.get(k)
        if k == "segment" and len(slot.get("segments") or []) > 1:
            v = f"ONE send to {len(slot['segments'])} segments — " + ", ".join(slot["segments"])
        b.append(f"- **{k}**: {v if v not in (None, '') else 'none'}")
    b += ["", f"**Why this slot exists:** {slot.get('why', '(the composer gave no why)')}", ""]

    mc = moment_context(brand_root, slot.get("occasion"))
    if mc:
        b += ["## The moment behind it", "", mc, ""]

    b += ["## Ground already spent — do not reuse", "",
          slot.get("spent") or "", "",
          "Every subject this type has already sent:", "",
          spent_ground(brand_root, slot), ""]

    src = slot.get("source", "")
    b += ["## The source", ""]
    if src and not src.startswith("[UNFILLED"):
        b += [f"`email-sms/sends/{src}` — the sent email whose shape this "
              "takes. The chain reads it directly.", ""]
    else:
        b += [src or "[UNFILLED: the composer named no source]", ""]

    b += ["## Obligations", ""]
    b.append(f"- **follows**: {slot.get('follows') or 'nothing — this opens its own ground'}")
    then = slot.get("then")
    b.append(f"- **then**: {then or 'nothing — self-contained'}"
             + (" (contingent — runs only if the ask stalls)" if then == "contingent" else ""))

    runs = variant_runs(slot, brand)
    b += ["", "## Produce it", ""]
    if len(runs) > 1:
        b.append(f"{len(runs)} variants — one email per avatar, same slot, "
                 "each run separately and shipped as one Klaviyo A/B test:")
        b.append("")
    for av, angle, label in runs:
        if len(runs) > 1:
            b.append(f"**{av}**" + (f" — {angle}" if angle else ""))
        b += ["```", chain_command(slot, brand, av, angle, label), "```",
              "Then draw it:  `python3 render_email.py results/" + label
              + f" --brand {brand}`", ""]
    return "\n".join(b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", help="a compose result folder holding slots.json")
    ap.add_argument("slot_ids", nargs="*", help="specific slots; default all")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.is_absolute():
        run_dir = HERE / run_dir
    slots_file = run_dir / "slots.json"
    if not slots_file.is_file():
        sys.exit(f"no slots.json in {run_dir} — run compose.py first")
    slots = json.loads(slots_file.read_text())
    run = json.loads((run_dir / "run.json").read_text())
    brand = run["brand"]
    brand_root = WORKSPACE / "brands" / brand

    want = set(args.slot_ids) or {s["id"] for s in slots}
    unknown = want - {s["id"] for s in slots}
    if unknown:
        sys.exit("not in this month: " + ", ".join(sorted(unknown)))

    out = run_dir / "briefs"
    out.mkdir(exist_ok=True)
    for slot in slots:
        if slot["id"] not in want:
            continue
        (out / f"{slot['id']}.md").write_text(build_brief(slot, brand, brand_root) + "\n")
        print(f"  -> briefs/{slot['id']}.md")
    print(f"done -> {out}")


if __name__ == "__main__":
    main()
