# Run the queue — what a session does when the owner says "run the queue"

**Efficient path first (2026-10-07):** run squares with `machine/proven_to_format.py run <batch> --square <name>` — each stage's prompt read once, each block once, Sonnet for 4a/4f, one square first then small batches. See PROVEN-TO-FORMAT-damon.md, "Running the squares efficiently".

The workflow is **proven ad → new format** (`PROVEN-TO-FORMAT-damon.md`). The old one-step swap (`machine/format_swap.py`) is superseded — do not use it for new squares.

**Rules (the owner, 2026-10-05):** video winner → video format only (no image → video for now). Face scrub runs ONE offer: buy 2, get 1 free. the owner picks the squares; nothing is queued for him. Questions go to him in chat, plainly — the page carries none. Claude stages are written by the session, always — never ask him to sign in.

The Creative Run Builder ((team page)) keeps the squares he activated in its page store: `requests/<winner run>__<format code>` — concept (winner run), format (swipe record), format_id, `target`, product, avatar, offer, batch, `state: "queued"`.

For each queued request:

1. Read it with ArtifactData (`list`, collection `requests`). `python3 machine/proven_to_format.py queue` prints the field list and what each target means.
2. Check both sides: `python3 machine/proven_to_format.py check <batch>`. Anything missing → `prep <batch> --go` (winner to 1b Doctrine, format to 2 Spec). Claude stages stop with `<stage>.prompt.md` in the run's `hand/` folder; write `<stage>.md` beside it and rerun the same command with `--from <that stage>`.
3. Run the square to its `target` (stage names from `tools/video-teardown/machine/chain.py`):
   - `stage2` — **2 Spec**: the format's baseline. Done by step 2.
   - `stage3` — **3 Injection**: the winner's content (script, mechanism, proof, offer logic) + product + offer go INTO the format's 2 Spec. Fill the format's stage-3 prompt with the chain (`run.py <format video> --label <format run label> --from 3 --to 3 --route ai --product <p> --for-avatar <a>` with `DAEMN_HAND_DIR` set — it stops leaving `3-injection.prompt.md`), add the winner slot (`prompts/stage-3-winner-slot/`) with that winner's transcript + 1b Doctrine, save as `runs/ad-variations/<brand>/p2f-<winner>__<code>/sent.md`, and write `3-injection.md` from it in-session.
   - `stage5` — through the **stage 4 loop** (4a Reading · 4b Hooks · 4c Placement · 4d Expansion · 4e Close · 4f Audit · 4g Spice — ask him in chat which parts run) to **5 Brief**, AI lane. The **Viewer Check** (Marketing Chain Checks) runs by itself after the brief; fails go back (opening → 4b, middle → 4c, close → 4e; 2 fails → held). Then 6 Frames → 7 Final brief.
4. Rebuild the page (`python3 machine/proven_to_format.py page <batch>`) and republish over the same URL.
5. Set the request's `state` to `"done"` (pin `if_version`).

Nothing goes to Meta without his go.
