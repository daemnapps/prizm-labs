#!/usr/bin/env python3
"""Fan a batch of image-concept prompts out to a generator and collect the results.

RETIRED 2026-09-13. This ran on fal; fal is not a generation path any more.

Damon, 2026-09-11, restated 2026-09-13: *"ensure fal is removed from the
workflow right now."* Pictures are made on Higgsfield and nowhere else — it is
the only place holding the roster identities and the product built from real
turntable angles, and a picture is only as good as its references.

The original is kept verbatim at `image-teardown/tools/superseded/iterate.py` so an old run's records still read.
Nothing imports it.

    a batch        image-production/run.py runs/<brand>/<batch>
    variations     image-production/tools/make_variations.py
    one edit       image-production/tools/hf.py edit

See image-production/PIPELINE.md.
"""
import sys

sys.exit(
    "iterate.py is retired — it ran on fal, and fal is not a generation path any "
    "more (Damon, 2026-09-11, restated 2026-09-13).\n"
    "  a batch:     image-production/run.py runs/<brand>/<batch>\n"
    "  variations:  image-production/tools/make_variations.py\n"
    "  one edit:    image-production/tools/hf.py edit\n"
    "The original is parked at image-teardown/tools/superseded/iterate.py.")
