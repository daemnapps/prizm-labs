"""A brief the register calls finished is never on a maker's waiting list."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import make as M  # noqa: E402


class FakeDrive(object):
    FOLDER_MIME = "x"

    def service(self):
        return None

    def folder_by_path(self, path, svc=None):
        return path

    def list_files(self, fid, svc=None):
        return []


class WaitingDone(unittest.TestCase):
    def test_finished_briefs_drop_off_and_open_ones_stay(self):
        with tempfile.TemporaryDirectory() as t:
            f = Path(t) / "components" / "image-teardown"
            f.mkdir(parents=True)
            (f / "briefs.json").write_text(json.dumps({"briefs": {
                "acme_w_brief-0001": {"state": "shipped"}, "acme_w_brief-0002": {"state": "for-review"},
                "acme_w_brief-0003": {"state": "superseded"},
                "acme_w_brief-0004": {"state": "for-review"}}}))
            (Path(t) / "runs" / "briefs").mkdir(parents=True)
            (Path(t) / "runs" / "briefs" / "approved.json").write_text(json.dumps({"approved": {
                "acme_w_brief-000%d" % i: {"by": "o", "at": "x", "how": "y"} for i in (1, 2, 3)}}))
            tree = {"Shared Assets/runs/handoffs/video-editor": [{"name": "acme", "id": "acme"}],
                    "acme": [{"name": "acme_w_brief-000%d" % i, "id": "k%d" % i} for i in (1, 2, 3, 4)]
                    + [{"name": "acme_w_idea-9", "id": "k9"}]}
            with mock.patch.object(M, "REPO", Path(t)), mock.patch.object(M, "_drive", lambda: (FakeDrive(), None)), \
                    mock.patch.object(M, "_subfolders", lambda E, svc, p: tree.get(p, [])):
                got = [k for _, _, k in M.waiting("video-editor")]
        self.assertEqual(got, ["acme_w_brief-0002"])      # 0001 and 0003 finished; 0004 not approved; idea-9 an idea

    def test_no_register_hides_nothing(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(M.done_keys(t), set())


if __name__ == "__main__":
    unittest.main()
