"""A big video goes up in the pieces Meta asks for: start -> transfer each piece -> finish (4 Oct 2026)."""
import sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import meta  # noqa: E402


class Chunked(unittest.TestCase):
    def test_sends_every_piece_then_finishes(self):
        m = meta.Meta.__new__(meta.Meta)
        m._t, m.ACCOUNT = "t", "1"
        data = bytes(range(256)) * 40          # 10,240 bytes
        sent, phases = bytearray(), []

        def fake(url, fields, file=None, timeout=300):
            phases.append(fields["upload_phase"])
            if fields["upload_phase"] == "start":
                return {"upload_session_id": "s", "video_id": "v1", "start_offset": "0", "end_offset": "4000"}
            if fields["upload_phase"] == "transfer":
                self.assertEqual(int(fields["start_offset"]), len(sent))
                sent.extend(file[2])
                a = len(sent)
                return {"start_offset": str(a), "end_offset": str(min(a + 4000, len(data)))}
            return {"success": True}

        m._multipart = fake
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(data)
        self.assertEqual(m._upload_chunked(Path(f.name), "x"), "v1")
        self.assertEqual(bytes(sent), data)
        self.assertEqual(phases, ["start", "transfer", "transfer", "transfer", "finish"])


if __name__ == "__main__":
    unittest.main()
