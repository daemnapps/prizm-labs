#!/usr/bin/env python3
"""SI-123 (Drive through engine): the two engine calls its callers now share.

    /usr/bin/python3 components/gdrive-creator/tests/test_update_and_root.py

`update_doc(file_id, html_path, name=None, svc=None)` rewrites a Doc BY ID and
hands back (webViewLink, trashed) — the caller decides what a trashed Doc
means. `shared_drive_id(name, svc=None)` finds a shared drive by its EXACT
name and answers None when it is not there — the caller decides what to say.

Offline, stdlib only, no key: a fake `svc` (the engine's own seam) and a
stand-in `googleapiclient.http`, installed for each test and removed after.
"""
import os
import re
import sys
import tempfile
import types
import unittest
import unittest.mock
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMPONENT = HERE.parent
WS = COMPONENT.parent.parent
sys.path.insert(0, str(COMPONENT))

from gdrive_creator import engine as E   # noqa: E402  imports nothing from Google


class MediaIoBaseUpload(object):
    """What update_doc builds; it keeps what it was given and nothing else."""

    def __init__(self, fd, mimetype=None, resumable=None):
        self.data = fd.read()
        self.mimetype = mimetype
        self.resumable = resumable


def google_stub():
    gac = types.ModuleType("googleapiclient")
    gac.__path__ = []
    http = types.ModuleType("googleapiclient.http")
    http.MediaIoBaseUpload = MediaIoBaseUpload
    gac.http = http
    return {"googleapiclient": gac, "googleapiclient.http": http}


class Exec(object):
    def __init__(self, log, call, result):
        self.log, self.call, self.result = log, call, result

    def execute(self):
        self.log.append(self.call)
        return self.result


class Files(object):
    def __init__(self, d):
        self.d = d

    def update(self, **kw):
        return Exec(self.d.log, dict(kw, op="files.update"),
                    {"id": kw["fileId"],
                     "webViewLink": "https://docs.google.com/document/d/%s/edit" % kw["fileId"],
                     "trashed": self.d.trashed})


class Drives(object):
    def __init__(self, d):
        self.d = d

    def list(self, **kw):
        tok = kw.get("pageToken")
        i = int(tok) if tok else 0
        page = {"drives": list(self.d.pages[i])}
        if i + 1 < len(self.d.pages):
            page["nextPageToken"] = str(i + 1)
        return Exec(self.d.log, dict(kw, op="drives.list"), page)


class Drive(object):
    def __init__(self, trashed=False, pages=None):
        self.log, self.trashed = [], trashed
        self.pages = pages if pages is not None else [[]]

    def files(self):
        return Files(self)

    def drives(self):
        return Drives(self)


class Offline(unittest.TestCase):
    """No key and no Google package in reach: a call that tried to build a
    real client would exit, so every test here proves it used the fake."""

    def setUp(self):
        self.env = unittest.mock.patch.dict(os.environ)
        self.env.start()
        os.environ.pop("GDRIVE_SA_KEY", None)
        self.mods = unittest.mock.patch.dict(sys.modules, google_stub())
        self.mods.start()
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()
        self.mods.stop()
        self.env.stop()


class UpdateDoc(Offline):
    def html(self, body=b"<h1>It's the brief</h1>"):
        p = Path(self.tmp.name) / "brief.html"
        p.write_bytes(body)
        return p

    def test_update_by_id_on_all_drives_returns_link_and_trashed(self):
        fake = Drive()
        link, trashed = E.update_doc("doc-1", self.html(), svc=fake)
        self.assertEqual(link, "https://docs.google.com/document/d/doc-1/edit")
        self.assertIs(trashed, False)
        self.assertEqual(len(fake.log), 1, fake.log)
        call = fake.log[0]
        self.assertEqual(call["op"], "files.update")
        self.assertEqual(call["fileId"], "doc-1")
        self.assertIs(call["supportsAllDrives"], True)
        self.assertEqual(set(call["fields"].split(",")), {"id", "webViewLink", "trashed"})

    def test_the_html_goes_up_as_html_in_one_write(self):
        fake = Drive()
        E.update_doc("doc-1", self.html(b"<p>bytes</p>"), svc=fake)
        media = fake.log[0]["media_body"]
        self.assertEqual(media.data, b"<p>bytes</p>")
        self.assertEqual(media.mimetype, "text/html")
        self.assertIs(media.resumable, False)

    def test_a_trashed_doc_is_reported_not_decided(self):
        fake = Drive(trashed=True)
        link, trashed = E.update_doc("doc-9", self.html(), svc=fake)
        self.assertIs(trashed, True)
        self.assertEqual(link, "https://docs.google.com/document/d/doc-9/edit")
        self.assertEqual([c["op"] for c in fake.log], ["files.update"],
                         "a trashed Doc is neither restored nor re-created here")

    def test_name_given_renames_name_omitted_leaves_the_title(self):
        fake = Drive()
        E.update_doc("doc-1", self.html(), name="One tube, four places", svc=fake)
        E.update_doc("doc-1", self.html(), svc=fake)
        self.assertEqual(fake.log[0]["body"], {"name": "One tube, four places"})
        self.assertNotIn("body", fake.log[1])


class SharedDriveId(Offline):
    def test_exact_name_answers_its_id(self):
        fake = Drive(pages=[[{"id": "d-other", "name": "Archive"},
                             {"id": "d-sa", "name": "Team Drive"}]])
        self.assertEqual(E.shared_drive_id("Team Drive", svc=fake), "d-sa")
        self.assertEqual(fake.log[0]["op"], "drives.list")

    def test_near_names_do_not_match(self):
        fake = Drive(pages=[[{"id": "d1", "name": "team drive"},
                             {"id": "d2", "name": "Team Drive (old)"},
                             {"id": "d3", "name": " Team Drive"},
                             {"id": "d4", "name": "Shared"}]])
        self.assertIsNone(E.shared_drive_id("Team Drive", svc=fake))

    def test_absent_is_none_not_an_exit(self):
        self.assertIsNone(E.shared_drive_id("Team Drive", svc=Drive(pages=[[]])))

    def test_the_first_exact_match_wins(self):
        fake = Drive(pages=[[{"id": "d-first", "name": "Team Drive"},
                             {"id": "d-second", "name": "Team Drive"}]])
        self.assertEqual(E.shared_drive_id("Team Drive", svc=fake), "d-first")

    def test_a_later_page_is_read(self):
        fake = Drive(pages=[[{"id": "d1", "name": "Archive"}],
                            [{"id": "d-sa", "name": "Team Drive"}]])
        self.assertEqual(E.shared_drive_id("Team Drive", svc=fake), "d-sa")
        self.assertEqual(len(fake.log), 2)
        self.assertEqual(fake.log[1].get("pageToken"), "1")


class Callers(unittest.TestCase):
    """The two callers outside image-teardown use the engine, not the raw API."""

    def test_video_teardown_updates_its_doc_through_the_engine(self):
        src = (WS / "tools/video-teardown/machine/run.py").read_text()
        m = re.search(r"\ndef update_doc\(.*?(?=\ndef )", src, re.S)
        self.assertTrue(m, "run.py update_doc not found")
        body = m.group(0)
        self.assertIn("_engine.update_doc(", body)
        self.assertNotIn("googleapiclient", body)
        self.assertNotIn("files().update", body)
        self.assertIn("in the trash", body, "the caller keeps its own trashed message")

    def test_ad_handoff_finds_the_drive_through_the_engine(self):
        src = (WS / "components/ad-handoff/handoff.py").read_text()
        self.assertIsNone(re.search(r"drives\(\)\s*\.\s*list", src))
        self.assertIn("engine.shared_drive_id(", src)


if __name__ == "__main__":
    print("python %s" % (sys.version_info[:2],))
    r = unittest.main(exit=False, verbosity=2).result
    print("\n%d/%d passed on python %s" % (
        r.testsRun - len(r.failures) - len(r.errors), r.testsRun,
        sys.version_info[:2]))
    sys.exit(0 if r.wasSuccessful() else 1)
