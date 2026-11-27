# page-writing

**The structure, filled with our brand.** Reads page-teardown's structure (never the source page) and writes a whole
page for the brand and the target topic: headline, subheads, section headings, buttons and every line new.

Where the words come from:
- customer language: raw language-bank rows, each block citing the row IDs whose words it uses; a quote is one row
  word for word. Past winning ads are not a source.
- offer and guarantee: the offer file, word for word; no guarantee the file does not state.
- product facts: the product file. Angle, enemy, mechanism and voice: the brand's position and story files.

The structure's job order and arc stay; its forms may change to fit the format (a roundup of other brands becomes a
roundup we can own), and every change is listed in `adapted`.

    python3 machine/write.py --brand <brand> --label <label> --avatar <avatar> --product <product file> \
        --offer <offer file> --next-url <url> --format "<format>" --topic "<topic>" [--target <topic brief.json>] \
        [--terms <words that pick the bank rows>] [--resume]

| Stage | Prompt | Out |
|---|---|---|
| write | `prompts/write-vN-owner.md` | the page as JSON: sections, blocks, row IDs, picture slots |
| check (per round) | `prompts/check-vN-owner.md` + `page-teardown/machine/identity.py` | survivors of the source: its names, people, places, offers, guarantees, calls to action, nav and footer text, headings, claims, any 8-word run shared with it |
| fix (when a round fails) | `prompts/fix-vN-owner.md` | the page with only the flagged blocks rewritten; up to three rounds |
| bank check | `machine/write.py` | every cited row is a real bank row; every quote is its row word for word |

Out: `page.json`, `identity-result.json`, `bank-check.json` in the run folder. Next: `components/page-production`.

Replaces, once proven, `lab/the owner/pages` stages 3 and 4 (injection and close), whose rules kept the source's
headline, buttons and section headings and restored dropped source lines. The lab version stays until this one is
proven.
