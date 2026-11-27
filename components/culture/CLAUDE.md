# components/culture — what a post's people recognize, one read for every chain

**culture** takes **a post** (a video, or a still picture post) and gives back **what the people looking at it
recognize and how they read it**: the references, the format, the slang, the double meanings, the joke in its words,
other jokes of the same kind, and what a remake must keep. It writes nothing for a brand: no product, no pitch.

the owner, 2026-10-27, on a picture swipe captioned "how to get the best NECK" that the picture chain read as nonsense:
*"I think we have some sort of humor tagging inside of video teardown. Do we have it in image teardown? ... shouldn't you
be able to just reuse that element from video into image instead of rewriting everything from scratch? ... some of that
cultural stuff should be its own component. That way ... video and image can pull from that same type of context. And
then we can just refine that context when we do research."*

**Owner:** the owner (engine and definitions both). Created directly 2026-10-27 (lab skipped): the video teardown's culture
read (stage 1k, since 2026-10-05) moved here by `git mv` with its history, so both chains call one read.

## Who calls it

| Chain | Step | Reads | Writes |
|---|---|---|---|
| `components/video-teardown` | stage 1k (`machine/chain.py` `PROMPT_HOMES`) | the teardown record, the post's caption and comments, the video attached | `stages/1k-culture.md` (+ `1k-culture.json` by `machine/culture_json.py`) |
| `components/image-teardown` | step 1k (`tools/run.py`, `prompts_dir("1k")`) | `out/01-teardown.md`, `assets/post-talk.md` | `out/01k-culture.md` |

Writing stages that read it: video's writing and spice stages; `components/image-writing` stage 5 v7 (`{culture_read}`:
a joke the read marks load-bearing stays in every variation).

## The four new-resident questions

- **Engine + owner:** none of its own yet: each chain's runner sends the prompt (video: Gemini with the video; pictures:
  `image-teardown/tools/gemini_text.py --search`, Google Search on). The parser `culture_json.py` and the caption and
  comment puller `culture.py` stay in `video-teardown/machine/` until they move with their readers. Owner the owner.
- **Definitions + curator:** `prompts/stage1k-culture-vN-owner.md`, the highest `-vN-` runs (v4: any post, the words
  read twice, THE JOKE IN THE WORDS and SAME-KIND JOKES); `archive/` never runs. Curator the owner. A changed prompt is a new
  file. The refined context it feeds is each avatar's culture map, `brands/<brand>/core-avatars/<avatar>/culture-map.md`
  (built from these reads and research, read-only to machines).
- **Plane:** none of its own; each chain files its read in its own run.
- **Manifest per entry:** none; the prompts are versioned files.
- **Runs by:** both.
