# A trimmed, brand-neutral ad-uploader hand-off (SI-126 (hand-off test fixture))

Read by `tests/test_upload.py` `RealHandoff`, which copies it into a temp
workspace, writes a 1×1 PNG per asset, and plans it with `upload.plan`.
Two ads, two pages; nothing here is a real brand, page or id.

| here | its real home |
|---|---|
| `manifest.json`, `assets/index.json`, `references/links.json` | the hand-off folder itself |
| `drop/copy.csv` | `runs/image-teardown/<brand>/<drop>/deliverable/copy.csv` |
| `brand/` | `brands/<brand>/` (account, funnels, angles, avatars) |

Only the SHAPE is copied from a real hand-off. If a real upload fails while
this test passes, the shape has drifted: regenerate this folder from the next
real drop.
