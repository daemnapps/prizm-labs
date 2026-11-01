"""The uploader moves like a person (pace.py, the owner 21 Oct 2026): busy waits and tries again, the hour has a budget."""
import io, json, os, sys, tempfile, time, unittest, urllib.error
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pace  # noqa: E402


def http_error(code, body=""):
    return urllib.error.HTTPError("https://graph-video.facebook.com/x", code, "x", {}, io.BytesIO(body.encode()))


class Busy(unittest.TestCase):
    def test_a_503_waits_then_succeeds(self):
        calls = []

        def send():
            calls.append(1)
            if len(calls) < 3:
                raise http_error(503, "<html>Facebook | Error</html>")
            return {"id": "v1"}
        with mock.patch.object(pace, "off", return_value=False), mock.patch.object(pace.time, "sleep") as sl:
            self.assertEqual(pace.with_retry(send, "the transfer step"), {"id": "v1"})
        self.assertEqual(len(calls), 3)
        self.assertEqual(sl.call_count, 2)
        self.assertGreaterEqual(sl.call_args_list[0][0][0], 45 * 0.75)

    def test_meta_slow_down_code_is_busy(self):
        self.assertTrue(pace.is_busy(400, json.dumps({"error": {"code": 17, "message": "User request limit reached"}})))
        self.assertTrue(pace.is_busy(400, json.dumps({"error": {"code": 999, "is_transient": True}})))

    def test_a_real_mistake_is_not_retried(self):
        calls = []

        def send():
            calls.append(1)
            raise http_error(400, json.dumps({"error": {"code": 100, "message": "Invalid parameter"}}))
        with mock.patch.object(pace, "off", return_value=False), mock.patch.object(pace.time, "sleep") as sl:
            with self.assertRaises(SystemExit) as e:
                pace.with_retry(send, "a call")
        self.assertEqual(len(calls), 1)
        sl.assert_not_called()
        self.assertIn("Invalid parameter", str(e.exception))

    def test_busy_through_every_wait_stops_and_says_it_resumes(self):
        def send():
            raise http_error(503, "busy")
        with mock.patch.object(pace, "off", return_value=False), mock.patch.object(pace.time, "sleep"):
            with self.assertRaises(SystemExit) as e:
                pace.with_retry(send, "a call")
        self.assertIn("resumes", str(e.exception))


class Budget(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.p = mock.patch.object(pace, "_log_file", lambda brand: Path(self.d) / f"{brand}.jsonl")
        self.p.start()
        self.off = mock.patch.object(pace, "off", return_value=False)
        self.off.start()

    def tearDown(self):
        self.p.stop(); self.off.stop()

    def test_under_budget_goes_now(self):
        self.assertEqual(pace.budget_wait("b", 100_000_000), 0)

    def test_over_budget_waits_for_the_hour_to_free(self):
        now = time.time()
        f = Path(self.d) / "b.jsonl"
        f.write_text("".join(json.dumps({"t": now - 600 + i, "bytes": 300_000_000}) + "\n" for i in range(4)))
        w = pace.budget_wait("b", 140_000_000, now=now)
        self.assertGreater(w, 2900)          # the oldest send leaves the window ~50 min from now
        self.assertLess(w, 3100)

    def test_card_markers_do_not_count_as_videos(self):
        for i in range(10):
            pace.card_done("b", f"ad-{i}")
        self.assertEqual(pace.budget_wait("b", 1000), 0)


class Off(unittest.TestCase):
    def test_off_never_sleeps(self):
        with mock.patch.dict(os.environ, {"META_PACE": "off"}), mock.patch.object(pace.time, "sleep") as sl:
            pace.between_videos(); pace.between_chunks(); pace.before_video("b", 10 ** 12)
        sl.assert_not_called()


if __name__ == "__main__":
    unittest.main()
