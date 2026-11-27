"""The tracking standard as code: load it, build the ad URL tags, judge a URL-tag string.

Public surface (other components use these, nothing else in this folder):
    load()                  -> the standard (standard.json) as a dict
    url_tags()              -> the url_tags string every Meta ad carries
    check_url_tags(tags)    -> list of problems with a url_tags / query string ([] = matches)
    brand_tracking(brand)   -> brands/<brand>/web/funnels/tracking.json as a dict
    meta_name(event_id), ga4_name(event_id) -> the vendor names for a standard event

  Email links (standard.json, email_url):
    email_params(campaign, message, section=None, term=None) -> [(key, value)] for one email link
    tag_email_link(url, campaign, message, section=None, term=None, funnel=None) -> the url, tagged
    untag_email_link(url)   -> the url without the standard's email keys (to compare with the plain link)
    email_link_skip(url)    -> why a link is never tagged (mailto, merge tag, unsubscribe ...), or None
    funnel_for(url, tracking) -> the CPK funnel's name when the url is one of its pages, else None
    own_link(url, own_hosts)  -> True when the url is on one of the brand's own sites
    site_host(url_or_host)    -> the site without www., for own_hosts lists
    tag_email_html(doc, campaign, message, own_hosts, tracking=None, term=None) -> the HTML, every own link tagged
    check_email_link(url, tracking=None) -> problems with one own email link ([] = matches)
    check_email_html(doc, own_hosts, tracking=None) -> problems with every own link in an email
    klaviyo_tracking_params(campaign, term=None) -> Klaviyo's custom_tracking_params, same values
"""
import json
from pathlib import Path
import html as _html
import re as _re
from urllib.parse import parse_qsl, quote, unquote_plus, urlsplit, urlunsplit

HERE = Path(__file__).resolve().parent
COMPONENT = HERE.parent
STANDARD = COMPONENT / "standard.json"


def load(path=None):
    return json.loads(Path(path or STANDARD).read_text())


def url_tags(std=None):
    std = std or load()
    return "&".join(k + "=" + v for k, v in std["ad_url"]["params"])


def _pairs(tags):
    tags = (tags or "").strip()
    if "?" in tags:
        tags = tags.split("?", 1)[1]
    return parse_qsl(tags, keep_blank_values=True)


def check_url_tags(tags, std=None, strict=False):
    """Problems with one ad's URL tags, in plain words. [] means it matches the standard.

    strict=False accepts the old utm_source values the standard lists as legacy (live ads
    sent 'facebook' before the standard); strict=True wants the standard's exact value."""
    std = std or load()
    want = dict(std["ad_url"]["params"])
    legacy = set(std["ad_url"].get("accepted_legacy_sources", []))
    have = {}
    for k, v in _pairs(tags):
        have.setdefault(k, v)
    out = []
    if not tags or not str(tags).strip():
        return ["no URL tags at all: the order arrives with no ad name"]
    for k, v in want.items():
        if k not in have:
            out.append("missing " + k + "=" + v)
            continue
        got = have[k]
        if got == v:
            continue
        if k == "utm_source" and not strict and got.lower() in legacy:
            continue
        out.append(k + " is " + repr(got) + ", the standard is " + repr(v))
    if "utm_content" in have and have["utm_content"] in ("{{ad.id}}",):
        out.append("utm_content carries the ad id, not the ad name: orders can't be split by brief")
    return out


def check_landing_url(url, std=None):
    """Problems with an ad's website URL itself: placeholders typed into the link are not filled
    by Meta in every format, so they must live in url_tags instead."""
    out = []
    if "{{" in (url or ""):
        out.append("the website link has {{...}} placeholders typed in; move them to URL parameters")
    return out


def brand_tracking(brand, repo=None):
    import sys
    if repo is None:
        sys.path.insert(0, str(COMPONENT.parent / "brandpath"))
        from brandpath import brand_path
        f = brand_path(brand, "web/funnels", "tracking.json")
    else:
        f = Path(repo) / "brands" / brand / "web" / "funnels" / "tracking.json"
    return json.loads(Path(f).read_text())


def event(std, eid):
    for e in std["events"]:
        if e["id"] == eid:
            return e
    raise KeyError(eid)


def meta_name(eid, std=None):
    return event(std or load(), eid)["meta"]


def ga4_name(eid, std=None):
    return event(std or load(), eid)["ga4"]


# ------------------------------------------------------------------ email links

def _email(std=None):
    return (std or load())["email_url"]


def email_params(campaign, message, section=None, term=None, std=None):
    """The standard's email tags for one link, in the standard's order. utm_content is
    <message>.<section> when the link's place in the email is given; utm_term is left out
    when there is no segment or flow step to name."""
    e = _email(std)
    vals = {"campaign": campaign, "message": message, "term": term}
    out = []
    for k, v in e["params"]:
        slot = e.get("slots", {}).get(v)
        if slot:
            v = vals.get(slot)
            if slot == "message" and v and section:
                v = "%s.%s" % (v, section)
        if v is None or str(v).strip() == "":
            continue
        out.append((k, str(v)))
    return out


_SKIP_SCHEMES = ("mailto:", "tel:", "sms:", "cid:", "data:", "javascript:")
_SKIP_WORDS = ("unsubscribe", "manage_preferences", "manage-preferences", "preferences_link",
               "opt-out", "optout")


def email_link_skip(url):
    """Why a link is never tagged, or None when it is a link the standard tags."""
    u = (url or "").strip()
    low = u.lower()
    if not u or u.startswith("#"):
        return "an anchor"
    if low.startswith(_SKIP_SCHEMES):
        return "not a web link"
    if u.startswith("{%") or u.startswith("{{"):
        return "a Klaviyo merge-tag link"
    if any(w in low for w in _SKIP_WORDS):
        return "an unsubscribe or preference link"
    if not low.startswith(("http://", "https://")):
        return "not a web link"
    return None


def _host(url):
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def _base(h):
    h = (h or "").lower().strip().strip(".")
    if "://" in h:
        h = _host(h)
    return h[4:] if h.startswith("www.") else h


def site_host(url_or_host):
    """The site a url or host belongs to, without www. ('https://www.x.com/a' -> 'x.com')."""
    return _base(url_or_host)


def own_link(url, own_hosts):
    """True when url sits on one of the brand's own sites (a host or any subdomain of it)."""
    h = _base(_host(url))
    if not h:
        return False
    for b in own_hosts or ():
        b = _base(b)
        if b and (h == b or h.endswith("." + b)):
            return True
    return False


def funnel_for(url, tracking):
    """The funnel's name when url is one of a brand's CPK funnel pages (tracking.json: a listed
    host and a path under the funnel's own folder), else None."""
    if not tracking or email_link_skip(url):
        return None
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    h, path = (parts.hostname or "").lower(), parts.path or "/"
    for f in tracking.get("funnels") or []:
        if h not in [x.lower() for x in f.get("hosts") or []]:
            continue
        roots = {"/" + p["path"].strip("/").split("/")[0] + "/" for p in f.get("pages") or [] if p.get("path")}
        if any(path.startswith(r) or path.rstrip("/") + "/" == r for r in roots):
            return f.get("name")
    return None


def _email_keys(std=None):
    e = _email(std)
    return [k for k, _ in e["params"]] + [e.get("funnel_param", "funnel")]


def _split(url):
    base, frag = (url.split("#", 1) + [""])[:2] if "#" in url else (url, "")
    q = ""
    if "?" in base:
        base, q = base.split("?", 1)
    return base, q, frag


def untag_email_link(url, std=None):
    """The link without the standard's email keys; every other part kept as written."""
    keys = set(_email_keys(std))
    base, q, frag = _split(url)
    kept = [p for p in q.split("&") if p and p.split("=", 1)[0] not in keys]
    return base + ("?" + "&".join(kept) if kept else "") + ("#" + frag if frag else "")


def _redirect(url, std=None):
    """(position in the query, key, target) when the link is a redirect the standard names
    (email_url.redirect_params, e.g. a store's /discount/<code>/?next=/product/): the store applies
    the code and sends the reader on to the target with only the target's own query string, so
    tags on the outer link are lost on the way. None for any other link."""
    names = set(_email(std).get("redirect_params") or [])
    if not names:
        return None
    for i, part in enumerate(_split(url)[1].split("&")):
        k, eq, v = part.partition("=")
        if eq and k in names:
            target = unquote_plus(v)
            if target.startswith("/") or target.lower().startswith(("http://", "https://")):
                return i, k, target
    return None


def tag_email_link(url, campaign, message, section=None, term=None, funnel=None, std=None):
    """The link with the standard's email tags. The rest of its query string is kept exactly as
    written (merge tags included); a standard key already there is replaced, never doubled.
    A redirect link (_redirect) also carries the tags on its target, so they reach the page."""
    if email_link_skip(url):
        return url
    std = std or load()
    pairs = email_params(campaign, message, section, term, std)
    if funnel:
        pairs.append((_email(std).get("funnel_param", "funnel"), funnel))
    plain = untag_email_link(url, std)
    add = "&".join(k + "=" + quote(v, safe="-_.~") for k, v in pairs)
    hop = _redirect(plain, std)
    if hop:
        i, key, target = hop
        tb, tq, tf = _split(untag_email_link(target, std))
        target = tb + "?" + (tq + "&" + add if tq else add) + ("#" + tf if tf else "")
        base, q, frag = _split(plain)
        parts = q.split("&")
        parts[i] = key + "=" + quote(target, safe="")
        plain = base + "?" + "&".join(parts) + ("#" + frag if frag else "")
    base, q, frag = _split(plain)
    q = q + "&" + add if q else add
    return base + "?" + q + ("#" + frag if frag else "")


def _query(url):
    q = _split(url)[1]
    have = {}
    for part in q.split("&"):
        if not part:
            continue
        k, _, v = part.partition("=")
        have.setdefault(k, unquote_plus(v))
    return have


def check_email_link(url, tracking=None, std=None):
    """Problems with one own email link, in plain words. [] means it carries the standard."""
    std = std or load()
    e = _email(std)
    fixed = {k: v for k, v in e["params"] if v not in e.get("slots", {})}
    have = _query(url)
    out = []
    for k in e.get("required", []):
        if not have.get(k, "").strip():
            out.append("%s: missing %s" % (url, k))
        elif k in fixed and have[k] != fixed[k]:
            out.append("%s: %s is %r, the standard is %r" % (url, k, have[k], fixed[k]))
    fn = funnel_for(url, tracking)
    fp = e.get("funnel_param", "funnel")
    if fn and have.get(fp) != fn:
        out.append("%s: a %s funnel page with no %s=%s" % (url, fn, fp, fn))
    hop = _redirect(url, std)
    if hop:
        there = _query(hop[2])
        for k in e.get("required", []):
            if not there.get(k, "").strip():
                out.append("%s: the page it sends the reader on to (%s=) is missing %s" % (url, hop[1], k))
    return out


_HREF = _re.compile(r'(<a\b[^>]*?\bhref=)(["\'])(.*?)\2', _re.I | _re.S)
_SECTION = _re.compile(r'\bdata-ut=(["\'])(.*?)\1', _re.I)


def email_links(doc):
    """[(href, section)] for every <a href> in an email; section is the anchor's data-ut, else None."""
    out = []
    for m in _HREF.finditer(doc or ""):
        tag_end = doc.find(">", m.end())
        sec = _SECTION.search(doc[m.start():tag_end if tag_end > 0 else m.end()])
        out.append((_html.unescape(m.group(3)), sec.group(2) if sec else None))
    return out


def tag_email_html(doc, campaign, message, own_hosts, tracking=None, term=None, std=None):
    """Every own link in an email, tagged. A link's section is its anchor's data-ut attribute
    (button, logo ...), else link-<n> in order. Partner links, merge tags, mailto/tel and
    unsubscribe links are left exactly as they are."""
    std = std or load()
    n = [0]

    def sub(m):
        tag_end = doc.find(">", m.end())
        sec = _SECTION.search(doc[m.start():tag_end if tag_end > 0 else m.end()])
        url = _html.unescape(m.group(3))
        if email_link_skip(url) or not own_link(url, own_hosts):
            return m.group(0)
        n[0] += 1
        section = sec.group(2) if sec else "link-%d" % n[0]
        new = tag_email_link(url, campaign, message, section, term, funnel_for(url, tracking), std)
        return m.group(1) + m.group(2) + _html.escape(new, quote=True) + m.group(2)
    return _HREF.sub(sub, doc or "")


def check_email_html(doc, own_hosts, tracking=None, std=None):
    """Problems with every own link in an email ([] = every own link carries the standard)."""
    out = []
    for url, _ in email_links(doc):
        if email_link_skip(url) or not own_link(url, own_hosts):
            continue
        out += check_email_link(url, tracking, std)
    return out


def klaviyo_tracking_params(campaign, term=None, std=None):
    """Klaviyo's own UTM tracking for a campaign (tracking_options.custom_tracking_params), set
    to the same values the links carry, for the keys the standard lets Klaviyo set."""
    std = std or load()
    e = _email(std)
    want = set(e.get("klaviyo_campaign_level", []))
    return [{"type": "static", "name": k, "value": v}
            for k, v in email_params(campaign, campaign, None, term, std) if k in want]
