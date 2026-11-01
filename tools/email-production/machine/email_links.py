"""Every link in an email carries the tracking standard's email tags (the owner, 2026-10-12:
"make sure when we ... schedule emails that utm parameters are all set up properly so we can
also stitch together our funnel data end to end").

The tags themselves are the funnel-tracking component's (components/funnel-tracking/
standard.json, email_url), read through its public surface (machine/standard.py). Nothing
here restates a tag name or value. This file only finds, for a brand, which sites are its own
and which pages are its CPK funnels — from the brand's own files:

    brands/<brand>/email-sms/simple.json   logo.link
    brands/<brand>/email-sms/machine.json  site
    brands/<brand>/web/funnels/tracking.json  every funnel's hosts (and its pages, for funnel=)

    tag(doc, brand, campaign, message=None, term=None) -> the email HTML, every own link tagged
    problems(doc, brand)                              -> own links missing the tags ([] = ok)
    klaviyo_tracking(campaign, term=None)             -> a campaign's tracking_options, same values
    term_for(segment_names)                           -> utm_term for a send's audience
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMPONENT = HERE.parent
WORKSPACE_DEFAULT = COMPONENT.parent.parent
_STD = COMPONENT.parent / "funnel-tracking" / "machine"
if str(_STD) not in sys.path:
    sys.path.append(str(_STD))
import standard as T  # noqa: E402  (components/funnel-tracking public surface)


def _read(f):
    try:
        return json.loads(Path(f).read_text())
    except (OSError, ValueError):
        return {}


def tracking(brand, workspace=None):
    """The brand's tracking.json, or {} when it has none (no funnel= then; tags still go on)."""
    ws = Path(workspace or WORKSPACE_DEFAULT)
    return _read(ws / "brands" / brand / "web" / "funnels" / "tracking.json")


def own_hosts(brand, workspace=None):
    """The brand's own sites, read off its own files. Never typed here."""
    ws = Path(workspace or WORKSPACE_DEFAULT)
    root = ws / "brands" / brand
    out = []
    logo = (_read(root / "email-sms" / "simple.json").get("logo") or {}).get("link")
    site = _read(root / "email-sms" / "machine.json").get("site")
    for u in (logo, site):
        if u and str(u).startswith("http"):
            out.append(T.site_host(u))
    for f in tracking(brand, ws).get("funnels") or []:
        out += list(f.get("hosts") or [])
    return sorted({T.site_host(h) for h in out if h})


TERM_MAX = 100   # Klaviyo refuses a tracking param value longer than this (400, 2026-10-15)


def term_for(segment_names):
    """utm_term for a send: its segment names joined, at most TERM_MAX characters. Too long
    (a send to every segment of a group) → the shared group prefix is said once
    ("Core | Lead + One-Time Customer + …"); still too long → cut, ending in "…"."""
    names = [n for n in (segment_names or []) if n]
    term = " + ".join(names) or None
    if not term or len(term) <= TERM_MAX:
        return term
    prefixes = {n.split(" | ", 1)[0] for n in names}
    if len(prefixes) == 1 and all(" | " in n for n in names):
        group = prefixes.pop()
        term = group + " | " + " + ".join(n.split(" | ", 1)[1] for n in names)
    return term if len(term) <= TERM_MAX else term[:TERM_MAX - 1].rstrip() + "…"


def _hosts(doc, brand, workspace):
    """The brand's own sites; a brand that names none treats every web link in the email as
    its own, so nothing leaves untagged for want of a site list."""
    hosts = own_hosts(brand, workspace)
    if hosts:
        return hosts
    return sorted({T.site_host(u) for u, _ in T.email_links(doc) if not T.email_link_skip(u)})


def tag(doc, brand, campaign, message=None, term=None, workspace=None):
    return T.tag_email_html(doc, campaign, message or campaign, _hosts(doc, brand, workspace),
                            tracking(brand, workspace), term)


def problems(doc, brand, workspace=None):
    return T.check_email_html(doc, _hosts(doc, brand, workspace), tracking(brand, workspace))


def klaviyo_tracking(campaign, term=None):
    """tracking_options for a Klaviyo campaign: Klaviyo's own UTM tracking on, with the same
    values the links carry, so the two never disagree."""
    return {"add_tracking_params": True,
            "custom_tracking_params": T.klaviyo_tracking_params(campaign, term)}


def untag(url):
    return T.untag_email_link(url)
