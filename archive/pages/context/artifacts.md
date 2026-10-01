# Artifacts — the page machine

| Subject | Artifact | URL | Mirror |
|---|---|---|---|
| The page machine's board — every run, every stage's prompt as sent and what came back | The Page Machine | https://claude.ai/code/artifact/8a517107-6a66-46ea-a8c1-eefffb2ee0dd | `runs/<label>/`, `docs/the-chain.md`; source `pages/board.html` (built by `machine/board.py`) |

Republish over that link after every run: `python3 machine/board.py`, then
publish `pages/board.html` to the URL above.
| The refinement log — every issue a run hit, at which stage, what it cost, the fix, whether it landed. Opened 2026-09-17 on the face-scrub CPK run. | Page Machine Refinements | https://claude.ai/artifact/97WSYATYm9zT9rEyY13o49 | `docs/refinements.md` (the team edits this); source `pages/refinements.html` (built by `machine/refinements.py`) |

Republish the refinement log over its link after every change to the log:
`python3 machine/refinements.py`, then publish `pages/refinements.html`.

