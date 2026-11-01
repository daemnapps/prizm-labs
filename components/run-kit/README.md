# run-kit

## How to use it → https://dashboard.the company.com/atlas#c-components-run-kit

    import sys; sys.path.insert(0, "<repo>/components/run-kit")
    from run_kit import filing
    from run_kit.stage import Chain

    out = filing.run_dir("video-teardown", brand, label)
    chain = Chain("video-teardown", brand, label, out, PROMPTS, STEPS,
                  assignment={...}, dry=args.dry_run, rerun_from=args.rerun_from)
    record = chain.run("stage1", source=text)
    draft  = chain.run("stage2", record=record)

`python3 test_run_kit.py` — 12 tests, no network, no model. See CLAUDE.md.
