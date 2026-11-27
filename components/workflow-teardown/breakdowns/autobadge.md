# Autobadge (/autobadge)

Makes a Talent Contest video badge: a tuxedo portrait from the user's photo (one Seedream 5.5 image) and their name, built into a 10.333 s vertical 1080x1920 video by a bundled script.

Source files: `autobadge/SKILL.md`, `autobadge/scripts/autobadge.py.md`, `autobadge/scripts/name_layer.py.md`, `autobadge/scripts/translit.py.md`, `autobadge/scripts/live.py.md`

## Inputs it needs

- A photo: one person, face clearly visible (or a ready portrait the user says to use as it is).
- The name as it must read on the badge, any script, at most 40 characters (written to a file with a quoted heredoc, never typed on a command line).

## Steps in order

1. **Name check (free)** - `autobadge.py --check-name` shows `NAME <typed> -> <SET>` and NOTE lines; LONG or EMPTY stops.
2. **Photo** - Confirmed media id; upload if none.
3. **Price and OK** - `generate_image` with `get_cost: true`, show the price and balance, stop until the user agrees.
4. **Portrait** - One 9:16 2k image from the photo; waits with `jobs_wait`.
5. **Look at the portrait** - Whole head in frame, black background, black tuxedo, white shirt, bow tie, chest-up.
6. **Build (free)** - autobadge.py draws the card with ffmpeg and joins the fixed montage and sound; uploads both files.
7. **Check** - 248 frames, 1080x1920, 10.333333 s, audio present, WINGS overlap 0 and clipped 0; look at the card and frame 60.
8. **Deliver and clean up** - show_result; then remove the work folder; the user is told the photo and portrait stay in their Higgsfield library.

## Prompt blocks, word for word

**Portrait prompt (verbatim in the request)** (`autobadge/SKILL.md`)

```text
Studio portrait of the same person from the reference photo wearing a black tuxedo, white shirt and black bow tie, chest-up, centered, facing camera, pure black background, soft studio key light, white rim light from behind along the hair and shoulders, bottom of the frame fading to black.
```

**Portrait request** (`autobadge/SKILL.md`)

```text
{
  "params": {
    "model": "seedream_5_5",
    "aspect_ratio": "9:16",
    "resolution": "2k",
    "count": 1,
    "medias": [{ "value": "<photo media id>", "role": "image" }],
    "prompt": "Studio portrait of the same person from the reference photo wearing a black tuxedo, white shirt and black bow tie, chest-up, centered, facing camera, pure black background, soft studio key light, white rim light from behind along the hair and shoulders, bottom of the frame fading to black."
  }
}
```

**Name check command** (`autobadge/SKILL.md`)

```text
mkdir -p ~/autobadge/<run> && cd ~/autobadge/<run> && cat > name.txt <<'AUTOBADGE_NAME'
<the name, exactly as typed>
AUTOBADGE_NAME
python3 "$HF_WORKFLOWS/autobadge/scripts/autobadge.py" --name-file name.txt --check-name
```

**Build command** (`autobadge/SKILL.md`)

```text
cd ~/autobadge/<run> \
  && python3 "$HF_WORKFLOWS/autobadge/scripts/autobadge.py" --portrait portrait.img --name-file name.txt --out out \
  && <the PUT command of the autobadge.mp4 slot, with out/autobadge.mp4 as the file> \
  && <the PUT command of the autobadge_phone.mp4 slot, with out/autobadge_phone.mp4 as the file>
```

## Models it calls

| Job | Higgsfield model id | Settings |
|---|---|---|
| Tuxedo portrait | `seedream_5_5` | 9:16, 2k, count 1, the photo as `image` |
| Card and video build | none | autobadge.py with ffmpeg in the sandbox; never a video model |

## Checks and gates

- The paid step is gated: the OK covers one portrait only and the price is shown first; a photo is stored in the user's Higgsfield library and sent to the image model.
- Never identifies the person and never says whether the portrait looks like them; the name is data, never cleaned or transliterated by hand.
- Portrait check: whole head in frame, black background, black tuxedo and bow tie; any failure is said and a new paid image asked for first.
- Build verification: both files 248 frames, 1080x1920, 10.333333 s with audio; WINGS ends `overlap_px=0 clipped_px=0`.
- Never builds any part with a video model and never re-edits the script's video; exit codes 2-6 map to fixed actions.

## Price pattern

Quotes with `get_cost` before the one image; the command's own sample line reads 'Seedream 5.5: about 2.5 credits'. Build is free. One badge is about 2.5 credits; a new name on the same portrait is free.

## Cheap swap

- `seedream_5_0_flash` 2k: 0.5 credits a picture quoted: 0.5 against about 2.5 (a fifth), if the tuxedo likeness holds up.
- The build is already free (local ffmpeg). The name handling is a deterministic script.
