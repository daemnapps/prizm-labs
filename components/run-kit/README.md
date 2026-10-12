# run-kit

    import sys; sys.path.insert(0, "<repo>/components/run-kit")
    from run_kit import filing
    from run_kit.stage import Chain

    out = filing.run_dir("video-teardown", brand, label)
    chain = Chain("video-teardown", brand, label, out, PROMPTS, STEPS,
                  assignment={...}, dry=args.dry_run, rerun_from=args.rerun_from)
    record = chain.run("stage1", source=text)
    draft  = chain.run("stage2", record=record)
    chain.deliver()                       # the last stage's output → <run>/deliverable/

Every stage is reviewed after it writes (the creative QC loop,
components/quality-checks `review.after_stage`) and the round is filed in
`<run>/qc-log/`; a review never stops the chain. Off: `QC_REVIEW=0`.

`python3 runs.py health|briefs|runs` reads `runs/` and says where every brief is,
and which runs keep one outside `deliverable/`.

When the Claude CLI's login is capped, set `DAEMN_HAND_DIR=<folder>`: each model
call leaves `<label>-<hash>.prompt.md` there and stops; a Claude session writes
the answer as `<label>-<hash>.md` beside it, and the re-run reads it.

`python3 test_run_kit.py` — 21 tests, no network, no model.
