# compare judge — v1 — 2026-09-22

Two pictures are attached. IMAGE 1 is the REFERENCE. IMAGE 2 is the RESULT of
an edit that was asked to change exactly one thing.

The change that was asked for:

> {change}

Answer every test below by looking at both pictures. A test PASSES only if you
can see it is true; if you are not sure, it FAILS. Judge the way a viewer
scrolling past would — a partly hidden hand or a one-pixel shift is not a
change; a different face, a moved element, a re-lettered word or a new colour is.

{tests}

Reply with JSON only, in this shape:

{"results": [{"test": 1, "verdict": "PASS", "evidence": "one line"}, ...]}
