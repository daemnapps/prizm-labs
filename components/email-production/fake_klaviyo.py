#!/usr/bin/env python3
"""A stand-in Klaviyo for the email approval card's tests and trials
(EP-3 (email approval card)). Nothing here reaches the network, and nothing
is ever sent: a send job only marks the campaign "Scheduled".

    fk = FakeKlaviyo()                      # campaigns made by POST, as create_draft makes them
    fk = FakeKlaviyo.from_cards([card...])  # campaigns read live from email-card.json files
    mock.patch.object(K.S, "kl", fk.kl)     # the one seam: simple_email.kl

A campaign known from a card is answered from that card's own recorded parts
and its email-card.html on EVERY read, so editing a card's subject (or the
html file) in a scratch tree makes the page refuse it as changed.

Stdlib only, and no import from this folder: email_approve.py loads it after
simple_email has taken this folder off sys.path (simple_email.py:44-47).
"""
import json
import sys
from pathlib import Path

# A campaign made with no send_strategy gets Klaviyo's own default, which may be
# IMMEDIATE (unchecked) — the fake says so, so the guard is exercised.
DEFAULT_STRATEGY = {"method": "immediate"}


class FakeKlaviyo:
    def __init__(self):
        self.calls = []            # (method, path) of every call, in order
        self.campaigns = {}        # id -> parts (made by POST) or {"card": Path} (from a card)
        self.templates = {}        # template id -> html
        self.fail = set()          # paths that answer as Klaviyo refusing them (SystemExit)
        self._n = 0

    # ----------------------------------------------------------- the stock
    @classmethod
    def from_cards(cls, cards, html_name="email-card.html"):
        fk = cls()
        fk.html_name = html_name
        for c in cards:
            fk.know(c)
        return fk

    def know(self, card_path):
        """A campaign read from its card file — added once, read live after."""
        p = Path(card_path)
        try:
            cid = json.loads(p.read_text()).get("campaign_id")
        except (OSError, ValueError):
            return None
        if cid and cid not in self.campaigns:
            self.campaigns[cid] = {"card": p, "status": None}
        return cid

    def _id(self, prefix):
        self._n += 1
        return f"{prefix}{self._n}"

    def parts(self, cid):
        """What this Klaviyo holds for the campaign, read now."""
        c = self.campaigns[cid]
        if "card" not in c:
            return c
        card = json.loads(c["card"].read_text())
        html_f = c["card"].parent / getattr(self, "html_name", "email-card.html")
        return {"name": card.get("campaign_name"),
                "status": c["status"] or ("Scheduled" if card.get("state") == "scheduled" else "Draft"),
                "subject": card.get("subject"), "preview": card.get("preview"),
                "audience_ids": [a.get("id") for a in card.get("audience") or []],
                "strategy": (card.get("send") or {}).get("strategy") or DEFAULT_STRATEGY,
                "message_id": card.get("message_id") or f"MSG-{cid}",
                "template_id": card.get("template_id") or f"TPL-{cid}",
                "html": html_f.read_text() if html_f.is_file() else ""}

    def _set_status(self, cid, status):
        self.campaigns[cid]["status"] = status

    def _refuse(self, path, status=404, why="not found"):
        sys.exit(f"Klaviyo refused {path}: {status} {why}"[:400])

    # ------------------------------------------------------------- the API
    def kl(self, method, path, key, payload=None, form=None):
        self.calls.append((method, path))
        if path in self.fail:
            self._refuse(path, 400, "the fake was told to refuse this")
        bare = path.split("?")[0]
        bits = bare.split("/")
        if method == "POST" and bare == "image-upload":
            return {"data": {"attributes": {"image_url": f"https://cdn.fake/{(form or {}).get('name')}"}}}
        if method == "POST" and bare == "templates":
            tid = self._id("TPL")
            self.templates[tid] = payload["data"]["attributes"]["html"]
            return {"data": {"id": tid}}
        if method == "POST" and bare == "campaigns":
            a = payload["data"]["attributes"]
            msg = a["campaign-messages"]["data"][0]["attributes"]["definition"]["content"]
            cid, mid = self._id("CAMP"), self._id("MSG")
            self.campaigns[cid] = {"name": a.get("name"), "status": "Draft", "subject": msg.get("subject"),
                                   "preview": msg.get("preview_text"),
                                   "audience_ids": list((a.get("audiences") or {}).get("included") or []),
                                   "strategy": a.get("send_strategy") or DEFAULT_STRATEGY,
                                   "message_id": mid, "template_id": None, "html": ""}
            return {"data": {"id": cid, "relationships": {"campaign-messages": {"data": [{"id": mid}]}}}}
        if method == "POST" and bare == "campaign-message-assign-template":
            mid = payload["data"]["id"]
            tid = payload["data"]["relationships"]["template"]["data"]["id"]
            for c in self.campaigns.values():
                if c.get("message_id") == mid:
                    c["template_id"], c["html"] = tid, self.templates.get(tid, "")
                    return {"data": {"id": mid}}
            self._refuse(path)
        if method == "POST" and bare == "campaign-send-jobs":
            cid = payload["data"]["id"]
            if cid not in self.campaigns:
                self._refuse(path)
            self._set_status(cid, "Scheduled")        # scheduled, never sent
            return {"data": {"type": "campaign-send-job", "id": cid, "attributes": {"status": "queued"}}}
        if method == "GET" and len(bits) == 2 and bits[0] == "campaigns":
            if bits[1] not in self.campaigns:
                self._refuse(path)
            p = self.parts(bits[1])
            out = {"data": {"type": "campaign", "id": bits[1], "attributes": {
                "name": p["name"], "status": p["status"],
                "audiences": {"included": p["audience_ids"], "excluded": []},
                "send_strategy": p["strategy"]}}}
            if "include=campaign-messages" in path:
                out["included"] = [{"type": "campaign-message", "id": p["message_id"], "attributes": {
                    "definition": {"channel": "email", "content": {
                        "subject": p["subject"], "preview_text": p["preview"]}}}}]
            return out
        if method == "GET" and len(bits) == 3 and bits[0] == "campaign-messages" and bits[2] == "template":
            for cid in self.campaigns:
                p = self.parts(cid)
                if p["message_id"] == bits[1]:
                    return {"data": {"type": "template", "id": p["template_id"],
                                     "attributes": {"html": p["html"]}}}
            self._refuse(path)
        self._refuse(path, 405, f"the fake does not answer {method} {bare}")
