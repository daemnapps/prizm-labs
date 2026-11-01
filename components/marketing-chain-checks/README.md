# marketing-chain-checks

(Renamed from `quality-checks`, 2026-10-02. Not `qc-checks`, the team's engine.)

## How to use it → https://dashboard.the company.com/atlas#c-components-marketing-chain-checks

    import marketing_chain_checks as Q
    problems  = Q.price_check(text, Q.offer_block(bank_text, offer), offer)
    problems += Q.unfilled_check(text)
    problems += Q.read_check_block(check_step_output)
    Q.hold("copy", problems, run_dir)        # writes check.json; raises Q.Held if anything failed

`python3 test_marketing_chain_checks.py` and four more test files, 68 tests in all. See CLAUDE.md.
