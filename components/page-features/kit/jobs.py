"""PF-13b (slow buttons): background jobs for the page kit — one module, used by kit/serve.py and kit/server.py.

A button whose entry in the family's direct table says "kind": "job" or "confirm-job" does not run while the page
waits: POST /act starts its command in a thread here and answers {job} at once (202); GET /job/<id> answers

    {"job", "item", "n", "state": queued|running|done|failed, "said": the last <= 8 lines, "started", "ended",
     "code": the exit code or null, "ask": the exact request line to paste in Claude}

queued = waiting for the copy's one git writer (the `gate` lock: a quick button or the page server's sync in flight);
running = the command is going. At most ONE job per email (family, item) at a time: a second start while one is
queued or running is Busy, answered 409 "already working on <item>"; another email runs beside it. A job past
`timeout` (20 min) is stopped — its whole process group — and fails with "stopped after 20 min". Jobs live in
memory only; `on_end(job)` (the page server's click log and push) runs once per finished job and may add a line.

The command's temp request file (a note may hold newlines, so it travels in this file, never argv) is deleted when
the job ends. Stdlib only, Python 3.9.
"""
import datetime
import os
import secrets
import signal
import subprocess
import threading
import time

TIMEOUT = 20 * 60
SAID_LINES = 8
KEEP = 200                      # finished jobs remembered for /job; the oldest finished go first


def now_z(t):
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def human(seconds):
    """1200 -> "20 min", 2 -> "2 s"."""
    s = int(seconds)
    return "%d min" % (s // 60) if s >= 60 and s % 60 == 0 else "%d s" % s


class Busy(Exception):
    """An email that already has a job queued or running; answered 409, nothing starts."""

    def __init__(self, item, job):
        Exception.__init__(self, "already working on %s" % item)
        self.item, self.job = item, job


class Job(object):
    def __init__(self, family, item, n, argv, ask, request_file, page=None):
        self.id = secrets.token_hex(8)
        self.family, self.item, self.n, self.argv, self.ask = family, item, n, argv, ask
        self.request_file, self.page = request_file, page
        self.state, self.code, self.lines = "queued", None, []
        self.started, self.ended = None, None
        self.lock = threading.Lock()

    def add(self, text):
        text = text.rstrip("\r\n")
        if text.strip():
            with self.lock:
                self.lines.append(text)
                del self.lines[:-SAID_LINES]

    def said(self):
        with self.lock:
            return "\n".join(self.lines)

    def view(self):
        with self.lock:
            said = "\n".join(self.lines)
        return {"job": self.id, "item": self.item, "n": self.n, "state": self.state,
                "said": said or ("working…" if self.state in ("queued", "running") else ""),
                "started": now_z(self.started) if self.started else None,
                "ended": now_z(self.ended) if self.ended else None, "code": self.code, "ask": self.ask}


class Jobs(object):
    """The kit's jobs. gate: the lock a job takes for a moment before it runs (one git writer at a time); env: the
    commands' environment (the page server's act_env), else this one's."""

    def __init__(self, root, gate=None, env=None, timeout=TIMEOUT, on_end=None, clock=time.time):
        self.root, self.gate, self.env, self.timeout = root, gate, env, timeout
        self.on_end, self.clock = on_end, clock
        self.all, self.lock = {}, threading.Lock()

    def working(self, family, item):
        """The job queued or running on this email, else None."""
        with self.lock:
            for j in self.all.values():
                if (j.family, j.item) == (family, item) and j.state in ("queued", "running"):
                    return j
        return None

    def running(self):
        """How many jobs are queued or running (the page server's sync waits while any are)."""
        with self.lock:
            return sum(1 for j in self.all.values() if j.state in ("queued", "running"))

    def get(self, job_id):
        with self.lock:
            j = self.all.get(job_id)
        return j.view() if j else None

    def start(self, family, item, n, argv, ask, request_file=None, page=None):
        """The new job's view; Busy when this email has one queued or running. Checked and registered in one step,
        so two clicks at once start one job. page: the page that asked (the page server's click line)."""
        with self.lock:
            for j in self.all.values():
                if (j.family, j.item) == (family, item) and j.state in ("queued", "running"):
                    raise Busy(item, j.id)
            job = Job(family, item, n, list(argv), ask, request_file, page)
            self.all[job.id] = job
            done = sorted((j for j in self.all.values() if j.ended), key=lambda j: j.ended)
            for old in done[:max(0, len(self.all) - KEEP)]:
                del self.all[old.id]
        threading.Thread(target=self._run, args=(job,), daemon=True).start()
        return job.view()

    # ------------------------------------------------------------------ the thread
    def _run(self, job):
        try:
            if self.gate is not None:
                with self.gate:                         # wait for a quick button or a sync in flight, then go
                    job.state, job.started = "running", self.clock()
            else:
                job.state, job.started = "running", self.clock()
            job.code = self._exec(job)
        except Exception as e:  # noqa: BLE001 — said on the email, never hidden
            job.add("the kit could not run it: %s" % str(e)[:300])
            job.code = job.code if job.code is not None else -1
        finally:
            if job.request_file:
                try:
                    os.unlink(job.request_file)
                except OSError:
                    pass
        state = "done" if job.code == 0 else "failed"
        if self.on_end:
            try:
                extra = self.on_end(job, state)
                if extra:
                    job.add(extra)
            except Exception as e:  # noqa: BLE001
                job.add("the page server could not record it: %s" % str(e)[:200])
        job.ended = self.clock()
        job.state = state

    def _exec(self, job):
        env = dict(self.env if self.env is not None else os.environ, PYTHONUNBUFFERED="1")
        kw = {"start_new_session": True} if os.name != "nt" else \
            {"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0)}
        p = subprocess.Popen(job.argv, cwd=self.root, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, env=env, universal_newlines=True, encoding="utf-8",
                             errors="replace", **kw)

        def read():
            for line in p.stdout:
                job.add(line)
        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        try:
            code = p.wait(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            self._kill(p)
            code = None
        reader.join(5)
        try:
            p.stdout.close()
        except OSError:
            pass
        if code is None:
            job.add("stopped after %s" % human(self.timeout))
            return 124
        return code

    @staticmethod
    def _kill(p):
        try:
            if os.name != "nt":
                os.killpg(p.pid, signal.SIGKILL)        # the command and everything it started
            else:
                p.kill()
        except OSError:
            pass
        try:
            p.wait(10)
        except subprocess.TimeoutExpired:
            pass
