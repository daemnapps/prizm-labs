# Playbook builder v1 — draft the specialised workflow for a NEW family of ad

GUARD: work only from the swipe records and the nearest playbook below. Do not invent
a brand, product, person, run, price or ruling. Every failure you list must name the
run it came from. Never name the swipe's brand, product, team or people — say "the
swipe's brand", "the subject", "a reporter": a playbook serves every brand. You have no runs for this family yet, so the failure list starts
EMPTY — risks you foresee go in `watch_for`, never in `failures`.

You are writing a PRODUCTION PLAYBOOK: the per-format settings the shared AI video
chain (teardown → writing → elements → voice/song → storyboard → pictures → clips →
edit) runs with for one kind of ad. The shared chain stays the same; the playbook
says, for THIS shape of ad, what to do differently and why. The matcher has already
decided this swipe is NOT close enough to any family we have — so name what makes
it its own workflow.

The aim, in the owner's words: volume with a machine, low cost per ad, and never AI
slop. Prefer the cheapest setting that keeps the look: a smaller picture size or a
lower quality where the frame is small or moving, several clips from one picture
where shots share a set-up, cast and sets reused across ads, short clips.

## The swipe

FORMAT id: {format_id}
STYLE id: {style_id}
What the doctrine read says the format is: {doctrine_format}

Its structural signature (read by machine — keep it unless the records plainly say otherwise):
{signature}

Triage:
{triage}

Teardown (the record of the swipe as it is):
{teardown}

Frame map summary:
{framemap}

## The nearest playbook we have (start from its shape; change what this swipe needs)

{nearest_playbook}

## Write

Return ONE JSON object in a ```json fence and nothing else. Keys, all required:

- "name": a plain name for this kind of ad, in search words (no jargon, no brand)
- "family": the family id (normally the same as the format id)
- "what": one sentence — what a piece of this shape is
- "signature": the eight keys audio · speakers · address · settings · product_role · pacing · capture · story
- "specialised": a list of {"what", "why"} — every setting that differs from the nearest
  playbook, and why THIS swipe needs it (cite what in the records shows it)
- "stage_order": the stations in the order this format runs them (audio first when a
  song or a voice drives the cut)
- "stages": the same stage keys the nearest playbook uses (audio, song, pictures, clips,
  cast, hooks, captions, gates, edit), each with the nearest's fields; null = the shared
  chain's own setting
- "failures": [] (empty — see GUARD)
- "watch_for": a list of the failures this shape invites, each one line
- "cost": {"target_usd_per_ad": a number, "why": one line}
- "quality_bar": a list of "not slop" checks specific to this format — each one a thing a
  reviewer can see in the finished ad, pass or fail
- "rulings": []
