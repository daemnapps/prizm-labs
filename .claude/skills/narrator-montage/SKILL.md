---
name: narrator-montage
description: Produce a video ad in the narrator-montage format from an accepted brief. A hook, then one narrator's voiceover over short shots, the proof, the offer and the ask. Use when a brief's format is narrator-montage, or someone says "produce this narrator montage", "run the narrator montage line", "make this brief" for a voiceover-over-footage ad, or "voiceover montage".
---

# Narrator montage

External dependencies: `components/video-production/formats/narrator-montage/` (`FORMAT.md`, `format.json`, `LEARNINGS.md`), `components/video-production/machine/workflow.py`.

This skill is a door. Every rule of the format lives in `components/video-production/formats/narrator-montage/FORMAT.md`; nothing here repeats it.

1. Read `FORMAT.md` start to finish.
2. Run the line one step at a time:
   `python3 components/video-production/machine/workflow.py run narrator-montage --brand <brand> --label <label>`
   Do the step it hands you as `FORMAT.md` says, then run it again for the next one.
3. Stop at every review step. A review is the owner's; never write one.
4. Spend nothing before the plan's total is approved. Each paid step states its price first.
5. At the Learn step, file every lesson in the run's `learned.md` with its one home from the routing table in `LEARNINGS.md`. A home is changed only after the owner says yes.

Done when the workflow reports the launch package ready for review.
