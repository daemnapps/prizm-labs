# Third-party notices: the video line's prompts and checks

Parts of the prompts, checks and formats installed on 2026-11-07 (the story-repo install) adapt text from three
repositories under the MIT License. Each source, the files it was adapted from and where the adaptation lives in
this workspace are listed below, followed by that source's copyright and permission notice, which travels with
every copy of the adapted text.

A fourth studied repository, chatfire/huobao-drama, is licensed CC BY-NC-SA. No text from it is copied: the rules
taken from it are written in our own words, so no notice is owed and none is given here.

The email flows keep their own full notice beside them: `components/email-production/flows/LICENSE-rmbc.md`.

## 1 · short-drama-factory

Source: https://github.com/lixiaoxiao9888-create/short-drama-factory (commit `33d9988`), MIT License.

| Adapted from | Lives in |
|---|---|
| `references/genre-map.md` | `video-teardown/prompts/proposed/stage1b-audience-v14-owner.md` |
| `references/emotion-flow-roundtrip.md` | `video-teardown/prompts/proposed/stage4i-idea-v2-owner.md` |
| `references/golden-3s-hook-library.md` | `video-teardown/prompts/proposed/stage4v2a-readhooks-v9-owner.md` |
| `references/hongguo-beat-sheet.md`, `character-bible.md`, `inner-monologue-vo.md`, `cliffhanger-master-formulas.md` | `video-teardown/prompts/proposed/stage4v2b-build-v10-owner.md` |
| `references/dialogue-doctor-anti-ai.md`, `references/script-doctor-protocol.md` | `video-teardown/prompts/proposed/stage4g-spice-v10-owner.md` |
| `references/mechanism-imitation.md` | `video-teardown/prompts/proposed/stage3-injection-v10-owner.md` |
| the rules behind checks E2, E4, E5, E6, E8, E15, E16, E21, E24 and E26, and its evaluation method (frozen cases, one held back, blind judging); the code itself is new | `video-writing/machine/script_check.py`, `video-writing/machine/bakeoff.py` |
| `references/continuity-ledger.md`, `templates/ledger.md`, `references/first-three-eps-beat-card.md`, `references/hongguo-beat-sheet.md`, `references/webnovel-adaptation.md` | `video-production/formats/ad-series/` (`format.json`, `FORMAT.md`, `series_check.py`) |

```
MIT License

Copyright (c) 2026 lixiaoxiao9888-create (老李)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 2 · RMBC copywriting skills

Source: https://github.com/coleschaffer/copywritingskills-rmbc (commit `8327d49b`), MIT License.

| Adapted from | Lives in |
|---|---|
| `skills/unified-research-synthesizer`, `skills/competitor-offer-analysis` | `video-teardown/prompts/proposed/stage1r-research-v1-owner.md` |
| `skills/mechanism-ideation` | `video-teardown/prompts/proposed/stage1m-mechanism-v1-owner.md` |
| `skills/creative-brief/SKILL.md`, `skills/ad-angle-generator/SKILL.md` | `video-teardown/prompts/proposed/stage4i-idea-v2-owner.md` |
| `skills/hook-battery/SKILL.md` | `video-teardown/prompts/proposed/stage4v2a-readhooks-v9-owner.md` |
| `skills/offer-stack`, `skills/guarantee-writer`, `skills/pricing-strategy`, `skills/scarcity-urgency` | `video-teardown/prompts/proposed/stage4v2b-build-v10-owner.md` |
| the README's copy gates, `skills/rmbc-copy-audit/SKILL.md`, `resources/scoring-rubric.md` | `video-teardown/prompts/proposed/stage4e-audit-v12-owner.md` |
| `skills/ugc-brief/SKILL.md` | `components/briefs/creator-brief/creator-brief-v1-owner.md` |
| `skills/` welcome-sequence, soap-opera-sequence, cart-abandonment-flow, checkout-abandonment, post-purchase-sequence, upsell-sequence-writer, upsell-script, lander-copy, pdp-ecomm-template | `components/email-production/flows/prompts/` (notice also in `flows/LICENSE-rmbc.md`) |

```
MIT License

Copyright (c) 2026 Stefan Georgi

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 3 · drama-skills

Source: https://github.com/zenstory-ai/drama-skills (commit `862ae46f` read on 2026-11-07), MIT License.

| Adapted from | Lives in |
|---|---|
| `skills/short-drama-develop/references/story-craft.md`, `assets/creative-brief.md` | `video-teardown/prompts/proposed/stage4i-idea-v2-owner.md` |
| `skills/short-drama-develop/references/episode-design.md` §4.4, `skills/short-drama-write/references/script-craft.md` | `video-teardown/prompts/proposed/stage4v2a-readhooks-v9-owner.md` |
| `skills/short-drama-develop/references/story-craft.md`, `episode-design.md`, `assets/story-engine.md` | `video-teardown/prompts/proposed/stage4v2b-build-v10-owner.md` |
| `skills/short-drama-write/references/script-craft.md` §9.10, `skills/short-drama-write/SKILL.md`, `skills/short-drama-develop/references/episode-design.md` §9.2 | `video-teardown/prompts/proposed/stage4v2b-patch-v2-owner.md`, `stage4g-spice-v10-owner.md` |
| `skills/short-drama-breakdown/references/gap-and-learning-loop.md`, `measure-and-read.md`, `stage-contract.md` | `video-teardown/prompts/proposed/stage4r-ruler-v1-owner.md` |
| `skills/short-drama-video-prompts/references/performance-action-timing.md`, `skills/short-drama/references/audience-reveal.md`, `skills/short-drama-storyboard/references/shot-craft.md` | `video-teardown/prompts/proposed/stage5-ai-brief-v13-owner.md` |

```
MIT License

Copyright (c) 2026 drama-skills contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## When a file moves

A proposed prompt that is picked moves out of `video-teardown/prompts/proposed/` into its stage folder. Update its
row above to the new path in the same change.
