# Movie-level depth in AI ad scenes

Research, 2026-10-28. For the line: 3D scene in Higgsfield 3D Jutsu → render from a set camera → Higgsfield "print" to a photoreal plate → cast member generated into the plate (GPT Image 2.5 for stills, Seedance 2.5 for clips).

**The problem it answers:** a cast member generated into a room picture looks printed into the scene — flat front light, no contact shadow, subject sharper and brighter than the room, no depth.

**The short answer:** the person looks pasted because the room's light never touches them. Fix it in three places, in this order:
1. **Build depth and light into the 3D scene.** Put something in the foreground, light the room from the side or behind with visible lamps, add haze, and set a real lens and camera height.
2. **Print the plate with that light kept.** Tell the print to keep the light's direction and colour, not to "make it photoreal" in general terms.
3. **Generate the person *into* that light.** Name where the light comes from, what it falls on, where the shadow lands and how sharp the person is compared with the room. Never just say "place her in the kitchen."

Every claim has its source on the line. Lines marked *(practice)* are our own synthesis from the sourced principles, not a quoted source.

---

## 1. What makes a frame read as deep

| Cue | What it does | How to get it in our scenes | Source |
|---|---|---|---|
| **Foreground / midground / background layers** | Layers make a flat picture read as 3D. "The more separation you create between layers, the more depth." | Always model a near object: a counter edge, a jar, a doorframe or a plant. Put it in the frame's near third, partly cut off by the frame edge. | [StudioBinder – Depth in film](https://www.studiobinder.com/camera-shots/composition/depth-in-film/), [StudioBinder – Foreground](https://www.studiobinder.com/camera-shots/composition/foreground-in-film/), [PremiumBeat](https://www.premiumbeat.com/blog/mastering-foreground-middleground-background-in-cinematography/) |
| **Occlusion / overlap** | The strongest cue for which thing is in front. Overlapping edges give the order of things even when distances are unknown. | Let the foreground object overlap the subject a little: a counter in front of the hips, a jar in front of a forearm. A subject with nothing in front of them floats. | [StudioBinder](https://www.studiobinder.com/camera-shots/composition/depth-in-film/), [Perspective Research Centre – depth cues](https://perspectiveresearchcentre.com/depth-cues/) |
| **Relative / familiar size** | Things of known size (mugs, tiles, doors) set the scale and distance. | Repeat objects of known size at different depths, such as the same jars near and far, and use floor tiles or wood grain running back. | [Perspective Research Centre](https://perspectiveresearchcentre.com/depth-cues/), Cutting & Vishton framework via [Wolfe, Sensation & Perception](https://learninglink.oup.com/public/files/cdn/wolfe4e/wa06.01.html) |
| **Texture gradient / leading lines** | Lines (stairs, counters, hallways) running through the layers pull the eye back. | Run the counter or worktop diagonally away from the lens. Do not set it square to the camera. | [StudioBinder](https://www.studiobinder.com/camera-shots/composition/depth-in-film/) |
| **Lens and camera distance** | A wide lens exaggerates the near/far size difference. A long lens flattens it. The real driver is how far the camera is from the subject. | Use a 28–40mm equivalent with the camera close to the foreground object for "deep". Use 50–85mm for a flatter portrait. Set the 3D camera's focal length and keep the same value in the prompts. | [PMC – perspective vs focal length](https://pmc.ncbi.nlm.nih.gov/articles/3440305), [Morphic – focal length](https://morphic.com/es/ai-glossary/focal-length) |
| **Camera height** | Eye-level or chest-height reads as natural. A counter-height camera puts the worktop in the foreground. | Kitchen shots: camera at counter or chest height (~1.1–1.3 m), 1–2 m from the subject. 3D Jutsu's own example locks camera distance and chest-height framing for consistency. | [Higgsfield – 3D Jutsu](https://higgsfield.ai/blog/higgsfield-3d-jutsu) |
| **Depth of field / focus falloff** | Shallow focus isolates the subject and tells the eye where to look. | One focus plane, on the subject's eyes. The foreground object goes soft, the background softer. Write it as "shallow-but-honest focus". | [StudioBinder](https://www.studiobinder.com/camera-shots/composition/depth-in-film/), [Higgsfield – 3D Jutsu](https://higgsfield.ai/blog/higgsfield-3d-jutsu) |
| **Atmospheric perspective (haze)** | More haze between the camera and the background makes distant areas brighter, lower in contrast, less saturated and slightly bluer. | Add a thin room-wide volume (density ~0.1 to start) so the back wall is lower contrast than the subject. | [Neil Oseman – The Science of Smoke](https://neiloseman.com/the-science-of-smoke/), [J.S. Abbott – God rays in Blender](https://jsabbott.artstation.com/blog/Z4Y77/tutorial-creating-god-rays-in-blender-3d-cycles) |
| **Haze needs backlight** | Smoke "shows up best when it's backlit". Front light barely shows it. | The window or key sits behind or to the side of the subject, never behind the camera. | [Neil Oseman](https://neiloseman.com/the-science-of-smoke/) |
| **Motivated light / practicals** | Every light has a reason to be there in the scene (window, lamp, fire), so the place reads as real and not as a lit set. Deakins's work uses sources with a logical origin. | Model the practicals: a window, a pendant over the counter, an under-cabinet strip. They are the light *and* bright spots that set depth. | [StudioBinder – practical lighting](https://www.studiobinder.com/blog/what-is-practical-lighting/), [No Film School – practicals primer](https://nofilmschool.com/2015/07/practical-light-primer-how-practical-lighting-bring-cinematography-to-life), [FilmLocal – Deakins style](https://filmlocal.com/?p=1446849), [ASC – Deakins on Sicario](https://theasc.com/blog/the-film-book/sicario-interview-with-roger-deakins-asc-bsc) |
| **Backlight / rim separation** | A light behind and to one side of the subject puts a bright edge on them that separates them from the background. Keep it dimmer than the key. It works best against a darker background. | A window or practical behind the cast member, three-quarter back. Their hair and shoulder edge catch it. | [No Film School – rim light](https://nofilmschool.com/what-is-a-rim-light-3-point-lighting), [How To Film School – back light](https://howtofilmschool.com/dictionary/back-light-film/), [Imaging Resource](https://www.imaging-resource.com/news/2012/10/05/friday-photo-tip-how-to-shoot-into-the-light-to-create-dramatic-images) |
| **Alternating light and shadow planes** | Bands of light and dark running back through the space build depth. | Let the room have a lit zone (the subject), a darker mid zone, then a lit back zone (window). Do not light evenly. | [Neil Oseman – Taking Decisions Lightly pt 2](https://neiloseman.com/taking-decisions-lightly-part-2/) |
| **Colour and value separation** | Contrast in light vs shadow and warm vs cool directs attention. | Warm key on the subject, cooler fill and background. Subject a stop brighter than the background, not five. | [Oseman – blue gels for distance](https://neiloseman.com/taking-decisions-lightly-part-2/), [fal.ai – GPT Image prompting](https://fal.ai/learn/tools/prompting-gpt-image-2) |
| **Parallax (moving shots)** | A sideways camera move makes near things slide faster than far ones. That is the strongest depth cue in motion, but only when there are clear layers. | For clips, use a slow truck or slow push past the foreground object. | [Atlabs – AI camera moves](https://www.atlabs.ai/blog/ultimate-guide-ai-camera-moves-prompts), [Morphic – parallax](https://morphic.com/ai-glossary/Parallax-Effect), [Crepal](https://crepal.ai/blog/?p=8162) |

---

## 2. How film and VFX make a person sit inside a plate

| Match | How the pros do it | Our version | Source |
|---|---|---|---|
| **Light direction** | Read the shadows in the plate: which way they fall, how long, how sharp. That locates the key light. | Write the key's direction into the shot prompt as a fact: "window light from frame left, behind her shoulder". | [Outpost VFX – 18 lighting tips](https://outpost-vfx.com/en/news/18-pro-tips-and-tricks-for-lighting), [Fiveable – CGI integration](https://fiveable.me/intermediate-cinematography/unit-13/lighting-compositing-cgi-integration/study-guide/5g2LjycsdOj6B1Ts) |
| **Light softness** | "A very long sharp shadow… the light source is very low, small, and strong." Short soft shadows mean a large, high source. | Pick soft (window, overcast) or hard (sun patch) once in 3D, and say the same word in the print and the shot. | [Outpost VFX](https://outpost-vfx.com/en/news/18-pro-tips-and-tricks-for-lighting), [Higgsfield Relight – soft/hard](https://higgsfield.ai/blog/Relight-Director-Style-Cinematic-Lighting) |
| **Colour temperature** | The plate's neutral midtones show its colour cast. Gel the lights to match. If the plate's shadows are open and soft, the subject must not drop into deep black. | Name the key's warmth ("warm 3200K tungsten pendant") and the fill's ("cool daylight from the window"). | [Photography Icon – lighting for composites](https://photographyicon.com/how-to-light-portraits-for-a-real-looking-composite/), [Fiveable](https://fiveable.me/intermediate-cinematography/unit-13/lighting-compositing-cgi-integration/study-guide/5g2LjycsdOj6B1Ts) |
| **Black and white points** | Grade the inserted element so its darkest and brightest values match the plate's blacks and whites (a toe / blacks-match step). | The person's darkest shadow should be no darker than the room's darkest shadow. Their brightest skin highlight should be no brighter than the brightest lit surface near them. | [UAL CG process blog](https://23008828.myblog.arts.ac.uk/?p=681) |
| **Exposure / values** | Sample the same patch in both (grey card or chart) and match the RGB and luminance. | *(practice)* Compare the subject's face brightness with the lit counter beside them. If the face is brighter than everything else in the room, it reads as pasted. | [Outpost VFX](https://outpost-vfx.com/en/news/18-pro-tips-and-tricks-for-lighting) |
| **Grain, sharpness, lens artefacts** | Match grain structure, sharpness, motion blur, bokeh and chromatic aberration. CG that looks too clean is missing microtexture and camera artefacts. Add grain last. | Ask for "same grain and softness as the room". Never "ultra sharp" or "8K". | [Gravitee – compositing overview](https://gravitee.io/corpus/gen-1783/computer-animation/compositing.html), [O'Reilly – Digital VFX ch. 6](https://www.oreilly.com/library/view/digital-visual-effects/9780133812664/ch06.html) |
| **Light wrap / edges** | Blur the background and let its colour bleed onto the subject's edges, so the background light "wraps" around them. | Say "background light spills softly onto her edges / hair rim". | [Vindral – light wrap](https://composer-docs.vindral.com/operators/operators-light-wrap.html), [Nukepedia – light wrap](https://www.nukepedia.com/knowledge/general-tutorials/written-tutorials/sledge-hammer-to-treat-light-wrap/) |
| **Contact shadows** | Two kinds: a *cast* shadow that matches the light direction, and a soft *contact* or ambient-occlusion shadow where things touch. Both are needed for grounding. | Name both: "her forearms rest on the counter with a soft dark contact shadow; her body casts a shadow to frame right". | [Versluis – Blender shadow catcher](https://versluis.com/2023/05/creating-a-shadow-catcher-in-blender-for-cycles-and-eevee), [Needle – contact shadows vs shadow catcher](https://engine.needle.tools/docs/api/ShadowCatcher), [Fiveable QC list](https://fiveable.me/intermediate-cinematography/unit-13/lighting-compositing-cgi-integration/study-guide/5g2LjycsdOj6B1Ts) |
| **Bounce** | Objects take on colour bounced from the surfaces near them. A missing bounce kills believability, even when the shadow is right. | "Warm bounce from the wooden counter on her lower face." | [Otoy forum (shadow catcher, no bounce)](https://render.otoy.com/forum/viewtopic.php?p=426341), [Outpost VFX](https://outpost-vfx.com/en/news/18-pro-tips-and-tricks-for-lighting) |
| **Lens / DOF match** | The insert must have the plate's lens: perspective, focus distance and bokeh. | The same focal length and eye-line height in the 3D camera, the print and the shot. The subject is in focus, but no sharper than the in-focus counter next to them. | [Gravitee](https://gravitee.io/corpus/gen-1783/computer-animation/compositing.html) |
| **Checking** | Zoom in and out, mirror the image, push the exposure up and down to find mismatches. | Use the same three checks on every still before it goes to video. | [Outpost VFX](https://outpost-vfx.com/en/news/18-pro-tips-and-tricks-for-lighting) |

---

## 3. How the best AI creators get real depth today

- **Blockout → render → image pass → video.** Keep the 3D scene rough: boxes and stand-ins, with the camera and its move locked. The render's job is depth, framing and placement. An image model then finishes the first frame "keeping the composition and pose unchanged", and that frame becomes Seedance's start frame. ([Flick – Blender for AI filmmaking](https://flick.art/blog/blender-ai-filmmaking), [Invideo FAQ](https://invideo.io/faq/how-do-you-use-a-blender-blocking-render-as-a-camera/), [Contra – Blender blockout to AI visuals](https://contra.com/community/nHij9r6C-blender-blockout-to-ai-generated-property-visuals))
  - **Caution:** Flick says over-detailed blockouts confuse the model and leaves lighting to the generation stage. For us, lighting *is* the problem, so we model light direction and practicals even when the geometry stays rough. *(practice)*
- **Use the 3D render as structure, not as style.** For a local or ComfyUI line, render depth, Canny, normal and segmentation passes from the same camera. Depth locks the layout, Canny locks the silhouettes. Recommended depth models are DepthAnything v2. Lowering depth-ControlNet strength or end % gives the model room to add detail. ([Flick](https://flick.art/blog/blender-ai-filmmaking), [RunComfy – IC-Light video relight](https://www.runcomfy.com/it/comfyui-workflows/comfyui-ic-light-workflow-for-video-relighting))
- **Relight the subject to the background.** IC-Light (lllyasviel) has a text-conditioned model and a background-conditioned model, both taking a foreground cutout. It is the standard open tool for making a person take a background's light. Use BiRefNet, not RMBG 1.4, for commercial cutouts. Keep the light-map strength low to avoid blowouts. ([IC-Light GitHub](https://github.com/lllyasviel/IC-Light), [RunComfy – product relighting](https://www.runcomfy.com/comfyui-workflows/comfyui-product-relighting-workflow), [ComfyUI wiki](https://comfyui-wiki.com/en/models/ic-light))
  - The hosted equivalent is **Higgsfield Relight**: depth-aware, with a direction pad, a Soft/Hard toggle, brightness and colour. A Video Relight version exists. ([Higgsfield Relight](https://higgsfield.ai/blog/Relight-Director-Style-Cinematic-Lighting), [Omid Saffari – video relight](https://omidsaffari.com/blog/higgsfield-video-relight-footage-after-recording-2026))
- **3D Jutsu specifics.** Scenes arrive with editable geometry, sun/point/spot lights, cameras with presets and trajectories, and GLB or Mixamo characters. Exports are MP4, a still frame or GLB. Higgsfield's own example prompt wording ([Higgsfield – 3D Jutsu](https://higgsfield.ai/blog/higgsfield-3d-jutsu)):
  - "47° diagonal field of view held for the entire shot, standard normal lens character"
  - "Shallow-but-honest focus riding his face"
  - "Photoreal capture, high dynamic range, natural cool-toned filmic grade, fine real grain, no stylized filter"
  - Their recommended flow: grey-proxy previz → character and location references → combine in one chat so the previz drives the camera.
- **The Higgsfield Blender plugin / Scene Builder MCP** keeps objects editable while you explore camera angles. ([Higgsfield Blender plugin](https://higgsfield.ai/blog/higgsfield-blender-plugin), [Digital Production](https://digitalproduction.com/2026/09/23/higgsfield-brings-ai-generation-into-blender-oh-goodey/), [Higgsfield Scene Builder](https://higgsfield.ai/mcp/scene-builder))
- **GPT Image (official OpenAI guide)** ([OpenAI cookbook – image prompting](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide)):
  - Say "photorealistic" or "real photograph".
  - Ask for real texture.
  - Camera specs are "interpreted loosely", so use them for look and composition.
  - Label each input ("Image 1: …, Image 2: …").
  - Say what moves where.
  - Say "change only X / keep everything else the same", and repeat the preserve list on every pass.
  - For composites, match "lighting, perspective, scale, and shadows".
  - For people placed in scenes, ask for "no cinematic lighting / dramatic color grading" so it feels like a real photo.
  - Wide or low-light scenes need atmosphere detail, or the model "trades mood for surface realism".
- **What fails in prompts:**
  - Buzzword stacks ("8K, ultra-realistic, cinematic masterpiece") come out blurry and generic. ([fal.ai](https://fal.ai/learn/tools/prompting-gpt-image-2))
  - Mood words ("moody", "cinematic lighting") do less than physical light descriptions. ([Fliki/Luma summaries](https://lumalabs.ai/learning-center/articles/how-to-prompt-seedance-2.0))
  - A plain pan or zoom just slides or scales the 2D image: "zero three-dimensional depth". A dolly or truck through layers makes parallax. ([Atlabs](https://www.atlabs.ai/blog/ultimate-guide-ai-camera-moves-prompts))
- **Seedance 2.5 (Higgsfield guide)** ([Higgsfield – Seedance 2.5 guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide)):
  - Use labelled sections: GLOBAL STYLE / SCENE / FIRST FRAME AND BLOCKING / OPTICS / CAMERA / LIGHTING.
  - Lighting is written as a "single motivated source" with its direction, and can be locked "unmoving for the full 15 seconds".
  - Use negatives like "NOT a clean CGI render", "no CGI sheen", "never strobe the exposure".
  - Write the camera move with distances: "slow straight push-in from 6 meters to 3.5 meters".
  - Write depth as focus: "deep focus holding…" or "receding into haze and shadow".
- **Seedance community rules:**
  - One camera move per clip. Stacked moves cause jitter or drift.
  - Give every reference a job ("for camera movement only"), or its lighting bleeds into your shot.
  - Keep reference strength around 70–80%. At 90–100% the character goes "cardboard cutout".
  - Change one variable per iteration.
  - Sources: [heyuan110 – Seedance failure modes](https://www.heyuan110.com/posts/ai/2026-07-11-seedance-2-prompt-guide/), [Crepal](https://crepal.ai/blog/aivideo/blog-seedance-2-0-prompt-engineering-guide/)
  - The 90–100% "cardboard cutout" warning describes exactly our "printed into the scene" look. *(practice: let the plate, not the face reference, govern light.)*
- **Blender → Seedance 2.5 (Dreamina).** Render a clay video as the reference. The example prompt says "Preserve the original camera angle… atmospheric depth". ([Dreamina – Seedance 2.5 + Blender](https://dreamina.capcut.com/seedance/seedance-2-5-blender-model-workflow))

---

## 4. Per-shot process

### A. Build the 3D scene (3D Jutsu)
1. **Camera first.** Set the focal length (28–40mm equiv for deep rooms, 50mm for a natural medium), the height (chest or counter, ~1.1–1.3 m) and the distance (1–2 m). Lock them. If there is a swipe frame, match its camera: same height, same lens feel, same subject size in frame. ([3D Jutsu](https://higgsfield.ai/blog/higgsfield-3d-jutsu), [PMC](https://pmc.ncbi.nlm.nih.gov/articles/3440305))
2. **Three layers.**
   - **Foreground:** a counter edge, product or jars, 0.3–0.6 m from the lens, cut off by the frame edge.
   - **Midground:** the subject's mark, with a stand-in box for the person at the right height.
   - **Background:** the window wall or a deep doorway, 3 m+ back.
   - Run the counter diagonally away from the lens. ([StudioBinder](https://www.studiobinder.com/camera-shots/composition/depth-in-film/))
3. **Overlap.** Place the foreground object so it will overlap the person's lower body. ([StudioBinder](https://www.studiobinder.com/camera-shots/composition/depth-in-film/))
4. **Light from the scene, not the camera.**
   - **Key:** a window or sun at three-quarter side or back of the subject's mark.
   - **One practical in frame:** a pendant or lamp.
   - **No light at the camera position.** Note the key's side, colour and softness in the shot sheet. ([Oseman](https://neiloseman.com/the-science-of-smoke/), [No Film School – practicals](https://nofilmschool.com/2015/07/practical-light-primer-how-practical-lighting-bring-cinematography-to-life))
5. **Haze.** Add a thin room volume (~0.1 density) so the window throws visible shafts and the back wall loses contrast. ([J.S. Abbott](https://jsabbott.artstation.com/blog/Z4Y77/tutorial-creating-god-rays-in-blender-3d-cycles), [Oseman](https://neiloseman.com/the-science-of-smoke/))
6. **Plan light and dark bands:** lit subject zone → darker middle → lit window. ([Oseman pt 2](https://neiloseman.com/taking-decisions-lightly-part-2/))
7. **A person stand-in that catches light.** A grey mannequin or Mixamo body on the mark shows where the key, rim and cast shadow will fall. Keep it in a separate render (step B). *(practice, from [3D Jutsu grey-proxy flow](https://higgsfield.ai/blog/higgsfield-3d-jutsu))*

### B. What to render
- **Beauty, empty set.** This is the plate to print.
- **Beauty with the grey stand-in on the mark.** This is the *lighting reference* for the person: it shows exactly where the shadow, rim and contact go.
- **Depth (Z / mist) pass.** Use it for ControlNet depth if we go local, and as a check that the layers are really separated. ([Flick](https://flick.art/blog/blender-ai-filmmaking))
- **Optional clay video of the camera move** for Seedance's movement reference. ([Dreamina](https://dreamina.capcut.com/seedance/seedance-2-5-blender-model-workflow), [Flick](https://flick.art/blog/blender-ai-filmmaking))

### C. Word the print (render → photoreal plate)
Name the light you built and forbid the model from re-lighting the scene. See prompt **P1** below. ([OpenAI cookbook](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide), [3D Jutsu](https://higgsfield.ai/blog/higgsfield-3d-jutsu))

### D. Word the shot (person into plate)
Give the model labelled inputs:
- Image 1: the printed plate
- Image 2: the grey stand-in render (light and shadow guide)
- Image 3: the cast face or body sheet

Then write the light as facts on the person: key side, rim, bounce, cast shadow direction, contact shadow, focus relative to the counter, and grain. See prompts **P2–P3**. ([OpenAI cookbook](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide))
- If the still still looks pasted, run one relight pass: Higgsfield Relight, with the direction set to the key's side and the same Soft/Hard as the scene. ([Higgsfield Relight](https://higgsfield.ai/blog/Relight-Director-Style-Cinematic-Lighting))

### E. Clip (Seedance 2.5)
- **Start frame:** the approved still.
- **One move:** a slow truck or push past the foreground object, for parallax.
- **Lighting:** locked to the same single source.
- **References:** each with a stated job. Cast reference strength ~70–80%.
- See **P4–P5**. ([Higgsfield Seedance guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide), [heyuan110](https://www.heyuan110.com/posts/ai/2026-07-11-seedance-2-prompt-guide/), [Atlabs](https://www.atlabs.ai/blog/ultimate-guide-ai-camera-moves-prompts))

### F. Failure checklist (run on every still before video)

| Failure | How to see it | Fix |
|---|---|---|
| **Pasted in** | Subject floats; nothing overlaps them; edges are cut-out clean. | Put a foreground object overlapping the body. Add "background light spills onto her hair and shoulder edge". Regenerate with the stand-in render as the light guide. ([StudioBinder](https://www.studiobinder.com/camera-shots/composition/depth-in-film/), [Vindral light wrap](https://composer-docs.vindral.com/operators/operators-light-wrap.html)) |
| **Flat front light** | Face evenly lit, no shadow side, no rim. | State the key side ("window frame left, slightly behind her") and "shadow side of her face toward camera-right". In 3D, move the key off the camera axis. Relight pass: Soft, from the key side. ([Outpost](https://outpost-vfx.com/en/news/18-pro-tips-and-tricks-for-lighting), [Higgsfield Relight](https://higgsfield.ai/blog/Relight-Director-Style-Cinematic-Lighting)) |
| **No contact shadow** | Hands, arms or feet don't darken the surface they touch. | Name both the soft contact shadow under her forearms and hands, and the cast shadow direction. ([Needle](https://engine.needle.tools/docs/api/ShadowCatcher)) |
| **Sharper than the plate** | Skin crisper than the in-focus counter; no grain on the person. | "Same focus, softness and fine film grain as the room; she is no sharper than the counter beside her." Remove "8K / ultra-detailed". ([Gravitee](https://gravitee.io/corpus/gen-1783/computer-animation/compositing.html), [fal.ai](https://fal.ai/learn/tools/prompting-gpt-image-2)) |
| **Brighter than the plate** | Face is the brightest thing in frame; shadows on her are lighter or darker than the room's. | "Her face is lit at the same level as the counter; her shadows match the room's shadow depth." Match the black and white points. ([UAL blog](https://23008828.myblog.arts.ac.uk/?p=681), [Photography Icon](https://photographyicon.com/how-to-light-portraits-for-a-real-looking-composite/)) |
| **Colour mismatch** | Neutral skin in a warm room, or the reverse; no bounce colour. | Name the temperature of the key and fill, plus "warm bounce from the wooden counter". ([Fiveable](https://fiveable.me/intermediate-cinematography/unit-13/lighting-compositing-cgi-integration/study-guide/5g2LjycsdOj6B1Ts)) |
| **Scale or perspective off** | Person too big or small for the counter or door; eye-line off the camera height. | Put the stand-in on the mark and say "same scale as the grey figure in Image 2; camera at her chest height". ([OpenAI cookbook](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide)) |
| **No depth (flat room)** | Back wall as contrasty and saturated as the foreground. | Add haze and backlight in 3D. In the print, write "back of room softer, lower contrast, slightly hazy". ([Oseman](https://neiloseman.com/the-science-of-smoke/)) |
| **Clip has no parallax** | Move looks like a slide or zoom on a flat image. | Use a truck or dolly past the named foreground object. Never a zoom. One move only. ([Atlabs](https://www.atlabs.ai/blog/ultimate-guide-ai-camera-moves-prompts)) |
| **Cutout in video** | Person stiff and evenly lit while the room moves. | Lower the cast-reference strength to ~70–80%. Give the plate image the lighting job. ([heyuan110](https://www.heyuan110.com/posts/ai/2026-07-11-seedance-2-prompt-guide/)) |

**Check method:** zoom in and out, mirror the image, push the exposure up and down. ([Outpost](https://outpost-vfx.com/en/news/18-pro-tips-and-tricks-for-lighting))

---

## 5. Prompt patterns (copyable)

Fill the `{slots}` from the shot sheet: lens, key side, colour, softness. These patterns follow the sourced guidance above. They have not been tested on our line yet.

**P1 — Print (3D render → photoreal plate)**
```
Photorealistic real photograph of this exact room. Keep the exact layout, objects, camera angle, lens and framing of the render.
Keep the lighting as built: {soft} {warm} light from the window at frame {left}, behind the counter; pendant lamp glowing in frame; light falls off toward camera.
Thin natural haze in the air; visible soft light shafts from the window; the back of the room is softer, lower contrast and slightly cooler than the foreground.
Foreground {counter edge and jars} slightly out of focus; focus at {the counter mark}.
Real materials, small imperfections, fine film grain. No added lights, no relighting, no cinematic grade, no CGI sheen.
```

**P2 — GPT Image: person into the plate**
```
Image 1: the room (keep it exactly — layout, light, camera, grain).
Image 2: grey figure showing where she stands and how the light falls on her.
Image 3: {cast name} — keep face, skin tone, hair, body.
Place the woman from Image 3 where the grey figure stands in Image 2, same scale and pose, photorealistic, one real photograph.
She is lit only by the room's light: {soft warm} window light from frame {left} and slightly behind her, rim of light on her hair and {left} shoulder, shadow side of her face toward camera; warm bounce from the wooden counter under her chin.
Her forearms rest on the counter with a soft dark contact shadow; her body casts a soft shadow toward frame {right}.
The foreground {jars} overlap her {waist} and are out of focus.
Same focus, exposure, colour and fine grain as the room; she is no brighter and no sharper than the counter beside her.
Change nothing else in Image 1. No cinematic lighting, no studio light, no dramatic grade.
```

**P3 — GPT Image: fix pass on a pasted still**
```
Keep everything in this image the same — person, pose, room, framing.
Change only the light on the person to match the room: key from the window at frame {left}, rim on her hair, shadow side toward camera, add a soft contact shadow where her {hands} touch the counter, match her skin's colour and grain to the room, and soften her to the same sharpness as the counter.
```

**P4 — Seedance 2.5: clip from the approved still (labelled sections, after Higgsfield's guide)**
```
GLOBAL STYLE: real handheld-free photograph come to life; natural film grain; NOT a clean CGI render; never strobe the exposure.
FIRST FRAME AND BLOCKING: start exactly on @Image1; she stays on her mark behind the counter.
OPTICS: {35mm} normal lens character, shallow-but-honest focus on her face, foreground {jars} soft.
CAMERA: one move only — slow lateral truck {right}, 0.5 metre, past the foreground {jars}; background moves slower than foreground.
LIGHTING: single motivated source, {soft warm} window light from frame {left} behind her, haze shafts visible, unmoving for the whole clip; her rim and shadows stay consistent.
ACTION: {one action}.
```

**P5 — Seedance reference jobs**
```
@Image1 is the first frame and sets all light and colour. @Image2 is for her face only. @Video1 is for camera movement only.
```

**Wording that works vs fails**

| Works (physical, specific) | Fails |
|---|---|
| "window light from frame left, behind her" | "cinematic lighting", "moody" ([Luma](https://lumalabs.ai/learning-center/articles/how-to-prompt-seedance-2.0)) |
| "fine film grain, same softness as the room" | "8K, ultra-detailed, masterpiece" ([fal.ai](https://fal.ai/learn/tools/prompting-gpt-image-2)) |
| "slow lateral truck past the jars" | "zoom in", "pan" ([Atlabs](https://www.atlabs.ai/blog/ultimate-guide-ai-camera-moves-prompts)) |
| "soft contact shadow under her forearms" | nothing about shadows (the model leaves them out) |
| "change only X, keep everything else" + the preserve list repeated | a full re-description of the scene each pass ([OpenAI](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide)) |
| "single motivated source … unmoving" | several lights, or none named ([Higgsfield Seedance](https://higgsfield.ai/blog/seedance-2-5-prompting-guide)) |

---

## Caveats
- Most AI-tool guidance here comes from vendor and community blogs (Higgsfield, Flick, Atlabs, Crepal, heyuan110). It is useful but not tested by us. Treat the prompt patterns as starting points and A/B them on one shot.
- GPT Image 2.x: per the OpenAI table, `input_fidelity` is disabled on gpt-image-2. The same guide's examples still pass it, so check the current API behaviour.
- No primary Deakins quote on backlight separation was found. The motivated-light claims rest on StudioBinder, No Film School and FilmLocal summaries, plus the ASC Sicario interview, which covers source-driven hard light.
- The official BytePlus Seedance lighting docs were not reachable. Seedance guidance comes from Higgsfield's guide and community testing.
