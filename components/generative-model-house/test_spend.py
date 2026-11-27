import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spend  # noqa: E402


def row(action, credits, name="Seedance 2.5", at="2026-11-20T10:00:00"):
    return {"action": action, "credits": credits, "display_name": name, "created_at": at}


class Guard(unittest.TestCase):
    def test_above_limit_is_refused(self):
        with mock.patch.dict(os.environ, {"UPRIGHT_SPEND_OK": ""}):
            for r in ("720p", "1080p", "4K"):
                with self.assertRaises(spend.Refused):
                    spend.check("seedance_2_5", {"resolution": r})

    def test_at_limit_unknown_or_unnamed_passes(self):
        spend.check("seedance_2_5", {"resolution": "480p"})
        spend.check("seedance_2_5", {})
        spend.check("kling4_0", {"resolution": "1080p"})

    def test_a_persons_yes_lets_it_through(self):
        with mock.patch.dict(os.environ, {"UPRIGHT_SPEND_OK": "owner: the hero shot"}):
            spend.check("seedance_2_5", {"resolution": "1080p"})

    def test_every_limit_names_a_known_size(self):
        for rule in spend.limits()["jobs"].values():
            self.assertIsNotNone(spend._size(rule["max_resolution"]))


class Door(unittest.TestCase):
    """The chain's clip door stops before anything is sent."""

    def test_the_command_line_door_sends_nothing_above_the_limit(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "video-production" / "machine"))
        import higgsfield_cli as hc
        with mock.patch.dict(os.environ, {"UPRIGHT_SPEND_OK": ""}), mock.patch.object(hc, "_run") as run:
            with self.assertRaisesRegex(RuntimeError, "nothing spent"):
                hc.submit("bytedance/seedance-2.5/image-to-video", {"prompt": "x", "resolution": "1080p"})
            run.assert_not_called()


class NothingMissing(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.d = Path(tempfile.mkdtemp())
        self.pic = self.d / "start.png"
        self.pic.write_bytes(b"picture")
        self.env = mock.patch.dict(os.environ, {"UPRIGHT_SPEND_OK": "", "UPRIGHT_SPEND_LEDGER": str(self.d / "led")})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_a_missing_file_and_words_that_leave_the_product_out_are_refused(self):
        with self.assertRaisesRegex(spend.Refused, "not there"):
            spend.inputs("a man", [self.d / "gone.png"])
        for words in ("his grip left open for the brush", "the tube is laid on at the edit", "a spot reserved for the real box"):
            with self.assertRaisesRegex(spend.Refused, "leave the product out"):
                spend.inputs(words, [self.pic])
        spend.inputs("he holds the brush", [self.pic, "https://x/y.png"])
        spend.inputs("leave the top clear, the headline is laid on in the edit", [self.pic])

    def test_the_same_request_is_paid_for_once_and_a_changed_input_goes_through(self):
        fp = spend.once("gpt", {"prompt": "a"}, [self.pic])
        spend.record("gpt", fp, "job-1", "/x/runs/image-edit/b/l/one.png")
        with self.assertRaisesRegex(spend.Refused, "already paid for"):
            spend.once("gpt", {"prompt": "a"}, [self.pic])
        spend.once("gpt", {"prompt": "b"}, [self.pic])
        self.pic.write_bytes(b"another picture")
        spend.once("gpt", {"prompt": "a"}, [self.pic])
        self.assertEqual(spend.paid(fp)["out"], "runs/image-edit/b/l/one.png")

    def test_a_persons_yes_pays_again(self):
        fp = spend.once("gpt", {"prompt": "a"})
        spend.record("gpt", fp, "job-1", "x.png")
        with mock.patch.dict(os.environ, {"UPRIGHT_SPEND_OK": "owner: again"}):
            spend.once("gpt", {"prompt": "a"})


class Meter(unittest.TestCase):
    def test_refunds_come_off_and_grants_do_not_count(self):
        rep = spend.report([row("spend", -45), row("refund", 45), row("spend", -30), row("grant", 3000, "Auto Top-Up"),
                            row("spend", -480, "Swap")])
        self.assertEqual(rep["credits"], 510)
        self.assertEqual(rep["refill_credits"], 3000)
        self.assertEqual([t["calls"] for t in rep["tools"] if t["tool"] == "Seedance 2.5"], [2])
        self.assertEqual([b["credits"] for b in rep["big"]], [480])

    def test_reads_every_page_until_the_period_ends(self):
        new, old = row("spend", -1), row("spend", -1, at="2026-01-01T00:00:00")
        pages = {0: [new] * 100, 100: [new] * 99 + [old]}
        self.assertEqual(len(spend.read("2026-11-01", page=lambda o: pages[o])), 199)

    def test_a_period_too_long_to_read_is_said_never_undercounted(self):
        with self.assertRaises(RuntimeError):
            spend.read("2026-11-01", page=lambda o: [row("spend", -1)] * 100, most_pages=2)


if __name__ == "__main__":
    unittest.main()
