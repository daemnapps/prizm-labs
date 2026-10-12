#!/usr/bin/env python3
"""The Meta Marketing API, as this lab uses it.

The bulk sheet could never make the ad the owner actually wants — one ad unit per
concept with its variations inside, same copy, Meta rotating the picture. The
sheet has one Image File Name column and one Title, and Meta's own exporter
says ads with multiple images "can't be imported or exported". The API can,
through asset_feed_spec. That is why this file exists.

    from meta import Meta
    m = Meta("<brand>")           # which brand's account to talk to
    m.get(f"act_{m.ACCOUNT}", fields="name")

Credential: the Keychain, service `daemn-META_ADS_TOKEN`, account `damon`.
Read at call time, never stored in the repo, never printed.
"""
import json
import os
import sys
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://graph.facebook.com/v25.0"   # v24 expires 6 Oct 2026 (Marketing API versions table)

# No account id lives here. Which account, Page, pixel and Instagram profile
# a call reaches is the brand's business, and the brand says so in
# `brands/<brand>/meta/account.json` (workspace rule 7). Pass the brand:
#
#     m = Meta("<brand>")
#     m.get(f"act_{m.ACCOUNT}", fields="name")


def token(name="PRIZM_META_TOKEN"):
    """The environment first ($PRIZM_META_TOKEN), else straight from the Keychain.
    Never cached to disk, never logged."""
    if os.environ.get(name):
        return os.environ[name]
    out = subprocess.run(
        ["security", "find-generic-password", "-a", "damon", "-s", f"daemn-{name}", "-w"],
        capture_output=True, text=True)
    if out.returncode:
        raise SystemExit(
            f"no Keychain entry daemn-{name}. The Meta token is a system-user "
            "token from Business Settings -> System users -> Generate token.")
    return out.stdout.strip()


class Meta:
    def __init__(self, brand, tok=None):
        """`brand` is a name ('<brand>') or an already-loaded Brand."""
        from brand import Brand
        self.brand = brand if isinstance(brand, Brand) else Brand(brand)
        self.ACCOUNT = self.brand.account_id
        self.PAGE = self.brand.page_id
        self.PIXEL = self.brand.pixel_id
        self.INSTAGRAM = self.brand.instagram_id
        self._t = tok or token(self.brand.token_key)

    def _call(self, path, params=None, post=False, files=None):
        params = dict(params or {})
        params["access_token"] = self._t
        url = f"{BASE}/{path.lstrip('/')}"
        if post:
            data = urllib.parse.urlencode(
                {k: (json.dumps(v) if isinstance(v, (dict, list)) else v)
                 for k, v in params.items()}).encode()
            req = urllib.request.Request(url, data=data)
        else:
            req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params))
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf8", "replace")
            # Meta's errors are the useful part — surface them whole, but never
            # the token, which urllib would otherwise echo back in the URL.
            raise SystemExit(f"Meta {e.code}: {body[:900]}")

    def get(self, path, **params):
        return self._call(path, params)

    def post(self, path, **params):
        return self._call(path, params, post=True)

    def paged(self, path, **params):
        """Every page of a list edge, followed to the end."""
        params.setdefault("limit", 200)
        out, res = [], self._call(path, params)
        out += res.get("data", [])
        while res.get("paging", {}).get("next"):
            nxt = res["paging"]["next"]
            with urllib.request.urlopen(nxt, timeout=120) as r:
                res = json.loads(r.read() or b"{}")
            out += res.get("data", [])
        return out

    # ---------------------------------------------------------------- media --
    def upload_image(self, url_or_path, name=None):
        """An image into the account library -> its hash.

        A URL is handed to Meta to fetch, which is why the 10 MB browser upload
        limit that forced eight-way chunking is simply not a problem here.
        """
        p = Path(str(url_or_path))
        if p.is_file():
            import base64
            res = self.post(f"act_{self.ACCOUNT}/adimages",
                            bytes=base64.b64encode(p.read_bytes()).decode(),
                            name=name or p.name)
        else:
            res = self.post(f"act_{self.ACCOUNT}/adimages",
                            url=str(url_or_path), name=name or "")
        imgs = res.get("images") or {}
        if not imgs:
            raise SystemExit(f"no image came back: {json.dumps(res)[:300]}")
        return next(iter(imgs.values()))["hash"]

    CHUNKED_OVER = 20_000_000      # bytes; bigger files go up in pieces (Meta drops one-shot posts of 150 MB masters)

    def upload_video(self, path, name=None, wait=900):
        """A finished video into the account library -> its id, once Meta has
        processed it (an ad cannot use a video that is still encoding).

        Small files go in one multipart post. Anything over CHUNKED_OVER uses
        Meta's resumable upload (start -> transfer the pieces Meta asks for ->
        finish) on graph-video, because a one-shot post of a 150 MB master is
        cut off mid-send (4 Oct 2026: broken pipe on every 2:22 master)."""
        import time
        p = Path(path)
        if p.stat().st_size > self.CHUNKED_OVER:
            vid = self._upload_chunked(p, name or p.name)
        else:
            vid = self._multipart(f"{BASE}/act_{self.ACCOUNT}/advideos",
                                  {"name": name or p.name}, ("source", p.name, p.read_bytes()), timeout=900)["id"]
        until = time.time() + wait
        while time.time() < until:
            st = self.get(vid, fields="status").get("status", {}).get("video_status")
            if st == "ready":
                return vid
            if st == "error":
                raise SystemExit(f"Meta could not process video {p.name}")
            time.sleep(10)
        raise SystemExit(f"video {p.name} still processing after {wait}s — run again, it resumes")

    def _multipart(self, url, fields, file=None, timeout=300):
        """One multipart POST (token added) -> the parsed answer; Meta's error text on failure."""
        import uuid
        boundary = uuid.uuid4().hex
        parts = [f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
                 for k, v in {"access_token": self._t, **fields}.items()]
        if file:
            key, fname, data = file
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"; filename="{fname}"\r\n'
                         f'Content-Type: application/octet-stream\r\n\r\n'.encode() + data + b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        req = urllib.request.Request(url, data=b"".join(parts),
                                     headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            raise SystemExit(f"Meta {e.code}: {e.read().decode('utf8', 'replace')[:900]}")

    def _upload_chunked(self, p, name, tries=4):
        """Meta's resumable video upload: start, send each piece Meta asks for, finish -> the video id."""
        import time
        url = BASE.replace("://graph.", "://graph-video.") + f"/act_{self.ACCOUNT}/advideos"
        size = p.stat().st_size
        s = self._multipart(url, {"upload_phase": "start", "file_size": size})
        sid, vid = s["upload_session_id"], s["video_id"]
        a, b = int(s["start_offset"]), int(s["end_offset"])
        with open(p, "rb") as f:
            while a < b:
                f.seek(a)
                piece = f.read(b - a)
                for n in range(tries):
                    try:
                        r = self._multipart(url, {"upload_phase": "transfer", "upload_session_id": sid, "start_offset": a},
                                            ("video_file_chunk", p.name, piece), timeout=600)
                        break
                    except (urllib.error.URLError, OSError):
                        if n == tries - 1:
                            raise SystemExit(f"video {p.name}: a piece kept failing at byte {a} — run again, it resumes")
                        time.sleep(5 * (n + 1))
                a, b = int(r["start_offset"]), int(r["end_offset"])
        done = self._multipart(url, {"upload_phase": "finish", "upload_session_id": sid, "title": name})
        if not done.get("success", True):
            raise SystemExit(f"Meta did not accept video {p.name}: {json.dumps(done)[:300]}")
        return vid

    def thumbnail_hash(self, video_id):
        """A processed video's preferred frame, put into the picture library —
        a video ad needs an image_hash beside it (error 1443226 without)."""
        import tempfile
        with urllib.request.urlopen(self.video_thumbnail(video_id), timeout=120) as r:
            data = r.read()
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as t:
            t.write(data)
        return self.upload_image(t.name, name=f"thumb-{video_id}.jpg")

    def video_thumbnail(self, video_id):
        """Meta's own preferred frame for a processed video — a video ad needs one."""
        th = self.get(f"{video_id}/thumbnails").get("data", [])
        pick = next((t for t in th if t.get("is_preferred")), th[0] if th else None)
        if not pick:
            raise SystemExit(f"no thumbnail for video {video_id}")
        return pick["uri"]


if __name__ == "__main__":
    import sys
    from brand import available
    for name in (sys.argv[1:] or available()):
        m = Meta(name)
        who = m.get("me", fields="id,name")
        acct = m.get(f"act_{m.ACCOUNT}", fields="name,account_status,currency")
        print(f"{name}: {who['name']} -> {acct['name']} "
              f"({acct['currency']}, status {acct['account_status']})")
