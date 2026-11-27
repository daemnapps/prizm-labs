---
name: 3d-print
description: Build, print and file the 3D set a picture is waiting for, then make the picture. Every generated picture comes from a filed 3D set print (image-production RULE GATE-4), so this runs whenever a picture was refused or held for one. Use when a tool says "Queued for the 3D print", "no filed 3D set", "held … set request", when someone says "clear the 3D queue", "print the sets", "make the 3D print for <picture>", "build the set for <email/ad/still/cast sheet>", "why is my picture waiting", or after an email run, a board Make, a Studio still or a cast sheet was refused for a set.
---

# 3D print

> **Activates component:** `components/image-production`: `picture_sets.py` (queue, plan, put, done), `cast_board.py`,
> `image_production/set_queue.py`, `image_production/set_gate.py`.

External dependencies: the Higgsfield 3D Jutsu tools in the session (`scene_builder_3d_*`); `components/3d-recipes/`
(every saved build, runnable in any account); `runs/ai-elements/<brand>/worlds/*/world.json` (the brand's worlds),
`runs/ai-elements/<brand>/products/<kit>/` (casting sheet, true size, 3D build), `runs/ai-elements/<brand>/casting/`
(people); `team/rollbacks.md` (GATE-4's switches).

Every picture the tools make is a print of a 3D set: sizes, depth, contact and light come from the set, the print's
reference sheet gives the materials. A tool that needs a picture with no print refuses and files a request here. This
skill clears the requests, one at a time, so the work never stops at a refusal. The process is the check: there is no
separate judging step.

**Headless, with no session in the loop (2026-11-20):** `python3 components/image-production/print_runner.py --brand
<brand> [--run <production run>] --cap <credits> --yes` clears open requests through this skill, one headless Claude
run per request on a Claude login (the one that carries the 3D builder), one print each, held to the cap read off the
account's own spend. The AI video lane runs it itself on its go (`ai_lane.py … --yes --cap N`). `--dry-run` lists.

## Each run

0. **A video shot of something we own footage of takes the footage, not a print** (video-production SHOT-ROUTES, rule 1:
   the hero product is never drawn when owned footage exists). Check the brand's footage first; a print is for what
   footage cannot give.
1. **See what is waiting:** `python3 components/image-production/picture_sets.py queue` (add `--brand <brand>`).
   Nothing waiting means nothing to do; say so in one line.
2. **For each request, get its plan** (nothing spent): `python3 components/image-production/picture_sets.py plan <brand> <request>`.
   It names the worlds to build in, each product's true size, casting sheet, 3D build and saved recipes, the cast board
   command when people are in it, the print's references and words, and the exact commands to file it.
   The request's `scene` may be the words a picture tool was given (with edit lines meant for an image model). When it
   names a run (`resume.run`), take the scene from that run's brief instead: what is in the picture, where the words go.
3. **Build the set in 3D Jutsu** (free):
   - **Any Higgsfield account runs this.** A project id in the plan works only on the account that made it; on any other
     it fails with PROJECT_AUTHORIZATION_CONFIGURATION_INVALID. So find builds by name, never by id:
     `scene_builder_3d_list_projects` and use the project named exactly `any_account.name` (each world and product in the
     plan has one). None on this account: create a project with that name and rebuild it from `any_account.recipe` in
     `components/3d-recipes/` (that folder's README: run each `step-NN.py` unchanged, in order). Next time it is found by
     name. Use the world the scene belongs in: the plan lists worlds with the rooms the scene names first (`match`). Jutsu cannot copy
     between projects, so build the scene inside the world's project. When no world has the room (`match` empty), a
     small standalone set at true size (the surface, the wall, the light) is right; save its recipe like any other.
   - Put each product in at its true size: its own build (the plan's `jutsu_project`, `recipes`) or a placeholder of
     its exact size. Only in a pose its kit allows (`rests`: the holder it sits in is built too; never `cannot` or
     `never_show`). A request whose words contradict the kit (a product "resting on a counter" that cannot stand) takes
     the kit's pose.
   - People: a plain figure per person at their true build, standing where the scene puts them, in the cast board's
     left-to-right order. A person who is not a cast member yet is cast first (the casting chain, from a real source
     person); never use the swipe as the print's reference to get a face: it copies the swipe's people.
   - Where words go on top (a board ad: the brief's zones; an email: the headroom): keep faces and the product out of
     those bands in the render, so the words never land on them.
   - Camera and light from the request's `frame` and `scene`. Render inside a scene edit, small: about 75% of 1080×1920,
     EEVEE, 8 samples (the print only needs layout, sizes and light; a heavy render hits the 5-minute limit).
4. **People in it:** run the plan's `cast_board.command` (it writes the board and its record next to the request).
   **Several reference pictures** (a casting sheet plus its rest photos, or a sheet and a cast board): the print takes
   ONE reference, so run the plan's `reference_board.command`; the board is the reference.
   **Skin in it (a person, or bare skin: acne, bumps, marks, pores):** `picture_sets.first_print` names the set's `skin`
   rows (a real customer crop + a macro shot from `runs/ai-elements/_texture-refs/`). Put them on that one reference
   board (`cast_board.py refs <out.png> <sheet or cast board> <skin files…>`), keep the print words' skin line, and
   file with `put … --skin <those files>`. A print that shows skin with no `--skin` is refused (owner, 2026-11-26: no
   plastic skin). The board's finish pass runs the same bank again (`model-inputs/preview.py finish_people`).
   **Never a hand-made product:** the product comes from its own true 3D build project; `put` refuses any other.
5. **Print** (once per request: a plan that says `stop` is already printing; do what it says, never print again) with
   `scene_builder_3d_generate_angles`. Take the account's `balance` first. The moment the call returns, run the plan's
   `print.first` command with the ids it returned, so no other session prints the same request.
   **"Submission unconfirmed"** (`submission_unknown`): read the generation once more. Still unconfirmed: never
   resubmit or allocate a new request ID. Check the submitting account's transaction history after `printing.sent_at`,
   matching the generation/job when possible; another job's charge is not proof. Record the account, time range and
   matching debit/refund. An unchanged balance or no visible charge is not proof of rejection. If the connector has
   no transaction tool, use that account's signed-in billing history; unavailable history leaves the request held.
   Clear only after checking transactions AND obtaining a terminal failed/rejected result or provider confirmation
   that no job was accepted. Record that evidence in the clear reason. A new paid attempt needs existing production
   authorization and remaining budget. A successful test on another account never clears this request.
   Print with the render, the plan's one `print.references` picture uploaded
   fresh (an upload older than a day fails with no reason), the plan's `print.words`, 9:16 at the plan's `print.resolution`
   (1.5k; a store picture 2k), never larger. One print is 1.25 (2k: 2.5)
   credits; the set and renders are free.
   Keep the render's `operationId` and `artifactId` as a pair; `requestId` identifies the paid print.
   The print's `operationId` is the render's own scene-edit operation (another id fails with
   INVALID_GENERATION_REFERENCE). People in the words are described as their casting sheet shows them: face shape,
   build, hair, facial hair. Never add a feature the sheet does not show; a print that makes a person slimmer,
   younger or better-looking than the sheet is wrong, and the clip's face gate refuses every still made from it.
   When the face gate judges against a real photo of the person (not the casting master), put that photo on the
   reference beside the cast board, labelled as his real face, and pick the look sheet that carries his true build
   (a suit sheet that draws a slimmer model gives a slimmer man); say the outfit in words. A face that is small in a
   wide frame comes back narrower and is refused: frame the person larger, as close as the swipe shot allows.
6. **Look at the print yourself** against each casting sheet and the cast board: label, shape, colour, true size, the
   holder, lettering (no invented words or misspelled marks), faces, outfits. Wrong means fix the set or the words and
   print again; never patch the print. Three prints that are still wrong: stop and report what keeps going wrong.
7. **File it:** the plan's `file_it` command with the render and the print. A right print gets `--note "kept: <what
   makes it right>"`; a wrong one is filed with a note saying what is wrong (no "kept") so the next print learns from it.
   Fill `--project`, `--generation`, `--reference` and `--words @<file>` so the set keeps its trail.
   Save the build's steps as `components/3d-recipes/<set>/step-NN.py` (the 3d-recipes README), so any account can rebuild it.
8. **Mark it done and finish the picture:** the plan's `then` command (it refuses while the set has no kept print, so a
   request is never closed by a wrong print) prints the `resume` step. Run it:
   - `make.py`: the printed command (the original request with `--set`).
   - `picture_chain` (email): run the email's picture step again; the print is the picture.
   - `plain.make` / the board: Make again (the set names the run through `put --run`).
   - `make_character`: add the set to the spec's `sets`, run make_character again.
   - `style_chain` (a style variant: a banked person, product, set, world or prop in the ad's style): run the printed
     `ensure-one` command. It adopts the kept print (a person then gets their sheets in the style).
   - A clip: the Video Studio recipe names `"set"` with no `still`, and the clip starts straight from the kept print.
9. **Report** in one line per picture: what was printed, where it is filed, what it unblocked, credits spent.

## A video scene's start picture: stage the set from its rehearsal

When the picture is a video scene's start picture (the scene has a motion rehearsal, `<scene>/motion/rehearsal/spec.json`),
the set is staged from that rehearsal, never from words or a camera of your own:
1. Put every person where the rehearsal's `people[].at` puts them (one shared offset for the whole scene) and facing the
   same way; nobody else stands in the shot.
2. Make the camera the rehearsal's first shot (`camera.shots[0]`: `at`, `look`, `lens`) exactly as the rehearsal
   tool sets it: Blender `sensor_fit = 'AUTO'`, 36 mm, the camera aimed at `look`. Scale the figures to the rehearsal's
   1.7 m people. Check by numbers before printing: project each person's neck through the camera
   (`world_to_camera_view`) and compare with the rehearsal's first frame (`motion/rehearsal/pose.json`, body point 1);
   every neck within 0.02 of the frame.
3. Print that render with the face board (every person in it, standing order) and the words
   `motion_chain.py print-words <scene>` gives (place, each person's place/size/facing/hands, each cast look); never
   write the print words by hand. File it; name it on the take as `set_print`. `motion_chain.ready` uses it as the
   start picture as printed when it passes `start_check`; it is never redrawn.
Check: `motion_chain.py start-check <scene> <print>` places everyone before the take is paid for.

## The ad's style

A request with `style` (filed by `components/video-production/styles/style_chain.py`) is printed in that style: the
plan's words carry the style's formula instead of "a real photograph", and its reference board ends with the look
reference (the style's swatch or a face-free swipe frame, look only). Identity comes from the element's master on the
board. Look at the print for both: the right person or product, and the right style.

## Rules

- **No credits on basic mistakes** (ruled 2026-11-23; that day
  6 of 9 prints were wrong for reasons visible before sending):
  - **Look at the reference before every print.** A product's only reference is its casting sheet: no CGI, no kit
    rest pictures, no board of mixed sources (the plan enforces it; check it anyway).
  - **Read the print words before every print** for lines that fight the set: a "no writing" line that would erase the
    set's signage, a rest or holder the set does not show, a product kit rule left out (`always`, `cannot`).
  - **One print first.** Several requests built the same way (variations of one set): print ONE, look at it against the
    casting sheet and the render, then send the rest with the same words. Never send a batch blind.
  - **Every product in the blockout has its real shape** (2026-11-23: a tube product blocked out as a pump bottle came
    back drawn as a pump bottle). A product is its own build from `components/3d-recipes/`, or a stand-in made from its
    kit's true size and silhouette (`size_cm`, how it rests, which end is up), checked against its casting sheet before
    printing. Never a guessed cylinder.
  - **Every product in a print is pasted** from its kit's real cut-outs (`product_paste.py`, the local-studio Python),
    not only the hero: the print model garbles small label text on every product it draws. Give the paste each
    product's box when products look alike (`--found`), and look at each one after.
  - **A print with several products names each one** in its words, by its number on the reference board, with its place
    and which end is up. The plan's words describe one product; for more, write each in.
  - **Render the set alone**: only its own collection on, the project's loose root objects hidden, the world light it was
    built with. A shared project carries other sets' lights and leftover products into the render.
- Never make the picture another way to get past a refusal: no direct model call, no Higgsfield picture tool by hand
  (the session hook blocks them), no edit of another picture.
- A lane that has to go back goes back by its switch (`team/rollbacks.md`), on the owner's word only.
- Several requests that share a world and products are one set with several cameras: build once, print each camera.
- A dry run of a tool files nothing: if you dry-ran first, the real run files the request (or `picture_sets.py request`).
