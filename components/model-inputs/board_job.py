"""ONE BOARD JOB, IN ITS OWN PROCESS (2026-10-28).

The board (prompt_bench.py, served by the Picture Bench) only starts jobs and shows them. Every job that makes, keeps
or remakes something runs here instead: a separate process that outlives the board, so a restart of the board never
kills a picture, a clip or an upscale half way. The job's state is its status file, runs/prompt-bench/jobs/<id>.json,
which this process writes when it ends and the board reads.

    python3 board_job.py <status file> <function> '<json args>'
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def main(argv) -> int:
    status, fn, args = Path(argv[0]), argv[1], json.loads(argv[2])
    jid = status.stem
    rec = json.loads(status.read_text()) if status.is_file() else {}
    try:
        import prompt_bench as pb
        pb.fresh()
        pb.JOBS[jid] = {"state": "running", "started": rec.get("started") or time.time()}
        got = getattr(pb, fn)(jid, *args)
        j = dict(pb.JOBS.get(jid) or {})
        if isinstance(got, dict):
            j.update(got)
        if j.get("state") in (None, "running"):
            j["state"] = "done"
    except BaseException as e:                              # noqa: BLE001  (a refusal is a SystemExit in the chain's door)
        j = {"state": "failed", "error": str(e)[:600]}
    status.write_text(json.dumps({**rec, **j, "ended": time.time()}, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
