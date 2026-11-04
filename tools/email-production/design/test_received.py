"""The before-and-after's change list (design/received.py): what the team reads above the two pictures must say what the
designer really changed, part by part, and nothing she didn't (the team, 2026-10-28).

    /usr/bin/python3 test_received.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import received as R  # noqa: E402

WORDS = lambda s: [v for k, v in s.items() if isinstance(v, str) and k not in ("s", "photo")]


def sec(s, text, photo=None, **more):
    d = {"s": s, "text": text}
    if photo:
        d["photo"] = photo
    d.update(more)
    return d


class Changes(unittest.TestCase):
    def said(self, old, new):
        return [c["what"] for c in R.changes({"sections": old}, {"sections": new}, words=WORDS)]

    def test_nothing_changed_says_nothing(self):
        S = [sec("band", "Header"), sec("letter", "Hi there")]
        self.assertEqual(self.said(S, S), [])

    def test_a_new_look_with_the_same_words_is_a_layout_change_not_words(self):
        self.assertEqual(self.said([sec("poster", "THE MATCHUP")], [sec("hero_photo", "THE MATCHUP")]),
                         ["Part 1: poster → hero_photo"])

    def test_two_parts_swapped_one_is_moved_and_the_rest_keep_their_place(self):
        old = [sec("band", "a"), sec("card", "b"), sec("arrows", "c"), sec("foot", "d")]
        new = [sec("band", "a"), sec("arrows", "c"), sec("card", "b"), sec("foot", "d")]
        self.assertEqual(len([w for w in self.said(old, new) if "moved" in w]), 1)

    def test_a_removed_part_does_not_make_every_later_part_moved(self):
        old = [sec("band", "a"), sec("hero", "b"), sec("letter", "c"), sec("foot", "d")]
        new = [sec("band", "a"), sec("letter", "c"), sec("foot", "d")]
        self.assertEqual(self.said(old, new), ["Removed: hero (was part 2)"])

    def test_changed_words_are_named(self):
        self.assertEqual(self.said([sec("letter", "Hi there")], [sec("letter", "Hello there")]),
                         ["Part 1 (letter): words changed"])

    def test_a_style_value_is_not_a_word(self):
        """the team's glow colours and positions sit among the fields the page lists as words."""
        old = [sec("specs", "Three facts")]
        new = [sec("specs", "Three facts", glow_bg="#062B14", glow_c="rgba(214,222,196,0.20)", glow_x="12%")]
        self.assertEqual(self.said(old, new), [])

    def test_a_background_picture_path_is_not_a_word(self):
        """brand-a nov-02 gift-buyer's quote gained a stone background: its path is not a change of words."""
        self.assertEqual(self.said([sec("bigquote", "Did not want to spend more")],
                                   [sec("bigquote", "Did not want to spend more", bg="run:media/x-stone.jpg")]), [])

    def test_new_pictures_are_counted(self):
        self.assertEqual(self.said([sec("card", "b", "drive:a.jpg")], [sec("card", "b", "run:media/new.jpg")]),
                         ["Part 1 (card): 1 new picture"])

    def test_subject_change_comes_first(self):
        out = R.changes({"subject": "A", "sections": []}, {"subject": "B", "sections": []})
        self.assertEqual(out[0]["what"], "Subject changed")


class Found(unittest.TestCase):
    """Which version counts as "as the team received it" (PF-20 (before from arrival), the team 2026-10-29): from the moment
    the email reaches her, not only after her Done. A throwaway git repo stands in for the workspace."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()     # /var is a link to /private/var on macOS
        self.addCleanup(shutil.rmtree, str(self.tmp))
        self.addCleanup(setattr, R, "REPO", R.REPO)
        R.REPO = self.tmp
        self.git("init", "-q")
        people = self.tmp / "team" / "people"
        (people / "designer").mkdir(parents=True)
        (people / "designer" / "identity.json").write_text(json.dumps({
            "person": "designer", "key_audience": "designer", "stations": ["email-production", "image-production"],
            "emails": [{"address": "the team@company.com"}]}))
        (people / "pm").mkdir()
        (people / "pm" / "identity.json").write_text(json.dumps({"person": "pm", "emails": []}))
        self.run_dir = self.tmp / "runs" / "email-production" / "fx" / "fx-nov-01"
        (self.run_dir / "design").mkdir(parents=True)
        (self.run_dir / "klaviyo").mkdir()
        self.card({})

    def git(self, *a, who=("the team", "pm-primary@company.com")):
        env = dict(os.environ, GIT_AUTHOR_NAME=who[0], GIT_AUTHOR_EMAIL=who[1],
                   GIT_COMMITTER_NAME=who[0], GIT_COMMITTER_EMAIL=who[1])
        return subprocess.run(["git", *a], cwd=str(self.tmp), env=env, capture_output=True, text=True,
                              check=True).stdout.strip()

    def card(self, c):
        (self.run_dir / "klaviyo" / "card.json").write_text(json.dumps(c))

    def commit(self, text, who=("the team", "pm-primary@company.com")):
        (self.run_dir / "design" / "email.json").write_text(json.dumps({"sections": [{"s": "letter", "text": text}]}))
        self.git("add", "-A", who=who)
        self.git("commit", "-q", "-m", text, who=who)
        return self.git("rev-parse", "--short=10", "HEAD")

    def test_never_committed_has_no_before(self):
        self.assertIsNone(R.found(self.run_dir))

    def test_no_done_and_no_designer_commit_is_the_newest_version_waiting(self):
        self.commit("first")
        newest = self.commit("words fixed")
        f = R.found(self.run_dir)
        self.assertEqual((f["rev"], f["by"], f.get("waiting")), (newest, "the team", True))

    def test_no_done_but_the_designer_committed_is_the_version_before_her_first(self):
        got = self.commit("as sent to the team")
        self.commit("the team's pictures", who=("the team", "the team@company.com"))
        f = R.found(self.run_dir)
        self.assertEqual((f["rev"], f["by"]), (got, "the team"))
        self.assertNotIn("waiting", f)

    def test_the_designer_is_found_by_her_email_too(self):
        got = self.commit("as sent")
        self.commit("by her other git name", who=("designer-laptop", "designer@company.com"))
        self.assertEqual(R.found(self.run_dir)["rev"], got)

    def test_a_done_finds_the_named_designer_as_before(self):
        got = self.commit("as sent")
        self.commit("the team's pictures", who=("the team", "the team@company.com"))
        self.card({"eve_done": {"by": "the team", "at": "2026-10-29T10:00:00+00:00"}})
        f = R.found(self.run_dir)
        self.assertEqual((f["rev"], f["by"]), (got, "the team"))
        self.assertNotIn("waiting", f)

    def test_once_she_commits_a_later_commit_by_someone_else_does_not_move_the_before(self):
        got = self.commit("as sent")
        self.commit("the team's pictures", who=("the team", "the team@company.com"))
        self.commit("the team's final words")
        self.assertEqual(R.found(self.run_dir)["rev"], got)

    def test_an_email_that_went_to_klaviyo_without_her_has_no_before(self):
        """Only emails on her list: a Klaviyo draft or a scheduled send with no Done never reached her."""
        self.commit("as sent")
        for c in ({"klaviyo": {"id": "x"}}, {"scheduled": "2026-10-20T08:00:00"}):
            self.card(c)
            self.assertIsNone(R.found(self.run_dir), c)

    def test_the_waiting_before_is_the_same_version_after_her_first_commit(self):
        """What she received stays what she received: the rev shown while waiting is the rev once she commits."""
        self.commit("first")
        waiting = R.found(self.run_dir)["rev"]
        self.commit("the team's pictures", who=("the team", "the team@company.com"))
        self.assertEqual(R.found(self.run_dir)["rev"], waiting)


if __name__ == "__main__":
    unittest.main()
