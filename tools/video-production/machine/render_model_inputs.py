#!/usr/bin/env python3
"""
render_model_inputs.py — print `model-inputs.json` as `MODEL-INPUTS.md`.

The contract is data so the machine can act on it; this is the same data as
a page, so a PROMPT can READ it instead of restating it. A prompt binds the
rendered file by path — `{model_inputs}` in its stage vars — the way every
doctrine slice is bound, and nothing about a door is ever written twice.

    python3 machine/render_model_inputs.py            # write MODEL-INPUTS.md
    python3 machine/render_model_inputs.py --check    # exit 1 if it is stale

Never hand-edit `MODEL-INPUTS.md`: it is rendered, and a hand edit is lost
the next time this runs. Change `model-inputs.json`.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "MODEL-INPUTS.md"

_spec = importlib.util.spec_from_file_location("vm_model_inputs_r", HERE / "model_inputs.py")
mi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mi)


def _mark(req) -> str:
    return "**required**" if req is True else ("optional" if req is False else str(req))


def render() -> str:
    c = mi.contract()
    L: list[str] = []
    L.append("# The model input contract")
    L.append("")
    L.append(f"*Rendered from `machine/model-inputs.json` (version {c.get('version')}, "
             f"read {c.get('read')}) by `machine/render_model_inputs.py` — "
             f"never hand-edited.*")
    L.append("")
    L.append("What each settled door actually takes, in the maker's own field names, "
             "with the order it recommends the prompt be assembled in, its limits, and "
             "which of our scene and frame fields fills each field. A prompt binds this "
             "page rather than restating it; the machine builds every request from the "
             "same rows, and the contract gate refuses an item that is missing one.")
    L.append("")
    L.append("## Declared once per piece, never per scene")
    L.append("")
    L.append("| | What it is | House default |")
    L.append("|---|---|---|")
    for name, row in (c.get("piece_fields") or {}).items():
        L.append(f"| **{name}** | {row.get('what', '')} | `{row.get('house_default')}` |")
    L.append("")
    sizes = " · ".join(f"`{k}` → `{v}`" for k, v in (c.get("aspect_to_size") or {}).items())
    L.append(f"Aspect resolves to a still size: {sizes}.")
    L.append("")
    words = " · ".join(f"`{k}` → “{v}”" for k, v in (c.get("aspect_words") or {}).items()
                       if not k.startswith("_"))
    if words:
        L.append(f"And to the framing sentence every FIRST FRAME prompt ends on: {words}.")
        L.append("")

    shape = c.get("clip_prompt") or {}
    if shape:
        L.append("## The clip prompt — the four blocks, shared by both clip stations")
        L.append("")
        for line in shape.get("_readme", []):
            L.append(line)
            L.append("")
        L.append("| Block | How it is written |")
        L.append("|---|---|")
        L.append(f"| 1 · assets | `{shape['assets']['first']}` `{shape['assets']['last']}` "
                 f"`{shape['assets']['audio']}` ({shape['assets'].get('audio_when')}) |")
        L.append(f"| 2 · summary | `{shape['summary']['template']}` — "
                 f"{shape['summary'].get('rule', '')} |")
        L.append(f"| 3 · timeline | `{shape['timeline']['line']}`, "
                 f"first `{shape['timeline']['first_beat']}`, "
                 f"last `{shape['timeline']['last_beat']}`, "
                 f"performance `{shape['timeline']['performance']}` |")
        L.append(f"| 4 · consistency | `{shape['consistency']['take']}` "
                 f"`{shape['consistency']['hold']}` `{shape['consistency']['lip']}` "
                 f"({shape['consistency'].get('lip_when')}) "
                 f"{' '.join(shape['consistency'].get('negatives', []))} |")
        L.append("")
        L.append("Every slot comes from a LABELLED field, and a slot that resolves to "
                 "nothing is refused by name — a block built from a gap is a fragment, "
                 "and a fragment is how a clip ends up being about something else.")
        L.append("")
        L.append("The summary's slots, and where each is read from:")
        L.append("")
        L.append("| Slot | Read from | What it is |")
        L.append("|---|---|---|")
        for slot, row in (shape["summary"].get("slots") or {}).items():
            L.append(f"| `{slot}` | {' → '.join(row.get('from', []))} | {row.get('what', '')} |")
        L.append("")
        L.append("The camera, in one phrase and in one sentence, from the LAST FRAME's "
                 "own Camera word:")
        L.append("")
        L.append("| Camera word | In the summary | In what holds |")
        L.append("|---|---|---|")
        for word, phrase in (shape.get("camera_phrases") or {}).items():
            L.append(f"| `{word}` | {phrase} | {(shape.get('camera_sentences') or {}).get(word, '')} |")
        L.append("")
        L.append(shape.get("camera_target", ""))
        L.append("")
        if shape.get("camera_words"):
            L.append("**The LAST FRAME's Camera is one of exactly these:** "
                     + " · ".join(f"`{w}`" for w in shape["camera_words"]) + ".")
            L.append("")
            L.append(shape.get("camera_words_why", ""))
            L.append("")
        grammar = shape.get("beat_grammar") or {}
        if grammar:
            L.append("### The beat grammar")
            L.append("")
            for line in grammar.get("_readme") or []:
                L.append(line)
                L.append("")
            L.append("Words a beat never opens on — they name the read, not the "
                     "picture: "
                     + ", ".join(f"`{w}`" for w in grammar.get("delivery_verbs") or [])
                     + ". " + grammar.get("delivery_verbs_why", ""))
            L.append("")
            L.append(f"The pause: `{grammar.get('pause_verb')}`. "
                     + grammar.get("pause_why", ""))
            L.append("")
            L.append(grammar.get("insert_why", ""))
            L.append("")

    sch = c.get("brief_schema") or {}
    if sch:
        L.append("## The brief — the json block, which IS the brief")
        L.append("")
        for line in sch.get("_readme") or []:
            L.append(line)
            L.append("")
        L.append("| Object | Every key it carries |")
        L.append("|---|---|")
        for key, label in (("required", "the block itself"), ("piece", "`piece`"),
                            ("cast_item", "each `cast[]`"), ("cast_voice", "a cast member's `voice`"),
                            ("world_item", "each `world[]`"), ("scene", "each `scenes[]`"),
                            ("delivery", "a scene's `delivery`"),
                            ("first_frame", "a scene's `first_frame`"),
                            ("beat", "each `beats[]`"),
                            ("last_frame", "a scene's `last_frame`")):
            if sch.get(key):
                L.append(f"| {label} | " + " · ".join(f"`{k}`" for k in sch[key]) + " |")
        L.append("")
        opt = sch.get("optional") or {}
        if opt:
            L.append("Optional, and never a refusal: "
                     + " · ".join(f"`{k}` on {where}"
                                  for where, keys in opt.items() if isinstance(keys, list)
                                  for k in keys)
                     + ". " + str(opt.get("why", "")))
            L.append("")
        for rule in sch.get("rules") or []:
            L.append(f"- {rule}")
        L.append("")

    for name, st in mi.stations().items():
        L.append(f"## {name} — {st.get('door')}")
        L.append("")
        model = mi.model_of(name)
        if model:
            L.append(f"Model: `{model}` (read from providers.json, never written twice).")
            L.append("")
        L.append(st.get("makes", ""))
        L.append("")
        if st.get("doors"):
            L.append("| Door | Takes the last frame? | As | Note |")
            L.append("|---|---|---|---|")
            for d in st["doors"]:
                L.append(f"| `{d['id']}` | {'yes' if d.get('takes_end_image') else 'no'} | "
                         f"`{d.get('field') or '—'}` | {d.get('note', '')} |")
            L.append("")
            if st.get("end_frame_rule"):
                L.append(st["end_frame_rule"])
                L.append("")
        L.append("| Field | Req? | Values | House default | What fills it |")
        L.append("|---|---|---|---|---|")
        for f in st.get("fields", []):
            L.append(f"| `{f['name']}` | {_mark(f.get('required'))} | {f.get('values', '')} | "
                     f"`{f.get('house_default')}` | {f.get('fills', '')} |")
        L.append("")
        asm = st.get("assembly") or {}
        L.append(f"**Assembly order:** {' → '.join(asm.get('order', []))}")
        L.append("")
        L.append(asm.get("rule", ""))
        L.append("")
        for block, text in (asm.get("blocks") or {}).items():
            L.append(f"- **{block}** — {text}")
        if asm.get("blocks"):
            L.append("")
        limits = st.get("limits") or {}
        if limits:
            L.append("**The maker's limits.**")
            L.append("")
            for k, v in limits.items():
                L.append(f"- `{k}`: {v}")
            L.append("")
        fills = st.get("fills_from_frame") or {}
        if fills:
            L.append("**Our field → its field.**")
            L.append("")
            L.append("| Ours | Where it lands |")
            L.append("|---|---|")
            for k, v in fills.items():
                L.append(f"| {k} | {v} |")
            L.append("")
        docs = sorted({f.get("doc") for f in st.get("fields", []) if f.get("doc")})
        if docs:
            L.append("Read from: " + " · ".join(docs))
            L.append("")
    return "\n".join(L).rstrip() + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if MODEL-INPUTS.md is not what the contract renders to")
    a = ap.parse_args(argv)
    text = render()
    if a.check:
        current = OUT.read_text() if OUT.exists() else ""
        if current != text:
            print(f"{OUT.name} is stale — run: python3 machine/render_model_inputs.py",
                  file=sys.stderr)
            return 1
        print(f"{OUT.name} is current")
        return 0
    OUT.write_text(text)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
