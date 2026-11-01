# Suno (v5 / v5.5, by hand, no API) — what it takes, and what works

*Rendered from `components/model-inputs/inputs/suno.json` (read 2026-10-27, status draft) by `input_rules.py render`; never hand-edited.*

## Limits

- style box chars: about 1,000 on v5 / v5.5 (community-tested; Suno publishes no limits table); older v4 about 200; text past the limit is cut silently
- lyrics box chars: sources conflict: about 3,000 or up to 5,000; stay near 2,500
- title chars: about 100 (one third-party source)
- style descriptors: 3 to 5 simple, 8 to 15 detailed, about 20 maximum; sweet spot 4 to 7
- genres max: 3
- exclusions max: about 2 to 3
- syllables per line: 6 to 10
- lines per section: 4 standard, 8 longer
- pipe stack max: 7
- voices upload seconds: 15 to 240
- voices kept seconds: 120
- custom models: 6 tracks minimum, 3 per account (Pro or Premier)
- numbers are: community figures except the sliders, which are Suno's own help page; confirm in the app before a batch
- House: how the chain writes style, exclude, lyrics (a section tag over every part) and sliders from the brief's song block and its style row's `suno` line; the take goes through the same song gate as any song ad (words heard in order, last line finished); door manual (registry transport), by hand on suno.com

## The prompt structure that works

- **Style box order: genre, tempo, mood, instruments, vocal style, era, reference. Put what matters most first.**
- **Use 4 to 7 descriptors; cut any two that say the same thing; stacking 15 or more dilutes it.**
- **One primary genre plus one modifier, three at most; strong genres (pop, rock, electronic) override weak ones (grunge, math rock, swing).**
- **Name specific instruments, two or three core textures only.**
- **Give BPM as a number and always pair it with a mood word.**
- **Put a section tag over every part of the lyrics; without them the whole song sits at one energy.**
- **Set the main vocal in the style box and the gender explicitly; use the lyrics box for a change within the song.**
- **Use the Exclude field for unwanted traits rather than 'no X' in the style box, and keep it to two or three.**
- **Move one slider at a time; weirdness low for commercial work; style influence high when the tags are vague.**
- **Write 6 to 10 syllable lines and 4-line sections; shorter lyrics make shorter songs, use Extend for length.**
- **When a take misses, change one thing before regenerating; the same prompt again gives the same result.**
- **Whatever Suno makes goes through the same song gate as any song ad: every script line heard in order, last line finished. Suno may sing words the lyrics do not hold.**

## Avoid

- Short poetic lines, ALL CAPS phrases or quotes in the style box: they get sung.
- An empty lyrics box.
- 'Don't' or 'no X' phrasing inside the style box.
- Contradictory tags such as calm with aggressive, or more than three genres.
- A BPM with no mood word.
- Putting the vocal style only in the lyrics box.
- More than three or four instruments.
- Relying on 'ethereal', 'crescendo' or 'realistic', and on chorus modifiers: they are often ignored or overridden.
- More than about seven elements in one pipe-stacked tag, or Bridge/Outro/Build used more than once.
- Trusting v5.5 to hold the style the whole way: it can drift to generic pop or change when extended.
- Naming a living artist as the style: the song-ad style is a ruled row, no free text.
