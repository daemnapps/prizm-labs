# Editor skills — what editors trigger inside Higgsfield


the owner, 1 Oct 2026: the editors work in Higgsfield; they should know where to pull briefs and where to
deliver without being told, by triggering a skill.

| Skill | Trigger | Does |
|---|---|---|
| `pull-briefs` | "pull briefs for Brand A" / "pull briefs for Brand B" / "next brief" | reads the live queue (only the rows its `For` column gives this person: video rows for editors, image and carousel rows for designers; a row sent back to them first), claims, unpacks, reviews, makes the asks, hands to the edit — the Pull-briefs prompt v2 |
| `edit-brief` | "edit this brief" / "cut it" / "make the master" | writes the cut sheet, listens to every clip, runs our edit kit in Higgsfield's sandbox (pulled from the public repo's `tools/video-edit-kit/`): cut to the sound, captions and cards, punch-ins, frame fixes, the 4:5 safe-zone check, loudness, one 9:16 master; then the editor's "why it works" note into DELIVERED.md |
| `deliver-brief` | "deliver" / "I'm done" | uploads the finished files to `briefs/delivered/<brief>/` (the brief as the queue names it, e.g. `crush brief-0003`), writes DELIVERED.md — an OLD return place: the one return place is `runs/handoffs/<role>/<brand>/<brief key>/returned/` (components/naming/WHERE-EVERYTHING-GOES-owner.md); the delivery check reads there |

**One place per brand** (shared drive *Shared Assets*): `brands/<brand>/briefs/` — `QUEUE.md`, the packages,
`claims/`, `delivered/<brief>/`. The folder links are inside the skills. They open for anyone with the link and
can be written to, so these skills stay in this private repo and go only into the editors' own Higgsfield
accounts — never the public Prizm Labs repo.

**After delivery, automatically (hourly, `~/.local/bin/brief-queue.sh`):** the delivery is renamed to the
naming standard (components/naming/delivery_rule.py) and filed as a card in
`Shared Assets/meta/<brand>/1-check/<video|image>/` for the approval page. Only the owner's Approve sends it to Meta.
