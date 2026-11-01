# Stage 0 — Brief intake: the chain

v2, 2026-08-30. Every sub-step, in order, from "a brief arrived" to "the
stations start work." Built against the real brief spec: the teardown
machine's stage-5 brief (v24, in `tools/video-teardown/`) — eight
labeled lines per frame, six openings, WHAT TO SAY assembled from the Say
lines. That spec was written for a REAL CREATOR filming on her own phone;
step 0.3 is the bridge that turns a UGC brief into AI-generation
requirements. Nothing here is final.

## What the brief hands over (the stage-5 contract, as-is)

- Concept: title + 1–3 sentence description
- The openings — six, each with Film + Say ("all of them ship to test")
- The frames — each with eight labeled lines, always in this order:
  **Frame N · start–end**, Source, Film, Hear, Wearing, On screen, Say,
  frame image
- WHAT TO SAY — the clean script, assembled from the Say lines
- Format credit ("built from a format that ran on …"), the AI-likeness
  notice, and the closing line telling the creator to email the brand
  with questions (meaningless for an AI run — the gate below replaces it)

## What the brief deliberately does NOT hand over (UGC by design)

These are not brief defects — the spec withholds them because a real
creator supplies them by existing. The AI route must derive every one:

| The brief assumes | The AI run must have |
|---|---|
| the person filming is "you" — never cast, never described | a full character identity + the load-bearing body details |
| a room she already has | the room written as generatable text |
| her own phone, propped ("rig notes") | one camera block — the realness ruling |
| clothes the subject owns | wardrobe table in full garment text |
| Hear = only what a phone captures | per-shot generatable ambience |
| product in her hand, appearance never described | real packshot references, appearance from the packshot only |
| she re-shoots the same moment six ways | six generated variants of shot 1 |
| second-person direction ("you look down the lens") | third-person generatable action |
| questions → email marketing@brand | the gate (0.8) answers or escalates |

## The chain

### 0.1 · Register
- 0.1.1 Slug the run (kebab, from the brief title)
- 0.1.2 Create the run folder
- 0.1.3 Record: brand · brief link · format credit · production route (AI)
  · date · who ran it
- 0.1.4 Open the run record (timeline skeleton: run, brief, brief_doc,
  aspect)

### 0.2 · Inventory — capture everything, interpret nothing
- 0.2.1 Snapshot the brief text verbatim into the run folder (the doc can
  change; the snapshot is what this run executed against)
- 0.2.2 Extract the concept (title + description)
- 0.2.3 Extract every opening: number · Film · Say
- 0.2.4 Extract every frame: number · timecode · Source · Film · Hear ·
  Wearing · On screen · Say
- 0.2.5 Extract WHAT TO SAY; verify it matches the frames' Say lines 1:1
  (mismatch = brief defect)
- 0.2.6 Extract the brand facts inside lines — product name, price,
  guarantee, site, claims — marked compliance-exact, never paraphrased
- 0.2.7 Extract format credit + AI notice
- 0.2.8 Completeness check: every frame has all eight lines, every opening
  has Film + Say, timecodes are continuous. A hole = a brief defect →
  reported upstream, never patched silently

### 0.3 · Translate UGC → AI (the bridge)
- 0.3.1 THE PERSON: derive the character identity from concept + Film +
  Wearing + story; list the load-bearing body details (in the real brief,
  the spotted forearms ARE the ad) → person block draft. VARIATION RULE:
  if the brief comes from a creator's video, the character is a NEW
  person — written identity only, never her photos as reference,
  deliberately different face/hair/details; similar register, never
  likeness
- 0.3.2 THE ROOM: collect every fixed object the frames rely on (mirror,
  open wardrobe door, dresser, window side) → world block draft
- 0.3.3 THE CAMERA: collapse the per-frame rig notes into one camera
  block — the realness ruling (this format: UGC)
- 0.3.4 WARDROBE: Wearing lines → wardrobe table (distinct outfits, full
  garment text, which frames wear which)
- 0.3.5 SOUND: Hear lines → per-shot generatable ambience ("room tone",
  "two soft taps on skin"); music stays out of generation (assembly
  concern, later)
- 0.3.6 PRODUCT: pull the brand's REAL packshots; write the
  product-appearance block from the packshot, never from imagination
- 0.3.7 PROPS & SCREENS: list every object hands touch and every screen
  shown (weather app, family photo, before/after photo); screens and photos
  follow the standing ruling — everything is a digital artifact: the
  pipeline composites a real or constructed artifact into the shot, the
  same way every time
- 0.3.8 GRAMMAR: rewrite second-person camera direction as third-person
  generatable action ("you look down the lens" → "she looks straight into
  the lens")

### 0.4 · Cast sheet
- 0.4.1 Character list (this format: one)
- 0.4.2 Bank check: does an existing character fit? else: new master
- 0.4.3 Master spec: person block + load-bearing details + first outfit +
  world + camera → the master-still prompt, ready to run
- 0.4.4 Voice binding placeholder (filled by 0.5)

### 0.5 · Voice sheet
- 0.5.1 Speaker list (this format: one)
- 0.5.2 Persona paragraph — age, accent, texture, temperament, from the
  concept
- 0.5.3 Pacing check (ruling: smooth and human beats runtime): voice
  runs at natural pace; compute how long each line actually takes and
  how long the film will really run — informational, never a reason to
  rush a line
- 0.5.4 Flag only lines that would sound rushed; the brief's timecodes
  are guides

### 0.6 · Scene sheet
- 0.6.1 Scene list: distinct rooms (this brief: one; multi-scene briefs
  get one world block per scene)
- 0.6.2 Continuity facts: the mark, the mirror, the window side — what
  must never move between frames
- 0.6.3 Final text of the three locked blocks (person / world / camera)

### 0.7 · Shot classification
- 0.7.1 Type every frame: talking / action / product / card ($__) / hard
- 0.7.2 Type every opening the same way — each is a variant of shot 1
- 0.7.3 Per shot: required references (master, packshot, prior still) ·
  target seconds (from the timecode) · on-screen text
- 0.7.4 Variant plan (ruling: control first): build the control opening
  + body, review, then generate the remaining hook variants once the
  body is approved

### 0.8 · The gate — closes before any money moves
- 0.8.1 Missing-asset list (packshots, reference photos)
- 0.8.2 Hard-shot rulings (every screen/prop flagged in 0.3.7)
- 0.8.3 Brief defects from 0.2.8 / 0.5.4 → back upstream
- 0.8.4 Every ambiguity: a written default ruling, or a question to the owner
- 0.8.5 The gate closes only when every item carries a ruling. A check
  whose result is not written down did not happen.

### 0.9 · Manifest + estimate
- 0.9.1 Counts: masters · stills (frames + openings) · voice lines ·
  clips · cards — per variant
- 0.9.2 Priced off the current cost table
- 0.9.3 The number shows on the board before anything runs

### 0.10 · Timeline + hand-off
- 0.10.1 Write the working copy: locked blocks, wardrobe, voice
  (id + speed), one entry per shot (type, target seconds, say, on-screen,
  still action, motion), openings as variants of shot 1
- 0.10.2 Execution order with the two approval gates:
  master still → APPROVE → chained stills; base voice take → APPROVE →
  chained lines; then clips → assemble
- 0.10.3 Hand to the stations: cast → voices → scenes → motion → assembly
- 0.10.4 After assembly: drift check — each frame's Film line is that
  shot's QC checklist

## Upstream note (teardown side, lives in components/)

The teardown machine already carries `production_route = founder / creator
/ AI` in its variables, but no prompt branches on the AI value yet — the
brief always comes out UGC-shaped. Step 0.3 compensates on our side.
The cleaner long-term fix is an AI-lane stage-5 prompt in
`tools/video-teardown/` that emits the person/room/product blocks
directly; that's the component owners' desk, flagged, not ours to edit
from the lab.

## Open

- [ ] Build the parser that runs 0.1–0.10 and lands the result on the
      board (A2 + H6/H8)
- [ ] Variants through assembly: six openings = six cuts (A4)
- [ ] The hard-shot playbook as standard treatments (A5)
- [ ] Verify the pacing budget actually lands the runtime (A6)
