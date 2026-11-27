# Video Editing (Higgsedit)

Cuts supplied footage and builds file-backed motion graphics (titles, overlays, shaders, native layouts) as an editable Higgsedit project and a rendered movie.

Source files: `video-editing/SKILL.md`, `video-editing/references/assembly.md`, `video-editing/references/compose.md`, `video-editing/references/failure-modes.md`, `video-editing/references/caption-titling.md`, `video-editing/references/shot-blueprints.md`

## Inputs it needs

- Footage, audio and images to import (media ids, downloaded in the sandbox).
- The edit described as cuts, trims, soundtrack changes, layout, animated text, overlays or title cards.
- Canvas size and fps (fixed at project creation), e.g. 1080x1920 at 30.

## Steps in order

1. **Reserve output slot** - `media_upload` first, so the render and the PUT can share one sandbox call.
2. **Create project** - `project({dir,size,fps,background})`; `p.add(file)` imports each asset.
3. **Place footage and audio** - `p.cut(handle,{from,dur,at,fit})`; `from` is source seconds, `at` is timeline seconds.
4. **Compose graphics** - `p.compose(nodes,{at,dur,name,camera})`: frames, text, rects, paths, masks, GLSL, 2.5D camera.
5. **Check frames** - `higgsedit frame` / `sheet` / `inspect`; `check` validates inputs.
6. **Render** - `p.render(out,{codec,depth,bitrate})`, then ffprobe the streams.
7. **Upload and confirm** - curl PUT in the same call, `media_confirm` only after HTTP 200.

## Prompt blocks, word for word

**Whole-edit script (the canonical shape)** (`video-editing/SKILL.md`)

```text
export default async ({ project }) => {
  const p = await project({ size: "640x360", fps: 24 });
  p.compose(
    <frame width={640} height={360} padding={40}>
      <rect
        width={400}
        height={80}
        fill="#32acff"
        animate={[{ property: "scaleX", from: 0, to: 1, duration: 0.6 }]}
      />
    </frame>,
    { dur: 2 }
  );
  await p.frame(1, "renders/frame.png");
  await p.render("renders/video.mp4");
};
```

**Commands** (`video-editing/SKILL.md`)

```text
higgsedit build edit.jsx
higgsedit inspect PROJECT --id CLIP_ID --at 1.2
higgsedit frame PROJECT 1.2 --out renders/frame.png
higgsedit sheet PROJECT --times 0.1,1,1.8
higgsedit render PROJECT --depth 10 --codec hevc --bitrate 8M --out renders/master.mp4
higgsedit do PROJECT VERB --help
```

**Cut, compose, render example** (`video-editing/references/assembly.md`)

```text
export default async ({ project, text }) => {
  const p = await project({ size: "1080x1920", fps: 30 });
  const source = await p.add("media/source.mp4");
  p.cut(source, { from: 0, dur: 8 });
  p.compose(text("Caption", { fontSize: 64 }), { at: 1, dur: 2 });
  await p.render("renders/final.mp4", { depth: 10, codec: "hevc", bitrate: 8_000_000 });
};
```

**Useful commands** (`video-editing/references/assembly.md`)

```text
higgsedit probe media/source.mp4
higgsedit check .
higgsedit build edit.jsx
higgsedit frame . 1.5 --out renders/frame.png
higgsedit render . --out renders/final.mp4
ffprobe -v error -show_entries stream=codec_type renders/final.mp4
```

## Models it calls

| Job | Higgsfield model id | Settings |
|---|---|---|
| Edit and render | none | Higgsedit CLI v0.14.0 pinned (`f39e3bc5882b`) in the sandbox; H.264 default, HEVC Main10 or AV1 at depth 10 |

## Checks and gates

- Pinned CLI identity: if `/opt/fable/VERSION.json` differs or help lacks a flag, it reports a runtime mismatch and stops.
- A whole-script build replaces the timeline: for shared or human-edited projects it uses `inspect` and bounded `do`/`ops` instead.
- Composed media nodes are picture-only; audio must stay on the spine or be mixed after render.
- Unsupported (refuses): HTML scenes, runtime animation callbacks, native LUTs, shader adjustment nodes.
- A script with no render call, or an interrupted render, is not a finished movie; there is no hosted-editor publish.

## Price pattern

No credits: no generation model is called. Nothing in `_prices.md` applies.

## Cheap swap

- Free already. Local ffmpeg on this Mac covers plain cuts, trims, audio mixing and overlays; HyperFrames (the team's own HTML renderer) covers motion graphics. Saving: 0 credits either way.
