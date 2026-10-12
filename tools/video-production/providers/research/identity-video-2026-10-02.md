# Swipe recreation: putting our characters into real footage (research, 2 Oct 2026)

**The goal:** start from a real swipe clip. Keep its exact camera, motion, hands, timing and light. Replace every person with our AI character (face, hair, skin marks, outfit). This includes two-person shots (patient and doctor). Talking shots get lip-synced to our ElevenLabs line, and the product stays exact.

How claims are labelled below:
- **[proven]**: from a paper, a model card, or official docs or pricing.
- **[claimed]**: from vendor marketing or a third-party blog.
- **[est]**: my own estimate, not measured.

No paid calls were made for this research.

---

## 0. The landscape in one table

| Tool | Keeps original background, light and camera? | Two people in frame | Identity source | Max length / resolution | Price (API) |
|---|---|---|---|---|---|
| **Wan 2.2 Animate – Replace** (open, Apache-2.0) | Yes. It keeps the source pixels outside the mask and only regenerates the person. Relighting LoRA included [proven, [paper](https://arxiv.org/html/2509.14055v1), [repo](https://github.com/Wan-Video/Wan2.2)] | Not built in. You select one person per pass (SAM2 point mask), so two people means two passes [proven that per-subject masking exists: [ComfyUI workflow](https://comfy.org/workflows/video_wan2_2_14B_animate-c2c4b45b7df5/); multi-person not addressed in the paper] | 1 reference image, plus an optional character LoRA | Long clips work by chaining segments (1–5 frame overlap) [proven]; 480/580/720p on fal | fal: $__ / $__ / $__ per "video second" at 480/580/720p. **Billed per 16 frames**, so resample to 16 fps first [proven, [fal](https://fal.ai/models/fal-ai/wan/v2.2-14b/animate/replace)] |
| **Wan-Animate-2** (released 7 Aug 2026) | End-to-end; no pose extractor | Not documented | ref image | 720p default; tuned for 8×A800 GPUs [proven, [HF](https://huggingface.co/Wan-AI/Wan2.2-Animate-2-14B)] | Too new for hosted pricing; **not a Mac candidate** |
| **MoCha** (CVPR 2026, on Wan 2.1-14B) | Yes. Mask on 1 frame only, so no per-frame pose/mask | **Yes: multi-character occlusion and interaction shown** [proven in paper, [arXiv](https://arxiv.org/html/2601.08587v2)] | Multiple reference images | Trained at **480×832**, 81 frames, so low resolution | WaveSpeed hosts it; code on [GitHub](https://github.com/Orange-3DV-Team/MoCha). Beats Wan-Animate on SSIM 0.746 vs 0.692 and LPIPS 0.152 vs 0.213 [proven, paper's own numbers] |
| **Kling O1 / O3 video edit** | Mostly. Prompt-driven edit "keeps motion" but re-renders the frame | **Yes, in theory**: up to 4 refs via @Element1/@Element2 [claimed, [fal](https://fal.ai/models/fal-ai/kling-video/o1/video-to-video/edit)] | Elements (front image plus angles) | **3–10 s** input | O1 $__/s (fal); O3 edit ≈ $__/s ([WaveSpeed](https://wavespeed.ai/models/kwaivgi/kling-video-o3-std/video-edit)) |
| **Kling 3.0 Motion Control** | **No.** Background comes from your character image, not the source video | **No: one subject only**; it picks the largest person, or none if they're similar size [proven, [Kling guide](https://kling.ai/quickstart/motion-control-user-guide)] | Image plus Element Binding (face only) | 3–30 s, 1080p | 9–12 credits/s on Kling; ≈ $__/s via APIs ([Vercel](https://vercel.com/ai-gateway/models/kling-v3.0-motion-control)) |
| **Higgsfield Genjutsu – Motion Transfer** | Keeps camera, motion and timing; **rebuilds the scene** around them | Not documented | Up to 30 reference images | 4–30 s, up to 1080p | 15 s: 40 cr (480p) / 104 cr (720p) / 144 cr (1080p) [proven, [Higgsfield blog](https://higgsfield.ai/blog/higgsfield-genjutsu)] |
| **Higgsfield Genjutsu – Object Swap** | Yes, replaces one targeted element | One element per run | ref images | same | same |
| **Runway Aleph 2.0** (21 May 2026) | Edit-in-context; you tell it what to keep | Prompt-dependent, not documented | Up to 5 keyframe images | 2–30 s, 1080p | $__/s API ([Runway pricing](https://docs.dev.runwayml.com/guides/pricing/)) |
| **Runway Act-Two** | No, it re-renders onto a character reference | One | image or video | — | $__/s |
| **Luma Ray3 Modify + Character Reference** | Yes, built to keep the actor's performance | Not documented | 1 character image | **10 s max** with character ref; Ray3.14 has no character ref [claimed, [Luma guide](https://lumalabs.ai/learning-hub/ray3-modify-user-guide)] | Subscription; API rate not published |
| **Seedance 2.0 video edit** | Yes | "Complex touching interactions need careful prompting" [claimed] | Up to 9 images | 15 s; 480p–4K; $__/s at 720p (input + output seconds) ([WaveSpeed](https://wavespeed.ai/models/bytedance/seedance-2.0/video-edit)) | **Blocks real human faces in uploaded images and videos** at the model layer (Volcengine policy) [claimed by several sources, e.g. [here](https://aividpipeline.com/blog/seedance-real-human-face-rules-2026)]. Our swipe footage is real people, so expect rejections |
| **FaceFusion 3.9** (local, open) | Yes, 100%. It only swaps the face region | **Yes: up to 6 faces, each mapped to a different source** (reference mode) [claimed, [guide](https://magichour.ai/blog/how-to-use-facefusion)] | 1+ face photos | Unlimited; any resolution (face is pasted back) | Free. Runs on Mac via CoreML. **Licences: inswapper/ArcFace are non-commercial; HyperSwap is ResearchRAIL.** Check before using in ads |

### Lip-sync (our ElevenLabs audio onto the finished video)

| Tool | Notes | Price |
|---|---|---|
| **sync-3** (sync.so, GA July 2026) | 4K native; **automatic occlusion handling** (hands near the mouth, which matters for doctor shots); can open closed lips; active-speaker detection in multi-person video [proven, [docs](https://sync.so/docs/models/lipsync)] | $__/s |
| lipsync-2-pro | 512×512 mouth region; occlusion is opt-in; needs natural mouth motion already in the input | $__/s |
| **LatentSync 1.6** (open, ByteDance) | Best local open model for dubbing existing video; mouth-region inpaint only [claimed, [instavar](https://instavar.com/research/ai-video/open-source-lip-sync-models)]. **MLX port: ~14 s per 16-frame chunk on M-series** [claimed, [repo](https://github.com/sb1992/latentsync-mlx)] | Free; on the M3 Max ≈ 2 min per 5 s clip [est] |
| MuseTalk 1.5 | Fast, softer (256 px face) | Free |
| InfiniteTalk V2V | Re-animates **the whole frame** (head and body), so it would undo the swipe's exact motion. Use only for talking shots with no source motion to keep | fal $__/s (480p), $__/s (720p) |
| OmniHuman 1.5 | Image + audio to new video. Not a dub of existing footage | ≈ $__/s |
| Kling lip-sync | Cheap. Quality is below sync-3 [claimed] | ≈ $__/s depending on reseller |

### Identity training (one-time, per character)
- **Wan 2.2 character LoRA**: fal trainer at about $__ per step, so a 1,000-step LoRA costs about **$__** [proven, [fal](https://fal.ai/models/fal-ai/wan-22-trainer/i2v-a14b)]. It plugs into Wan Animate in ComfyUI on a rented GPU. Hosted fal Animate accepts no custom LoRA [proven absence on the page]. Known issue: the reference image can override the LoRA, so keep LoRA strength modest.
- **Kling Elements**: free to create. Face only, no outfit.
- **Higgsfield Soul ID**: 20+ photos, a few minutes [claimed]. **Does not plug into Kling Motion Control** [claimed, [Higgsfield blog](https://higgsfield.ai/blog/5-Best-AI-Video-Models-2026-Tested-Compared)].
- For outfit and skin marks (age spots), the strongest lever is the **reference image itself**: a full-body, evenly lit, neutral-background still of the character in the shot's outfit. Genjutsu's own guide warns that a reference "brings its whole frame with it" (background and light bleed in) [claimed, [riffkit](https://riffkit.ai/blog/how-to-use-higgsfield-genjutsu)].

### Local on the M3 Max (64 GB) vs renting vs APIs
- **Wan 2.2 Animate 14B**: GGUF quantised weights exist (Q5/Q6 fit easily in 64 GB) and run in ComfyUI on Apple's GPU (MPS) [proven weights exist, [QuantStack](https://huggingface.co/QuantStack/Wan2.2-Animate-14B-GGUF)]. **No published M3 Max timings were found.** For scale, an H100 takes about 10–12 min for 5 s at 720p with the full-step 14B ([source](https://www.spheron.network/blog/deploy-wan-2-1-ai-video-generation-gpu-setup/)). M-series runs roughly 8–15× slower than an H100 on diffusion [est], so **expect about 1–3 h per 5 s clip at 720p, or about 20–45 min at 480p with the 4-step distill LoRA** [est]. Usable for overnight batches; not for iteration. One report says Wan 2.7's custom attention crashes on Apple's GPU.
- **MLX ports** ([mlx-video](https://github.com/Blaizzy/mlx-video), [mlx-video-rs](https://github.com/bhubbard/mlx-video-rs)) cover Wan 2.1/2.2 text- and image-to-video and LTX-2. **They do not cover Animate, VACE or video-to-video**, so they don't help with replacement.
- **FaceFusion on Mac (CoreML)**: works, with CoreML as a first-class install target since 3.9. Slower than a mid-range RTX card, and enhancers are slow [claimed]. Fine for 5–15 s clips.
- **LatentSync-MLX on Mac**: viable, about 2 min per 5 s clip [est from repo figures].
- **Rented GPU**:
  - RunPod pods: RTX 5090 $__/h, A100 80 GB $__/h, H100 $__/h. Serverless runs $__ / $__ / ~$__ per hour.
  - Modal: H100 $__/h, billed per second ([RunPod](https://www.runpod.io/articles/guides/nvidia-h100), [Modal](https://www.spheron.network/blog/modal-gpu-pricing-2026-per-second-billing/)).
  - A 5 s Wan Animate replace on an H100 with the distill LoRA takes about 2–5 min [est], so **about $__ per pass**. That's cheaper than fal at volume, and it unlocks character LoRAs.
- **Hosted APIs** (fal, WaveSpeed, Replicate) are the fastest way to a result. Prices are in the tables above.

---

## 1. Ranked shortlist: three end-to-end pipelines

### #1: Masked replacement on the real footage: Wan 2.2 Animate Replace (one pass per person), then a face lock, then sync-3
This pipeline keeps the most real pixels: background, light, camera and props stay the source's own.

**Steps**
1. **Prep the shot:** trim it, then **resample to 16 fps** (fal bills per 16 frames; re-time to 30 fps at the end). Take the clean audio-free source.
2. **Mask each person:** SAM2 point-select the patient (mask A) and the doctor (mask B). Grow and blur each mask. **Keep the product and the doctor's gloved hands outside the mask wherever possible** so they stay real pixels.
3. **Pass 1:** Wan 2.2 Animate Replace with mask A, the patient reference image and the relighting LoRA on.
4. **Pass 2:** take the pass-1 output, apply mask B, use the doctor reference image. This is the two-person method: sequential single-person passes. The model has no native multi-person mode; this approach is [claimed/community], not in the paper.
5. **Face lock (optional, if the identity check fails):** FaceFusion in reference mode maps patient→patient face and doctor→doctor face, with a ≤256 px swapper and blend. Mind the licence (prefer HyperSwap and check terms, or skip). Alternative: on a rented GPU, add a **character LoRA** in the ComfyUI Wan Animate graph instead.
6. **Lip-sync:** sync-3 with our ElevenLabs line, active-speaker on. If the source mouth was already talking, lipsync-2-pro is cheaper.
7. **Product guard:** composite the source product pixels back with a product mask (SAM2 on the product) if any drift shows up.
8. Re-time to 30 fps (or keep 16 and frame-blend; RIFE interpolation is better) and grade-match.

**Where it runs:** fal API for steps 3–4 (fastest), or ComfyUI on a RunPod H100/5090 (cheaper at volume, and allows a LoRA). FaceFusion and LatentSync can run on the Mac.

**Cost per 5 s clip:**
- fal 720p at 16 fps: $__ per person pass, so **$__ for one person or $__ for two**.
- At native 30 fps without resampling: $__ per pass.
- sync-3: about $__.
- **Total about $__ per clip.** Rented GPU: about $__ per clip plus lip-sync.

**Per character (one-time):** a reference still (we already make these). Optional Wan LoRA about $__ plus 1–2 h of prep.

**Time:** fal takes about 2–6 min per pass [est]. The whole clip lands in about 15 min.

**Evidence:**
- Paper human evaluation beats Runway Act-Two on identity, motion and expression [proven, [paper](https://arxiv.org/html/2509.14055v1)].
- The relighting LoRA is official.
- Wan-Animate is beaten by MoCha on lighting fidelity metrics (SSIM/LPIPS) [proven, MoCha paper].

**Failure modes:**
- Face drift after about 3 s [claimed, community].
- Body-shape mismatch causes deformation (the paper says don't retarget pose when the shapes differ much).
- **Hands crossing between people** (the doctor touching the patient's face): the mask boundary flickers or the hand gets eaten, so dilate masks generously and keep the doctor's hand in the doctor's mask.
- A slight "pasted" look if relighting is off.
- Fine skin marks (age spots) soften at 720p; they need a reference showing them clearly, and maybe the face-lock step.

**Variant (watch closely):** MoCha does two people in one pass with only a first-frame mask and handles occlusion. Its catch is 480p, so pair it with an upscale. Test it on the two-person doctor shots.

### #2: One-pass prompt edit with both characters as references: Kling O3 (or O1) video edit, falling back to Runway Aleph 2.0, then sync-3
This pipeline does two people in one call; it re-renders the frame, so it's less pixel-faithful.

**Steps**
1. Cut the shot to **3–10 s** (Kling's limit; Aleph allows 2–30 s).
2. Create Elements: patient (front image plus 2–3 angles, with the age spots visible) and doctor. Add an image of the product.
3. Prompt: "Replace the woman with @Element1 and the doctor with @Element2. Keep camera, motion, hands, timing, lighting, background and @Image1 product exactly." Turn on keep-audio-off.
4. sync-3 lip-sync with our line.
5. Product guard composite, as in #1.

**Where:** fal or WaveSpeed API (Kling); Runway API (Aleph). Nothing runs locally.

**Cost per 5 s clip:**

| Option | Edit cost | Total with sync-3 |
|---|---|---|
| Kling O3 edit | ≈ $__ | **≈ $__** |
| Kling O1 edit | ≈ $__ | ≈ $__ |
| Runway Aleph 2.0 | $__ | ≈ $__ |

**Per character:** free (create the Element).

**Time:** about 2–5 min per call [est].

**Evidence:**
- The specs (4 refs, @Element syntax, 3–10 s, price) are official ([fal](https://fal.ai/models/fal-ai/kling-video/o1/video-to-video/edit)).
- **Two-character replacement quality is [claimed] only.** No benchmark was found.

**Failure modes:**
- The whole frame is regenerated, so the background, product label and hands may subtly change.
- Identities can swap or blend between the two people.
- The 10 s cap.
- Prompt-dependence: each re-roll costs money.
- Possible face-moderation rejections on real-person source footage (confirmed for Seedance; untested for Kling).

### #3: Swapped first frame plus motion transfer: Nano-Banana-style edit of frame 1, then Kling 3.0 Motion Control (one-person shots) or Higgsfield Genjutsu Motion Transfer, then sync-3
This is what we half-tried with still images. It works for single-person selfie and mirror shots, and is weakest for two-person shots.

**Steps**
1. Grab the source's first frame. Use an image edit to put our character into **that exact frame** (same background and light). Use our existing locked image-draft workflow.
2. Generate the video:
   - **Kling 3.0 Motion Control** (Pro, Element Binding with the character's face refs): image = swapped frame 1, motion = the source clip. Up to 30 s, 1080p.
   - Or **Genjutsu Motion Transfer** with up to 30 refs (the 44 credits/clip already known).
3. sync-3 lip-sync. Product guard.

**Where:** Kling API or Higgsfield (our Higgsfield connector exposes `hf_mult_motion_control` / `hf_mult_replace_object`).

**Cost per 5 s clip:**
- Kling 3.0 MC Pro: ≈ $__. Genjutsu: 44 credits (≈ $__ at the blog's $__/credit).
- Plus sync-3, so **about $__**.

**Per character:** free (Elements), or Soul ID (which doesn't feed Motion Control).

**Two people:**
- **Kling MC cannot**: it drives the largest person only [proven].
- Genjutsu is undocumented. Workaround: put both characters in frame 1, but only one gets motion-driven, so the second person's motion is invented.

**Failure modes:**
- The background is regenerated from frame 1, so it drifts when the camera moves to areas frame 1 didn't show.
- The camera move is approximated, not pixel-exact.
- Element Binding is face-only (outfit comes from the image).
- The "pasted look" if the frame-1 edit's lighting is off.

**Why it ranks third:** it never touches the real pixels after frame 1, so it can't guarantee "looks like real footage" for moving-camera or two-person shots.

### Not recommended as the main route
- **Seedance 2.0 edit**: real-face uploads get blocked, and our sources are real footage.
- **InfiniteTalk / OmniHuman for talking shots**: they re-animate the body, which loses the swipe's motion.
- **Pure FaceFusion**: it keeps everything real, but only the face changes. Hair, outfit and skin outside the face stay the source person's, and the non-commercial model licences are a problem for ads. It's best used as the "face lock" step inside #1.
- **Local Wan on the M3 Max as the main engine**: too slow to iterate (hours per clip [est]). Use the Mac for FaceFusion, LatentSync-MLX and the automatic checks; rent a GPU or call fal for generation.

---

## 2. Automatic verification (run on every output clip)
1. **Identity:**
   - Embed every Nth frame with InsightFace ArcFace (buffalo_l) and compare each tracked face to its character's reference embeddings.
   - Pass if the **median cosine is ≥ 0.60 and the 10th percentile is ≥ 0.45** per character. Thresholds of 0.5–0.6 are typical for same-person; ≥ 0.7 is typical for frame-to-frame consistency ([face-sim overview](https://zenn.dev/taku_sid/articles/20250511_face_sim_metric?locale=en)).
   - **Leak check:** the similarity to the *source* actor's face must be **< 0.35**.
   - **Two-person check:** assign tracks by position and IoU with the source masks, then confirm patient≠doctor (no identity swap or blend).
2. **Temporal stability:** standard deviation of per-frame cosine; flag frames that drop > 0.15 from the rolling median (drift onset).
3. **Background, light and camera kept:** SSIM/LPIPS between source and output **outside the person masks**. Pass at SSIM ≥ 0.85; this mainly catches pipelines #2 and #3 when they rewrite the scene.
4. **Product exact:** crop the product box from source and output each frame and compare with DINOv2/CLIP plus a pixel SSIM; fail if it falls below threshold. If it fails, auto-composite the source product back.
5. **Lip-sync:** SyncNet ([syncnet_python](https://github.com/joonson/syncnet_python)) on the talking-face track:
   - **AV offset within ±1 frame**, LSE-C ≥ ~6, LSE-D ≤ ~8 (real footage is typically about 7 and about 7).
   - Caveat: these correlate only loosely with human judgement ([paper](https://arxiv.org/pdf/2405.04327)), so use them as a gate, not a score.
6. Reviewer still frames for the human: 3 frames per clip, side by side with the source, plus the numbers.

---

## 3. Bottom line
The only way to get footage that still looks real is to keep the real pixels and regenerate only the people. That means **Wan 2.2 Animate Replace with one masked pass per person, then sync-3 lip-sync on our ElevenLabs line**:
- **Cost:** about $__ per 5 s clip on fal, nothing per character beyond the reference still.
- **Identity fix:** if the face drifts, add a FaceFusion face-lock pass (mind the licences) or train a $__ character LoRA on a rented GPU.
- **Proven:** the model card and paper confirm it keeps the background and lighting with a relighting LoRA.
- **Not proven:** two-person handling by sequential masked passes is community practice, not documented. MoCha shows real one-pass two-person replacement but only at 480p. Kling O3 edit claims both characters in one prompt but with no evidence.

Kling 3.0 Motion Control and Genjutsu Motion Transfer rebuild the scene and drive only one person, which explains the "pasted"/drift results so far. Seedance blocks real faces in uploads. The M3 Max is fine for face-swap, lip-sync and the automatic checks, but at an estimated 1–3 h per 5 s clip it's too slow to be the generator. Generation belongs on fal or a rented H100 at about $__/h.

**Cheapest real test:** about $__ total on 3 shots (one selfie, one mirror, one doctor two-shot), run through pipelines #1 and #2 and scored by the checks in section 2.
