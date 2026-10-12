# objects: the 3D object component

**objects** takes a thing we need in a scene (a prop, a person, a place) and
makes **a finished, satin-finished 3D object**, recorded in the project's
catalogue with where it came from. Built 2026-09-26 for Lost & Found, on
the owner's word: *"establish the process / tool / skill to create 3d objects…
I want to reuse this in the future… it should be a component just like we have
with video teardown."* Brought into the workspace 2026-09-29 nested inside
`video-edit/`; moved out 2026-09-30 to `components/objects/` — production, not
editing, and the owner's own word above already called for it to be its own
component. `components/3d/` (the local generator this calls) moved out the
same day, as a sibling.

**Owner:** the owner (engine and definitions both). **Definitions + curator:**
the owner — `steps.json` and `definitions/finish.json` are the definitions,
changed by him or on his word. **The plane it emits:** a row per object in
`<project>/3d/catalogue.json`, files under `<project>/3d/objects/<id>/`.
**What each catalogue row holds** is what `machine/run.py`'s `make` writes into
`cat["objects"][<id>]` — read it there; this file does not restate it.

## The steps: `steps.json` is the list

ref → mesh → finish → check → web → record

| Step | Who | What |
|---|---|---|
| ref | Claude, **Higgsfield connector** | One clean reference image. The prompt is `prompts/object-reference-v1-damon.md`, word for word; the model is GPT Image 2.5 (`gpt_image_2_5`). A real photo of the thing is sent as a reference image whenever one exists. For a person, the reference is their **character sheet**, never prose. |
| mesh | Claude, **Higgsfield connector** (default) | Image → 3D on Higgsfield (`image_to_3d`, or `multi_image_to_3d` for 2–4 views — use views for anything thin or symmetrical, e.g. the racket). the owner, 2026-09-26: "just use Higgsfield for all the stuff… so we're just clean and clear". `make` requires `--mesh <file.glb>` (the connector's result) or `--local`, which runs the free local generator (`components/3d/make3d`, TRELLIS.2, ~7 min) — background props only; faces and small detail are clearly worse (SI-136 (objects mesh default), 2026-10-08). |
| finish | the machine | The house finish (`definitions/finish.json`): satin, a clear lacquer coat over the object's own colours, like the light on his 3D head. Centred, colours kept. |
| check | the machine, then Claude **looks** | A Blender still. Claude opens it next to the reference: shape, colours, text, proportions. Nothing ships unseen. |
| web | the machine | A small copy the artifact page can spin (quantized, webp textures, packed as JSON because the page host won't serve .glb). |
| record | the machine | A row in `<project>/3d/catalogue.json`: id, what, song word, where it came from, cost, files. |

## Rules

- **Cheapest route that does the job**, then finish locally (the owner, 2026-09-26).
  Reference images cost 2.75 credits; every mesh is Higgsfield credits by default (the developer, 2026-10-08), `--local` 3D is free for background props.
- **Generation goes through the Higgsfield connector**, not scripts calling
  APIs (the owner, 2026-09-26: "we've been using higgsfield MCP"). The machine
  never generates. It only builds, finishes, checks, packs and records.
- **One look across the set:** photoreal, modern iPhone quality, satin finish.
  Not PS2, not low-poly.
- **Consistency:** an object keeps the same colours and shape in every
  scene. People come from their character sheet (`cast/<name>/`), never
  from prose.
- **Every prompt used is kept verbatim** next to the object (`prompt.md`).

## One command

    python3 machine/run.py make <project> <id> --ref <image> [--what "..."] [--word "..."]
    python3 machine/run.py finish <project> <id>        # re-finish an existing mesh
    python3 machine/run.py list <project>               # the catalogue

`<project>` is a folder like `productions/music-video`. Output lands in
`<project>/3d/objects/<id>/`.

**Before you start (objects#6, 2026-10-08):** `cd components/objects/machine && npm ci` (the packages are `machine/package.json`'s; `node_modules/` is not in git); Blender on PATH (`blender --version`), since every make and finish ends in `blender -b`. The free mesh route also needs components/3d's local install (its README, "What's installed"); without it, pass `--mesh <file.glb>` from a paid route.
