# Research: multi-character, in-scene, identity-exact stills for swipe recreation

Date: 2026-10-02 · Desk research only. Nothing below was run or paid for. "Proven" means a vendor doc, a benchmark or a repo shows it. "Claimed" means a blog or model card says it and no independent test was found. "Untested" means it is my own design, built from parts that are documented.

---

## 0. The diagnosis, in short

What went wrong before has one pattern. **One generation was asked to do three jobs at once: composition, identity, and light.**

- **Multi-ref GPT-image / Nano Banana Pro:** the references compete, so identity drifts. Zero-shot multi-identity is weak even in research. On MultiID-Bench (2 people), the best open method scores about **0.40 ArcFace sim to ground truth** (WithAnyone 0.405, AnyPhoto 0.401). GPT-4o-image scores 0.332 ([leaderboard](https://www.sota2.com/research/sota/identity-preserving-image-generation-on-multiid-bench-2-people), [WithAnyone, ICLR 2026](https://arxiv.org/html/2510.14975v1)). Those scores are well below single-person LoRA levels. **Proven.**
- **Gemini "face pass":** this gets identity right, but it copies the reference's pose and light. That is the "copy-paste" failure the WithAnyone paper measures with its Copy-Paste score. **Proven as a known failure mode.**
- **inswapper_128:** the swap runs on a 128-px crop and is driven by an ArcFace identity embedding. That embedding encodes face geometry, not texture, so freckles and age spots are not carried, and hair is outside the swap. Character LoRAs "carry texture (pores, scars, fine wrinkles, asymmetry) that embedding-based methods average away" ([aiofm comparison](https://aiofm.info/en/guides/pulid-vs-instantid-vs-faceid)). **The mechanism is proven. The freckle claim is community consensus.**
- **Higgsfield Soul ID:** Higgsfield's own help docs say one Soul ID holds one person per generation. Its "Elements" feature handles 2+ people, and the docs admit identity blurs where characters touch ([Higgsfield blog](https://higgsfield.ai/blog/tools-for-consistent-ai-characters)). **Proven (vendor-stated).**

**The fix that all three pipelines below share:**
1. Build the scene **plate** first. Faces don't matter at this step.
2. Put identity in **one person per pass**: a masked head region, cropped at high resolution, with one identity source per pass. Nothing competes.
3. Carry skin marks with a **trained per-character LoRA**, not an embedding.
4. **Composite the real product pixels**; never generate the label.

---

## 1. Ranked shortlist

### #1 — Plate → per-person head pass on FLUX.2 [klein] 9B (hosted on fal) with the BFS head-swap LoRA plus a per-character LoRA → composited product → grain match

**Why it ranks first:** every component is hosted, licensed for commercial use, cheap, and API-callable today. It is also the most active community route for head swaps that keep pose and light.

**Steps**
1. **Plate (composition).** Build the plate from the swipe frame (original face blurred) plus outfit sheets. Use Nano Banana Pro or GPT-image, as now. The plate rebuilds the camera, poses, wardrobe, set and hands. It may contain invented faces, which is fine because they get replaced. Leave a clean product position (or a placeholder bottle).
   fal Nano Banana Pro: **$__/image at 1K–2K** ([fal](https://fal.ai/models/fal-ai/nano-banana-pro)).
2. **Character LoRA (one-time, per person).**
   - Dataset: 20–30 images from the casting master, the angles/expressions sheet and the outfit sheets.
   - If the sheet is thin, add angles with `qwen-image-edit-2511-multiple-angles` on fal ($__/MP) ([fal](https://fal.ai/models/fal-ai/qwen-image-edit-2511-multiple-angles)).
   - Caption the skin marks explicitly ("age spots on left cheekbone").
   - Train on fal `flux-2-klein-9b-base-trainer` at **$__/step**, so 1,000–2,000 steps ≈ **$__** ([fal](https://fal.ai/models/fal-ai/flux-2-klein-9b-base-trainer)).
   - Recommended dataset size is 10–30 images (["10–20 multi-angle images deliver 90%+ consistency"](https://selfielabstudio.com/blog/flux-2-lora-training-create-unique-characters-fast-20260311), claimed).
3. **Head pass (one per person, sequential).**
   - Detect each head in the plate and crop it with padding. Upscale the crop to about 1024 px.
   - Mask face plus hair. **Exclude any hand touching the face**, such as the doctor's hand, so the hand stays from the plate.
   - Pick the casting-sheet shot whose head yaw/pitch is closest to the plate's head. Pose estimation from InsightFace does this automatically.
   - Run `fal-ai/flux-2/klein/9b/edit/lora` with: input order body/plate crop first, reference head second; the **BFS head-swap LoRA** ([HF: Alissonerdx/BFS-Best-Face-Swap](https://huggingface.co/Alissonerdx/BFS-Best-Face-Swap), MIT, Klein 4B/9B versions) plus that person's **character LoRA**; a short prompt like "swap the head, keep pose, gaze and expression, relight the face to match the scene".
   - Stitch the crop back (crop-and-stitch keeps the rest of the frame's pixels untouched; see the [MyAIForce Klein head-swap workflow](https://myaiforce.com/head-swap-with-flux-2-klein/)). Then do the next person.
   - Price: **$__/MP in + out** ([fal](https://fal.ai/models/fal-ai/flux-2/klein/9b/edit/lora)), so about **$__ per head attempt**. Commercial use is OK through fal. The local 9B weights are non-commercial ([HF model card](https://huggingface.co/black-forest-labs/FLUX.2-klein-9B)).
4. **Product.** Perspective-warp the **real packshot pixels** into the product region and match them to the scene:
   - Run a low-strength relight or shadow pass on the bottle edges and hand contact only (IC-Light v2 on fal is ~$__ per relight ([fal](https://fal.ai/models/fal-ai/iclight-v2/api)), or a masked Klein edit).
   - **Re-paste the label panel afterwards** so the text pixels are the originals.
   - Reason: an Aug-2026 benchmark found no model reliably preserves labels. The best product-accuracy rate was 29%, and all models invented Supplement Facts text ([Lamina benchmark roundup](https://uselamina.ai/blog/benchmark-can-ai-product-photography-generate-ecommerce-ready-images-without-changing-logos-labe)). **Proven: generated labels are not trustworthy.**
5. **Finish.** Add sensor noise, chroma noise and JPEG artefacts matched to the swipe frame's noise level, plus a slight unsharp mask. This is local, free and deterministic.
6. **QC gate** (section 3). Up to 3 automatic retries per failed head with new seeds or a different reference angle.

**Cost**
- Per character (one-time): about **$__** of training, plus about $__ of extra angles.
- Per picture: plate $__ + 2 heads × ~3 tries × $__ + product pass ~$__ ≈ **$__**.

**Time**
- Training: minutes per character (fal fast trainers usually finish in "a few minutes" ([fal](https://fal.ai/models/fal-ai/flux-lora-fast-training)); the 9B base trainer is likely ~10–20 min, which I have not verified).
- Picture: about 1–2 minutes wall-clock.

**Proven vs claimed**
- Proven (docs): endpoint existence, prices, licence, LoRA support, BFS's existence and input order.
- **Claimed:** BFS keeps the target's lighting, eye direction and expression while transferring hair and identity ([comfyui-wiki 25 Sep 2026](https://comfyui-wiki.com/en/news/2026-09-25-bfs-qwen-image-2-1-head-swap); [klein-head-swap repo](https://github.com/Adeliox/klein-head-swap)).
- **Untested:** stacking BFS with a character LoRA in one fal call. LoRAs trained on Klein *base* are applied here to the 9B edit model, and the transfer quality is unknown, so test with 2 characters before scaling.

**Known failure modes (documented)**
- BFS/Klein lose fidelity on "small faces, extreme angles, occlusion, hands over the face, hair boundaries and strong lighting changes" ([comfyui-wiki](https://comfyui-wiki.com/en/news/2026-09-25-bfs-qwen-image-2-1-head-swap)). This is exactly the doctor-touching-face shot, which is why the hand is masked out and the crop is upscaled.
- The head-swap LoRA sometimes causes "hair consistency issues" and wrong eye direction. One author found plain Klein plus a good reference beat the LoRA ([MyAIForce](https://myaiforce.com/head-swap-with-flux-2-klein/)). Keep both variants as retry options.
- An earlier BFS version on Qwen produced skin "too smooth and qwen-like", and the author retrained Klein 9B on 200 sets for realism ([BFS discussion](https://huggingface.co/Alissonerdx/BFS-Best-Face-Swap/discussions/7)). The character LoRA plus the grain pass is the counter.

---

### #2 — Same structure, open Apache-2.0 models, run locally or on a rented GPU (Qwen-Image-Edit-2511 or FLUX.2 [klein] 4B + BFS + character LoRA in ComfyUI)

**Why it ranks second:** this is the same method with no per-image API cost and full control: masks, hand exclusion, crop-and-stitch, exposure matching and DWPose. On the M3 Max it is slow, and LoRA training on the Mac is not reliable.

**Steps:** identical to #1, with two changes. The head pass runs in ComfyUI with either:
- **Qwen-Image-Edit-2511** (Apache 2.0). Its multi-image edit is built for identity consistency and two-person group fusion ([HF](https://huggingface.co/Qwen/Qwen-Image-Edit-2511); [Replicate](https://replicate.com/qwen/qwen-image-edit-2511)). Use it with the BFS 2511 head LoRA and the MyAIForce recipe: RMBG on the reference, Blockify mask, DWPose, LayerColor exposure-match, inpaint, hi-res fix, edge blur ([MyAIForce Qwen head swap](https://myaiforce.com/head-face-swaps-with-qwen-edit/)).
- or **Klein 4B** (Apache 2.0) with the BFS Klein-4B LoRA.

Avoid Qwen-Image-2.1 (released 20 Sep 2026, 10 references, strong on paper). It is under the **Qwen Research License, non-commercial** ([novoads](https://novoads.ai/en/blog/qwen-image-2-1)), and its VAE encode is currently broken on MPS ([ComfyUI #16433](https://github.com/Comfy-Org/ComfyUI/issues/16433)).

**Where it runs**
- **Inference on the Mac.**
  - Qwen-Image-Edit-2511 with a 4-step Lightning LoRA took **~2.5 min/image on an M1 Max 64 GB** (ComfyUI `--fp16-vae --fp16-unet`, or mflux 8-bit at 2:28). On the default BF16 path it took about 10 min, because M1–M3 have no hardware BF16 ([lilting](https://lilting.ch/en/articles/comfyui-qwen-mps-bf16-slowdown)). Expect similar on the M3 Max.
  - Klein 9B: **105 s at 1024² on an M3 Max** (needs ~29 GB). Klein 4B: about **30–40 s** on an M1 Max with mflux ([lilting](https://lilting.ch/en/articles/flux2-klein-apple-silicon)).
  - Per picture (2 heads × ~3 tries): **~5–15 min** on the Mac with Qwen, **~3–5 min** with Klein 4B.
- **LoRA training: not on the Mac.**
  - Draw Things crashes at step 0 when training Klein on Apple Silicon ([issue #114](https://github.com/drawthingsai/draw-things-community/issues/114)).
  - Qwen-Image LoRA training does work through diffusers on MPS, at 4–11 s/step on an *M3 Ultra 256 GB*, with fp32 required. That is about 1.5–3 h per LoRA, and the author did not evaluate quality ([Souch](https://christinasouch.com/blog/qwen-image-lora-training-on-apple-silicon-it-works-and-heres-how)).
  - Rent a GPU instead: ai-toolkit on a **RunPod RTX 4090 ($__/h community)** trains a Klein LoRA in "about an hour… roughly $__ per run" ([HF/BFL blog](https://huggingface.co/blog/black-forest-labs/flux-2-klein-lora); [RunPod pricing](https://www.synpixcloud.com/blog/rtx-4090-cloud-rental-worth-it)).
  - Or keep using fal's trainer from #1.
- **Alternative:** run the whole ComfyUI graph on a rented 4090. Each head pass takes seconds there, and the cost is about $__/h, so a few cents per picture.

**Cost**
- Per character: **~$__** (RunPod) or $__ (fal).
- Per picture: $__ plate (or a free local Klein/Qwen plate) + **$0 local** / a few cents rented.

**Time:** 1 h of training per character. Per picture, 5–15 min on the Mac or under 1 min on a 4090.

**Proven vs claimed**
- Proven: licences, Mac timings, the training crash.
- Claimed: 2511's two-person fusion and its face-drift reduction (vendor and press).
- Untested: the whole graph on our shots.

**Failure modes**
- Mac black-image or NaN bugs in fp16 (they need an fp32 attention upcast).
- Same occlusion and hair-boundary limits as #1.
- 2511 skin can be smooth, so the character LoRA, hi-res fix and grain are mandatory.

---

### #3 — One-shot multi-character generation with masked (activation-delta) regional LoRAs, posed by the swipe frame

**Why it ranks third:** this is the only route that renders 2+ trained identities *in one generation*, so contact points such as a hand on a cheek are drawn together rather than stitched. It is the most experimental and the least proven, so keep it for shots where #1/#2's per-head pass visibly breaks the contact.

**Steps**
1. Train per-character LoRAs, as in #1 or #2.
2. Get the pose from the swipe frame: depth plus DWPose control.
3. Draw a box per person.
4. Each LoRA is **zeroed outside its box at the activation level**. A softer attention-couple or regional-prompt approach "can still route around it… partial bleed".
   - The ready-made implementation is the Krea 2 node ([CliffNodes Krea2 Multi-Character LoRA](https://github.com/CliffNodes/Krea2-Multi-Character-Lora-Node-with-bounding-box-Scene-and-Outfit-Edit), 96★). It has per-region reference images, and its reference anchors lock pose plus framing.
   - For FLUX, ComfyUI hook/mask LoRA scheduling exists ([Comfy blog](https://blog.comfy.org/p/masking-and-scheduling-lora-and-model-weights/comments)). Community guidance: drop each LoRA to 0.5–0.65 and expect "10–15% more region bleeding with Flux" than with SD (apatero blog, mask-based regional prompting guide, 2025).
5. Then run #1's step 4 (product), step 5 (grain) and the QC gate.
6. Optional: run a #1 head pass on any face that fails QC.

**Where it runs:** a rented GPU (RunPod 4090/H100 at $__/h ([pricing](https://gpuhosted.com/en/runpod-review/))). Krea 2 is listed in mflux, so the Mac is possible but slow. The Krea 2 weights licence is **unverified**; check it before any commercial use.

**Cost:** about $__ per character (training) and a few cents per picture on a rented GPU.
**Time:** setup is days of graph work; each picture then takes seconds to a minute.

**Proven vs claimed:** the masking mechanism is documented. The identity quality at skin-mark level is **unproven**; no benchmark was found.

**Failure modes:** bleed at contact points, which is the very case it targets. Hands get worse with lower LoRA weights. Reference anchoring locks pose and framing together.

---

### Considered and not shortlisted
- **FaceFusion** (local, works on the Mac).
  - Hyperswap 1A/1B/1C at 256 px are much better than inswapper_128, and pixel boost goes up to 1024 ([docs](https://docs.facefusion.io/usage/cli-arguments/processors/face-swapper)).
  - It is still an embedding swapper: no hair, and the face-enhancer stage (GFPGAN/CodeFormer) smooths skin.
  - No source shows it keeping freckles or age spots. Keep it only as a quick fallback, not as a pipeline.
- **PuLID-FLUX / InstantID / IP-Adapter FaceID / PhotoMaker / InfiniteYou:** all ArcFace-embedding identity, with the same texture loss as inswapper ([aiofm](https://aiofm.info/en/guides/pulid-vs-instantid-vs-faceid)). Usable only stacked under a LoRA.
- **UNO / USO / OmniGen2 / DreamO / UMO / XVerse / MOSAIC:** zero-shot multi-subject. On MultiID-Bench they score 0.22–0.36 Sim(GT) at 2 people ([leaderboard](https://www.sota2.com/research/sota/identity-preserving-image-generation-on-multiid-bench-2-people)), too weak for "unmistakably our character".
- **FLUX.2 Pro/Max multi-ref (up to 8 refs, $__/MP ([OpenRouter](https://openrouter.ai/black-forest-labs/flux.2-pro))), Seedream 5.0 (up to 14 refs; claimed better face stability ([eachlabs](https://www.eachlabs.ai/blog/seedream-5-0-lite-vs-seedream-4-5-comparison))), Kling/Higgsfield Elements:** the same reference-competition problem we already hit. They are fine as **plate builders** in step 1.
- **Easel advanced face swap (2-person, hair option):** end-of-life on fal since 15 Jan 2026 ([fal](https://fal.ai/models/easel-ai/advanced-face-swap/llms.txt)).

---

## 2. Requirement check

| Requirement | #1 fal Klein + BFS + LoRA | #2 local / rented Qwen-2511 or Klein-4B | #3 regional multi-LoRA |
|---|---|---|---|
| (1) Each person is our character, incl. skin marks, 2+ people | One identity per pass plus LoRA texture (claimed) | Same | One pass with masked LoRAs (unproven) |
| (2) Photoreal in scene (pose, gaze, light, grain) | Model regenerates the head in context; grain pass | Same plus explicit exposure match | Native, since everything is generated together |
| (3) Composition matches the swipe | Plate locks it; head pass touches only the head crop | Same | ControlNet pose/depth; looser |
| (4) Exact product / props | Real pixels composited; label re-pasted | Same | Same |

---

## 3. Automatic verification (runs after every picture, before the owner sees it)

1. **Who is who.** Detect every face (InsightFace `antelopev2`/`buffalo_l`).
   - Compute the ArcFace cosine of each face to every character's casting set.
   - Pass when each face clears ~0.5 to its own character **and** beats the other character by a margin. That catches swaps and blending.
   - ArcFace is blind to freckles, so this alone isn't enough.
2. **Skin marks.** This check is my own design (untested). Keep a short marks list per character (e.g. "3 age spots, left cheekbone").
   - Landmark-align each output face to the casting master.
   - Compare the marked patches: dark-blob count in the patch, plus a LPIPS patch distance.
   - Add a vision-model judge given side-by-side crops and the checklist: "Is each listed mark present? yes/no".
3. **Not pasted.**
   - Head yaw/pitch/roll of each output face must sit within ~10° of the swipe frame's person, not of the reference photo.
   - "Copy-paste" flag: if the output is far more similar to one specific reference photo than to the character's other photos, it was pasted (WithAnyone's CP idea ([paper](https://arxiv.org/html/2510.14975v1))).
   - Light-direction check: compare the face shading gradient to the swipe face region.
4. **Composition.** DWPose keypoints of the output vs the swipe frame (normalised distance), plus an edge-map SSIM of the background.
5. **Product.**
   - Pixel SSIM of the label region against the warped packshot (should be ≈1, since those pixels are pasted).
   - OCR (Apple Vision locally) string-match against the label copy.
6. **Grain.** Noise-level estimate of the output within ±X of the swipe frame.

Failures retry automatically (new seed or a different reference angle). the owner sees the picture plus pass/fail.

---

## 4. Bottom line

No model available today reliably puts two of our people into one still in a single shot with their freckles and age spots intact. Benchmarks for doing that in one shot top out around 0.40 identity similarity, and references fighting each other is exactly the drift we saw. The documented route that works is to split the job:
- rebuild the swipe frame as a plate with stand-in faces;
- swap each person's head in alone, on a high-res crop, with a trained LoRA of that character, so skin marks are learned rather than guessed, plus the BFS head-swap LoRA, which regenerates the head in the scene's pose, gaze and light instead of pasting the casting photo;
- paste the real product pixels last.

**Start with pipeline #1 on fal.** It costs about $__ once per character and roughly $__ per finished picture, a minute or two each, and needs no setup on the Mac. Pipeline #2 is the same method locally or on a ~$__/h rented GPU once it proves out. The Mac is fine for running pictures (~2.5 min each with Qwen, ~35 s with Klein 4B), but not for training. #3 is the experiment for shots where a hand on a face makes the head-by-head method visibly break.

**What is proven:** the parts, prices and licences. **What is claimed:** BFS keeping light, gaze and hair while carrying identity. **What nobody has shown publicly:** freckle and age-spot survival through this chain. That has to be our first 2-character test, scored by the checks in section 3.
