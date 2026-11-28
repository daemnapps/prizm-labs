---
name: ingredient-evidence
description: Pull the published studies on one ingredient for one problem, strongest first, every line linked, so the unique mechanism and the proof come only from studies. Use whenever someone says "pull the evidence for <ingredient>", "what do the studies say about <ingredient> for <problem>", "find the research on <ingredient>", "is there evidence for <ingredient>", or the brand-launch evidence step runs.
---

# Ingredient evidence

> **Activates component:** `components/ingredient-evidence`

1. Run `python3 components/ingredient-evidence/evidence.py search --ingredient "<ingredient>" --problem "<problem words, OR between synonyms>" [--men] --out brands/<brand>/products/<product>/evidence`.
2. Read `EVIDENCE.md`. Report the strongest studies with their numbers, each with its link. Facts and sources only.
3. The mechanism step writes the mechanism from these lines only, each line citing its study.

Never add a claim, number or mechanism that is not in `EVIDENCE.md`.
