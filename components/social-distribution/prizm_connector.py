#!/usr/bin/env python3
"""Prizm delivery card -> durable social jobs -> reconciliation receipts.

Local, single-operator connector. Python standard library, no model calls.
Network operations require --execute (dispatch, reconcile or attach-task).
Run with --help; see CONNECTOR.md for the boundary of this first version.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

SCHEMA = "prizm-social/1"
PLATFORMS = ("tiktok", "instagram", "youtube")
MAX_MEDIA = 100 * 1024 * 1024
UTC = dt.timezone.utc


class Refused(Exception):
    """An actionable, credential-free local error."""


class ProviderError(Exception):
    """Never contains an unfiltered provider response or URL."""


def stamp():
    return dt.datetime.now(UTC).isoformat(timespec="seconds")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def identifier(value, label="identifier"):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,199}", value):
        raise Refused(f"Invalid {label}; use lowercase letters, numbers, hyphens or underscores")
    return value


def aware_time(value):
    try:
        t = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if t.tzinfo is None or t.utcoffset() is None:
            raise ValueError
        return t.astimezone(UTC).isoformat(timespec="seconds")
    except (ValueError, TypeError, AttributeError):
        raise Refused("schedule_at must be an ISO timestamp with an explicit UTC offset") from None


def read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        raise Refused("Could not read the requested JSON file") from None


def private_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".connector-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def token_value(name, env_file=None):
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*", name):
        raise Refused("Invalid credential environment variable name")
    token = os.environ.get(name)
    if not token and env_file:
        p = Path(env_file)
        if p.stat().st_mode & 0o077:
            raise Refused("The credential file must have private permissions (chmod 600)")
        for line in p.read_text().splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() == name:
                token = value.strip().strip("\"'")
    if not token or any(c.isspace() for c in token):
        raise Refused(f"Credential {name} is missing or invalid")
    return token


def safe_link(value, platform):
    try:
        p = urllib.parse.urlsplit(value or "")
        hosts = {"tiktok": ("tiktok.com",), "instagram": ("instagram.com",),
                 "youtube": ("youtube.com", "youtu.be")}[platform]
        host = (p.hostname or "").lower()
        if p.scheme == "https" and not p.username and not p.password and any(
                host == h or host.endswith("." + h) for h in hosts):
            return urllib.parse.urlunsplit((p.scheme, p.netloc, p.path, "", ""))
    except (ValueError, TypeError):
        pass
    return None


class GeeLark:
    """Fresh adapter: no dependency on the legacy CSV CLI, no raw error logging."""

    def __init__(self, token):
        self.token = token

    def call(self, path, body, trace=None):
        req = urllib.request.Request("https://openapi.geelark.com/open/v1" + path,
            data=canonical(body).encode(), method="POST", headers={
                "Content-Type": "application/json", "traceId": trace or str(uuid.uuid4()).upper(),
                "Authorization": "Bearer " + self.token})
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                out = json.load(r)
        except urllib.error.HTTPError as e:
            raise ProviderError(f"provider_http_{e.code}") from None
        except Exception:
            raise ProviderError("provider_transport_or_response_error") from None
        if not isinstance(out, dict) or out.get("code") != 0:
            code = out.get("code") if isinstance(out, dict) else None
            code = str(code) if isinstance(code, int) else "invalid_response"
            raise ProviderError("provider_code_" + code)
        if not isinstance(out.get("data"), dict):
            raise ProviderError("provider_missing_data")
        return out["data"]

    def upload(self, media):
        info = self.call("/upload/getUrl", {"fileType": "mp4"})
        # These URLs are temporary capabilities. Never persist them in receipts or logs.
        try:
            url = info["uploadUrl"]
            if urllib.parse.urlsplit(url).scheme != "https":
                raise ProviderError("provider_upload_requires_https")
            req = urllib.request.Request(url, data=Path(media).read_bytes(), method="PUT")
            with urllib.request.urlopen(req, timeout=60) as response:
                if response.status not in (200, 201):
                    raise ProviderError("provider_upload_rejected")
            resource = info["resourceUrl"]
            if urllib.parse.urlsplit(resource).scheme != "https":
                raise ProviderError("provider_resource_requires_https")
            return resource
        except ProviderError:
            raise
        except Exception:
            raise ProviderError("provider_upload_error") from None

    def submit(self, account, target, resource, trace):
        when = max(int(dt.datetime.fromisoformat(target["schedule_at"]).timestamp()), int(time.time()))
        common = {"scheduleAt": when, "name": "prizm-" + trace.lower(), "remark": trace}
        phone = account["phone_id"]
        if account["platform"] == "tiktok":
            data = self.call("/task/add", {"planName": "prizm-" + trace.lower(), "remark": trace,
                "taskType": 1, "list": [{
                "scheduleAt": when, "envId": phone, "video": resource,
                "videoDesc": target["caption"], "needShareLink": True,
                "markAI": target["ai_disclosure"], "maxTryTimes": 0,
                "sourceVideoVolume": 100, "sameVideoVolume": 0}]}, trace)
            ids = data.get("taskIds")
            task = ids[0] if isinstance(ids, list) and len(ids) == 1 else None
        elif account["platform"] == "instagram":
            data = self.call("/rpa/task/instagramPubReels", {**common, "id": phone,
                "description": target["caption"], "video": [resource],
                "needShareLink": True, "aiTag": target["ai_disclosure"]}, trace)
            task = data.get("taskId")
        else:
            data = self.call("/rpa/task/youtubePubShort", {**common, "id": phone,
                "title": target["title"], "video": resource, "sameStyleVoice": 0,
                "originalVoice": 100, "isDisclosureMandatory": target["ai_disclosure"]}, trace)
            task = data.get("taskId")
        if not isinstance(task, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,150}", task):
            raise ProviderError("provider_missing_task_id")
        return task

    def status(self, task):
        items = self.call("/task/query", {"ids": [task]}).get("items", [])
        matches = [x for x in items if isinstance(x, dict) and x.get("id") == task]
        if len(matches) != 1:
            raise ProviderError("provider_task_not_found")
        return matches[0]


DDL = """
CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS account (
 workspace TEXT NOT NULL, brand TEXT NOT NULL, account_id TEXT NOT NULL,
 platform TEXT NOT NULL, platform_account_id TEXT NOT NULL, phone_id TEXT NOT NULL,
 token_env TEXT NOT NULL, ready INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(workspace,brand,account_id), UNIQUE(platform,platform_account_id));
CREATE TABLE IF NOT EXISTS batch (
 batch_id TEXT PRIMARY KEY, workspace TEXT NOT NULL, brand TEXT NOT NULL,
 source_key TEXT NOT NULL, fingerprint TEXT NOT NULL, manifest TEXT NOT NULL,
 approved_by TEXT, approved_at TEXT, cancelled_at TEXT, created_at TEXT NOT NULL,
 UNIQUE(workspace,brand,source_key));
CREATE TABLE IF NOT EXISTS job (
 job_id TEXT PRIMARY KEY, batch_id TEXT NOT NULL REFERENCES batch(batch_id),
 workspace TEXT NOT NULL, brand TEXT NOT NULL, account_id TEXT NOT NULL,
 target TEXT NOT NULL, state TEXT NOT NULL, task_id TEXT, error_code TEXT,
 observed TEXT, updated_at TEXT NOT NULL,
 FOREIGN KEY(workspace,brand,account_id) REFERENCES account(workspace,brand,account_id));
CREATE TABLE IF NOT EXISTS attempt (
 attempt_id TEXT PRIMARY KEY, job_id TEXT NOT NULL REFERENCES job(job_id),
 phase TEXT NOT NULL, task_id TEXT, error_code TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit (
 seq INTEGER PRIMARY KEY, workspace TEXT NOT NULL, brand TEXT NOT NULL,
 event TEXT NOT NULL, entity TEXT NOT NULL, actor TEXT, at TEXT NOT NULL);
"""


class Connector:
    def __init__(self, db):
        self.path = Path(db).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        os.chmod(self.path, 0o600)
        self.db = sqlite3.connect(str(self.path), timeout=15)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=DELETE")
        self.db.executescript(DDL)
        version = self.db.execute("SELECT value FROM metadata WHERE key='schema'").fetchone()
        if version and version[0] != SCHEMA:
            raise Refused("Unsupported connector database version")
        self.db.execute("INSERT OR IGNORE INTO metadata VALUES('schema',?)", (SCHEMA,))
        self.db.commit()
        self.media_dir = self.path.parent / (self.path.name + ".media")

    def close(self):
        self.db.close()

    @contextlib.contextmanager
    def lock(self):
        fd = os.open(str(self.path) + ".lock", os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(fd, "w") as f:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise Refused("Another connector mutation is running; try again after it finishes") from None
            yield

    def audit(self, workspace, brand, event, entity, actor=None):
        self.db.execute("INSERT INTO audit(workspace,brand,event,entity,actor,at) VALUES(?,?,?,?,?,?)",
                        (workspace, brand, event, entity, actor, stamp()))

    def account(self, workspace, brand, account_id):
        row = self.db.execute("SELECT * FROM account WHERE workspace=? AND brand=? AND account_id=?",
                              (workspace, brand, account_id)).fetchone()
        if not row:
            raise Refused("Target account is not registered for this workspace and brand")
        return dict(row)

    def register(self, workspace, brand, account_id, platform, platform_account_id, phone_id,
                 token_env="GEELARK_API_TOKEN", ready=False):
        for value in (workspace, brand, account_id):
            identifier(value)
        for value in (platform_account_id, phone_id):
            if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,200}", value):
                raise Refused("Platform and device IDs must be opaque IDs, without spaces or credentials")
        if platform not in PLATFORMS or not re.fullmatch(r"[A-Z][A-Z0-9_]*", token_env):
            raise Refused("Unsupported platform or invalid credential reference")
        with self.lock(), self.db:
            old = self.db.execute("SELECT * FROM account WHERE workspace=? AND brand=? AND account_id=?",
                                  (workspace, brand, account_id)).fetchone()
            values = (workspace, brand, account_id, platform, platform_account_id, phone_id, token_env)
            if old:
                if tuple(old)[:7] != values:
                    raise Refused("Account identity/binding is immutable; register a new account ID")
                return False
            try:
                self.db.execute("INSERT INTO account VALUES(?,?,?,?,?,?,?,?)", (*values, int(ready)))
            except sqlite3.IntegrityError:
                raise Refused("That platform identity is already registered to an account") from None
            self.audit(workspace, brand, "account_registered", account_id)
        return True

    def readiness(self, workspace, brand, account_id, ready, actor):
        identifier(actor, "actor")
        with self.lock(), self.db:
            self.account(workspace, brand, account_id)
            self.db.execute("UPDATE account SET ready=? WHERE workspace=? AND brand=? AND account_id=?",
                            (int(ready), workspace, brand, account_id))
            self.audit(workspace, brand, "account_ready" if ready else "account_paused", account_id, actor)

    def plan(self, card_path, asset_name, targets, workspace, ledger=None, request_key=None):
        identifier(workspace, "workspace")
        card_path = Path(card_path).resolve()
        card = read_json(card_path)
        if not isinstance(card, dict) or card.get("schema") != "meta-card/1":
            raise Refused("Expected Prizm's meta-card/1 delivery format")
        brand, product, brief = (card.get(k) for k in ("brand", "product", "brief_id"))
        for value in (brand, product, brief):
            identifier(value)
        if not re.fullmatch(r"brief-[0-9]{4,}", brief):
            raise Refused("The card must carry its registered brief number")
        unit = card.get("ad_name")
        prefix = f"{brand}_{product}_{brief}_batch-"
        if not isinstance(unit, str) or not unit.startswith(prefix) or not re.fullmatch(r"[a-z0-9_-]+", unit):
            raise Refused("Card naming disagrees with its brand/product/brief")
        if not isinstance(asset_name, str) or not re.fullmatch(re.escape(unit) + r"_asset-[0-9]+\.mp4", asset_name):
            raise Refused("Choose a named MP4 asset from this delivery card")
        if asset_name not in (card.get("media") or []):
            raise Refused("Selected asset is not listed on the delivery card")
        approval = card.get("approval") or {}
        made_by = card.get("made_by") or {}
        if not isinstance(approval, dict) or not isinstance(made_by, dict):
            raise Refused("Card approval and made_by must be objects")
        if approval.get("decision") in ("disapprove", "send-back"):
            raise Refused("The upstream card is sent back; resolve that decision before intake")
        checks = card.get("checks") or {}
        if not isinstance(checks, dict) or any(isinstance(x, dict) and x.get("ok") is False for x in checks.values()):
            raise Refused("The upstream card has failing checks")
        media = card_path.parent / asset_name
        if media.is_symlink() or not media.is_file() or media.resolve().parent != card_path.parent:
            raise Refused("Media must be a regular file beside the card")
        if not 0 < media.stat().st_size <= MAX_MEDIA:
            raise Refused("Connector v1 accepts nonempty MP4 files up to 100 MiB")
        asset_id = media.stem
        if ledger:
            uri = Path(ledger).resolve().as_uri() + "?mode=ro"
            try:
                with contextlib.closing(sqlite3.connect(uri, uri=True)) as source:
                    row = source.execute("SELECT brand_id,brief_id,product FROM asset WHERE asset_id=?", (asset_id,)).fetchone()
                if row != (brand, brief, product):
                    raise Refused("Asset Ledger identity does not match this delivery")
            except sqlite3.Error:
                raise Refused("Could not validate identity against the read-only Asset Ledger") from None
        if not isinstance(targets, list) or not targets:
            raise Refused("At least one explicit publishing target is required")
        normalized, seen = [], set()
        for target in targets:
            if not isinstance(target, dict) or set(target) - {"account_id", "caption", "title", "schedule_at", "ai_disclosure"}:
                raise Refused("Unknown target fields; use the documented target contract")
            account_id = identifier(target.get("account_id"), "account ID")
            if account_id in seen:
                raise Refused("Duplicate account in one handoff")
            seen.add(account_id)
            account = self.account(workspace, brand, account_id)
            caption, title = target.get("caption"), target.get("title", "")
            if not isinstance(caption, str) or not caption.strip() or len(caption) > 2200:
                raise Refused("Every target needs an explicit caption of 1–2200 characters")
            if not isinstance(title, str) or len(title) > 100 or (account["platform"] == "youtube" and not title.strip()):
                raise Refused("YouTube needs an explicit title; titles are limited to 100 characters")
            disclosure = target.get("ai_disclosure")
            if not isinstance(disclosure, bool):
                raise Refused("ai_disclosure must be a boolean")
            normalized.append({"account_id": account_id, "platform": account["platform"],
                "platform_account_id": account["platform_account_id"], "phone_id": account["phone_id"],
                "token_env": account["token_env"], "caption": caption, "title": title,
                "schedule_at": aware_time(target.get("schedule_at")), "ai_disclosure": disclosure})
        normalized.sort(key=lambda x: x["account_id"])
        source_key = request_key or asset_id
        identifier(source_key, "request key")
        manifest = {"schema": SCHEMA, "workspace": workspace, "brand": brand,
            "source_key": source_key, "product": product, "brief_id": brief,
            "brief_key": f"{brand}_{product}_{brief}", "asset_id": asset_id,
            "asset_sha256": file_hash(media), "source_tool": made_by.get("tool"),
            "source_run": made_by.get("run"), "source_card_sha256": file_hash(card_path),
            "upstream_ledger_checked": bool(ledger), "targets": normalized}
        return {"batch_id": "batch_" + digest([workspace, brand, source_key])[:24],
                "fingerprint": digest(manifest), "manifest": manifest, "media": media}

    def intake(self, plan):
        m = plan["manifest"]
        with self.lock():
            old = self.db.execute("SELECT * FROM batch WHERE workspace=? AND brand=? AND source_key=?",
                                 (m["workspace"], m["brand"], m["source_key"])).fetchone()
            if old:
                if old["fingerprint"] != plan["fingerprint"]:
                    raise Refused("This source was already ingested with different media or instructions; use a new explicit request key")
                return {"batch_id": old["batch_id"], "created": False, "jobs": len(m["targets"])}
            self.media_dir.mkdir(mode=0o700, exist_ok=True)
            staged = self.media_dir / (m["asset_sha256"] + ".mp4")
            if not staged.exists():
                fd, tmp = tempfile.mkstemp(dir=self.media_dir)
                try:
                    with os.fdopen(fd, "wb") as dst, plan["media"].open("rb") as src:
                        shutil.copyfileobj(src, dst)
                        dst.flush()
                        os.fsync(dst.fileno())
                    if file_hash(tmp) != m["asset_sha256"]:
                        raise Refused("Media changed during intake; run the plan again")
                    os.replace(tmp, staged)
                finally:
                    if os.path.exists(tmp):
                        os.unlink(tmp)
            if file_hash(staged) != m["asset_sha256"]:
                raise Refused("The staged media hash no longer matches")
            with self.db:
                self.db.execute("INSERT INTO batch VALUES(?,?,?,?,?,?,NULL,NULL,NULL,?)",
                    (plan["batch_id"], m["workspace"], m["brand"], m["source_key"],
                     plan["fingerprint"], canonical(m), stamp()))
                for target in m["targets"]:
                    job_id = "job_" + digest([plan["batch_id"], target["account_id"]])[:24]
                    self.db.execute("INSERT INTO job VALUES(?,?,?,?,?,?,?,NULL,NULL,NULL,?)",
                        (job_id, plan["batch_id"], m["workspace"], m["brand"], target["account_id"],
                         canonical(target), "awaiting_approval", stamp()))
                self.audit(m["workspace"], m["brand"], "handoff_ingested", plan["batch_id"])
        return {"batch_id": plan["batch_id"], "created": True, "jobs": len(m["targets"])}

    def batch(self, workspace, brand, batch_id):
        row = self.db.execute("SELECT * FROM batch WHERE workspace=? AND brand=? AND batch_id=?",
                              (workspace, brand, batch_id)).fetchone()
        if not row:
            raise Refused("Batch not found in this workspace and brand")
        return dict(row)

    def approve(self, workspace, brand, batch_id, fingerprint, actor):
        identifier(actor, "actor")
        with self.lock(), self.db:
            batch = self.batch(workspace, brand, batch_id)
            if fingerprint != batch["fingerprint"] or batch["cancelled_at"]:
                raise Refused("Approval must match the exact, uncancelled handoff fingerprint")
            self.db.execute("UPDATE batch SET approved_by=?,approved_at=? WHERE batch_id=?", (actor, stamp(), batch_id))
            self.db.execute("UPDATE job SET state='approved',updated_at=? WHERE batch_id=? AND state='awaiting_approval'", (stamp(), batch_id))
            self.audit(workspace, brand, "handoff_approved", batch_id, actor)

    def cancel(self, workspace, brand, batch_id, actor):
        identifier(actor, "actor")
        with self.lock(), self.db:
            self.batch(workspace, brand, batch_id)
            self.db.execute("UPDATE batch SET cancelled_at=? WHERE batch_id=?", (stamp(), batch_id))
            self.db.execute("UPDATE job SET state='cancelled',updated_at=? WHERE batch_id=? AND state IN ('awaiting_approval','approved')", (stamp(), batch_id))
            self.audit(workspace, brand, "handoff_revoked", batch_id, actor)
        # Submitted tasks are not claimed cancelled: v1 has no remote cancellation.

    def jobs(self, workspace, brand):
        return [dict(r) for r in self.db.execute("SELECT * FROM job WHERE workspace=? AND brand=? ORDER BY job_id", (workspace, brand))]

    def change(self, job_id, state, error=None, task=None, observed=None):
        with self.db:
            self.db.execute("UPDATE job SET state=?,error_code=?,task_id=COALESCE(?,task_id),observed=COALESCE(?,observed),updated_at=? WHERE job_id=?",
                (state, error, task, canonical(observed) if observed is not None else None, stamp(), job_id))

    def dispatch_check(self, job, now):
        """One local readiness decision shared by preview and execution."""
        if job["state"] != "approved":
            return "not_approved"
        batch = self.batch(job["workspace"], job["brand"], job["batch_id"])
        if not batch["approved_by"] or batch["cancelled_at"]:
            return "approval_missing_or_revoked"
        m = json.loads(batch["manifest"])
        target = json.loads(job["target"])
        if digest(m) != batch["fingerprint"] or target not in m["targets"]:
            return "handoff_integrity_mismatch"
        at = dt.datetime.fromisoformat(target["schedule_at"]).timestamp()
        if at > now + 30:
            return "not_due"
        if now - at > 900:
            return "schedule_window_expired"
        account = self.account(job["workspace"], job["brand"], job["account_id"])
        if not account["ready"]:
            return "account_paused"
        busy = self.db.execute("SELECT 1 FROM job j JOIN account a USING(workspace,brand,account_id) WHERE a.phone_id=? AND a.token_env=? AND j.state IN ('submitted','dispatching','needs_reconciliation') LIMIT 1",
                               (account["phone_id"], account["token_env"])).fetchone()
        if busy:
            return "device_has_unresolved_work"
        media = self.media_dir / (m["asset_sha256"] + ".mp4")
        if not media.is_file() or file_hash(media) != m["asset_sha256"]:
            return "media_hash_mismatch"
        return None

    def dispatch(self, workspace, brand, *, execute=False, env_file=None, adapter_factory=None, now=None):
        now = time.time() if now is None else now
        if not execute:
            preview = []
            for job in self.jobs(workspace, brand):
                reason = self.dispatch_check(job, now)
                preview.append({"job_id": job["job_id"], "state": job["state"],
                    "would_submit": reason is None, "reason": reason, "account_id": job["account_id"]})
            return preview
        with self.lock():
            # A crash after submission must never become another blind attempt.
            for j in self.jobs(workspace, brand):
                if j["state"] == "dispatching":
                    self.change(j["job_id"], "needs_reconciliation", "interrupted_attempt")
            for job in self.jobs(workspace, brand):
                reason = self.dispatch_check(job, now)
                if reason:
                    if reason in ("schedule_window_expired", "media_hash_mismatch", "handoff_integrity_mismatch"):
                        self.change(job["job_id"], "blocked", reason)
                    continue
                batch = self.batch(workspace, brand, job["batch_id"])
                target = json.loads(job["target"])
                account = self.account(workspace, brand, job["account_id"])
                m = json.loads(batch["manifest"])
                media = self.media_dir / (m["asset_sha256"] + ".mp4")
                if adapter_factory:
                    adapter = adapter_factory(account)
                else:
                    probe_video(media)
                    adapter = GeeLark(token_value(account["token_env"], env_file))
                attempt = str(uuid.uuid4()).upper()
                with self.db:
                    self.db.execute("INSERT INTO attempt VALUES(?,?,?,NULL,NULL,?)", (attempt, job["job_id"], "uploading", stamp()))
                    self.db.execute("UPDATE job SET state='dispatching',updated_at=? WHERE job_id=?", (stamp(), job["job_id"]))
                try:
                    resource = adapter.upload(media)
                except Exception:
                    self.change(job["job_id"], "blocked", "media_upload_failed")
                    with self.db:
                        self.db.execute("UPDATE attempt SET phase='upload_failed',error_code='media_upload_failed' WHERE attempt_id=?", (attempt,))
                    continue
                with self.db:
                    self.db.execute("UPDATE attempt SET phase='submitting' WHERE attempt_id=?", (attempt,))
                try:
                    task = adapter.submit(account, target, resource, attempt)
                    if not isinstance(task, str) or not task:
                        raise ProviderError("missing_task_id")
                except Exception:
                    self.change(job["job_id"], "needs_reconciliation", "submission_outcome_unknown")
                    with self.db:
                        self.db.execute("UPDATE attempt SET phase='unknown',error_code='submission_outcome_unknown' WHERE attempt_id=?", (attempt,))
                    continue
                with self.db:
                    self.db.execute("UPDATE attempt SET phase='submitted',task_id=? WHERE attempt_id=?", (task, attempt))
                    self.db.execute("UPDATE job SET state='submitted',task_id=?,updated_at=? WHERE job_id=?", (task, stamp(), job["job_id"]))
                    self.audit(workspace, brand, "task_submitted", job["job_id"])
        return self.receipts(workspace, brand)

    def reconcile(self, workspace, brand, *, execute=False, env_file=None, adapter_factory=None):
        if not execute:
            return [{"job_id": j["job_id"], "state": j["state"], "task_id": j["task_id"]}
                    for j in self.jobs(workspace, brand) if j["state"] in ("submitted", "dispatching", "needs_reconciliation")]
        with self.lock():
            for job in self.jobs(workspace, brand):
                if job["state"] not in ("submitted", "dispatching", "needs_reconciliation"):
                    continue
                if not job["task_id"]:
                    self.change(job["job_id"], "needs_reconciliation", "operator_task_lookup_required")
                    continue
                account = self.account(workspace, brand, job["account_id"])
                adapter = adapter_factory(account) if adapter_factory else GeeLark(token_value(account["token_env"], env_file))
                try:
                    item = adapter.status(job["task_id"])
                except Exception:
                    self.change(job["job_id"], "needs_reconciliation", "status_unavailable")
                    continue
                if str(item.get("envId")) != account["phone_id"]:
                    self.change(job["job_id"], "needs_reconciliation", "provider_device_mismatch")
                    continue
                status = item.get("status")
                state = {1: "submitted", 2: "submitted", 3: "provider_completed", 4: "provider_failed", 7: "provider_cancelled"}.get(status, "needs_reconciliation")
                fail = item.get("failCode")
                if status == 4 and fail == 20003:
                    state = "needs_reconciliation"
                observation = {"provider_status": status if isinstance(status, int) else None,
                    "failure_code": fail if isinstance(fail, int) else None,
                    "provider_duration_seconds": item.get("cost") if isinstance(item.get("cost"), int) and item["cost"] >= 0 else None,
                    "reported_post_url": safe_link(item.get("shareLink"), account["platform"]),
                    "live_verified": False, "observed_at": stamp()}
                self.change(job["job_id"], state, observed=observation)
        return self.receipts(workspace, brand)

    def attach_task(self, workspace, brand, job_id, task_id, actor, adapter):
        identifier(actor, "actor")
        if not isinstance(task_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,150}", task_id):
            raise Refused("Invalid provider task ID")
        with self.lock():
            job = next((j for j in self.jobs(workspace, brand) if j["job_id"] == job_id), None)
            if not job or job["state"] != "needs_reconciliation" or job["task_id"]:
                raise Refused("Only an unresolved submission without a task ID can be linked")
            account = self.account(workspace, brand, job["account_id"])
            item = adapter.status(task_id)
            if str(item.get("envId")) != account["phone_id"]:
                raise Refused("Provider task belongs to another device")
            other = self.db.execute("SELECT 1 FROM job WHERE task_id=?", (task_id,)).fetchone()
            if other:
                raise Refused("Provider task is already linked")
            self.change(job_id, "submitted", task=task_id)
            with self.db:
                self.audit(workspace, brand, "operator_task_linked", job_id, actor)

    def receipts(self, workspace, brand):
        out = []
        for job in self.jobs(workspace, brand):
            batch = self.batch(workspace, brand, job["batch_id"])
            m = json.loads(batch["manifest"])
            account = self.account(workspace, brand, job["account_id"])
            receipt = {"schema": "prizm-social-result/1", "workspace": workspace, "brand": brand,
                "brief_id": m["brief_id"], "brief_key": m["brief_key"], "product": m["product"],
                "asset_id": m["asset_id"], "asset_sha256": m["asset_sha256"],
                "source_tool": m["source_tool"], "source_run": m["source_run"],
                "job_id": job["job_id"], "batch_id": job["batch_id"], "account_id": job["account_id"],
                "platform": account["platform"], "state": job["state"], "provider_task_id": job["task_id"],
                "error_code": job["error_code"], "observation": json.loads(job["observed"]) if job["observed"] else None,
                "updated_at": job["updated_at"]}
            receipt["attempts"] = [dict(row) for row in self.db.execute(
                "SELECT attempt_id,phase,task_id,error_code,created_at FROM attempt WHERE job_id=? ORDER BY created_at,attempt_id", (job["job_id"],))]
            receipt["event_id"] = "result_" + digest(receipt)
            out.append(receipt)
        return out


def probe_video(path):
    binary = shutil.which("ffprobe")
    if not binary:
        raise Refused("Live dispatch requires ffprobe to validate the staged video")
    r = subprocess.run([binary, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                       capture_output=True, timeout=30)
    try:
        info = json.loads(r.stdout)
        if r.returncode or not any(s.get("codec_type") == "video" for s in info["streams"]) or float(info["format"]["duration"]) <= 0:
            raise ValueError
    except (ValueError, KeyError, TypeError):
        raise Refused("Staged file is not a readable video; resolve upstream media checks") from None


def report(connector, workspace, brand, out):
    records = connector.receipts(workspace, brand)
    esc = lambda x: html.escape(str(x if x is not None else "—"))
    cards = []
    for r in records:
        observation = r["observation"] or {}
        link = observation.get("reported_post_url")
        cards.append(f"<article><h2>{esc(r['platform'])} · {esc(r['account_id'])}</h2>"
            f"<p class='state'>{esc(r['state'])}</p><dl><dt>Brief</dt><dd>{esc(r['brief_key'])}</dd>"
            f"<dt>Asset</dt><dd>{esc(r['asset_id'])}</dd><dt>Task</dt><dd>{esc(r['provider_task_id'])}</dd>"
            f"<dt>Updated</dt><dd>{esc(r['updated_at'])}</dd></dl>"
            + (f"<p><a href='{esc(link)}' rel='noopener noreferrer'>Provider-reported post</a> · Unverified</p>" if link else "")
            + "</article>")
    document = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Prizm connector receipt</title><style>
:root{color-scheme:light dark;font:16px system-ui;background:light-dark(#f6f7f8,#131820);color:light-dark(#17212d,#eef2f6)}
body{max-width:860px;margin:0 auto;padding:24px}h1{font-size:1.6rem}h2{font-size:1.05rem}article{background:light-dark(#fff,#202935);padding:20px;margin:16px 0;border-radius:12px}
dl{display:grid;grid-template-columns:75px minmax(0,1fr);gap:10px}dd{margin:0;overflow-wrap:anywhere}.state{font-weight:600}a{color:light-dark(#075cba,#85baff)}
</style><h1>Prizm → distribution connector</h1>"""
    document += f"<p>{esc(workspace)} / {esc(brand)} · {len(records)} publishing jobs</p>"
    document += "<p>Static local snapshot. This page does not publish, refresh itself, or verify a live post.</p>"
    document += "".join(cards) or "<p>No jobs in this scope.</p>"
    document += "<p>Provider duration is execution time, not a financial charge. Existing upstream records are unchanged.</p></html>"
    private_write(out, document)
    return {"report": str(out), "jobs": len(records)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="Private local SQLite path; use output/ or a private state directory")
    sub = parser.add_subparsers(dest="command", required=True)
    def scoped(name, help):
        p = sub.add_parser(name, help=help)
        p.add_argument("--workspace", required=True)
        p.add_argument("--brand", required=True)
        return p
    p = scoped("account", "Register an immutable account binding")
    p.add_argument("--id", required=True)
    p.add_argument("--platform", choices=PLATFORMS, required=True)
    p.add_argument("--platform-account-id", required=True)
    p.add_argument("--phone-id", required=True)
    p.add_argument("--token-env", default="GEELARK_API_TOKEN")
    for name, help in (("ready", "Attest login/device/proxy readiness"), ("pause", "Stop new dispatches on an account")):
        p = scoped(name, help); p.add_argument("--account", required=True); p.add_argument("--actor", required=True)
    for name in ("plan", "intake"):
        p = sub.add_parser(name, help="Inspect without writing jobs" if name == "plan" else "Stage media and create approval-pending jobs")
        p.add_argument("--workspace", required=True); p.add_argument("--card", required=True)
        p.add_argument("--asset", required=True); p.add_argument("--targets", required=True)
        p.add_argument("--ledger"); p.add_argument("--request-key")
    p = scoped("approve", "Approve the exact handoff fingerprint locally")
    p.add_argument("--batch", required=True); p.add_argument("--fingerprint", required=True); p.add_argument("--actor", required=True)
    p = scoped("cancel", "Revoke approval and cancel only unsent work")
    p.add_argument("--batch", required=True); p.add_argument("--actor", required=True)
    for name in ("dispatch", "reconcile"):
        p = scoped(name, "Preview by default; --execute allows provider requests")
        p.add_argument("--execute", action="store_true"); p.add_argument("--env-file")
    scoped("status", "Read scoped receipts")
    for name in ("export", "report"):
        p = scoped(name, "Write a private JSONL receipt outbox" if name == "export" else "Write a mobile-readable static HTML snapshot")
        p.add_argument("--out", required=True)
    p = scoped("attach-task", "Record an operator-found task for an uncertain submission")
    p.add_argument("--job", required=True); p.add_argument("--task", required=True)
    p.add_argument("--actor", required=True); p.add_argument("--env-file")
    p.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    store = None
    try:
        store = Connector(args.db)
        w, b = args.workspace, getattr(args, "brand", None)
        if b:
            identifier(w); identifier(b)
        if args.command == "account":
            result = {"created": store.register(w, b, args.id, args.platform, args.platform_account_id, args.phone_id, args.token_env)}
        elif args.command in ("ready", "pause"):
            store.readiness(w, b, args.account, args.command == "ready", args.actor); result = {"ready": args.command == "ready"}
        elif args.command in ("plan", "intake"):
            plan = store.plan(args.card, args.asset, read_json(args.targets), w, args.ledger, args.request_key)
            result = {k: v for k, v in plan.items() if k != "media"}
            if args.command == "intake":
                result = {**store.intake(plan), "fingerprint": plan["fingerprint"]}
        elif args.command == "approve":
            store.approve(w, b, args.batch, args.fingerprint, args.actor); result = {"approved": args.batch}
        elif args.command == "cancel":
            store.cancel(w, b, args.batch, args.actor); result = {"revoked": args.batch, "remote_cancellation": False}
        elif args.command in ("dispatch", "reconcile"):
            result = getattr(store, args.command)(w, b, execute=args.execute, env_file=args.env_file)
        elif args.command == "attach-task":
            job = next((j for j in store.jobs(w, b) if j["job_id"] == args.job), None)
            if not job:
                raise Refused("Job not found in this scope")
            if args.execute:
                account = store.account(w, b, job["account_id"])
                store.attach_task(w, b, args.job, args.task, args.actor, GeeLark(token_value(account["token_env"], args.env_file)))
                result = {"linked": args.job}
            else:
                result = {"would_lookup_task": args.task, "job_id": args.job}
        elif args.command == "report":
            result = report(store, w, b, args.out)
        elif args.command == "export":
            records = store.receipts(w, b)
            private_write(args.out, "".join(canonical(x) + "\n" for x in records))
            result = {"receipts": len(records), "out": args.out}
        else:
            result = store.receipts(w, b)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (Refused, ProviderError) as e:
        print(str(e)); return 2
    except (OSError, sqlite3.Error, ValueError, TypeError, subprocess.SubprocessError):
        print("Local connector operation failed; check the input contract, file access and database version")
        return 2
    finally:
        if store:
            store.close()


if __name__ == "__main__":
    raise SystemExit(main())
