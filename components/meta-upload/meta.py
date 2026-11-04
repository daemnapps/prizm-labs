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

Credential: by name (`PRIZM_META_TOKEN`, or the brand's `token_key`) through
the one key loader, components/keys/loader.py via mu_keys.py — the environment
first, then this repo's .env (add the NAME=value line there). Read at call time, never stored in the repo, never printed.
"""
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://graph.facebook.com/v25.0"   # v24 expires 6 Oct 2026 (Marketing API versions table)


def _log(msg):
    print(msg, file=sys.stderr, flush=True)

# No account id lives here. Which account, Page, pixel and Instagram profile
# a call reaches is the brand's business, and the brand says so in
# `brands/<brand>/meta/account.json` (workspace rule 7). Pass the brand:
#
#     m = Meta("<brand>")
#     m.get(f"act_{m.ACCOUNT}", fields="name")


def token(name="PRIZM_META_TOKEN"):
    """By name through the one key loader. Never cached to disk, never logged."""
    import mu_keys
    tok = mu_keys.key(name)
    if not tok:
        raise SystemExit(
            f"{mu_keys.missing(name)}. The Meta token is a system-user "
            "token from Business Settings -> System users -> Generate token.")
    return tok


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
        def send():
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read() or b"{}")
        # Meta's errors are the useful part — surfaced whole (never the token, which urllib would echo in the
        # URL); a "busy / slow down" answer waits and tries again first (pace.py, the owner 2026-10-21)
        import pace
        return pace.with_retry(send, path.split("?")[0] or "a call", log=_log)

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
        processed it. send_video + wait_videos for one file."""
        vid = self.send_video(path, name)
        self.wait_videos([vid], {vid: Path(path).name}, wait=wait)
        return vid

    def send_video(self, path, name=None):
        """Send a video into the account library -> its id, without waiting for
        Meta to process it (wait_videos does that, for every video of an ad at once).

        Small files go in one multipart post. Anything over CHUNKED_OVER uses
        Meta's resumable upload (start -> transfer the pieces Meta asks for ->
        finish) on graph-video, because a one-shot post of a 150 MB master is
        cut off mid-send (4 Oct 2026: broken pipe on every 2:22 master)."""
        import pace
        p = Path(path)
        brand = getattr(getattr(self, "brand", None), "name", None) or "unknown"
        size = p.stat().st_size
        pace.before_video(brand, size, log=_log)      # never more than the hour's budget (pace.json per_hour)
        if size > self.CHUNKED_OVER:
            vid = self._upload_chunked(p, name or p.name)
        else:
            vid = self._multipart(f"{BASE}/act_{self.ACCOUNT}/advideos",
                                  {"name": name or p.name}, ("source", p.name, p.read_bytes()), timeout=900)["id"]
        pace.sent(brand, size, p.name)
        return vid

    def statuses(self, ids):
        """{video id: {"status": …}} for many videos in ONE HTTP request (POST / batch=…)."""
        res = self.post("", batch=[{"method": "GET", "relative_url": f"{v}?fields=status"} for v in ids],
                        include_headers="false")
        out = {}
        for v, r in zip(ids, res if isinstance(res, list) else []):
            try:
                out[v] = json.loads((r or {}).get("body") or "{}")
            except ValueError:
                out[v] = {}
            if (r or {}).get("code", 200) >= 400:
                raise SystemExit(f"Meta {(r or {}).get('code')}: {str((r or {}).get('body'))[:600]}")
        return out

    POLL_EVERY = 30                # seconds between status reads while videos process

    def wait_videos(self, ids, names=None, wait=900):
        """Until every video is processed (an ad cannot use one still encoding):
        ONE request for all of them each time (statuses: Meta's batch call —
        `?ids=` is refused on this account, "deprecated in v26.0+", 12 Oct 2026),
        every POLL_EVERY seconds. `wait` is the budget for one video; each extra
        video adds 300 s. Any video in error stops it."""
        import time
        names = names or {}
        left = list(dict.fromkeys(ids))
        until = time.time() + wait + 300 * max(0, len(left) - 1)
        while left:
            res = self.statuses(left)
            for vid in list(left):
                st = ((res.get(vid) or {}).get("status") or {}).get("video_status")
                if st == "ready":
                    left.remove(vid)
                elif st == "error":
                    raise SystemExit(f"Meta could not process video {names.get(vid, vid)}")
            if not left:
                return
            if time.time() + self.POLL_EVERY > until:
                raise SystemExit(f"video(s) {', '.join(names.get(v, v) for v in left)} still processing — "
                                 "retry, it resumes")
            time.sleep(self.POLL_EVERY)

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

        def send():
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read() or b"{}")
        import pace
        return pace.with_retry(send, f"the {fields.get('upload_phase') or 'upload'} step", log=_log)

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
                if a < b:
                    import pace
                    pace.between_chunks()
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
