# Stage 4 — Motion (clips)

Status: **baseline only** — to be built out in detail.

## Job

Turn stills and voice takes into clips. Output of this stage — a bank of
finished clips named per story beat — is the machine's finished product,
handed to the edit process (separate build).

## Baseline (from the proven run)

Three shot types, one station:

- **A. Talking shot** — scene still + voice take, NO prompt. The model
  animates and lip-syncs to the track. ~4s per beat, ~6s b-roll. The
  volume mode.
- **B. Cinematic shot** — 0–2 refs + full written direction, model
  generates its own ambience. 8–15s single takes; works with no image for
  establishing shots.
- **C. Product hero** — product photo + motion direction, silent, slow,
  label-first. 8–9s.

Re-rolling is the iteration: keep the same (still, voice) pair and re-roll
until the motion lands. The pair is the asset.

## The slot

Any video model that can: animate from a start frame, **lip-sync to a
supplied audio track** (the one capability that cannot be faked), follow a
written shot direction with or without a reference, and optionally
generate its own ambient audio.

**Audition:** a 4s lip-synced talking beat from a still + a voice take —
mouth matches the words.

## To build out

- [ ] Shot-direction template for mode B (action beat-by-beat, sound
      spelled out incl. negatives)
- [ ] Duration rules per shot type; when a long single earns its length
- [ ] Re-roll budget: how many rolls before the still or take is the
      problem
- [ ] Clip naming/banking so the edit process can consume them blind
- [ ] Candidates for the local slot — may be TWO models (lip-sync vs
      prompted cinematic) if no one local model passes both (proven /
      testing / rejected)
