"""own_picture reads a picture's https link (a Higgsfield result) as well as a file or a Drive link (the team,
2026-10-22). No network: the link is answered by a fake opener.

    /usr/bin/python3 test_own_picture_link.py
"""
import importlib.util
import io
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("own_picture", os.path.join(HERE, "own_picture.py"))
OP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(OP)


def png():
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (30, 20), "orange").save(b, "PNG")
    return b.getvalue()


class Answer(io.BytesIO):
    def __init__(self, data, kind):
        super().__init__(data)
        self.headers = {"Content-Type": kind}


class FromLink(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.asked = []

    def opener(self, data, kind):
        def o(req, timeout=None):
            self.asked.append(req.full_url)
            return Answer(data, kind)
        return o

    def test_a_picture_link_lands_as_a_file_the_jpeg_step_reads(self):
        f = OP.from_link("https://cdn.example.test/u/abc/result.png?sig=1", self.tmp, self.opener(png(), "image/png"))
        self.assertEqual(f.suffix, ".png")
        self.assertEqual(OP.as_jpeg(f, os.path.join(self.tmp, "out.jpg")), (30, 20))
        self.assertEqual(self.asked, ["https://cdn.example.test/u/abc/result.png?sig=1"])

    def test_a_web_page_is_refused_by_name(self):
        with self.assertRaises(SystemExit) as c:
            OP.from_link("https://higgsfield.example.test/asset/1", self.tmp, self.opener(b"<html>", "text/html"))
        self.assertIn("not a picture", str(c.exception))

    def test_plain_http_is_refused_before_any_read(self):
        with self.assertRaises(SystemExit):
            OP.from_link("http://cdn.example.test/a.png", self.tmp, self.opener(png(), "image/png"))
        self.assertEqual(self.asked, [])

    def test_too_big_is_refused(self):
        big = OP.MAX_LINK_BYTES
        try:
            OP.MAX_LINK_BYTES = 10
            with self.assertRaises(SystemExit) as c:
                OP.from_link("https://cdn.example.test/a.png", self.tmp, self.opener(png(), "image/png"))
            self.assertIn("over 60 MB", str(c.exception))
        finally:
            OP.MAX_LINK_BYTES = big

    def test_fetch_sends_https_links_here_and_drive_links_to_the_drive(self):
        seen = []
        real = OP.from_link
        OP.from_link = lambda url, tmp, opener=None: seen.append(url) or "ok"
        try:
            self.assertEqual(OP.fetch("https://cdn.example.test/r.png", self.tmp), "ok")
            self.assertEqual(OP.drive_id("https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrStUvWxYz012345/view"),
                             "1AbCdEfGhIjKlMnOpQrStUvWxYz012345")
        finally:
            OP.from_link = real
        self.assertEqual(seen, ["https://cdn.example.test/r.png"])


if __name__ == "__main__":
    unittest.main()
