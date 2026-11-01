"""Bounded concurrency — never one worker per job. Lifted from
email-production/run_month.py:25,145-156. A usage limit stops the pool."""
from concurrent.futures import ThreadPoolExecutor, as_completed

from .model import UsageLimit


def run_all(jobs, fn, workers=4, on_done=None):
    """jobs: iterable of (label, payload). fn(label, payload) -> result.
    Returns {label: ("done", result) | ("failed", message) | ("stopped", why)}."""
    results, stop = {}, None
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futs = {ex.submit(fn, label, payload): label for label, payload in jobs}
        for fut in as_completed(futs):
            label = futs[fut]
            try:
                results[label] = ("done", fut.result())
            except UsageLimit as e:
                stop = str(e)
                results[label] = ("stopped", stop)
                for other in futs:
                    other.cancel()
            except Exception as e:                       # noqa: BLE001 — one job failing is a row, not a crash
                results[label] = ("failed", str(e))
            if on_done:
                on_done(label, results[label])
    return results
