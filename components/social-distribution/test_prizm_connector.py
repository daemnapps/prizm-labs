"""Behavior tests: isolated local state, synthetic brands/media, no network."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import prizm_connector as C

NOW = 1800000000
AT = C.dt.datetime.fromtimestamp(NOW, C.UTC).isoformat()


class FakeProvider:
    def __init__(self):
        self.uploads = 0
        self.submissions = 0
        self.raise_submit = None
        self.raise_upload = False
        self.item = {"id": "task-1", "envId": "phone-tt", "status": 3,
                     "cost": 42, "shareLink": "https://www.tiktok.com/@demo/video/123?tracking=secret"}

    def upload(self, path):
        self.uploads += 1
        if self.raise_upload:
            raise RuntimeError("private provider payload must not leak")
        return "https://media.example/temporary"

    def submit(self, account, target, resource, trace):
        self.submissions += 1
        if self.raise_submit:
            raise self.raise_submit
        return "task-1"

    def status(self, task):
        return self.item


class ConnectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.card = self.root / "card.json"
        self.asset = "brand-a_product-a_brief-0001_batch-2026-10-19-a_asset-01.mp4"
        (self.root / self.asset).write_bytes(b"synthetic test fixture, never submitted")
        self.card_data = {"schema": "meta-card/1", "brand": "brand-a", "product": "product-a",
            "brief_id": "brief-0001", "ad_name": self.asset.rsplit("_asset-", 1)[0],
            "media": [self.asset], "checks": {}, "approval": None,
            "made_by": {"tool": "video-edit", "run": "runs/video-edit/brand-a/demo"}}
        self.save_card()
        self.db = self.root / "private" / "connector.db"
        self.store = C.Connector(self.db)
        self.addCleanup(lambda: self.store.close())
        self.store.register("workspace-a", "brand-a", "account-tt", "tiktok", "platform-tt", "phone-tt")
        self.targets = [{"account_id": "account-tt", "caption": "Approved fixture caption", "schedule_at": AT, "ai_disclosure": False}]
        self.provider = FakeProvider()
        self.factory = lambda account: self.provider
        self.network = patch("urllib.request.urlopen", side_effect=AssertionError("Network forbidden in behavior tests"))
        self.network.start()
        self.addCleanup(self.network.stop)

    def save_card(self):
        self.card.write_text(json.dumps(self.card_data))

    def plan(self, **kwargs):
        return self.store.plan(self.card, self.asset, self.targets, "workspace-a", **kwargs)

    def enqueue(self, approve=True):
        p = self.plan()
        self.store.intake(p)
        if approve:
            self.store.approve("workspace-a", "brand-a", p["batch_id"], p["fingerprint"], "owner")
            self.store.readiness("workspace-a", "brand-a", "account-tt", True, "owner")
        return p

    def dispatch(self):
        return self.store.dispatch("workspace-a", "brand-a", execute=True, adapter_factory=self.factory, now=NOW)

    def state(self):
        return self.store.jobs("workspace-a", "brand-a")[0]["state"]

    def test_idempotent_intake_survives_restart(self):
        p = self.plan()
        self.assertTrue(self.store.intake(p)["created"])
        self.store.close()
        self.store = C.Connector(self.db)
        self.assertFalse(self.store.intake(p)["created"])
        self.assertEqual(len(self.store.jobs("workspace-a", "brand-a")), 1)

    def test_changed_caption_is_revision_conflict(self):
        self.store.intake(self.plan())
        self.targets[0]["caption"] = "Different words"
        with self.assertRaises(C.Refused):
            self.store.intake(self.plan())
        self.assertTrue(self.store.intake(self.plan(request_key="revision-2"))["created"])

    def test_cross_brand_and_cross_workspace_targets_rejected(self):
        self.store.register("workspace-a", "brand-b", "other", "youtube", "platform-b", "phone-b")
        self.targets[0]["account_id"] = "other"
        with self.assertRaises(C.Refused): self.plan()
        self.store.register("workspace-b", "brand-a", "external", "youtube", "platform-c", "phone-c")
        self.targets[0]["account_id"] = "external"
        with self.assertRaises(C.Refused): self.plan()

    def test_multiple_platform_targets_keep_asset_identity(self):
        self.store.register("workspace-a", "brand-a", "account-ig", "instagram", "platform-ig", "phone-ig")
        self.store.register("workspace-a", "brand-a", "account-yt", "youtube", "platform-yt", "phone-yt")
        self.targets += [{"account_id": "account-ig", "caption": "IG caption", "schedule_at": AT, "ai_disclosure": False},
                         {"account_id": "account-yt", "caption": "YT caption", "title": "Explicit title", "schedule_at": AT, "ai_disclosure": False}]
        p = self.plan()
        self.store.intake(p)
        self.assertEqual(self.plan()["fingerprint"], p["fingerprint"])
        self.targets.reverse()
        self.assertEqual(self.plan()["fingerprint"], p["fingerprint"])
        receipts = self.store.receipts("workspace-a", "brand-a")
        self.assertEqual(len(receipts), 3)
        self.assertEqual(len({x["asset_sha256"] for x in receipts}), 1)
        self.assertEqual(len({x["job_id"] for x in receipts}), 3)

    def test_media_frozen_and_mutation_blocked(self):
        p = self.enqueue()
        (self.root / self.asset).write_bytes(b"changed original")
        staged = self.store.media_dir / (p["manifest"]["asset_sha256"] + ".mp4")
        self.assertNotEqual(C.file_hash(staged), C.file_hash(self.root / self.asset))
        staged.write_bytes(b"tampered staged copy")
        self.dispatch()
        self.assertEqual(self.state(), "blocked")
        self.assertEqual(self.provider.uploads, 0)

    def test_partial_intake_is_atomic_for_bad_target(self):
        self.targets.append({"account_id": "missing", "caption": "x", "schedule_at": AT})
        with self.assertRaises(C.Refused): self.plan()
        self.assertEqual(self.store.jobs("workspace-a", "brand-a"), [])

    def test_metadata_timezone_and_duplicate_target_validation(self):
        for value in ("2026-10-19T12:00:00", "bad", None):
            self.targets[0]["schedule_at"] = value
            with self.assertRaises(C.Refused): self.plan()
        self.targets[0]["schedule_at"] = AT
        self.targets.append(copy.deepcopy(self.targets[0]))
        with self.assertRaises(C.Refused): self.plan()

    def test_read_only_ledger_identity_check(self):
        ledger = self.root / "ledger.db"
        with contextlib.closing(sqlite3.connect(ledger)) as db, db:
            db.execute("CREATE TABLE asset(asset_id,brand_id,brief_id,product)")
            db.execute("INSERT INTO asset VALUES(?,?,?,?)", (self.asset[:-4], "brand-a", "brief-0001", "product-a"))
        before = C.file_hash(ledger)
        self.assertTrue(self.plan(ledger=ledger)["manifest"]["upstream_ledger_checked"])
        self.assertEqual(before, C.file_hash(ledger))
        with contextlib.closing(sqlite3.connect(ledger)) as db, db:
            db.execute("UPDATE asset SET brand_id='brand-b'")
        with self.assertRaises(C.Refused): self.plan(ledger=ledger)

    def test_upstream_rejection_and_failed_checks_block_intake(self):
        self.card_data["approval"] = {"decision": "disapprove"}; self.save_card()
        with self.assertRaises(C.Refused): self.plan()
        self.card_data["approval"] = None
        self.card_data["checks"] = {"media": {"ok": False}}; self.save_card()
        with self.assertRaises(C.Refused): self.plan()

    def test_meta_approval_does_not_authorize_social_post(self):
        self.card_data["approval"] = {"decision": "approve", "by": "someone"}; self.save_card()
        self.enqueue(approve=False)
        self.dispatch()
        self.assertEqual(self.state(), "awaiting_approval")
        self.assertEqual(self.provider.submissions, 0)

    def test_approval_hash_and_scope_must_match(self):
        p = self.enqueue(approve=False)
        for workspace, brand, fingerprint in (("workspace-b", "brand-a", p["fingerprint"]),
                ("workspace-a", "brand-b", p["fingerprint"]), ("workspace-a", "brand-a", "wrong")):
            with self.assertRaises(C.Refused):
                self.store.approve(workspace, brand, p["batch_id"], fingerprint, "owner")

    def test_dispatch_preview_is_network_free_and_does_not_advance(self):
        self.enqueue()
        self.store.dispatch("workspace-a", "brand-a")
        self.assertEqual(self.state(), "approved")
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM attempt").fetchone()[0], 0)

    def test_successful_submission_is_not_a_live_post(self):
        self.enqueue(); self.dispatch(); self.dispatch()
        self.assertEqual(self.state(), "submitted")
        self.assertEqual(self.provider.submissions, 1)
        self.store.reconcile("workspace-a", "brand-a", execute=True, adapter_factory=self.factory)
        self.assertEqual(self.state(), "provider_completed")
        receipt = self.store.receipts("workspace-a", "brand-a")[0]
        self.assertFalse(receipt["observation"]["live_verified"])
        self.assertEqual(receipt["observation"]["provider_duration_seconds"], 42)
        self.assertNotIn("tracking", receipt["observation"]["reported_post_url"])

    def test_timeout_never_blindly_resubmits(self):
        self.enqueue(); self.provider.raise_submit = TimeoutError("token=must-not-leak")
        self.dispatch(); self.dispatch()
        self.assertEqual(self.state(), "needs_reconciliation")
        self.assertEqual(self.provider.submissions, 1)
        text = C.canonical(self.store.receipts("workspace-a", "brand-a"))
        self.assertNotIn("must-not-leak", text)

    def test_process_interruption_leaves_recoverable_attempt(self):
        self.enqueue(); self.provider.raise_submit = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt): self.dispatch()
        self.assertEqual(self.state(), "dispatching")
        self.provider.raise_submit = None
        self.dispatch()
        self.assertEqual(self.state(), "needs_reconciliation")
        self.assertEqual(self.provider.submissions, 1)

    def test_device_mismatch_is_not_accepted(self):
        self.enqueue(); self.dispatch()
        self.provider.item["envId"] = "other-device"
        self.store.reconcile("workspace-a", "brand-a", execute=True, adapter_factory=self.factory)
        self.assertEqual(self.state(), "needs_reconciliation")

    def test_provider_execution_timeout_is_uncertain(self):
        self.enqueue(); self.dispatch()
        self.provider.item.update(status=4, failCode=20003)
        self.store.reconcile("workspace-a", "brand-a", execute=True, adapter_factory=self.factory)
        self.assertEqual(self.state(), "needs_reconciliation")

    def test_paused_account_never_dispatches(self):
        self.enqueue()
        self.store.readiness("workspace-a", "brand-a", "account-tt", False, "owner")
        self.dispatch()
        self.assertEqual(self.provider.submissions, 0)

    def test_preview_respects_due_time_and_readiness(self):
        self.enqueue()
        preview = self.store.dispatch("workspace-a", "brand-a", now=NOW-60)
        self.assertFalse(preview[0]["would_submit"])
        self.assertEqual(preview[0]["reason"], "not_due")
        self.store.readiness("workspace-a", "brand-a", "account-tt", False, "owner")
        preview = self.store.dispatch("workspace-a", "brand-a", now=NOW)
        self.assertEqual(preview[0]["reason"], "account_paused")
        self.assertEqual(self.state(), "approved")

    def test_corrupt_target_invalidates_existing_approval(self):
        self.enqueue()
        with self.store.db:
            target = copy.deepcopy(self.targets[0]); target["caption"] = "Unapproved edit"
            self.store.db.execute("UPDATE job SET target=?", (C.canonical(target),))
        self.dispatch()
        self.assertEqual(self.state(), "blocked")
        self.assertEqual(self.provider.submissions, 0)

    def test_cancel_revokes_unsent_work_and_cannot_reapprove(self):
        p = self.enqueue()
        self.store.cancel("workspace-a", "brand-a", p["batch_id"], "owner")
        self.dispatch()
        self.assertEqual(self.state(), "cancelled")
        with self.assertRaises(C.Refused):
            self.store.approve("workspace-a", "brand-a", p["batch_id"], p["fingerprint"], "owner")

    def test_cancel_does_not_claim_remote_task_cancelled(self):
        p = self.enqueue(); self.dispatch()
        self.store.cancel("workspace-a", "brand-a", p["batch_id"], "owner")
        self.assertEqual(self.state(), "submitted")

    def test_outage_does_not_flush_stale_schedules(self):
        self.enqueue()
        self.store.dispatch("workspace-a", "brand-a", execute=True, adapter_factory=self.factory, now=NOW+901)
        self.assertEqual(self.state(), "blocked")
        self.assertEqual(self.provider.submissions, 0)

    def test_early_schedule_waits(self):
        self.enqueue()
        self.store.dispatch("workspace-a", "brand-a", execute=True, adapter_factory=self.factory, now=NOW-60)
        self.assertEqual(self.state(), "approved")
        self.assertEqual(self.provider.submissions, 0)

    def test_upload_failure_is_blocked_without_submission(self):
        self.enqueue(); self.provider.raise_upload = True
        self.dispatch()
        self.assertEqual(self.state(), "blocked")
        self.assertEqual(self.provider.submissions, 0)

    def test_task_can_be_recovered_without_resubmitting(self):
        self.enqueue(); self.provider.raise_submit = TimeoutError()
        self.dispatch()
        job = self.store.jobs("workspace-a", "brand-a")[0]
        self.store.attach_task("workspace-a", "brand-a", job["job_id"], "task-1", "owner", self.provider)
        self.store.reconcile("workspace-a", "brand-a", execute=True, adapter_factory=self.factory)
        self.assertEqual(self.state(), "provider_completed")
        self.assertEqual(self.provider.submissions, 1)

    def test_account_binding_and_platform_ownership_immutable(self):
        with self.assertRaises(C.Refused):
            self.store.register("workspace-a", "brand-a", "account-tt", "tiktok", "platform-tt", "different-phone")
        with self.assertRaises(C.Refused):
            self.store.register("workspace-b", "brand-b", "account-other", "tiktok", "platform-tt", "phone-other")

    def test_platform_ids_preserve_case(self):
        self.store.register("workspace-a", "brand-a", "youtube-main", "youtube", "UCExample_ChannelID", "123456789")
        self.assertEqual(self.store.account("workspace-a", "brand-a", "youtube-main")["platform_account_id"], "UCExample_ChannelID")

    def test_missing_disclosure_is_not_silently_assumed(self):
        del self.targets[0]["ai_disclosure"]
        with self.assertRaises(C.Refused): self.plan()

    def test_unresolved_device_blocks_other_jobs_on_device(self):
        self.enqueue(); self.provider.raise_submit = TimeoutError(); self.dispatch()
        p = self.plan(request_key="second-explicit-job")
        self.store.intake(p)
        self.store.approve("workspace-a", "brand-a", p["batch_id"], p["fingerprint"], "owner")
        self.dispatch()
        self.assertEqual(self.provider.submissions, 1)

    def test_cross_brand_reports_are_scoped_and_event_ids_stable(self):
        self.enqueue()
        self.assertEqual(self.store.receipts("workspace-a", "brand-b"), [])
        a = self.store.receipts("workspace-a", "brand-a")
        self.assertEqual(a, self.store.receipts("workspace-a", "brand-a"))
        self.assertNotIn("phone_id", C.canonical(a))
        self.assertNotIn("token_env", C.canonical(a))

    def test_database_media_and_export_permissions_private(self):
        self.enqueue()
        path = self.root / "receipts.jsonl"
        C.private_write(path, "fixture")
        for f in [self.db, path, *self.store.media_dir.glob("*.mp4")]:
            self.assertEqual(f.stat().st_mode & 0o077, 0)

    def test_lock_prevents_overlapping_mutations(self):
        other = C.Connector(self.db)
        try:
            with self.store.lock():
                with self.assertRaises(C.Refused):
                    other.register("workspace-a", "brand-a", "new-account", "instagram", "p-new", "phone-new")
        finally: other.close()

    def test_report_escapes_content_and_has_no_live_controls(self):
        self.enqueue()
        path = self.root / "report.html"
        C.report(self.store, "workspace-a", "brand-a", path)
        doc = path.read_text()
        self.assertIn("awaiting", doc) if self.state() == "awaiting_approval" else self.assertIn("approved", doc)
        self.assertIn("Static local snapshot", doc)
        self.assertNotIn("<script", doc)
        self.assertNotIn("<form", doc)

    def test_traversal_and_symlink_media_rejected(self):
        self.card_data["media"] = ["../outside.mp4"]; self.save_card()
        with self.assertRaises(C.Refused):
            self.store.plan(self.card, "../outside.mp4", self.targets, "workspace-a")
        self.card_data["media"] = [self.asset]; self.save_card()
        p = self.root / self.asset; p.unlink()
        external = self.root / "outside.mp4"; external.write_bytes(b"x")
        p.symlink_to(external)
        with self.assertRaises(C.Refused): self.plan()

    def test_disclosure_is_explicit_and_typed(self):
        self.targets[0]["ai_disclosure"] = True
        self.assertTrue(self.plan()["manifest"]["targets"][0]["ai_disclosure"])
        self.targets[0]["ai_disclosure"] = "false"
        with self.assertRaises(C.Refused): self.plan()


class TransportTests(unittest.TestCase):
    def test_provider_error_does_not_echo_secret_fields(self):
        payload = {"code": 123, "msg": "token=secret", "data": {"password": "secret"}}
        response = contextlib.closing(io.StringIO(json.dumps(payload)))
        with patch("urllib.request.urlopen", return_value=response):
            with self.assertRaises(C.ProviderError) as caught:
                C.GeeLark("not-a-real-key").call("/task/query", {"ids": ["demo"]})
        self.assertEqual(str(caught.exception), "provider_code_123")

    def test_platform_request_shapes_and_disclosures(self):
        adapter = C.GeeLark("not-a-real-key")
        target = {"schedule_at": AT, "caption": "Caption", "title": "Title", "ai_disclosure": True}
        with patch.object(adapter, "call", return_value={"taskId": "example-task"}) as call:
            for platform, endpoint, disclosure in (("instagram", "/rpa/task/instagramPubReels", "aiTag"),
                    ("youtube", "/rpa/task/youtubePubShort", "isDisclosureMandatory")):
                task = adapter.submit({"platform": platform, "phone_id": "phone-demo"}, target, "https://media.example/v.mp4", "request-demo")
                self.assertEqual(task, "example-task")
                self.assertEqual(call.call_args.args[0], endpoint)
                self.assertTrue(call.call_args.args[1][disclosure])
        with patch.object(adapter, "call", return_value={"taskIds": ["example-task"]}) as call:
            adapter.submit({"platform": "tiktok", "phone_id": "phone-demo"}, target, "https://media.example/v.mp4", "request-demo")
            self.assertEqual(call.call_args.args[0], "/task/add")
            self.assertEqual(call.call_args.args[1]["list"][0]["envId"], "phone-demo")
            self.assertTrue(call.call_args.args[1]["list"][0]["markAI"])
            self.assertEqual(call.call_args.args[1]["list"][0]["maxTryTimes"], 0)
            self.assertEqual(call.call_args.args[1]["remark"], "request-demo")


if __name__ == "__main__":
    unittest.main()
