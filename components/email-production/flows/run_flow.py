#!/usr/bin/env python3
"""Fill one flow prompt from the brand's files and bank, ready for a writer to run. Calls no model.

    python3 flows/run_flow.py --brand brand_a --flow welcome --avatar fed-up-king [--offer NAME]
        [--product FILE] [--set length=6 --set link=https://...] [--out FILE]

Every placeholder is filled from the sources in README.md ("What fills each input"). One the files cannot fill
(a link, a length, a story the brand has not filed) is set with --set, or is left as `[UNFILLED] name` so the
writer sees the gap instead of a guess. The filled prompt goes to --out (default: stdout) with a header that
lists which bank queries filled which slot.

THE BANK QUERIES BY FLOW (2026-11-07). The bank's rows carry a funnel: prospect (social comments from people
who have not opted in), lead (people who opted in, commented on an ad or abandoned), customer (buyers) and
churned. A flow speaks to one of those people, so its customer and objection rows come from that funnel, and its
proof rows always come from buyers. Before this, the flows' only query was the prospect one, which returns
social comments only.

Writes nothing but --out. The bank query is made without a run id, so no exposure record is written: nothing
is shown to a reader until a writer runs the prompt. Never sends, schedules or builds anything in a platform.
Python 3.9, standard library plus the repo's own modules.
"""
import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMP = HERE.parent
WS = COMP.parents[1]
sys.path.insert(0, str(COMP))
# the email lane's own modules first (offers -> paths), then the copy lane's language query, the order
# email_line.py uses; the other way round, copywriter's paths.py shadows this one and offers fails to import
try:
    import offers as OFFERS
except Exception as e:                                    # pragma: no cover
    OFFERS, OFFERS_ERR = None, e
sys.path.insert(0, str(WS / "components" / "copywriter" / "machine"))
sys.path.append(str(WS / "components" / "naming"))
import names as NAMES  # noqa: E402  one product name (2026-11-19)

PROMPTS = HERE / "prompts"
# flow -> (funnel of the reader: customer and objection rows, funnel of the proof rows)
FLOW_FUNNELS = {
    "welcome": ("lead", "customer"),
    "soap-opera": ("lead", "customer"),
    "cart-abandonment": ("lead", "customer"),
    "checkout-abandonment": ("lead", "customer"),
    "lander": ("lead", "customer"),
    "product-page": ("lead", "customer"),
    "post-purchase": ("customer", "customer"),
    "upsell-sequence": ("customer", "customer"),
    "upsell-page": ("customer", "customer"),
}
UNFILLED = "[UNFILLED] {name} — not on file; set it with --set {name}=... or leave the line general"


def prompt_file(flow):
    files = sorted(PROMPTS.glob("%s-v*-owner.md" % flow), key=lambda f: int(re.search(r"-v(\d+)-", f.name).group(1)))
    if not files:
        raise SystemExit("no prompt for flow %r in %s; the flows are: %s" % (flow, PROMPTS, ", ".join(sorted(FLOW_FUNNELS))))
    return files[-1]


def read(path):
    p = Path(path)
    if p.is_dir():
        return "\n\n".join("## %s\n\n%s" % (f.name, f.read_text()) for f in sorted(p.glob("*.md")))
    return p.read_text().strip() if p.is_file() else ""


ALWAYS_SECTIONS = ("proof",)      # the bank's filed proof travels with any named offer


def offer_section(bank_text, offers):
    """The named offers' own sections of the offer bank (## or ### headings, matched on the id before the
    dash), plus its Proof section; the whole bank when no offer is named."""
    if not offers:
        return bank_text
    want = [o.strip().lower() for o in offers] + list(ALWAYS_SECTIONS)
    lines, out, keep, level = bank_text.splitlines(), [], False, 0
    for line in lines:
        m = re.match(r"^(#{2,3}) (.+)$", line)
        if m:
            depth, sid = len(m.group(1)), re.split(r"\s+[—-]\s+", m.group(2).strip())[0].strip().lower()
            if keep and depth <= level:
                keep = False
            if not keep and sid in want:
                keep, level = True, depth
        if keep:
            out.append(line)
    return "\n".join(out)


def language(brand, stage, avatar, funnel, limit=40):
    """The bank rows for one slot, queried the way the email line does, with no run id (nothing recorded)."""
    if not avatar:
        return "(no avatar was declared, so there is no customer language for this flow)"
    try:
        import language as L
    except Exception as e:                                # pragma: no cover - the copy lane is absent
        return "(the language layer is not importable here: %s)" % e
    text = L.for_stage(brand, stage, avatar, funnel, None, limit, None, used="fresh", moments=False)
    if stage == "injection":                              # the lived moments ride once, picked without a record
        try:
            sys.path.insert(0, str(WS / "components" / "language-layer"))
            from language_layer import experience as X
            rows = X.pick(brand, avatar, record=False)
            if rows:
                text += ("\n\n## Lived moments for this flow\n\nReal moments in their own words. A lived moment "
                         "in this flow comes from this list, never from memory or another ad.\n\n" + X.render(rows))
        except Exception:                                 # pragma: no cover - no moments index for this avatar
            pass
    return text


def sources(brand, avatar, offer, product, flow):
    b = WS / "brands" / brand
    reader, proof = FLOW_FUNNELS[flow]
    if OFFERS is None:
        raise SystemExit("the offer rules can't be read (offers.py did not import: %s)" % OFFERS_ERR)
    offer_rule = OFFERS.writer_rules(brand, offer[0] if offer else None)
    bank = read(b / "products" / "offer-bank.md")
    filled = {
        "brand": brand,
        "customer_language": language(brand, "injection", avatar, reader),
        "proof_language": language(brand, "proof", avatar, proof),
        "objection_language": language(brand, "close", avatar, reader),
        "language_bank": read(b / "core-avatars" / (avatar or "_none") / "language" / "rules.md"),
        "offer_rule": offer_rule,
        "offer": offer_section(bank, offer),
        "product_file": read(NAMES.product_file(brand, product) or b / "products" / product) if product else read(b / "products"),
        "mechanism": read(b / "brand-identity" / "position.md"),
        "shipping": read(b / "operations" / "shipping.md"),
        "offer_box": read(b / "offers" / "standard-offer-box.md"),
        "sender_identity": read(b / "email-sms" / "identity" / "sender.md"),
        "story": read(b / "brand-identity" / "story.md"),
        "words_rule": read(HERE / "WORDS.md"),
    }
    where = {"customer_language": "bank: injection rows, funnel %s" % reader,
             "proof_language": "bank: proof rows, funnel %s" % proof,
             "objection_language": "bank: close rows, funnel %s" % reader}
    return filled, where


def fill(flow, brand, avatar=None, offer=None, product=None, sets=None):
    """(the filled prompt, {slot: where it came from}, [slots left unfilled])."""
    p = prompt_file(flow)
    text = p.read_text()
    asks = sorted(set(re.findall(r"(?<!`)\{([a-z_]+)\}(?!`)", text)))    # slots, not names quoted in the tables
    got, where = sources(brand, avatar, offer, product, flow)
    got.update(sets or {})
    left = []
    for name in asks:
        value = got.get(name)
        if not value:
            value = UNFILLED.format(name=name)
            left.append(name)
        # only the slot itself is filled; a name written `{like_this}` in the inputs table or the rules stays text
        text = re.sub(r"(?<!`)\{%s\}(?!`)" % re.escape(name), lambda _m: str(value), text)
    return text, p, where, left


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fill one flow prompt. No model call, nothing sent.")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--flow", required=True, choices=sorted(FLOW_FUNNELS))
    ap.add_argument("--avatar")
    ap.add_argument("--offer", action="append", default=[], help="an offer id from the offer bank; repeat for more")
    ap.add_argument("--product", help="a file name under brands/<brand>/products/")
    ap.add_argument("--set", action="append", default=[], metavar="NAME=VALUE")
    ap.add_argument("--out")
    import importlib.util as _u, pathlib as _pl
    _s = _u.spec_from_file_location("profile_arg", next(q for q in _pl.Path(__file__).resolve().parents if q.name == "components") / "naming" / "profile_arg.py")
    _PA = _u.module_from_spec(_s); _s.loader.exec_module(_PA)   # --profile <avatar>[_<sub>][_<demographic>] (naming/PEOPLE.md)
    a = ap.parse_args(_PA.expand(argv, has=('avatar',)))
    sets = dict(s.split("=", 1) for s in a.set if "=" in s)
    text, p, where, left = fill(a.flow, a.brand, a.avatar, a.offer, a.product, sets)
    head = ["<!-- filled by flows/run_flow.py from %s · status: draft · no model call made" % p.name]
    head += ["     %s: %s" % (k, v) for k, v in sorted(where.items())]
    head += ["     unfilled: %s -->" % (", ".join(left) or "none")]
    out = "\n".join(head) + "\n\n" + text
    if a.out:
        Path(a.out).write_text(out)
        print("wrote %s (%d unfilled: %s)" % (a.out, len(left), ", ".join(left) or "none"))
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
