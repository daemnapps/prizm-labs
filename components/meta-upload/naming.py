#!/usr/bin/env python3
"""What things are called in the ad account, and how a batch is cut to fit.

The rule is: **read the convention off the account, do not invent one.** Open
the live campaigns, see how they are already named, and add only what is
missing — typically the funnel on the campaign and the drop date on the ad
set, because those are what make a drop findable later.

There is no default brand and no reference brand. Every account states its
own shape as a template, and this module renders whichever it is given. Two
shapes seen in the wild:

    {market!u}{sep}{product}{sep}{funnel!u}{sep}{lane!t}     sep " | "
    {budget!l}{sep}{market!l}{sep}{event!l}{sep}{product!l}  sep "_"

A brand's own words — which market, which product, how it spells its slugs
— come from `brands/<brand>/meta/account.json`, never from here.

    campaign   which market, product, funnel, and lane?
    ad set     which avatar, which promise, and which drop?
    ad         which exact picture?

    MARKET | PRODUCT | FUNNEL | Lane            <- the campaign
      Avatar | Man | Promise | YYMMDD           <- the ad set
        <the 13-field ad name>                  <- the ad

The campaign persists for months — it is the thing whose CPA is compared
month over month, so nothing dated or creative-specific goes in it. The drop
date on the ad set is the owner's rule (2026-09-11): "Every time we run a new
batch of creatives, we need to create a new ad set to put that batch of
creatives in." It is also forced — `Culture Integration` already holds 115
ads, `Content Creator` 62 and `Problem Solution` 60, so those themes cannot
take another ad without a new ad set under them. The ad name is the 13-field
spec and is not this module's business — it arrives already named.

Pipes separate the fields because that is what the account already uses, and
because the ad name owns hyphens.

Read `STRUCTURE.md` beside this file for the limits these rules exist to
respect. The one that shapes everything: 50 ads per ad set, hard.
"""
from datetime import date

# Meta's hard cap, verified against the Help Center 2026-09-11. It is not a
# guideline and not tier-dependent — regular and managed accounts both get 50.
ADS_PER_AD_SET = 50

# The default shape, which is what the first account through here already ran.
# A brand whose account names things differently declares its own in
# `brands/<brand>/meta/account.json` under `naming` — see `render`.
# `sep` is the default joint; `campaign_sep` / `ad_set_sep` override it for
# one name. Both levels need their own because an account can join campaign
# fields with underscores while its ad sets read as Title Case prose, and
# at least one live account does exactly that.
DEFAULT = {
    "sep": " | ",
    "campaign": "{market!u}{sep}{product}{sep}{funnel!u}{sep}{lane!t}",
    "ad_set": "{avatar!t}{sep}{talent!t}{sep}{problem!t}{sep}{shipped}",
}


def sep_for(n, level):
    """The separator for one level, falling back to the brand's default."""
    return n.get(f"{level}_sep", n.get("sep", DEFAULT["sep"]))

CASES = {
    "u": lambda v, spell: str(v).upper(),
    "l": lambda v, spell: str(v).lower(),
    "t": lambda v, spell: pretty(v, spell),
    "":  lambda v, spell: str(v),
}


def render(template, fields, sep=" | ", spell=None):
    """A name from a template, with empty fields and their separator dropped.

    The template is the brand's, because **the convention is read off the
    account, never imposed on it.** No shape here is the default; these are
    two that exist:

        {market!u}{sep}{product}{sep}{funnel!u}{sep}{lane!t}
            -> US | WIDGET™ | ICON | Avatar One

        {budget!l}_{market!l}_{event!l}_{product!l}_{lane!l}
            -> cbo_us_purchase_body-scrub_creators

    `!u` upper, `!l` lower, `!t` Title Case through the brand's own spelling
    map, and no suffix means leave it exactly as written. `{sep}` is the
    brand's separator so one setting changes every joint.

    A field that is missing or empty takes its separator with it, so an
    optional part — a lane, a qualifier — simply is not there rather than
    leaving a dangling `| |`.
    """
    import re
    out, last_sep = [], ""
    for chunk in re.split(r"(\{sep\})", template):
        if chunk == "{sep}":
            last_sep = sep
            continue
        def sub(m):
            key, _, case = m.group(1).partition("!")
            v = fields.get(key)
            return "" if v in (None, "") else CASES[case](v, spell)
        piece = re.sub(r"\{([a-z_]+(?:![ult])?)\}", sub, chunk)
        if piece:
            out.append((last_sep if out else "") + piece)
        last_sep = ""
    return "".join(out)


def campaign(fields, template=None, sep=None, spell=None):
    """The persistent container. Stable for the life of the lane.

    Whatever the shape, the rule about CONTENT is the same in every account:
    no date, no avatar, no batch. Put any of those in a campaign name and it
    stops being comparable to itself next month, which is its whole job.

    The lane belongs here because lanes never blend — two lanes are different
    arguments to different people and must never share a budget Meta can move
    between.
    """
    return render(template or DEFAULT["campaign"], fields,
                  sep if sep is not None else DEFAULT["sep"], spell)


def ad_set(fields, shard=1, shards=1, template=None, sep=None, spell=None):
    """One avatar, one person, one promise, one drop.

    The ad set is the only place spend can be forced. Inside one, Meta decides
    where the money goes and it will back one option and starve the rest — so
    anything you would be annoyed to see skipped needs its own ad set, and
    anything you are happy for Meta to choose between does not.

    Three things fail that test, so three things split.

    The **promise**: forty-year-shaver carried 37 razor-bump ads beside 12
    about lines. In one ad set the lines ads would never have spent.

    The **person in the picture**: the owner, 2026-09-11, "the white guy, black
    guy, and indian dude should not be in the same ad set". Where three
    people play the same avatar, one ad set means Meta picks a face and the
    other two are never really tested. Note what this is and is not — it
    separates the CREATIVE so each of them gets shown. It is not targeting:
    every ad set stays broad, and nobody is targeted by who they are.

    The **avatar**, which was already the split, and leads the name so an
    avatar's ad sets sort together in a column that truncates.

    Not the format, not the concept: those Meta may choose between, and the ad
    name says afterwards which won.

    `shipped` is the day the batch goes into the account (YYMMDD), not the day
    the pictures were made — the ad name already carries that. Dating it here
    means nothing ever fills up: each drop opens new ad sets.

    The shard suffix appears only past the 50-ad cap.
    """
    fields = dict(fields)
    if isinstance(fields.get("shipped"), date):
        fields["shipped"] = fields["shipped"].strftime("%y%m%d")
    sep = sep if sep is not None else DEFAULT["sep"]
    name = render(template or DEFAULT["ad_set"], fields, sep, spell)
    return f"{name}{sep}{shard} of {shards}" if shards > 1 else name


# Slugs are kebab-case everywhere they are stored and Title Case everywhere
# the owner reads them. Ads Manager is somewhere he reads.
#
# No brand's words live here. A brand's own spellings — `el-jefe` -> `El
# Jefe`, `avatarone` -> `Avatar One` — are in its account.json, and
# `Brand.pretty` is passed in as `spell` by whoever knows the brand. Called
# without one, this falls back to a plain capitalise, which is right for
# every slug a brand has not had to correct.
def pretty(slug, spell=None):
    if spell:
        return spell(slug)
    return " ".join(w.capitalize() for w in str(slug).split("-"))


def shards(n, cap=ADS_PER_AD_SET):
    """How many ad sets a batch of n ads needs."""
    return max(1, -(-n // cap))


def deal(items, key=None, cap=ADS_PER_AD_SET):
    """Cut a batch into ad sets of at most `cap`, dealt round-robin.

    Round-robin rather than sliced, so every ad set gets the same mix of
    sub-avatars and concepts. That makes the ad sets interchangeable, which
    is the point: the ad set is a container forced on us by the 50-cap, not
    a variable under test. If one shard outran another on a sliced deal we
    would not know whether we had learned something about the creative or
    just about which pictures landed in which bucket.

    `key` groups first (by sub-avatar, say) so the deal alternates across
    groups instead of dealing an accidental run of one.

    Returns a list of lists, longest first, none longer than `cap`.
    """
    items = list(items)
    n = shards(len(items), cap)
    out = [[] for _ in range(n)]
    if not key:
        for i, it in enumerate(items):
            out[i % n].append(it)
        return out

    # Deal each group in turn off one running counter, rather than
    # interleaving the groups first. Interleaving looks like the obvious
    # move and is wrong: it produces a cycle as long as there are groups,
    # and whenever that length shares a factor with n the same groups land
    # in the same shards every time. Six sub-avatars into three ad sets put
    # two whole sub-avatars in one shard and none in another. Carrying the
    # counter across groups spreads every group evenly and keeps the shards
    # within one ad of each other.
    buckets = {}
    for it in items:
        buckets.setdefault(key(it), []).append(it)
    k = 0
    for group in sorted(buckets):
        for it in buckets[group]:
            out[k % n].append(it)
            k += 1
    return out


if __name__ == "__main__":
    # Two real accounts, two conventions, one renderer — neither invented.
    pipes = {"sep": " | ",
             "campaign": "{market!u}{sep}{product}{sep}{funnel!u}{sep}{lane!t}",
             "ad_set": "{avatar!t}{sep}{talent!t}{sep}{problem!t}{sep}{shipped}"}
    under = {"sep": "_",
             "campaign": "{budget!l}{sep}{market!l}{sep}{event!l}{sep}{product!l}{sep}{lane!l}",
             "ad_set": "{theme}"}

    print(campaign({"market": "us", "product": "WIDGET\u2122", "funnel": "icon",
                    "lane": "avatarone"}, pipes["campaign"], pipes["sep"],
                   spell=lambda s: {"avatarone": "Avatar One"}.get(s, s.title())))
    print(campaign({"budget": "cbo", "market": "us", "event": "purchase",
                    "product": "body-scrub", "lane": "creators"},
                   under["campaign"], under["sep"]))
    print(campaign({"budget": "cbo", "market": "us", "event": "purchase",
                    "product": "body-scrub"},          # no lane -> no dangling _
                   under["campaign"], under["sep"]))
    print(ad_set({"avatar": "forty-year-shaver", "talent": "ray",
                  "problem": "razorbumps", "shipped": "260911"},
                 template=pipes["ad_set"], sep=pipes["sep"]))
    print(ad_set({"theme": "Promotion"}, template=under["ad_set"], sep=under["sep"]))
