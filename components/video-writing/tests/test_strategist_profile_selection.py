"""Audience selection and every writing pass use the strategist's actual person; no model calls."""
import hashlib
import json
import unittest
from unittest import mock

import test_who_reaches_writing as base
W = base.W


class Profiles(base.Base):
    def setUp(self):
        super().setUp()
        self.who = W.who_module()
        self.profile = {
            "brand": "acme", "avatar": "owner", "sub": "porch-painter", "name": "owner_porch-painter",
            "own_lines": 1, "desire": {"text": "Keep the porch coating through winter", "from": "own"},
            "experiences": [{"text": "The third coat peeled after frost", "from": "own"}],
            "emotions": [], "behaviors": [], "culture": [], "missing": ["Their buying budget"],
            "doubt": {"text": "Will it peel again?", "from": "own"},
            "opening": {"text": "Three coats and it still peels", "from": "own"},
            "lines": {"lead_1": {"text": "The third coat peeled after frost"}}}
        self.draft = self.who.draft("acme", "owner", "porch-painter")
        self.draft.parent.mkdir(parents=True, exist_ok=True)
        self.draft.write_text(json.dumps(self.profile))

    def test_catalog_reads_draft_without_index_and_records_exact_source(self):
        row = self.who.catalog("acme")[0]
        self.assertEqual(row["state"], "draft")
        self.assertEqual(row["source"], str(self.draft.relative_to(self.ws)))
        self.assertEqual(row["sha256"], hashlib.sha256(self.draft.read_bytes()).hexdigest())
        self.assertFalse(self.draft.with_name("index.json").exists())
        block = self.who.catalog_block("acme")
        for text in ("SUB-AVATAR: porch-painter", "third coat peeled", "Their buying budget", row["source"]):
            self.assertIn(text, block)

    def test_filed_profile_wins_and_is_the_same_one_writing_uses(self):
        filed = self.who.home("acme", "owner", "porch-painter")
        filed.parent.mkdir(parents=True, exist_ok=True)
        chosen = dict(self.profile, desire={"text": "The filed person's desire", "from": "own"})
        filed.write_text(json.dumps(chosen))
        row = self.who.catalog("acme")[0]
        self.assertEqual(row["state"], "filed")
        self.assertEqual(row["source"], str(filed.relative_to(self.ws)))
        self.assertEqual(row["profile"], self.who.full("acme", "owner", "porch-painter")["person"])

    def test_broken_profile_cannot_silently_become_a_broad_avatar(self):
        self.draft.write_text("{broken")
        with self.assertRaisesRegex(SystemExit, "cannot read strategist profile"):
            self.who.catalog("acme")

    def test_broad_or_unavailable_selection_stops_when_profiles_exist(self):
        with self.assertRaisesRegex(SystemExit, "choose a specific creative-strategist profile"):
            self.who.selection("acme", "owner")
        self.assertIsNone(self.who.selection("no-brand", None))
        self.assertEqual(self.who.selection("acme", "owner", "sub-01-porch-painter")["sub"], "porch-painter")

    def test_audience_pass_gets_complete_profiles_instead_of_roster_and_saves_receipt(self):
        st = self.state(label="piece", slug="piece", audience={})
        ok, prompt, st = base.OldLine.stage(self, "stage1b", "Audience", st)
        self.assertTrue(ok)
        self.assertIn("CREATIVE STRATEGIST PROFILES", prompt)
        self.assertIn("The third coat peeled after frost", prompt)
        self.assertEqual(st["selected_profile"]["source"], str(self.draft.relative_to(self.ws)))

    def test_old_broad_run_cannot_write(self):
        st = self.state(audience={"_avatar": "owner", "_sub_avatar": None})
        with self.assertRaisesRegex(SystemExit, "choose a specific creative-strategist profile"):
            W.who_block(self.run, st, "3-injection.md")

    def test_resumed_broad_run_is_held_before_any_writing_call(self):
        import run as R
        st = self.state(label="piece", slug="piece", audience={"_avatar": "owner", "_sub_avatar": None},
                        writing_lane={"lane": "swipe"}, production_route="ai")
        original = R.claude
        try:
            with mock.patch.object(W, "apply_call", lambda d, s: s), mock.patch.object(W, "format_approved", return_value=True), \
                    mock.patch.object(W, "winner_match_step", return_value=(True, "")), mock.patch.object(W, "plan") as plan:
                self.assertFalse(W.run_writing(self.run, st, {}))
                plan.assert_not_called()
        finally:
            R.claude = original
        saved = json.loads((self.run / "run.json").read_text())
        self.assertEqual(saved["waiting_for"], "strategist profile")
        self.assertEqual(saved["stages"]["stage3"]["status"], "held")

    def test_actual_audience_variable_replaces_old_roster_and_rejects_no_sub(self):
        import run as R
        tpl = self.ws / "audience-v1.md"
        tpl.write_text("Candidates: {avatars}")
        stage = dict(key="stage1b", id="1c", file_id="1b", name="Audience", prompt=str(tpl),
                     version=1, engine="claude", vars={"avatars": "?roster"}, role="stage", per_run=[])
        seen = []
        def fake(prompt, out, model=None):
            seen.append(prompt)
            out.write_text("AVATAR: owner\nSUB-AVATAR: none\n")
            return "fake"
        st = self.state(label="piece", slug="piece", audience={})
        with mock.patch.object(R, "claude", fake), mock.patch.object(R, "creative_qc"), mock.patch.object(R, "record_time"), \
                mock.patch.object(R, "TMP", self.ws / "tmp"), mock.patch.object(R.C, "chain_version", return_value="v1"), \
                mock.patch.object(R.C, "resolve_source", side_effect=AssertionError("old roster must not be read")):
            self.assertFalse(R.run_stage(self.run, st, stage, {}))
        self.assertIn("The third coat peeled after frost", seen[0])
        self.assertIn("choose a specific creative-strategist profile", st["stages"]["stage1b"]["error"])

    def test_swipe_format_is_pinned_without_a_board_combo(self):
        st = self.state(format_id="comedy-skit", layers={"format": "comedy-skit"})
        matrix = mock.Mock()
        matrix.values.return_value = {"format": ["comedy-skit"]}
        with mock.patch.object(W, "_matrix_off", return_value=False), mock.patch.object(W, "_matrix", return_value=matrix):
            self.assertEqual(W.matrix_start(self.run, st), "")
        self.assertEqual(matrix.start.call_args.args[4], {"format": "comedy-skit"})

    def test_actual_profile_reaches_each_sent_pass_and_is_attached(self):
        st = self.state()
        for key, name in (("stage3", "3-injection.md"), ("stage4i", "4i-controlling-idea.md"),
                          ("stage4v2a", "4ab-reading-hooks.md"), ("stage4v2b", "4cde-placement-expansion-close.md"),
                          ("stage4e", "4f-audit.md"), ("stage4g", "4g-spice.md"), ("stage5", "5-brief.md")):
            sent = self.sent(name, key)
            self.assertIn("the profile `owner_porch-painter`", sent)
            self.assertIn("The third coat peeled after frost", sent)
            self.assertIn("Their buying budget", sent)
        W.who_attach(self.run, st)
        saved = json.loads((self.run / "profile.json").read_text())
        self.assertEqual(saved["person"], self.profile)
        self.assertEqual(saved["person_lives_in"], str(self.draft.relative_to(self.ws)))


if __name__ == "__main__":
    unittest.main()
