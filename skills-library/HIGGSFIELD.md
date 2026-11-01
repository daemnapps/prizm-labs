# Higgsfield — what it already does (inventory 28 Oct 2026)

Read live from the Higgsfield connector. Plan: **Ultra**, **7,190 credits**.
Higgsfield goes first: before reaching for any outside tool, check here.
(Personal and side work runs on his personal Higgsfield workspace.)

## Built-in workflows (each is a full skill inside Higgsfield)

| Workflow | What it makes |
|---|---|
| website-builder-flow | Hosted **websites** (Animated "scroll-scrub" template = a scroll-driven film page, or plain), **apps**, and **browser games** with realtime multiplayer rooms; live at `<name>.higgsfield.app`; optional listing on the community feed |
| — game pipeline | Game design system → one style formula for every asset → sprites, spritesheets (`autosprite`), tiles/PBR textures, 3D models (Meshy, rigging, 696 canned animations), procedural rigs, music (`sonilo_music`), SFX, voice |
| brand-asset-creation | Logos, visual identity, brand kits, brandbooks, packaging, mockups, merch, signage, decks, posters, social graphics; SVG/PNG export |
| ads-studio | Static ad creatives with copy, from a website, product page, photo or prompt; Meta formats |
| ad-multiplier | One 4–30 s ad → many versions: swap people, products, backgrounds, text; or **recreate** the ad for a new market, audience, language, cast or product |
| product-photoshoot | Packshots, lifestyle, hero banners, carousels, static ad packs, virtual try-on, CGI-style concepts |
| ugc-video | Creator review, product-only voiceover, unboxing, try-on, tutorial, website tour |
| faceless-video | Narrated explainers, history, kids, picture story, myth |
| character-sheet | Consistent character sheets (photoreal, editorial, anime, 3D, game-concept) |
| thumbnail-generation | YouTube / Reel covers, 16 thumbnail frameworks |
| video-editing (Higgsedit) | Cuts, trims, soundtrack, animated text, shaders, overlays, title cards |
| video-montage | Assemble clips, soundtrack, burned captions |
| narration | Timed voiceover takes; "put me in this video" presenter |
| katana | Remix a reference edit onto your subject |
| reel-effects | Fixed effects on talking-head clips (/text-behind, /grade-wipe…) |

## Setup commands
- **/use-blender** — local Blender driven by Claude, no add-on (Blender is on this Mac).
- **/use-after-effects** — drive After Effects.
- **/3d-jutsu** — hosted 3D scenes (Blender in the cloud): build, light, render, export GLB/.blend, new camera angles of a real location, render → AI image/video.

## Models (~120)
- **Image (45+)**: Soul 2 / Soul Cinema / Soul Cast / Soul Location, GPT Image 2 / 2.5, Nano Banana Pro / 2, Seedream 5, Flux 2/3, Kling Omni, Grok, **Ideogram 4.5 + Ideogram Vector (SVG)**, **Recraft v4 + Recraft styles**, Cinematic Studio (camera body / lens / focal length), Marketing Studio product shot (product, people, poster, ads, marketplace; brand kits), background remover, outpaint, Topaz upscale, image decompose, **autosprite** (game sprite sheets).
- **Video (50+)**: Kling 2.6 / 3.0 / 4.0 (+ Motion Control), Veo 3.1, Seedance 2.0 / 2.5, Wan 2.6 / 2.7 / 3.0, MiniMax Hailuo / H3, Grok video, Gemini Omni Flash, Cinematic Studio Video 3.0 / 3.5 / 4.0 (genre, camera style, lighting, grade, multi-shot), Marketing Studio Video (2D motion, hypermotion, mixed media, SaaS motion, UGC, product link, **ad reference**, app video), Reference-to-video (recreate a reference video with your character + product), Ad Multiplier v1/v2, motion control / replace object, draw-to-video, reframe, video bg removal, depth maps, FPS boost, upscale, deflicker, lip sync (sync.so), voice change, dubbing.
- **3D (17)**: Meshy 6/7 (text/image → 3D, rigging, animation, remesh, retexture), Tripo H3.1 / P2, Hunyuan3D v3 / v3.1, SAM-3 3D object + 3D body, image/multi-image → 3D, rigging.
- **Audio (8)**: ElevenLabs v4 / v4 turbo, Inworld TTS, Qwen TTS, Seed audio, Sonilo music, Mirelo text-to-audio (SFX), TTS v2. Plus voice cloning, dubbing.

## Preset galleries
- 80+ named recipes (product shots: hero, angles, before-after, benefits, flatlay, ice capsule, water splash, unboxing, specs…; motion: product spin, crane reveal, light sweep, liquid wrap, whip pan…).
- Viral effects, Marketing Studio templates, **Genjutsu** motion presets + Genjutsu Styles (redraw your video in a look, keep its motion), Soul styles, Katana remixes, What If / content factory.

## Other tools on the connector
AI Influencer builder, Shorts Studio, TikTok connect / trending music / publish, virality predictor, video analysis, Match Cut + Tracelab app (28 effects: face cut, logo cut, product cut, CRT, VHS, thermal, glitch…), projects/folders, sandbox for code.
