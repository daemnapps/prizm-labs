#!/usr/bin/env python3
"""PF-16 (fixed port): one permanent page-server port per person, from team/people/<person>/identity.json; a held port
is refused with its holder named; no fallback, ever.

    python3 components/page-features/kit/test_pf16_fixed_port.py

PF-14 (page server)'s fixture (imported from test_pf14_page_server): launchctl goes to its recorder, git runs for
real on temp folders, tess's record port is a free one outside 8740–8749. The holder is a socket this test listens
on, named by the real lsof; the Windows holder is read from recorded netstat and tasklist output.

PF-16b (Windows port check): the Windows check runs on a fake netstat/tasklist runner with every connect made to time
out, as a connect to a closed loopback port does on Windows; the macOS cases above it are unchanged.
"""
import contextlib
import io
import json
import os
import socket
import sys
import tempfile
import shutil
import unittest
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import server  # noqa: E402
import test_pf14_page_server as pf14  # noqa: E402  the fixture's helpers only; its tests run in their own file

PERSON, PORT = pf14.PERSON, pf14.PORT
REAL = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CARD = {"developer": 8740, "designer": 8741, "email_lead": 8742, "editor": 8743, "owner": 8744, "creator": 8745, "victoria": 8746}
OLD = 8766                                                # an address from the old 8765–8799 range


@contextlib.contextmanager
def holding(port, addr="127.0.0.1"):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((addr, port))
        s.listen(16)
        yield s
    finally:
        s.close()


class FixedPortTest(unittest.TestCase):
    setUp, tearDown, main, on = (pf14.PageServerTest.setUp, pf14.PageServerTest.tearDown,
                                 pf14.PageServerTest.main, pf14.PageServerTest.on)

    def cfg(self):
        return json.loads((self.state / "config.json").read_text())

    def record(self, doc):
        pf14.write(self.clone, "team/people/%s/identity.json" % PERSON, json.dumps(doc))

    def bootstraps(self):
        return [c for c in self.rec.made("launchctl") if c[1] == "bootstrap"]

    # ------------------------------------------------------------------ (a) the port is the record's
    def test_a_the_port_comes_from_the_identity_record(self):
        self.assertEqual(server.record_port(self.clone, PERSON), (PORT, None))
        out = self.on()
        self.assertEqual(self.cfg()["port"], PORT)
        self.assertIn("on: tess's pages at http://127.0.0.1:%d/" % PORT, out)
        self.assertIn("your address is http://localhost:%d/ — fixed, the same on every machine" % PORT, out)
        self.assertFalse(hasattr(server, "PORTS"), "no range to fall back on")

    def test_a_a_record_without_a_port_is_refused_by_name(self):
        for doc, said in (({"emails": [{"address": pf14.EMAIL}]}, "has no page_server_port"),
                          ({"emails": [{"address": pf14.EMAIL}], "page_server_port": "8740"},
                           "has no page_server_port it can use ('8740')")):
            self.record(doc)
            code, out = self.main("on", "--no-open")
            self.assertEqual(code, 2, out)
            self.assertIn("refused: tess has no page-server address — team/people/tess/identity.json %s" % said, out)
            self.assertIn("ask the lead to add page_server_port to your record", out)
            self.assertFalse(self.plist.exists())
            self.assertFalse(self.state.exists(), "nothing made for a person with no address")
            self.assertEqual(self.bootstraps(), [])

    # ------------------------------------------------------------------ (b) held: refused, holder named, no fallback
    def test_b_a_held_port_refuses_naming_the_holder_and_binds_nothing_else(self):
        with holding(PORT):
            code, out = self.main("on", "--no-open")
        self.assertEqual(code, 2, out)
        self.assertIn("refused: port %d — tess's fixed address (team/people/tess/identity.json) — is held by pid %d: "
                      % (PORT, os.getpid()), out)
        self.assertIn("python", out.lower(), "the holder's command, from ps")
        self.assertIn("Stop it, or ask the lead for a per-person override", out)
        self.assertIn("the page server never takes another port", out)
        self.assertFalse((self.state / "config.json").exists(), "no address recorded")
        self.assertFalse(self.plist.exists())
        self.assertEqual(self.bootstraps(), [], "nothing started, on this port or any other")
        self.assertFalse((self.copy / ".git").exists(), "refused before the private copy is made")

    def test_b_a_holder_on_every_address_is_held_too(self):
        with holding(PORT, "0.0.0.0"):
            self.assertFalse(server.port_free(PORT))
            code, out = self.main("on", "--no-open")
        self.assertEqual(code, 2, out)
        self.assertIn("is held by pid %d" % os.getpid(), out)

    def test_b_run_refuses_a_held_record_port_whatever_config_says(self):
        state = Path(tempfile.mkdtemp(prefix="pf16-run-"))
        self.addCleanup(shutil.rmtree, str(state), True)
        pf14.write(state, "config.json", json.dumps({"person": PERSON, "port": OLD}))
        pf14.write(state / "repo", "team/people/tess/identity.json", json.dumps({"page_server_port": PORT}))
        out = io.StringIO()
        with holding(PORT), contextlib.redirect_stdout(out):
            code = server.cmd_run(str(state))
        self.assertEqual(code, 2, out.getvalue())
        self.assertIn("refused: port %d — tess's fixed address" % PORT, out.getvalue())
        self.assertIn("pid %d" % os.getpid(), out.getvalue())
        self.assertNotIn(":%d" % OLD, out.getvalue(), "config.json's old port is never tried")
        pf14.write(state / "repo", "team/people/tess/identity.json", json.dumps({}))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = server.cmd_run(str(state))
        self.assertEqual(code, 2, out.getvalue())
        self.assertIn("refused: tess has no page-server address", out.getvalue())

    def test_b_an_unreadable_holder_is_said_as_such(self):
        none = lambda argv: (1, "")                       # noqa: E731
        self.assertEqual(server.holder(PORT, "darwin", none)[0], None)
        line = server.held(PERSON, PORT, "darwin", none)
        self.assertIn("is held by a process this machine would not name (lsof named no listener", line)
        self.assertIn("Stop it, or ask the lead for a per-person override", line)

    def test_b_the_windows_holder_from_netstat_and_tasklist(self):
        calls = []

        def win(argv):
            calls.append(argv)
            if argv[0] == "netstat":
                return 0, ("\r\nActive Connections\r\n\r\n  Proto  Local Address          Foreign Address        State"
                           "           PID\r\n  TCP    0.0.0.0:135            0.0.0.0:0              LISTENING       9"
                           "\r\n  TCP    127.0.0.1:%d         127.0.0.1:50000        ESTABLISHED     7\r\n"
                           "  TCP    127.0.0.1:%d         0.0.0.0:0              LISTENING       4242\r\n"
                           % (PORT, PORT))
            if argv[0] == "tasklist":
                return 0, '"python.exe","4242","Console","1","25,000 K"\r\n'
            raise AssertionError(argv)
        self.assertEqual(server.holder(PORT, "win32", win), (4242, "python.exe"))
        self.assertEqual(calls, [["netstat", "-ano", "-p", "TCP"],
                                 ["tasklist", "/FI", "PID eq 4242", "/FO", "CSV", "/NH"]])
        line = server.held(PERSON, PORT, "win32", lambda argv: (0, "  TCP  0.0.0.0:135  0.0.0.0:0  LISTENING  9\r\n"))
        self.assertIn("would not name (netstat -ano named no listener", line)

    # ------------------------------------------------------------------ (c) restart keeps it; an old port moves
    def test_c_restart_keeps_the_same_port(self):
        self.on()
        code, out = self.main("restart", "--no-open")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.cfg()["port"], PORT)
        self.assertIn("http://127.0.0.1:%d/" % PORT, out)
        self.assertNotIn("your address is", out, "said once, when the address moved; a restart moves nothing")
        self.assertEqual(len(self.bootstraps()), 2)

    def test_c_an_old_saved_port_is_ignored_and_the_move_is_announced(self):
        self.state.mkdir(parents=True)
        pf14.write(self.state, "config.json", json.dumps({"person": PERSON, "repo": str(self.clone), "port": OLD}))
        out = self.on()
        self.assertEqual(self.cfg()["port"], PORT)
        self.assertIn("your address is now http://localhost:%d/ (was :%d)" % (PORT, OLD), out)
        self.assertEqual(out.count("your address is"), 1)
        out = self.on()
        self.assertIn("already on", out)
        self.assertNotIn("your address is", out, "told once")

    def test_c_a_running_server_on_an_old_port_is_moved_by_on(self):
        self.on()
        cfg = dict(self.cfg(), port=OLD)                  # as a server PF-14 started at 8766 left it
        pf14.write(self.state, "config.json", json.dumps(cfg))
        code, out = self.main("on", "--no-open")
        self.assertEqual(code, 0, out)
        self.assertIn("moving: your page server was started on :%d" % OLD, out)
        self.assertIn("your address is now http://localhost:%d/ (was :%d)" % (PORT, OLD), out)
        self.assertEqual([c[1] for c in self.rec.made("launchctl") if c[1] != "print"][-3:],
                         ["bootstrap", "bootout", "bootstrap"])
        self.assertEqual(self.cfg()["port"], PORT)

    def test_c_a_move_to_a_held_port_leaves_the_old_server_running(self):
        self.on()
        pf14.write(self.state, "config.json", json.dumps(dict(self.cfg(), port=OLD)))
        with holding(PORT):
            code, out = self.main("on", "--no-open")
        self.assertEqual(code, 2, out)
        self.assertIn("is held by pid %d" % os.getpid(), out)
        self.assertNotIn("bootout", [c[1] for c in self.rec.made("launchctl")], "the old address still works")
        self.assertEqual(self.cfg()["port"], OLD)

    # ------------------------------------------------------------------ (d) status and the index say so
    def test_d_status_shows_the_fixed_port_and_a_disagreement(self):
        self.on()
        code, out = self.main("status")
        self.assertEqual(code, 0, out)
        self.assertIn("address: http://localhost:%d/ (fixed, team/people/tess/identity.json)" % PORT, out)
        self.record({"emails": [{"address": pf14.EMAIL}], "page_server_port": PORT + 1})
        code, out = self.main("status")
        self.assertEqual(code, 0, out)
        self.assertIn("address: your record says http://localhost:%d/ (team/people/tess/identity.json) but the server "
                      "was started on :%d — say 'restart my page server' to move it" % (PORT + 1, PORT), out)
        self.record({"emails": [{"address": pf14.EMAIL}]})
        code, out = self.main("status")
        self.assertIn("refused: tess has no page-server address", out)

    def test_d_the_index_shows_the_address_and_a_record_that_moved(self):
        self.on()
        srv = server.PageServer(self.state, self.copy, PERSON, port=PORT)
        self.assertIn("your address: http://localhost:%d/" % PORT, srv.status_line())
        self.assertNotIn("your record now says", srv.status_line())
        self.assertEqual(srv.info()["port"], PORT)
        srv = server.PageServer(self.state, self.copy, PERSON, port=OLD)
        self.assertIn("your address: http://localhost:%d/ — your record now says :%d; say 'restart my page server' "
                      "to move there" % (OLD, PORT), srv.status_line())
        self.assertNotIn("your address", server.PageServer(self.state, self.copy, PERSON).status_line(),
                         "a server built without a port (tests) says nothing about one")

    # ------------------------------------------------------------------ (e) the seven real records, at HEAD
    def test_e_the_seven_real_records_each_carry_a_distinct_port_in_8740_8749(self):
        got = {}
        for f in sorted(Path(REAL, "team", "people").glob("*/identity.json")):
            port, why = server.record_port(REAL, f.parent.name)
            self.assertIsNotNone(port, why)
            self.assertIn(port, range(8740, 8750), f)
            got[f.parent.name] = port
        self.assertEqual(got, CARD, "the card's ports, one per person")
        self.assertEqual(len(set(got.values())), len(got), "distinct")


HEAD = "\r\nActive Connections\r\n\r\n  Proto  Local Address          Foreign Address        State           PID\r\n"
SMB = "  TCP    192.168.1.212:65356    192.168.1.169:445      ESTABLISHED     4\r\n"   # the Legion's last line


def row(local, state="LISTENING", pid=4242, foreign="0.0.0.0:0"):
    return "  TCP    %-22s %-22s %-15s %d\r\n" % (local, foreign, state, pid)


class Netstat(object):
    """netstat -ano -p TCP / TCPv6 answered from two tables, tasklist naming pid 4242; every argv recorded."""

    def __init__(self, v4="", v6="", code=0):
        self.tables, self.code, self.calls = {"TCP": HEAD + v4 + SMB, "TCPv6": HEAD + v6}, code, []

    def __call__(self, argv):
        self.calls.append(list(argv))
        if argv[:3] == ["netstat", "-ano", "-p"]:
            return (self.code, self.tables[argv[3]]) if self.code == 0 else (self.code, "netstat: access denied\r\n")
        if argv[0] == "tasklist":
            return 0, '"python.exe","4242","Console","1","25,000 K"\r\n'
        raise AssertionError(argv)


class WindowsPortTest(unittest.TestCase):
    """PF-16b (Windows port check): "held" on Windows is the listener table, never a connect probe."""

    def setUp(self):
        # On Windows a connect to a closed loopback port retries ~2 s, so the 0.5 s probe always times out.
        p = mock.patch.object(socket.socket, "connect", side_effect=socket.timeout("timed out"))
        p.start()
        self.addCleanup(p.stop)

    def test_the_timing_out_connect_is_what_called_every_free_port_held(self):
        self.assertTrue(server.listening(PORT, "darwin"), "the probe's reading, which Windows must not use")
        self.assertFalse(server.port_free(PORT, "darwin"))

    def test_a_free_port_with_no_listening_row_is_free(self):
        net = Netstat(row("0.0.0.0:135", pid=9))
        self.assertFalse(server.listening(PORT, "win32", net))
        self.assertTrue(server.port_free(PORT, "win32", net))
        self.assertEqual([c for c in net.calls if c[0] == "netstat"],
                         [["netstat", "-ano", "-p", "TCP"], ["netstat", "-ano", "-p", "TCPv6"]] * 2)

    def test_a_listening_row_on_every_address_is_held_and_named_through_tasklist(self):
        for net in (Netstat(row("0.0.0.0:%d" % PORT)), Netstat(row("127.0.0.1:%d" % PORT)),
                    Netstat(v6=row("[::]:%d" % PORT, foreign="[::]:0")), Netstat(v6=row("[::1]:%d" % PORT,
                                                                                       foreign="[::]:0"))):
            self.assertTrue(server.listening(PORT, "win32", net), net.tables)
            self.assertFalse(server.port_free(PORT, "win32", net))
            self.assertEqual(server.holder(PORT, "win32", net), (4242, "python.exe"))
            self.assertIn(["tasklist", "/FI", "PID eq 4242", "/FO", "CSV", "/NH"], net.calls)
            line = server.held(PERSON, PORT, "win32", net)
            self.assertIn("is held by pid 4242: python.exe", line)

    def test_an_established_row_or_a_longer_port_is_not_a_match(self):
        net = Netstat(row("127.0.0.1:%d" % PORT, "ESTABLISHED", 7, "127.0.0.1:50000") +
                      row("0.0.0.0:%d0" % PORT) + row("0.0.0.0:1%d" % PORT) + row("192.168.1.212:%d" % PORT),
                      row("[::]:%d0" % PORT, foreign="[::]:0") + row("[::]:1%d" % PORT, foreign="[::]:0"))
        self.assertFalse(server.listening(PORT, "win32", net))
        self.assertTrue(server.port_free(PORT, "win32", net))
        self.assertEqual(server.holder(PORT, "win32", net)[0], None)
        self.assertNotIn("tasklist", [c[0] for c in net.calls], "no pid, nothing to name")

    def test_no_listener_found_quotes_nothing(self):
        net = Netstat(row("127.0.0.1:%d" % PORT, "ESTABLISHED", 7, "127.0.0.1:50000") + row("0.0.0.0:1%d" % PORT))
        self.assertEqual(server.holder(PORT, "win32", net),
                         (None, "netstat -ano named no listener on port %d: no listener found" % PORT))
        line = server.held(PERSON, PORT, "win32", net)
        self.assertIn("is held by a process this machine would not name (netstat -ano named no listener on port %d: "
                      "no listener found)" % PORT, line)
        for quoted in ("TCP", "ESTABLISHED", "LISTENING", "192.168.1.", "1%d" % PORT, "50000", "445"):
            self.assertNotIn(quoted, line)

    def test_a_netstat_that_cannot_be_read_is_held_and_says_why(self):
        net = Netstat(code=1)
        self.assertTrue(server.listening(PORT, "win32", net), "never called free unread")
        self.assertFalse(server.port_free(PORT, "win32", net))
        self.assertEqual(server.holder(PORT, "win32", net),
                         (None, "netstat -ano -p TCP failed (netstat: access denied)"))

    def test_printed_lines_survive_a_cp1252_console(self):
        raw = io.BytesIO()
        out = io.TextIOWrapper(raw, encoding="cp1252", errors="strict", write_through=True)
        server.utf8_console("win32", [out])
        out.write("port %d — tess's fixed address → 中\n" % PORT)
        self.assertEqual(raw.getvalue().decode("utf-8"), "port %d — tess's fixed address → 中\n" % PORT)
        mac = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
        server.utf8_console("darwin", [mac])
        self.assertEqual(mac.encoding, "cp1252", "macOS: nothing changes")
        server.utf8_console("win32", [io.StringIO(), None])   # no reconfigure, no stream: left alone


if __name__ == "__main__":
    unittest.main()
