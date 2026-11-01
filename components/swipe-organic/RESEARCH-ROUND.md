# The research round — the checklist every pull runs through

*the owner, 2026-10-17, after a fight-format pull searched only fights for Fed-Up King and
missed NBA/NFL, his biggest world: "how can we ensure this actually is triggered on
the next research round?"* Page: **The Research Round**, (private page)

**Trigger:** say "research <avatar>" (any brand, any avatar). The team skill
`.claude/skills/research-round/` runs these steps with `round.py`
(`worlds → plan → pull → rank`). `components/apify/tiktok.py` refuses a paid search
that does not come from an approved, covered plan, so the gates hold even for a
session that never read this file.

`METHOD.md` is the why. This is the order, with a stop at each gate. A session that
runs any organic pull for an avatar (My Feeds Dig, `components/apify/tiktok.py`, a
hand-made search list) goes through every step, in order, and says on the page which
gate each one passed.

## 1. Read the avatar first

- The avatar's profile (`brands/<brand>/core-avatars/<avatar>/profile.md`): what he
  watches, the shows, the sports, the music.
- His feeds in My Feeds (`records/avatar-feeds/<brand>--<avatar>*`): count what his
  posts actually touch, and write down his **top worlds** by count.
- Output: a short list of his worlds, biggest first, with the count beside each.

## 2. Plan the seeds from that list — GATE: coverage

- Seeds are scaffolding (`METHOD.md`): just enough to reach real people.
- **Every one of his top worlds gets at least one seed.** A world in his top three
  with no seed holds the pull. This is the gate that was missed on 17 Oct.
- An idea for a new world (wrestling, anime) can be added as a seed on top, never in
  place of his own worlds.
- One avatar per plan. Two avatars are two plans, never one mixed list.

## 3. Show the plan and the price — GATE: his yes

- Searches, posts per search, total posts and the hard cap in dollars, on the page.
- Nothing spends until the owner says go (rule 0 in `CLAUDE.md`; credits plan before pull).

## 4. Pull wide, follow the people

- Aim for about 1,000 posts per avatar.
- Prefer **Dig** on My Feeds: it follows the commenters out to their own feeds, which
  is where the worlds nobody named come from.

## 5. Rank — the house rules

- **2026 and later only.** Drop older posts before ranking; formats evolve. Say how
  many the floor removed.
- Remove ads and repeats.
- Score = views + likes + comments (the house score, `components/apify/apify.py`
  `score()`); show shares and saves beside it.
- **Rank each avatar on his own posts**: his top 50 (or top 100), then his worlds by
  how many of their posts made it, with typical (median) views as the tie-break.

## 6. Show it

- One page per round: each avatar's world ranking, his top formats with real
  thumbnails, the top posts linked.
- File every kept post into My Feeds under that avatar, so teardowns trigger from there.

## 7. The matrix — formats × his problem × the bodies that pull

- Once an avatar has a formats round and a problem round, `matrix.py` builds his creative matrix
  (Outlier → Matrix tab): his top formats, the problem moments in his own words, and the problem
  videos that already pull, grouped by kind. Every category and video opens to read.
- The merged concepts live in `runs/swipe-organic/<brand>/matrix-<avatar>/concepts.json`.

## 8. He picks — then write

- the owner picks the formats (three this round). Writing starts only on his picks.
