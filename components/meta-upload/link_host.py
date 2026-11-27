"""link_host — a short-lived private link Meta can fetch a video from, so the video goes up in ONE call.

Meta's advideos edge takes `file_url`: Meta downloads the file itself. One POST replaces the chunked upload's
start + ~15 pieces + finish (11 Nov 2026: a 73 MB video = 17 calls chunked, 1 by link; on development access
every call counts against the ad account's limit).

Where the file sits for those minutes: a private Google Cloud Storage bucket, read through a V4 signed URL that
expires (upload-link.json `expires_s`, default 1 h). The bucket is never public, the object name is random, and
the object is deleted as soon as Meta has processed the video (meta.wait_videos). Set the bucket's lifecycle to
delete objects after 1 day as a backstop. Credential: the Google service account in GDRIVE_SA_KEY (by name
through mu_keys; its JSON, or a path to it), which needs Storage Object Admin on that bucket only.

Nothing here is required: no bucket set, the switch off, a missing library or any failure -> `available()` is
False or `put()` raises, and meta.send_video uses the chunked upload as before.

Switch: upload-link.json `"on": false`, or META_UPLOAD_LINK_OFF=1 on one machine.
"""
import base64, binascii, datetime, hashlib, json, os, urllib.parse, urllib.request, uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
CFG_F = HERE / "upload-link.json"
GCS = "https://storage.googleapis.com"


def cfg():
    try:
        return json.loads(CFG_F.read_text())
    except (OSError, ValueError):
        return {}


def available():
    c = cfg()
    return bool(c.get("on") and c.get("bucket") and os.environ.get("META_UPLOAD_LINK_OFF") != "1")


def _creds():
    import mu_keys
    from google.oauth2 import service_account
    import google.auth.transport.requests as gr
    raw = mu_keys.key(cfg().get("key") or "GDRIVE_SA_KEY")
    if not raw:
        raise RuntimeError("no service account key")
    info = json.loads(raw) if raw.lstrip().startswith("{") else json.loads(Path(os.path.expanduser(raw)).read_text())
    c = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/devstorage.read_write"])
    c.refresh(gr.Request())
    return c


def _q(s, safe="/"):
    return urllib.parse.quote(s, safe=safe + "-_.~")


def signed_url(creds, bucket, name, expires_s, now=None):
    """A V4 signed GET URL for one object (Google's documented algorithm, GOOG4-RSA-SHA256)."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    stamp, day = now.strftime("%Y%m%dT%H%M%SZ"), now.strftime("%Y%m%d")
    scope = f"{day}/auto/storage/goog4_request"
    host = "storage.googleapis.com"
    path = f"/{bucket}/{_q(name)}"
    query = {
        "X-Goog-Algorithm": "GOOG4-RSA-SHA256",
        "X-Goog-Credential": f"{creds.service_account_email}/{scope}",
        "X-Goog-Date": stamp,
        "X-Goog-Expires": str(int(expires_s)),
        "X-Goog-SignedHeaders": "host",
    }
    qs = "&".join(f"{_q(k, '')}={_q(v, '')}" for k, v in sorted(query.items()))
    canonical = "\n".join(["GET", path, qs, f"host:{host}\n", "host", "UNSIGNED-PAYLOAD"])
    to_sign = "\n".join(["GOOG4-RSA-SHA256", stamp, scope, hashlib.sha256(canonical.encode()).hexdigest()])
    sig = binascii.hexlify(creds.signer.sign(to_sign.encode())).decode()
    return f"https://{host}{path}?{qs}&X-Goog-Signature={sig}"


def put(path):
    """Upload `path` privately -> (signed URL Meta can fetch, object name). Raises on any failure."""
    c = cfg()
    bucket, prefix = c["bucket"], c.get("prefix", "meta-upload/")
    creds = _creds()
    name = f"{prefix}{uuid.uuid4().hex}{Path(path).suffix.lower()}"
    req = urllib.request.Request(
        f"{GCS}/upload/storage/v1/b/{_q(bucket, '')}/o?uploadType=media&name={_q(name, '')}",
        data=Path(path).read_bytes(),
        headers={"Authorization": f"Bearer {creds.token}", "Content-Type": "video/mp4"})
    with urllib.request.urlopen(req, timeout=900) as r:
        json.loads(r.read() or b"{}")
    return signed_url(creds, bucket, name, c.get("expires_s", 3600)), name


def remove(name):
    """Delete one object (after Meta processed the video). Never raises: the bucket's lifecycle is the backstop."""
    try:
        c = cfg()
        creds = _creds()
        req = urllib.request.Request(f"{GCS}/storage/v1/b/{_q(c['bucket'], '')}/o/{_q(name, '')}",
                                     method="DELETE", headers={"Authorization": f"Bearer {creds.token}"})
        urllib.request.urlopen(req, timeout=60).close()
        return True
    except Exception:  # noqa: BLE001
        return False
