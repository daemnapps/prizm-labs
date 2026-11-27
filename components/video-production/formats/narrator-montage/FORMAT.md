# Narrator montage

Status: draft, unsigned. No ad has been carried end to end on it yet; the first run writes `proven_on` and its lessons into `LEARNINGS.md`.

This folder is the format's one home (`../README.md`, "One home per format"):

| File | Holds |
|---|---|
| `format.json` | the bank row, the playbook settings and the workflow steps. The chain reads it through the copies `../sync.py` writes. |
| `FORMAT.md` | this page: what the format is and how each step is done right. |
| `LEARNINGS.md` | one entry per run, each with the home its fix went to. |

## What it is

A hook, then one narrator's voiceover over a fast run of short shots, then the offer and the ask.

| Part | What is on screen | What is heard |
|---|---|---|
| Hook | whatever the chosen hook is (a slot) | the hook's own sound |
| Body | short shots: the product, people using it, how it feels | one narrator, one continuous read |
| Proof | a real customer's before and after | the narrator |
| Offer and ask | the product, the offer, the ask | the narrator |

- The hook is an input, not part of the format. Any hook opens it: a filmed street interview, a meme beat, a talking head. The brief's `openings` (V0 to Vn) are the hooks to choose from.
- It is not `testimonial-montage` (many people, the same line, again and again) and not `single-presenter` (one person to camera).

## Inputs

- An accepted brief (writing station) whose run names `narrator-montage` as its format in `run.json`.
- The chosen hook: one of the brief's openings.
- The brand's cast, voice and product kits (casting, product kits).

## Steps

Run `python3 components/video-production/machine/workflow.py run narrator-montage --brand <brand> --label <label>`; it hands out one step at a time. The exact commands live in `format.json`. What right looks like at each step:

1. **Brief.** The writing station's accepted brief. A held or stale brief stops here.
2. **Plan.** Nothing is spent.
   - Build the storyboard and the total: `machine/storyboard_plan.py <production run> --teardown <teardown run>` writes `storyboard.json` and `BUDGET.md`.
   - Pick each scene's route (`../../SHOT-ROUTES.md`): owned footage or generated. Every scene may be generated.
   - `plan.md` lists every scene: route, seconds, cost, and the total from `BUDGET.md`. The total goes on the quote: the owner's go on that quote (his one stop, `workflow.py go`) comes before anything is spent.
3. **Elements.** List every person, voice, place and product the generated scenes need (`machine/elements_check.py`), match each to the bank, make only the gaps. The narrator is a voice only: a cloned voice, no face.
4. **Narrator read and storyboard.** The read comes first and times every scene (`run_v2.py start … --voice-only`, then `run_v2.py storyboard`). One read, start to finish of the body; it is never re-recorded per scene.
5. **Pictures.** One start picture per generated section, built from the brief's `first_frame` fields (`machine/model_inputs.py` `still_prompt`). No picture for an owned-footage scene. An end picture only where the shot changes inside the section.
6. **Proof clips.** The first body shot after the hook and the hardest shot, one take each, total stated first. Nothing else is made until the decision layer passes the look (filed for the owner to overrule).
7. **All clips.** The rest, from the approved pictures, through the chain's clip route (`machine/clips_run.py`): Seedance 2.5 at 480p, one take, three at most, only the kept take upscaled. Body shots are silent image-to-video; nobody's lips move.
8. **Score.** `machine/first_take.py` counts shots right on take one.
9. **Learn.** Every lesson goes to its one home (`LEARNINGS.md`, routing table). The lesson is filed through the decision layer; a home changes only after the owner agrees with the filed call, never inside the run.
10. **Edit and hand-off**, then **launch package.** Each decided by the decision layer; the launch package is filed on the Meta approval page, and going live is the owner's click there.

## Pace (measured from the source swipes, 2026-11-09)

Measured with `machine/pace.py <video> --hook-end <s> --transcript <transcript.json>` on the swipes this format was built from. Every edit is checked against these numbers before it ships.

| Source swipe | Hook | Body | Body cuts / 10 s | Median body shot | Narrator |
|---|---|---|---|---|---|
| Street interview into montage (teardown 156477006) | 11.0 s | 29.8 s | 7.4 | 1.13 s | 4.7 words/s |
| Dramatic hook into montage (157026140) | 14.0 s | 28.2 s | 8.9 | 1.00 s | 6.8 words/s (several voices) |
| A brand's proven winner (its own teardown run) | 1.5 s | 13.2 s | 6.8 | 1.38 s | not measured |

**Targets for an edit in this format:**
- The hook runs 11–14 s, unless the brief's hook is longer by its own lines.
- The body copies the swipe's own cuts: every swipe shot a scene names, at its share of the scene (`video-studio/swipe_shots.py`), checked against the swipe with `machine/edit_style.py`. The numbers above describe the swipes; they are not a target to cut to, and no minimum shot length is coded (owner, 10 Nov 2026).
- The narrator reads at about 4.5 words per second, as one continuous read, with no silence over 0.12 s between phrases.
- The runtime follows from the words: the body's words divided by 4.5, plus the hook.

The first carried edit missed these (body 3.4 cuts per 10 s, median shot 2.8 s, read 2.2–3.5 words per second) and read as slow (owner, 9 Nov).

## The edit, done right

First carried on a street-interview brief: a street-interview hook, cut to six versions (see LEARNINGS.md, 2026-11-08). These rules hold for every narrator-montage edit.

**Lock three things before the first cut, and check every pick against them.**
- **Avatar.** The hook's person sets it. Every man on screen matches that person. One creator who matches carries the body; women can vary. Supporting characters (a relative, a date) carry the avatar's own features, and the proof is a customer of the same avatar.
- **Angle.** The brief's core message. Every shot serves it: the hook states the verdict, the body earns it, and the proof answers the doubt.
- **Format.** The swipe's section order, kept from the hook to the ask.

**Hook**
- It starts on the first spoken word. Dead air between answers is cut, and the interviewer's prompts ("Why?") stay.
- A hook variation plays the interviewer's whole question before the answer lands. An effect never cuts his line.
- A before/after question hook shows BEFORE and AFTER on screen above the people, inside the safe zone. AFTER is marked when it is chosen.

**Body**
- Every swipe shot the scene copies is one of our shots, in the swipe's order, at its share of the scene (`video-studio/swipe_shots.py`). The swipe's own lengths decide; no minimum length or shot-per-phrase rule is coded. A shot leaves the list only on the owner's call (`swipe_overrides`).
- The same clip section never appears twice. The same creator may.
- A demonstration plays long enough to land, and the product first appears held up or in use.
- A shot of the problem is followed by the same person solved.
- Every shot is checked frame by frame for the creator's own cuts inside its window, and moved to a clean stretch.
- Every shot shows what its swipe shot shows, judged on the pictures before the owner sees a cut (`video-studio/shot_copy.py`, run by `swipe_check.py` as `shots_copy`): the swipe frame and ours side by side, after the swipe's product, places and page become ours. A different moment fails the cut. Misses are filled in order: owned footage, then a generated shot (no product in it), then a creator shoot for a product shot. A clip at the right length is not a copy (owner, 10 Nov 2026).

**Generated shots**
- A gap no owned clip covers is generated, never left empty and never filled by reusing a clip.
- A generated shot's movement comes from the motion chain (`../../../motion/`, the only route, 2026-11-12): real footage of the same action found, tracked, read as body mechanics, rehearsed in 3D with the real camera; the take is made only when the chain's own checks pass, and checked against the reference after. No written shot sizes when the camera is tracked.
- It starts from a reference frame: a real frame of the footage, or a still edited from the creator's real face. A text prompt alone is not used.
- The still copies the reference frame's camera (phone softness, grain, white balance, exposure). The clip is then re-encoded the way a phone records (lower resolution, grain, compression, a small handheld drift), so it sits with the real footage.
- Generated shots carry no product; the product comes from real footage.

**Sound and graphics**
- The narration is one continuous read from the start of the body to the end. There are no silent picture beats.
- A press quote or review rides over the narration as motion. Press logos are the publication's real mark.
- Nothing sits over the speaker's face, and no tag follows the product around the frame.
- The music bed runs under the whole ad and follows the swipe's shape (where it drops, where it hits; the hit lands on the offer). It sits at about -23 dB under the interview and -19 dB under the narrator, and the mix lands at -14 LUFS.
- The bed is current, chart-level music in the avatar's own lane, made instrumental. The chain picks the lane and the take and files the pick for the owner to overrule (owner, 2026-11-27: the only stop is the quote).
- The bed is cut to the edit. Map the take (tempo, phrase starts, its own stops and drops), then put a phrase start on each scene change that carries the story: the drop on the product's name, back in on the mechanism line, a stop on the doubt question, back in heavy on the offer, and the song's own ending under the ask. Each stretch is nudged under 3 % so the pulse never skips.
- Under a voice, the bed's highs come down (about -6 dB above 3 kHz, -3 dB around 1.8 kHz) and its bass comes up (about +3 dB below 90 Hz), so the bass is felt and the words stay on top.

**Checks before the hand-off**
- The render shows no cut shorter than 3 frames, and captions change on the cut.
- A transcript of the final mix matches the script at 0.95 or above, with spelling the only difference.
- Loudness is -14 ± 0.5 LUFS.
- Every man on screen matches the locked avatar.

## Cost rules

- Price before spend: `BUDGET.md` before any call, and the owner's go on the quote's total.
- One picture per section, one version. One take per clip; another only on a named failure, three at most.
- 480p first; only the kept take is upscaled, on the machine.
- No 3D set, no swap and no motion reference unless the shot's motion is the point.
- An owned clip that fits is cut, not generated.

## Checks before the cut

- One narrator voice across the whole body, no restarts.
- No body shot has a moving mouth.
- The proof shot is a real customer's before and after, unaltered. When the read asks viewers to send theirs ("send your before and after"), a second real before and after plays on that line.
- Every clip passed the shared QC gate (inspector and director verdicts).
