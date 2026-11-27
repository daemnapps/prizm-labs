#!/usr/bin/env python3
"""Page teardown: any page -> its structure and each section's persuasion job, stripped of the source's words, offer,
brand, people, places and claims; plus the source's identity list, which the writing stage's check tests against.

    python3 teardown.py --brand <brand> --page <page ID> --job new-page|new-control|variant --url <url>
                        [--product <product>] [--source page.txt]
    python3 teardown.py --hypothesis runs/session-teardown/<brand>/<label>/hypothesis.json
                        (the testing loop: a variant of the hypothesis's page, torn down from its control)
    python3 teardown.py --brand <brand> --label <label> --url <url> --resume      (a run already started)

A run starts from its page brief: --page and --job number it in the brief register before anything runs, reserve
the version it builds on the page list and name the run `<place>_<page>_<vN>`.

Writes into runs/page-chain/<brand>/<label>/: source/page.txt, structure--sent.md, structure.md/.json,
identity--sent.md, identity.md/.json, identity-all.json (model list + read off the capture), teardown-check.json
(the structure itself carries none of the source's identity).
"""
import argparse
import datetime
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chain_io as C  # noqa: E402
import identity as I  # noqa: E402
from capture import capture  # noqa: E402

PROMPTS = HERE.parent / "prompts"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", help="the brand (read off the page with --hypothesis)")
    ap.add_argument("--page", help="the page ID this run builds a version of (components/naming/page_list.py)")
    ap.add_argument("--job", choices=C.JOBS, help="new-page, new-control or variant")
    ap.add_argument("--product")
    ap.add_argument("--label", help="an existing run's folder name (with --resume)")
    ap.add_argument("--hypothesis", help="a session-teardown hypothesis.json: a variant of its page, built from "
                                         "the control (the testing loop)")
    ap.add_argument("--url", help="the page to tear down (with --hypothesis: the control, by default)")
    ap.add_argument("--source", help="an already captured page.txt (else the url is captured)")
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args(argv)
    if a.hypothesis:
        label, bid, version, rec = C.open_from_hypothesis(a.hypothesis)
        a.brand = rec["brand"]
        a.url = a.url or C.control_url(rec["page"])
        run = C.Run(a.brand, label)
        run.save(brief=bid, page=rec["page"], version=version, job="variant",
                 hypothesis=rec["hypothesis"]["text"], change=rec["hypothesis"]["change"],
                 hypothesis_file=rec["hypothesis"]["file"])
        print(f"page brief {bid} · {rec['page']} {version} (variant) · run {label}")
    elif not a.brand:
        raise SystemExit("--brand is needed")
    elif a.page:
        if not a.job:
            raise SystemExit("--page needs --job (new-page, new-control or variant)")
        label, bid, version = C.open_page_brief(a.brand, a.page, a.job, a.product)
        run = C.Run(a.brand, label)
        run.save(brief=bid, page=a.page, version=version, job=a.job)
        print(f"page brief {bid} · {a.page} {version} ({a.job}) · run {label}")
    elif a.label and (C.WS / "runs" / "page-chain" / a.brand / a.label / "run.json").is_file():
        run = C.Run(a.brand, a.label)
    else:
        raise SystemExit("a page run starts from its page brief: --page <page ID> --job new-page|new-control|variant, "
                         "or --hypothesis <hypothesis.json> (or --label <existing run> --resume)")
    if not a.url:
        raise SystemExit("--url is needed (the page to tear down)")
    src_dir = run.dir / "source"
    if a.source:
        src_dir.mkdir(exist_ok=True)
        shutil.copy(a.source, src_dir / "page.txt")
    elif not (a.resume and (src_dir / "page.txt").exists()):
        capture(a.url, src_dir)
    page = (src_dir / "page.txt").read_text()
    run.save(source_url=a.url)
    today = datetime.date.today().isoformat()

    structure = run.stage("structure", PROMPTS, dict(source=page, source_url=a.url, today=today), tier="designs",
                          resume=a.resume, order=1, component="page-teardown", title="Teardown · structure")
    ident = run.stage("identity", PROMPTS, dict(source=page, source_url=a.url), tier="checks",
                      resume=a.resume, order=2, component="page-teardown", title="Teardown · the source's identity")
    items = [dict(x, **{"from": "model"}) for x in ident.get("items", [])] + I.from_capture(page)
    (run.dir / "identity-all.json").write_text(json.dumps({"items": items}, indent=1, ensure_ascii=False))

    leak = I.check(json.dumps(structure, ensure_ascii=False), page, items)
    (run.dir / "teardown-check.json").write_text(json.dumps(leak, indent=1, ensure_ascii=False))
    print(f"teardown: {structure.get('format')} · {len(structure.get('sections', []))} sections · "
          f"{len(items)} identity items · structure clean: {'yes' if leak['pass'] else 'NO — ' + str(len(leak['hits'])) + ' hits'}")
    run.save(format=structure.get("format"))
    return run


if __name__ == "__main__":
    try:
        main()
    except C.UsageLimit as e:
        sys.exit(f"STOPPED — {e}\n  run the same command with --resume once usage is back")
