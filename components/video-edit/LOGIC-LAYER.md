# The logic layer in the edit (2026-11-18)

What the edit now decides by rule, where the rule lives, and what it carries so the reason travels with the cut.
Nothing here is a new gate.

## The two review points do not wait (ruled 2026-11-18)

The owner ruled: timeline and captions approval sit with the video editor role; the owner steps in only on a trip-wire.

- `machine/run.py start` goes straight through to the finished file. It still writes both pages, each as its own
  file beside the final one: `stop-1-timeline.html`, `stop-2-captions.html`.
- The run's record says so: each stop carries `by: the line` and a note that nobody waited, and `stops_mode` names
  the mode. Nothing is recorded as a person's approval.
- The trip-wires are the checks that already hold a run: a red gate, an audit finding, a final check that holds the
  master. Straight through never means past one of them.
- `--stops` (on `start` and on `handoff`) waits at both, as before; `approve` moves the run on. A run that was
  already waiting at a stop keeps waiting until it is approved.
- `machine/steps.json` names the role (`who: video-editor`) and that nothing waits (`stop: false`).

## Pace and caption look by format

| Setting | Order it is read in | Where |
|---|---|---|
| Pace | a value set for the run, then the format's own row, then the default | `machine/defaults.json` `pace`, read by `machine/looks.py` `pace()` |
| Caption look | the format's own look, then the app the piece seems made in, then the default | `looks/bank.json` `pick`, read by `looks.pick_caption()` |

`pace()` used to read format, default, value: a set value was never reached. The per-format pace list was empty; it
now holds the formats the craft doctrine (`components/video-doctrine` `shapes`) or a format's own playbook speaks to,
each row with its reason and source. Every per-format pace keeps `max_pause` null: no take is cut inside (V15).
A format with no look of its own is not pinned to one, so a piece stays native to the app it seems made in.
`pace_call()` and `caption_call()` give the same answers with who chose and why.

## The hand-off carries the thinking

`maker/maker_pack.py` writes, in `clips.json` and at the end of `BRIEF.md` and `CLIPS.md`: the idea, the angle, the
concept (none until writing names one), who it is for, the openings, the caption look and the pace with their
reasons, how the ad is made with its reason, and the decision trail of every stage before it.

A scene the footage decision passed now reaches the editor as a file: in the AI + Real lane it is kept as made (and
cut here when the Studio has not cut it yet); a scene cut from clips the decision did not pass still goes to the
maker with our cut as a reference. The AI lane and the Real lane are unchanged.

`machine/kit_from_run.py` carries each clip's route and reason (`made_as`, `made_why`), marks a clip cut from our own
footage (`owned`), and carries production's trail rows (`trail`).

## Lessons written by machine

`machine/learn.py` is the declared `learn` step, run last by `run.py start` and `line.py`. It reads the changes made
on an edit since its last lesson, asks the `stage9-learn` prompt, and writes:

- `runs/video-edit/_lessons/lessons.jsonl`: every lesson, with the stage of the line it teaches
- `runs/video-edit/_lessons/learned.json`: the same by stage, rules and observations apart, rebuilt whole each time

No change means no model call. A step that cannot run is said on the run's record and never fails the edit. Nothing
is written inside this component: `learned.json` here stays the rules kept by hand, and the cut reads both
(`learn.for_cut()`). `learn.block(stage)` is the reader for the stages upstream.

## Tests

`tests/test_straight_through.py` · `tests/test_pace_caption_by_format.py` · `tests/test_learn.py` ·
`maker/tests/test_pack_thinking.py` (`/usr/bin/python3 -m unittest <name>`; nothing renders, no network).
