# ingredient-evidence

The published studies on one ingredient for one problem, strongest first, every line linked.

You say "pull the evidence for <ingredient> and <problem>". Claude runs it. You never type a command.

| | |
|---|---|
| **Where it looks** | PubMed, the US National Library of Medicine's public index of studies |
| **What it keeps** | Meta-analyses, systematic reviews, randomised trials and other clinical trials, in that order |
| **What you get** | `evidence.json` and `EVIDENCE.md`: each study's link, year, journal, kind, and its results and conclusion lines, verbatim |
| **Where it goes** | the brand's `products/<product>/evidence/` |

The unique mechanism and the proof points are taken only from these lines, each citing its study.

    python3 components/ingredient-evidence/evidence.py search --ingredient "<ingredient>" --problem "<problem words>" [--men] --out <dir>
    python3 components/ingredient-evidence/evidence.py show <dir>

## Keys this tool needs

None. `NCBI_API_KEY` (optional, free) raises PubMed's rate limit.
