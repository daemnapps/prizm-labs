# Video Tools Map

Page: https://claude.ai/artifact/LvQRVQExDCQEus1LqUQXrX. Source: `video-tools-map-owner.html`.

Teardown and writing are shared. Production splits by how a video is made. Edit and hand-off are shared again.

## Production lines

| Line | Example | Unit of work | Tools | State |
|---|---|---|---|---|
| Talking | One person to camera, B-roll on top | A take of the line | Voice, start picture, Seedance | Runs |
| Movie | Micro-drama, skits | A whole scene | Cast, sets, Seedance up to 15 s, alternate door up to 30 s | Not built as its own line |
| Song | Sung story | A lyric line | Suno, MiniMax H3 | Runs, costs too much |
| Swap | Swipe shot with our cast | A swipe shot | Genjutsu object swap | Runs shot by shot |
| Drawn in code | Thread, stick, cartoon, anime, low-poly | A screen or beat | `thread`, `stick`, `cartoon`, `anime`, `lowpoly` | Works, sits in video-edit |

## The missing step

No single step sends a video down a different line. There are 13 playbooks and 2 full workflows.

## Scene has three meanings

- The chain's word key: one spoken line.
- The storyboard: one swipe cut.
- The September rule: a paragraph, one clip.

## Words

- A-roll: the person carrying the line.
- B-roll: cover shots over a line that keeps playing.
- Cutscene: a moment that plays as its own scene. No word for it in the system yet.
- Element: person, place, prop, voice or look, built once and used inside scenes.

## Next

1. Add the routing step after writing.
2. Pick one meaning of scene: one continuous moment, built in one generation as far as the model allows.
3. Build the Movie line first.
4. Add cutscene from the brief onward.
5. Move the code tools into production on one shared base.
6. A format that does not fit gets its own line, built from existing tools.
