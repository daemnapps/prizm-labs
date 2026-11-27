# 3D recipes: every Higgsfield build, runnable in any account

Higgsfield cannot share a 3D Jutsu project between accounts or import a 3D file. A build is the code that made it, so
the code is the standard. Each folder here holds a build's steps, in order. Run them in a new project in any Higgsfield
account and the same build comes out. Sets and renders are free; only a print spends credits.

Proven 2026-11-02: PRIME v2 master rebuilt from its recipe in a fresh project. Same 13 parts, 4,757 points, 4,595 faces,
same materials, and an identical geometry fingerprint to the original. Not yet run in a second person's account.

## Rebuild a build that is not in your account

1. `scene_builder_3d_list_projects`. If the build is already there, use it.
2. Find it in the table below and `scene_builder_3d_create_project` with its name.
3. For each `step-NN.py` in order, `scene_builder_3d_run_python` with the file's code unchanged, the revision from the
   last step (0 to begin) and scene sequence 0. Wait for `succeeded` before the next step.
4. Pass the code as it is. Never retype or rewrite it. A step that fails stops the rebuild: report it.
5. Use the new project wherever the brief names the build. Print with the product's casting sheet, as always.

Large builds are long: run them once per account, in their own session, and keep the project.

## Save every new build

A build counts only once its recipe is here. After a scene is kept, add each successful `scene_builder_3d_run_python`
in order as `components/3d-recipes/<build>/step-NN.py`, code unchanged, and add the build to `recipes.json` and the table.
A step may not load a file from a computer or name another project: everything must be in the code.

## Recipes

| Build | Folder | Steps | Size |
|---|---|---|---|
| Brand A CORE product casting sheet | `Brand A-core-product-casting-sheet` | 2 | 13 KB |
| Brand A CORE v2 product master | `Brand A-core-v2-product-master` | 3 | 9 KB |
| Brand A CRUSH product casting sheet | `Brand A-crush-product-casting-sheet` | 4 | 24 KB |
| Brand A CRUSH v2 product master | `Brand A-crush-v2-product-master` | 6 | 18 KB |
| Brand A FLEX CHARGING CASE product casting sheet | `Brand A-flex-charging-case-product-casting-sheet` | 4 | 16 KB |
| Brand A FLEX charging case v2, open and closed | `Brand A-flex-charging-case-v2-open-and-closed` | 5 | 21 KB |
| Brand A FLEX product casting sheet | `Brand A-flex-product-casting-sheet` | 38 | 97 KB |
| Brand A FLEX statics sets, 7 Nov (briefs 0107, 0108, 0204) | `Brand A-flex-statics-1107-sets` | 10 | 24 KB |
| Brand A Fed-Up King carousel sets (bathroom, aisle, clearance bin) | `Brand A-fuk-carousel-bath-and-aisle-sets` | 5 | 19 KB |
| Brand A PRIME product casting sheet | `Brand A-prime-product-casting-sheet` | 1 | 6 KB |
| Brand A PRIME v2 product master | `Brand A-prime-v2-product-master` | 3 | 13 KB |
| Brand A The Jet | `Brand A-the-jet` | 1 | 4 KB |
| Brand B I stole a bottle · cast stage | `Brand B-stole-cast-stage` | 1 | 4 KB |
| Brand A brief-0336 · family-3d cast stage (8 cast elements at true build) | `Brand A-brief-0336-family-3d-cast-stage` | 2 | 6 KB |
| Brand B I stole a bottle · locations | `Brand B-stole-locations` | 1 | 4 KB |
| Brand A WAR product casting sheet | `Brand A-war-product-casting-sheet` | 1 | 6 KB |
| Brand A WAR v2 product master | `Brand A-war-v2-product-master` | 10 | 31 KB |
| Brand A World: Around Town | `Brand A-world-around-town` | 13 | 35 KB |
| Brand A World: The Arena | `Brand A-world-the-arena` | 10 | 33 KB |
| Brand A World: The Family House | `Brand A-world-the-family-house` | 7 | 28 KB |
| Brand A World: The Gym | `Brand A-world-the-gym` | 1 | 9 KB |
| Brand A World: The Job | `Brand A-world-the-job` | 5 | 13 KB |
| Brand A World: The Megachurch | `Brand A-world-the-megachurch` | 2 | 10 KB |
| Brand A World: The Shop | `Brand A-world-the-shop` | 3 | 13 KB |
| Brand B BF body scrub 09-11 sets | `Brand B-bf-body-scrub-09-11-sets` | 2 | 12 KB |
| Brand B Brilliance Body Scrub product casting sheet | `Brand B-brilliance-body-scrub-product-casting-sheet` | 1 | 6 KB |
| Brand B Brilliance Body Scrub v2 product master | `Brand B-brilliance-body-scrub-v2-product-master` | 13 | 50 KB |
| Brand B Brilliance Face Scrub product casting sheet | `Brand B-brilliance-face-scrub-product-casting-sheet` | 9 | 25 KB |
| Brand B Brilliance Face Scrub v2 product master | `Brand B-brilliance-face-scrub-v2-product-master` | 25 | 97 KB |
| Brand B Coco's kitchen shot sets | `Brand B-coco-s-kitchen-shot-sets` | 1 | 3 KB |
| Brand B Radiance Body Cream product casting sheet | `Brand B-radiance-body-cream-product-casting-sheet` | 1 | 6 KB |
| Brand B Radiance Body Cream v2 product master | `Brand B-radiance-body-cream-v2-product-master` | 1 | 10 KB |
| Brand B World: a creator's House | `Brand B-world-a creator-s-house` | 1 | 10 KB |
| Brand B At-Home Thai Spa Bundle hero set | `Brand B-thai-spa-bundle-hero` | 5 | 25 KB |
| Brand B At-Home Thai Spa Bundle store picture on white | `Brand B-thai-spa-bundle-white` | 7 | 32 KB |
| Brand B December Christmas statics sets (T7, K1, K2, M1) | `Brand B-dec26-christmas-statics-sets` | 7 | 21 KB |
| Brand B pop-up 3-pack sets (body + face scrub in the open pouch; needs the bundle-white set) | `Brand B-popup-3pack-sets` | 2 | 4 KB |
| Brand B At-Home Thai Spa Bundle gallery picture (picture standard, gallery kind) | `Brand B-thai-spa-bundle-gallery` | 9 | 38 KB |
| Brand B Brilliance Body Scrub texture swirl (How to Use card) | `Brand B-body-scrub-swirl` | 1 | 3 KB |
| Brand B World: Margo's Desert Estate | `Brand B-world-margo-s-desert-estate` | 1 | 15 KB |
| Brand B World: Sunday Church | `Brand B-world-sunday-church` | 3 | 9 KB |
| Brand B World: The Clinic | `Brand B-world-the-clinic` | 3 | 11 KB |
| Brand B World: Yai's Golden Siam | `Brand B-world-yai-s-golden-siam` | 4 | 14 KB |
| Brand B Yai court-interior (casting room) | `Brand B-yai-court-interior-casting-room` | 1 | 3 KB |
| Brand B Yai gilded-pavilion (casting room) | `Brand B-yai-gilded-pavilion-casting-room` | 1 | 3 KB |
| Brand B Yai gold-leaf-road (casting room) | `Brand B-yai-gold-leaf-road-casting-room` | 1 | 3 KB |
| Brand B Yai golden-barge (casting room) | `Brand B-yai-golden-barge-casting-room` | 1 | 3 KB |
| Brand B Yai lotus-terrace (casting room) | `Brand B-yai-lotus-terrace-casting-room` | 1 | 3 KB |
| Brand B Yai turmeric-kitchen (casting room) | `Brand B-yai-turmeric-kitchen-casting-room` | 5 | 10 KB |
| Brand B desert estate pool terrace (casting room) | `Brand B-desert-estate-pool-terrace-casting-room` | 3 | 4 KB |
| Brand B desert golf-fairway (casting room) | `Brand B-desert-golf-fairway-casting-room` | 1 | 4 KB |
| Brand B desert helipad (casting room) | `Brand B-desert-helipad-casting-room` | 2 | 5 KB |
| Brand B desert living-room (casting room) | `Brand B-desert-living-room-casting-room` | 1 | 4 KB |
| Brand B desert outdoor-bar (casting room) | `Brand B-desert-outdoor-bar-casting-room` | 2 | 4 KB |
| Brand B desert walk-in-closet (casting room) | `Brand B-desert-walk-in-closet-casting-room` | 2 | 4 KB |
| Brand A brief-0336 + brief-0339 family-3d empty sets: coffee shop, office, gym, bedroom, church steps, church altar, reception, product void; mama's table, balcony, party bathroom, pore world, shared sink, golden doorway | `Brand A-0336-family-3d-sets` | 20 | 113 KB |
| Brand A brief-0336 family-3d bedroom, first version with ironing board, superseded by the bedroom in `Brand A-0336-family-3d-sets` (runs on `Brand A-world-the-family-house`) | `Brand A-0336-bedroom-family-3d` | 2 | 13 KB |
| Brand B brief-0380 porch sets: the 15 start-picture cameras (S1 to S10), with the scrub and cream builds parked hidden at true size (runs on the brief's porch set, whose first three revisions have no saved recipe) | `Brand B-brilliance-body-scrub-brief-0380-porch-sets` | 15 | 51 KB |

## One file for one set

Higgsfield has no way to share a project between accounts, and a build cannot be imported as a file. A pack is the way a set moves: one file in `packs/`, named after the set, that loads it in a new project in a single edit at no credit cost, ending with a render to check.

- **To load one:** new project, run the file from `packs/` as one edit. `SET_bf_timeout.py` is 13 KB, took under 3 minutes and matched the original exactly, part for part.
- **To make one:** `python3 pack.py <recipe> packs/<SET name>.py <steps>`. Steps are the ones that build the product, plus the ones that build that set. Compare it to the original before saving it here.
- **Every new set gets a pack** when it is kept, so the next account never rebuilds the whole recipe.
| Brand A idea2 Cole hug set (campus plaza) | `Brand A-idea2-cole-hug-plaza` | 3 | 7 KB |
| Brand A idea-15 family-3d empty sets: bar, kitchen, parking lot, house party, hallway, shrine room, night bathroom, street at dusk | `Brand A-idea15-family-3d-sets` | 11 | 47 KB |
| Brand A idea-15 cover room (built inside The Family House, after its recipe) | `Brand A-idea-15-cover-room` | 2 | 7 KB |
| Brand A FLEX family-3d product print (render step; runs in the FLEX product project, needs its SET_store_charger) | `Brand A-flex-family-3d-product-print` | 1 | 1 KB |
| Brand B brief-0384 sets (hands master, parody gift set, shower bay, beauty aisle) | `Brand B-brief-0384-sets` | 5 | 19 KB |
