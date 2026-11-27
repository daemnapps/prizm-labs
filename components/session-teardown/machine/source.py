"""Where the visits and recordings come from — PostHog (live) or a recorded sample (samples/<name>/).

Both answer the same four questions, so every later step is the same code:
    page_views(brand, days)        -> [{session, page_id, step, at}]        one row per page view
    outcomes(brand, days)          -> [{session, event, revenue, at}]       checkout_click / checkout_reached / purchase
    recordings(session_ids)        -> {session: {duration_s, active_s, clicks, start_url, start}}  only sessions WITH a recording
    session_events(session_ids)    -> {session: [{at, event, url, text, scroll, tag}]}  in time order
    replay_link(session, at_s)     -> a link that opens the recording at that moment (None for samples)
    page_text(page_id)             -> the page as captured text, or None (live: page-teardown's capture reads it)

Live keys, by name only (components/keys/loader.py): POSTHOG_PERSONAL_API_KEY (read-only: query + recordings),
POSTHOG_PROJECT_ID. POSTHOG_HOST may override the default US host. Nothing is ever written to PostHog.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMPONENTS = HERE.parents[1]
DEFAULT_HOST = "https://us.posthog.com"
EVENT_COLS = ["$session_id", "timestamp", "event", "properties.$current_url", "properties.$el_text",
              "properties.$prev_pageview_max_scroll_percentage", "properties.$event_type"]


def _key(name, required=True):
    if str(COMPONENTS / "keys") not in sys.path:
        sys.path.append(str(COMPONENTS / "keys"))
    from loader import key
    return key(name, required=required)


def _quote(v):
    return "'" + str(v).replace("\\", "\\\\").replace("'", "\\'") + "'"


class PostHog:
    def __init__(self, host=None, project=None, token=None, opener=None):
        self.host = (host or os.environ.get("POSTHOG_HOST") or DEFAULT_HOST).rstrip("/")
        self.project = project or _key("POSTHOG_PROJECT_ID")
        self._token = token
        self._open = opener or urllib.request.urlopen

    def _call(self, method, path, body=None):
        token = self._token or _key("POSTHOG_PERSONAL_API_KEY")
        req = urllib.request.Request(self.host + path, method=method,
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
        with self._open(req) as r:
            return json.loads(r.read() or b"null")

    def query(self, hogql):
        out = self._call("POST", "/api/projects/%s/query/" % self.project,
                         {"query": {"kind": "HogQLQuery", "query": hogql}})
        return out.get("results") or []

    def page_views(self, brand, days):
        rows = self.query(
            "select $session_id, properties.page_id, properties.page_step, timestamp from events "
            "where event = '$pageview' and properties.brand = %s and timestamp > now() - interval %d day "
            "and properties.pv_qa != true and $session_id != '' limit 50000" % (_quote(brand), int(days)))
        return [{"session": r[0], "page_id": r[1] or "", "step": r[2] or "", "at": str(r[3])} for r in rows]

    def outcomes(self, brand, days):
        rows = self.query(
            "select $session_id, event, toFloat(properties.revenue), timestamp from events "
            "where event in ('checkout_click', 'checkout_reached', 'purchase') and properties.brand = %s "
            "and timestamp > now() - interval %d day and $session_id != '' limit 50000" % (_quote(brand), int(days)))
        return [{"session": r[0], "event": r[1], "revenue": r[2] or 0.0, "at": str(r[3])} for r in rows]

    def recordings(self, session_ids):
        found = {}
        ids = list(session_ids)
        for i in range(0, len(ids), 50):
            part = ids[i:i + 50]
            out = self._call("GET", "/api/projects/%s/session_recordings/?session_ids=%s&limit=50" % (
                self.project, urllib.request.quote(json.dumps(part))))
            for r in (out or {}).get("results", []):
                found[r["id"]] = {"duration_s": r.get("recording_duration") or 0, "active_s": r.get("active_seconds") or 0,
                                  "clicks": r.get("click_count") or 0, "start_url": r.get("start_url") or "",
                                  "start": r.get("start_time") or ""}
        return found

    def session_events(self, session_ids):
        ids = list(session_ids)
        out = {s: [] for s in ids}
        for i in range(0, len(ids), 50):
            part = ", ".join(_quote(s) for s in ids[i:i + 50])
            rows = self.query("select %s from events where $session_id in (%s) order by timestamp limit 50000" % (
                ", ".join(EVENT_COLS), part))
            for r in rows:
                out.setdefault(r[0], []).append({"at": str(r[1]), "event": r[2], "url": r[3] or "", "text": r[4] or "",
                                                 "scroll": r[5], "tag": r[6] or ""})
        return out

    def page_text(self, page_id):
        return None

    def replay_link(self, session, at_s):
        return "%s/project/%s/replay/%s?t=%d" % (self.host, self.project, session, int(at_s or 0))


class Sample:
    """A recorded sample: samples/<name>/{page_views,outcomes,recordings,events}.json. Same answers, no network."""

    def __init__(self, folder):
        self.folder = Path(folder)

    def _load(self, name):
        return json.loads((self.folder / (name + ".json")).read_text())

    def page_views(self, brand, days):
        return [r for r in self._load("page_views") if r.get("brand", brand) == brand]

    def outcomes(self, brand, days):
        return [r for r in self._load("outcomes") if r.get("brand", brand) == brand]

    def recordings(self, session_ids):
        rec = self._load("recordings")
        return {s: rec[s] for s in session_ids if s in rec}

    def session_events(self, session_ids):
        ev = self._load("events")
        return {s: ev.get(s, []) for s in session_ids}

    def replay_link(self, session, at_s):
        return None

    def page_text(self, page_id):
        """A sample may carry its pages as captured text (pages/<page_id>.txt), page-teardown's capture format."""
        f = self.folder / "pages" / (page_id + ".txt")
        return f.read_text() if f.is_file() else None

    def page_list(self):
        """A sample may carry its own page list (pages.json) so it needs no real page."""
        f = self.folder / "pages.json"
        return json.loads(f.read_text()) if f.is_file() else None
