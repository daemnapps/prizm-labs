# The Format Frontier — style board, the stack, the line, the edit hand

Artifact: https://claude.ai/artifact/RUBXajrAH5uyiVH6eyJM5h (republish over it, never a second one). Printed by `render_board.py`; do not edit by hand.

## The test

If you can swap it and the script, the cast and the beats all stay the same — it is a style. If the script or who carries it has to change — it is a format.

## The style bank

| Style | Family | Looks like | The internet calls it | Keeps the proof | Flag |
|---|---|---|---|---|---|
| **Claymation** (`claymation`) | handmade | Everything is hand-sculpted modelling clay, shot frame by frame on a tabletop set. | Claymation | yes |  |
| **Paper cut-out** (`paper-cutout`) | handmade | Layered cut paper and card, flat shapes with real paper shadows between the layers. | Paper animation / paper style | yes |  |
| **Crochet** (`crochet`) | handmade | Everything is knitted or crocheted yarn — soft amigurumi people and props. | Crochet style | no |  |
| **Needle felt** (`needle-felt`) | handmade | Matted wool felt figures, fuzzier and more sculpted than crochet. | (extension of crochet) | faint |  |
| **Felt puppet** (`felt-puppet`) | handmade | Hand-and-rod foam puppets with felt skin, big mouths and ping-pong eyes on a TV-studio set. | Muppet story | no | Named after a trademarked puppet franchise — keep the look generic, never the characters. |
| **Brick figure** (`brick-figure`) | handmade | A world of snap-together plastic bricks with little cylinder-headed figures. | Lego character | no | Trademarked toy system — never show the logo or licensed figures. |
| **Miniature diorama** (`miniature-diorama`) | handmade | A real place shrunk to a model-railway set, shot tilt-shift. | (adjacent to brick figure) | yes |  |
| **Anime** (`anime`) | drawn | Japanese TV animation — clean ink lines, flat cel shading, big expressive eyes, painted backgrounds. | Anime style | no |  |
| **1950s hand-drawn cel** (`cel-1950s`) | drawn | Mid-century feature animation — inked outlines, gouache backgrounds, storybook warmth. | Disney character (the classic 2D half) | yes | Keep it period-generic; never a studio's characters. |
| **Adult cartoon** (`adult-cartoon`) | drawn | Flat wobbly-line TV cartoon with bug eyes and deadpan faces. | Rick and Morty | yes | Named after a trademarked show — generic look only. |
| **Comic panel** (`comic-panel`) | drawn | Printed comic book — heavy inks, halftone dots, panel borders and speech balloons. | Cartoon comic | yes |  |
| **Whiteboard sketch** (`whiteboard-sketch`) | drawn | Black marker line drawings on a white board, drawn in as you watch. | Whiteboard explainer | no |  |
| **Storybook watercolour** (`storybook-watercolour`) | drawn | Soft children's-book illustration — wet washes, pencil lines, paper grain. | (extension) | yes |  |
| **Family 3D animation** (`family-3d`) | 3d | Big-studio 3D feature look — appealing stylised people, huge eyes, soft subsurface skin, cinematic light. | Disney / Pixar character | faint | Studio names are trademarks — generic look only, never their characters. |
| **3D cutaway explainer** (`cutaway-3d`) | 3d | Glossy 3D simulation that flies inside a body or object to show what is happening. | Zack D Films | yes | Named after a creator — the look is generic 3D explainer. |
| **Skeleton character** (`skeleton-3d`) | 3d | A friendly glossy 3D skeleton living a normal life — the narrator of body stories. | Skeleton stories | no |  |
| **Low poly** (`low-poly`) | 3d | Faceted 3D made of flat triangles, like an early game console or a papercraft model. | Low poly story | no |  |
| **16-bit pixel art** (`pixel-16bit`) | 3d | Chunky retro-game pixels, side-on, limited palette. | (extension) | yes |  |
| **Hypermotion cinematic** (`hypermotion-cinematic`) | photoreal | Car-commercial energy — impossible fast camera moves, macro details, speed ramps, hard light. | Hypermotion cinematic | yes |  |
| **Phone-camera UGC** (`phone-ugc`) | photoreal | Looks like a real person filmed it on their phone. The baseline everything else departs from. | (the default real look) | yes |  |
| **Horror** (`horror`) | photoreal | Dread lighting — underlit faces, green-black shadows, grain, something wrong in the background. | Horror style | yes |  |
| **VHS camcorder** (`vhs-camcorder`) | photoreal | 1990s home video — soft, smeary colour, tracking lines, date stamp. | (extension) | yes |  |
| **Fight-night broadcast** (`fight-night-broadcast`) | photoreal | Pay-per-view sports graphics — tale of the tape, metallic lower-thirds, arena light. | UFC fight night | no | League names and logos are trademarks — generic broadcast look only. |
| **Glass ASMR** (`glass-asmr`) | photoreal | Everyday things made of clear coloured glass or jelly, sliced or squeezed in macro. | (AI-native trend) | no |  |
| **Macro beauty commercial** (`macro-commercial`) | photoreal | Extreme close-ups on skin, liquid and glass — razor-sharp texture, everything else falling away. | Macro product / beauty commercial | yes |  |
| **Studio product hero** (`studio-hero`) | photoreal | Clean studio photography in motion: seamless backdrop, controlled light, the subject as the only thing in the world. | Studio product hero | yes |  |
| **Dark luxury** (`dark-luxury`) | photoreal | Black marble, cool clinical light, deep blacks — the prestige skincare look. | Dark-marble luxury commercial | yes |  |
| **16mm archival film** (`archival-16mm`) | photoreal | Looks like found documentary footage — grain, gate weave, light leaks, soft old lenses. | Vintage 16mm archival documentary | yes |  |
| **Neon noir** (`neon-noir`) | photoreal | Wet night streets, warm bulbs against cold neon, glass and chrome. | Neon-noir cyberpunk | yes |  |
| **Fashion editorial** (`fashion-editorial`) | photoreal | Magazine-campaign glamour — glossy skin, big light, oversized type energy. | Luxury editorial / fashion campaign | yes | Magazine names are trademarks — generic look only. |
| **Oil painting in motion** (`oil-painting`) | drawn | Thick visible brushstrokes that swirl as the scene moves. | Van Gogh oil-painting animation | yes |  |
| **Ink wash** (`ink-wash`) | drawn | Black ink and water on rice paper — soft bleeds, empty space, a few decisive strokes. | Ink-wash transformation | faint |  |

### Style locks

**claymation** — stop-motion claymation: every surface hand-sculpted plasticine with visible thumbprints and tool marks, slightly lumpy proportions, matte clay skin, tiny handmade props, soft tabletop studio light, shallow depth of field of a miniature set  
*Moves:* animated on twos, tiny jitter between frames, no motion blur

**paper-cutout** — layered paper-craft: every shape cut from coloured card and construction paper, visible fibre texture and cut edges, stacked layers casting small real drop shadows, flat colour, no gradients, lit like a shadow box  
*Moves:* pieces slide, hinge and pop like puppets on pins; stepped timing

**crochet** — crochet amigurumi: every person and object made of chunky yarn stitches, visible loops and fuzz, safety-eye faces, stuffed rounded forms, felt details, warm soft window light, macro lens look  
*Moves:* gentle wobble, stop-motion on twos, yarn squashes softly

**needle-felt** — needle-felted wool: figures and props sculpted from matted wool roving, fuzzy halo of stray fibres on every edge, bead eyes, muted natural dyes, miniature handmade set, soft daylight  
*Moves:* stop-motion on twos, fibres shimmer slightly frame to frame

**felt-puppet** — children's television puppet show: soft fleece-and-foam puppet characters with wide hinged mouths and round plastic eyes, visible fleece texture and stitched seams, bright 1980s television studio lighting, colourful simple set  
*Moves:* puppeteered bobbing, mouth flaps on syllables, arms move on rods

**brick-figure** — plastic brick toy world: every object built from glossy interlocking studded bricks, people as small cylinder-headed toy figures with printed faces and claw hands, injection-moulded plastic sheen, macro photography of a toy set, shallow depth of field  
*Moves:* stiff stop-motion, figures hop and swivel at the waist, on twos

**miniature-diorama** — handmade miniature diorama: scale-model buildings, painted figurines, static grass and model trees, tilt-shift lens with a thin band of focus, bright hobby-lamp light, slight plastic sheen  
*Moves:* slow overhead drift, figures move in tiny stop-motion steps

**anime** — Japanese anime: clean black line art, two-tone cel shading, large expressive eyes, glossy hair highlights, detailed hand-painted background, soft bloom on light sources  
*Moves:* held poses with snappy moves, speed lines, hair and cloth sway, animated on threes

**cel-1950s** — 1950s hand-drawn cel animation: confident ink outlines, flat opaque paint fills, rounded appealing character design, soft gouache painted background, slight film grain and gate weave  
*Moves:* on twos, squash and stretch, overlapping follow-through

**adult-cartoon** — adult animated sitcom: thin uniform outlines, flat colours with no shading, simple rubbery bodies, large white eyes with scribbled pupils, slack mouths, plain flat backgrounds  
*Moves:* limited animation, mouth-flap dialogue, sudden jerky gestures

**comic-panel** — printed comic book panel: bold black inks, Ben-Day halftone dot shading, limited four-colour palette, slightly misregistered print, white panel gutter around the frame  
*Moves:* parallax between cut-out layers, panel-to-panel snaps, impact bursts

**whiteboard-sketch** — whiteboard marker illustration: simple black dry-erase line drawings on a clean white board, one accent colour, hand-lettered labels, slight marker streaks, no shading  
*Moves:* lines draw themselves on, a hand may enter to sketch; nothing else moves

**storybook-watercolour** — children's storybook watercolour: loose wet-on-wet washes, visible pencil under-drawing, cold-press paper grain, soft edges, gentle limited palette  
*Moves:* subtle boil on the line, slow page-turn moves, drifting washes

**family-3d** — big-studio 3D animated feature: stylised appealing character with large expressive eyes and simplified features, soft subsurface-scattered skin, groomed hair, richly detailed set, warm cinematic key light with rim light  
*Moves:* full fluid character animation, anticipation and follow-through, slow push-ins

**cutaway-3d** — 3D science-explainer animation render: smooth simplified mannequin-like figure with matte neutral-grey surface, clean dark studio void background, soft even light, one glowing highlighted region with a floating magnified inset showing a simple stylised diagram of skin layers, saturated colour only on the part being explained  
*Moves:* continuous camera fly-in from outside to inside, parts animate mechanically, labels pop on

**skeleton-3d** — stylised 3D skeleton character: clean ivory bones with soft gloss, big round eye sockets with expressive pupils, wearing everyday clothes, everyday real-world setting, soft cinematic light, shallow depth of field  
*Moves:* full character animation, exaggerated jaw on speech, bones clack subtly

**low-poly** — low-poly 3D: every form built from large flat-shaded triangles, no textures, simple gradient sky, pastel palette, hard facet edges, soft ambient occlusion  
*Moves:* smooth floaty camera orbit, simple bobbing loops

**pixel-16bit** — 16-bit pixel art: chunky visible pixels, limited 32-colour palette, dithered shading, side-on game-screen composition, crisp nearest-neighbour edges  
*Moves:* few-frame sprite loops, screen scrolls sideways, text types on

**hypermotion-cinematic** — high-end commercial cinematography: anamorphic lens, hard rim light and deep contrast, macro detail, atmospheric haze, rich saturated grade, razor-sharp product surfaces  
*Moves:* fast FPV-style fly-throughs, whip pans, speed ramps into slow motion, match cuts

**phone-ugc** — native phone-camera footage: handheld front camera, available room light, true unretouched skin texture, slight noise and compression, nothing styled  
*Moves:* handheld micro-shake, natural pauses, no cuts inside a line

**horror** — horror film still: low-key underlighting, sickly green-teal shadows, crushed blacks, heavy film grain, fog, wide-angle lens slightly too close, unsettling stillness  
*Moves:* slow creeping push-in, flicker, sudden jump cut

**vhs-camcorder** — 1990s VHS camcorder footage: soft low-resolution image, colour bleed, tracking-line noise, blown highlights, orange date stamp in the corner, 4:3 feel inside the frame  
*Moves:* handheld zooms, auto-focus hunting, tape glitches on cuts

**fight-night-broadcast** — combat-sports broadcast: dark arena with hard spotlights and haze, metallic chrome-and-red broadcast graphics, versus split, stat bars, dramatic rim light on the subject  
*Moves:* graphic slams and wipes, slow-motion walkouts, crowd flashes

**glass-asmr** — translucent glass-object macro: the subject made of clear coloured glass with internal refraction and caustics, on a clean cutting board, softbox highlights, extreme macro  
*Moves:* one slow satisfying action — a slice, a crack, a squeeze — in a single take

**macro-commercial** — high-end macro beauty commercial: extreme close-up detail, razor-sharp surface texture, very shallow depth of field, soft wrapped studio light with a specular kicker, clean luminous grade  
*Moves:* slow macro slides and rack-focus pulls, liquid in slow motion

**studio-hero** — studio product-hero photography: seamless single-colour cyclorama backdrop, controlled softbox key with gentle gradient falloff, crisp edges, no set, catalogue-clean grade  
*Moves:* slow turntable rotation, gentle push-in, light sweeps across the surface

**dark-luxury** — dark luxury editorial commercial: black marble and slate surfaces, cool clinical top light, deep saturated blacks, fine metallic and glass highlights, restrained desaturated palette  
*Moves:* slow deliberate dolly moves, light glints travelling across edges

**archival-16mm** — vintage 16mm archival documentary film: heavy organic grain, gate weave, light leaks at the frame edge, soft vintage lens, faded warm colour, slight vignette  
*Moves:* handheld observational camera, film flicker, occasional splice jump

**neon-noir** — neon-noir night cinematography: wet reflective surfaces, cold cyan and magenta neon against warm practical bulbs, deep shadow, atmospheric haze, anamorphic flares  
*Moves:* slow gliding camera, reflections rippling, signs flickering

**fashion-editorial** — luxury fashion magazine editorial campaign: glossy retouched skin, bold hard beauty light, saturated colour-blocked backdrop, confident high-fashion styling, Y2K gloss  
*Moves:* snappy cuts, poses that hit on the beat, fast zoom punches

**oil-painting** — post-impressionist oil painting: thick impasto brushstrokes, visible palette-knife texture, swirling directional strokes, saturated complementary colours, canvas weave showing through  
*Moves:* brushstrokes flow and re-form every frame, slow drifting camera

**ink-wash** — East Asian ink-wash painting: black sumi ink bleeding into wet rice paper, soft tonal washes, large areas of empty paper, a few decisive dry-brush strokes, one muted accent colour  
*Moves:* ink blooms and spreads, forms dissolve into and out of washes

## Show formats (candidates)

You caught what the first board missed. 'UFC fight night' is not a paint job — it is a kind of entertainment with its own cast, its own big moment, its own voice and its own ending. When you borrow the show, the viewer already knows how to watch it, and every part of the show is a place to put the brand.

**The six roles — the brand injection:** The hero = the customer — always her, never the brand · The villain = the problem, given a name, a face and a personality · The move = the product, used the way this show uses its biggest moment · The voice = whoever this show lets explain things — they carry the mechanism so the hero never has to lecture · The replay = the place this show naturally zooms in or slows down — that is where the mechanism scene lives · The verdict = how this show ends — that is the offer

### Fight night (`fight-night`)

A championship bout, called live by two ringside commentators. The commentators can say anything about the product and it sounds like excitement, not a pitch. The fight gives the problem a body to lose.

- **The hero:** the challenger, walking out to her own music
- **The villain:** the undefeated opponent — the problem with a fighter's name
- **The move:** the finishing move: she pulls out the product and locks the opponent up
- **The voice:** two ringside commentators, one hype, one analyst — the analyst explains the mechanism mid-hold
- **The replay:** the slow-motion replay: zoom into the opponent fading, down to what the active ingredient is doing underneath
- **The verdict:** the belt, 'and NEW…', the offer on the broadcast lower-third
- **Sound:** crowd roar, bell, walk-out music, commentators talking over each other
- **Styles it pairs with:** fight-night-broadcast, brick-figure, anime, adult-cartoon
- **Who watches (a guess to check):** men 18–45; combat-sports and highlight-clip scrollers

### Cooking show (`cooking-show`)

A warm kitchen-counter show where the host makes the thing in front of you. Her trust in a recipe transfers to the product: ingredients you can see, steps you can follow, a result you can taste.

- **The hero:** the host at her own counter
- **The villain:** the recipe that always fails — the thing everyone gets wrong
- **The move:** the secret ingredient, added with a flourish
- **The voice:** the host to camera, plus a sidekick who asks the questions the viewer would
- **The replay:** the overhead close-up: the mixture changing colour and texture in the bowl
- **The verdict:** the reveal plate and the recipe card — the offer is the recipe card
- **Sound:** sizzle, studio audience warmth, gentle theme sting
- **Styles it pairs with:** phone-ugc, claymation, macro-commercial, storybook-watercolour
- **Who watches (a guess to check):** women 50+; daytime TV and recipe-reel watchers

### Soap opera (`soap-opera`)

Daytime drama: long stares, a secret, someone who was supposed to be gone comes back. The problem that 'keeps coming back' is literally a soap plot. She already knows the grammar — the return, the reveal, the cliffhanger.

- **The hero:** the woman who has been wronged
- **The villain:** the one who keeps coming back — the ex, the twin, the rival; the problem returning in the same place
- **The move:** the reveal: the truth she produces at the dramatic moment
- **The voice:** inner monologue and the confidante in the next scene
- **The replay:** the soft-focus flashback: how it came back last time, and why
- **The verdict:** the cliffhanger — 'find out' is the call to act
- **Sound:** swelling strings, a held pause, a door
- **Styles it pairs with:** dark-luxury, vhs-camcorder, cel-1950s, felt-puppet
- **Who watches (a guess to check):** women 50+; (telenovela is a variant for Spanish-speaking households, not a second format)

### Home shopping hour (`home-shopping`)

A live sell on a shopping channel: host, demo table, caller on the line, clock ticking. It is the one show that is ALREADY a direct-response ad, and her generation bought from it for thirty years.

- **The hero:** the caller on the line who already owns it
- **The villain:** the old product on the demo table that did not work
- **The move:** the live demo on the back of a hand
- **The voice:** the host, and the caller's own words
- **The replay:** the split-screen close-up of the demo hand
- **The verdict:** the countdown clock and 'quantity remaining' — the offer, natively
- **Sound:** phone line beep, host patter, soft bed music
- **Styles it pairs with:** vhs-camcorder, studio-hero, felt-puppet
- **Who watches (a guess to check):** women 55+

### Courtroom TV (`courtroom`)

Small-claims television: a plaintiff, a defendant, a judge with no patience. A judge can say 'that product never worked and you knew it' — a verdict lands harder than a claim.

- **The hero:** the plaintiff
- **The villain:** the defendant: the thing she tried that failed her
- **The move:** Exhibit A
- **The voice:** the judge
- **The replay:** the evidence photo, enlarged on the easel
- **The verdict:** the gavel — judgment for the plaintiff, the offer as the ruling
- **Sound:** gavel, gallery murmur, bailiff
- **Styles it pairs with:** phone-ugc, adult-cartoon, brick-figure
- **Who watches (a guess to check):** daytime TV watchers, 45+

### True-crime documentary (`true-crime`)

A hushed investigation: evidence board, archive footage, the culprit hiding in plain sight. 'It was never what you thought it was' is the mechanism-led argument wearing a trench coat.

- **The hero:** the one who would not let it go
- **The villain:** the culprit everyone overlooked — the real cause
- **The move:** the piece of evidence that cracks it
- **The voice:** the hushed narrator and the expert interview
- **The replay:** the forensic zoom: enhance, enhance
- **The verdict:** case closed — the offer as 'what she uses now'
- **Sound:** low drone, tape hiss, a single piano note
- **Styles it pairs with:** archival-16mm, horror, dark-luxury
- **Who watches (a guess to check):** women 25–60; podcast and docuseries bingers

### Game show (`game-show`)

A bright studio, a host, a big board, a contestant who has been wrong before. Every product she already tried becomes a wrong answer on the board — the objections get handled as a game.

- **The hero:** the contestant
- **The villain:** the wrong answers: everything she tried
- **The move:** the final answer
- **The voice:** the host
- **The replay:** the board flipping to reveal the answer
- **The verdict:** the prize — the offer
- **Sound:** buzzer, ding, audience gasp
- **Styles it pairs with:** vhs-camcorder, felt-puppet, adult-cartoon, pixel-16bit
- **Who watches (a guess to check):** broad; 45+ skews daytime

### Home makeover (`home-makeover`)

Before, demolition, rebuild, the walk-through reveal. Two steps — strip the old surface, rebuild what is underneath — is exactly how a renovation is told.

- **The hero:** the homeowner
- **The villain:** the 'before' — what was hiding under the surface
- **The move:** demo day, then the rebuild
- **The voice:** the contractor and the designer
- **The replay:** the time-lapse
- **The verdict:** the reveal walk-through — the offer at the front door
- **Sound:** sledgehammer, upbeat montage music, the gasp
- **Styles it pairs with:** phone-ugc, miniature-diorama, brick-figure
- **Who watches (a guess to check):** women 35–65; home and garden channel watchers

### Nature documentary (`nature-documentary`)

A calm famous-sounding narrator observes a creature doing what it does. The narrator can describe skin, a cell or an ingredient as wildlife — the mechanism becomes a story with an animal in it.

- **The hero:** the creature we are rooting for
- **The villain:** the predator
- **The move:** the adaptation that saves it
- **The voice:** the narrator, never on screen
- **The replay:** the extreme macro
- **The verdict:** the season turns — the offer as the closing line
- **Sound:** orchestral swell, wind, the narrator's hush
- **Styles it pairs with:** macro-commercial, cutaway-3d, claymation, storybook-watercolour
- **Who watches (a guess to check):** broad; 35+

### Sports analyst desk (`analyst-desk`)

Two analysts at a desk arguing over a replay, drawing on the screen. Us-versus-them staged as a debate, and the telestrator is a licence to draw the mechanism on a freeze-frame.

- **The hero:** the player having the comeback season
- **The villain:** the rival — or last season's version of him
- **The move:** the play that changed the game
- **The voice:** two analysts who disagree
- **The replay:** the telestrator: circles and arrows drawn on the frozen replay
- **The verdict:** the final score graphic — the offer
- **Sound:** desk banter, whoosh graphics, highlight music
- **Styles it pairs with:** fight-night-broadcast, hypermotion-cinematic, adult-cartoon
- **Who watches (a guess to check):** men 18–55

### Boss fight (`boss-fight`)

A video-game level: health bars, a boss, a power-up, 'level cleared'. A health bar is the clearest progress picture ever invented — the problem visibly loses hit points.

- **The hero:** the player character
- **The villain:** the boss, with a name and a health bar
- **The move:** the power-up item
- **The voice:** the on-screen text and the announcer voice
- **The replay:** the boss's health bar draining while the hit lands
- **The verdict:** level cleared, loot drop — the offer is the loot
- **Sound:** 8-bit hits, power-up chime, victory fanfare
- **Styles it pairs with:** pixel-16bit, low-poly, anime
- **Who watches (a guess to check):** men and teens 13–35

## The stack

Every one of these is its own bank with its own test. A finished ad is one pick from each. That is why the big brands look like they are doing something wild: they are only turning more than one dial at once.

| Element | Question | Example |
|---|---|---|
| Avatar | Who is it for? | a core person, then a narrower sub-avatar |
| Angle | What do we claim? | one sentence she could agree or disagree with |
| Format | What kind of ad is it, and who carries it? | song ad · single presenter · or a whole borrowed show: fight night, cooking show, soap opera |
| Structure | What are the beats, in what order? | your 50 swiped structures |
| Argument | What is the plan of the argument? | problem-agitate-solve · mechanism-led · story |
| Style | What does it look like? | claymation · anime · phone-camera UGC |
| Delivery | How does it sound? | humour · register · pacing |
| Medium | What asset is it? | video · image · carousel · email · page |

### The $30M-a-month ad you described, taken apart

- **Style:** Skeleton character, in Family 3D animation
- **Format:** Song ad
- **Argument:** Long-form sales letter (VSL), 7 minutes
- **Medium:** Video
- **Angle + avatar:** theirs — the only part you can't copy, and the only part that matters

### The Instagram list of 21, sorted

| # | They call it | It is | Where it goes |
|---|---|---|---|
| 1 | Thirst trap | format | A hook device more than a format — an attractive person stops the thumb, then the pitch. File as a hook/scroll-stopper, flag for Meta policy. |
| 2 | Zack D Films | style + format | Style: 3D cutaway explainer (in the bank). Format: the 'what happens inside' explainer — new format profile. |
| 3 | Asian doctor | cast | Not a format. It is your Expert consultation format with a specific cast member. Goes in the AI cast, not the format bank. |
| 4 | Claymation | style | In the bank. |
| 5 | Fake podcast | format | New format profile: two mics, two people, clipped like a podcast moment. |
| 6 | UFC fight night | style + format | Both, and the format is the bigger half: a full show format with commentators, a villain and a finishing move (see Show formats). The broadcast look is the style. |
| 7 | Talking object | format | New format profile: the product or the problem speaks. Works in any style. |
| 8 | Whiteboard explainer | style + format | Style: Whiteboard sketch (in the bank). Format: it is your Demonstration, drawn. |
| 9 | Rick and Morty | style | In the bank as Adult cartoon. Trademarked name — generic look only. |
| 10 | Skeleton stories | style | In the bank as Skeleton character. |
| 11 | Muppet story | style | In the bank as Felt puppet. Trademarked name — generic look only. |
| 12 | Singing ingredients | format | Your Song ad crossed with Talking object. A variant, not a new format. |
| 13 | Hypermotion cinematic | style | In the bank. |
| 14 | Anime style | style | In the bank. |
| 15 | Disney character | style | In the bank twice: Family 3D animation, and 1950s hand-drawn cel (you already proved that one). Trademarked name. |
| 16 | Low poly story | style | In the bank. |
| 17 | Crochet style | style | In the bank. |
| 18 | Cartoon comic | style | In the bank as Comic panel. |
| 19 | Paper style | style | In the bank as Paper cut-out. |
| 20 | Horror style | style | In the bank. |
| 21 | Lego character | style | In the bank as Brick figure. Trademarked name — generic look only. |

## The line, end to end — as you described it

Two triggers are yours: an idea of your own, or swipes sent to teardown. Everything else runs itself and stops only where your eye is needed. Eye marks are your review stops.

| Step | Your eye | State | Note |
|---|---|---|---|
| Teardown (if it's a swipe) |  | built today | Every row of the source is now labelled: A-roll (the speaker on screen saying it), B-roll over a speaker, B-roll under a voice we never see, silent B-roll, or a card. Each row also carries its sound — music, added effects and what they land on, room sound — which was only captured before when nobody was speaking. The teardown closes with a make-list: every shot that isn't the speaker, the words it covers, how long. |
| Brief and script | yes | running | Your main review stop for now. The AI brief now treats the teardown's make-list as the floor for B-roll — every B-roll shot in the source becomes one of ours or is named as dropped, with the reason — and hands the edit a headline, the source's caption look, the music and the effects. |
| Voiceover — one full read |  | running | Already how the voice step works since 09-19: one read for the whole piece, never stitched line by line, with every pause trimmed to a breath. |
| Music and sound effects |  | partly | Songs are made today. A sound-effects pass and a music bed for non-song ads are not a station yet. |
| You approve the audio | yes | gap | Voice, music and effects on one page with play buttons. No picture is made until this is signed. |
| Cast, storyboard, A-roll frames, B-roll frames | yes | partly | First frame, last frame, and what happens between, for every scene. B-roll scenes now have a source: the teardown's make-list, carried through the brief. |
| Scenes generate on top of the approved audio |  | running | Each scene gets its slice of the voice track; lip sync where the scene calls for it; every talking clip is checked word for word against its line. |
| Clip review | yes | running | Two machine checks first — is it the scene we specified, would it stop a thumb — then your eye. |
| Edit stage 1 — the timeline, dead space out | yes | built today | The model lays the approved clips: talking A-roll with its own sound, dead air cut on the clip, B-roll placed by the words it covers. You see the timeline and a rough cut before anything is final. |
| Edit stage 2 — captions | yes | built today | Captions are a setting: three house looks so far, word-timed off the real audio, inside the safe zone. Matching a swipe's caption style is next. |
| Edit stage 3 — final export |  | built today | One render, machine-checked. |
| Learning |  | partly | In the edit, every change you make is already kept with your reason, and the learning prompt is written. Writing those rules back into the next cut — and doing the same for script, audio and frames — is still to build. |

**What the chain already heard, and what it didn't.** It was half there. Stage 0 already listens and rules the sound form — spoken, sung, rapped, music only, silent — and the teardown already described the music when NOBODY SPEAKS. The hole was music and effects UNDER speech, which is most ads: they were invisible. And the two middle stages, the spec and the injection, carry nothing about sound at all. The fix is one column on the row where the sound happens, which the brief reads straight off the record — not another stage.

**The roll labels:** `A` A-roll — The person whose words we hear is on screen saying them. · `B-over` B-roll over a speaker — Her words carry on, the picture leaves her to show something. · `B-vo` B-roll under a voice — A narrator we never see. · `B-silent` Silent B-roll — Picture with only music or sound under it. · `C` A card — A packshot, a title, a graphic, a text-only frame.

**Prompts:**

- Teardown — stage 1, v11 (adds Roll and Sound per row, and the make-list): `components/video-teardown/prompts/stage-1-teardown/stage1-teardown-v11-damon.md`
- AI brief — stage 5, v11 (uses the roll labels; adds the edit block): `components/video-teardown/prompts/stage-5-brief/ai-lane/stage5-ai-brief-v11-damon.md`

**Built next, in order:**

1. Run one real swipe through the new teardown and brief — nothing has been run on them yet.
2. A music and sound-effects station before frames, with the audio review stop — the teardown now hears them and nothing makes them.
3. Copy a swipe's caption style from the brief's caption read; headline placement that knows where the face is.
4. Write up the show formats you pick — fight night first.

## The video edit — how it works, and how you run it

The video edit tool, in the lab, built to the same shape as every other tool in your blueprint. It is joined to the video machine, the model cut is on, and it ran end to end on a test tonight. Nothing about it needs a person in a timeline.

> The model decides. The cut sheet records. The machine executes. You approve. The cut sheet is one file that IS the edit — every clip, trim, sound, caption and overlay. A change is a new version of that file, never a regeneration, and every change is kept with your reason.

**Proof:** The second test, after your notes. Two new B-roll scenes were generated with the same woman in the same kitchen — a scroll stopper for the hook, and sunscreen going onto her arm with a frustrated face. Her talking A-roll was not touched.

- Lip sync fixed at the root. The first test laid a separate voice file over her talking clip, and used a second talking take as 'B-roll' — both wrong. Now a talking clip keeps its own sound, always, and the finished file is measured against it: 0 ms off on every talking cut.
- Dead air is cut on the clip itself — picture and sound together at every long pause. The same scene went from 12 seconds to 7.9.
- The headline is on screen from frame one, no fade, and lives exactly as long as the scroll stopper under it.
- B-roll is placed by the WORDS it covers — 'is why … worked' — so it lands right even after the pauses are cut.
- Still open, as you said: the headline doesn't yet know where her face is.

**The model cut's first try — and why your notes matter.** I gave the model the two B-roll clips with no placement and let it cut. It put the scroll stopper under the WHOLE hook sentence and left the sunscreen clip out, explaining that the words it belonged under were already covered, and offering the swap. A defensible read — and not yours. Your version (stopper over the opening clause, sunscreen over 'is why the sunscreen hasn't worked') is the cut in the video above, and the difference is filed so the next cut starts closer. That is the loop working.

### The steps

1. **Gather** (machine) — Reads the video machine's own run record and builds the kit: a to-camera scene becomes talking A-roll, a B scene becomes B-roll over its slice of the voice read. A clip only counts as approved when the record says so; everything else is listed by name.
2. **Cut** (model) — The machine first makes the lip-safe draft — talking A-roll cut at its pauses, every word timed. Then the model decides where B-roll and on-screen text go, reading the brief, the A/B labels and everything you have taught it. It is ON. If its cut is refused twice, the mechanical cut takes over and the page says so.
3. **Gate** (machine) — Nothing renders red. A hole in the picture, a trim past the end of a clip, B-roll with nothing under it, text where the app's buttons sit, a caption look that isn't on the list, a cut with no reason — each is named and held.
4. **Stop 1 — the timeline** (you) — The timeline page plus a rough cut with no captions. Approve, or say what to change in plain words.
5. **Stop 2 — the captions** (you) — Same cut, captions on. Approve, switch the look, fix a word. Switching the look never touches the footage.
6. **Export** (machine) — The cut sheet becomes a HyperFrames page and renders. Same sheet, same video, every time.
7. **Checks** (machine) — Length matches the sheet. Picture never black. Voice level where a phone expects it. Lips in time on every talking cut, measured. (Caption contrast over every second is next.)
8. **File** (machine) — The record goes to the runs folder under the brand; the video to the same path on the Drive, named by your naming convention.
9. **Learn** (model) — What you say as a rule is filed as a rule straight away — two are on file from today. A one-off change is kept as an observation and only becomes a rule when it is seen twice.

### How you control it

- **Two triggers** — It starts itself when production hands over an approved kit. Or you point it at a folder. That's all.
- **Two stops** — Timeline, then captions. Everything else runs without you.
- **Plain words** — 'Lose the pause after sunscreen.' 'B-roll a beat earlier.' 'Captions in the clean look.' Each one becomes a new version of the cut sheet with your reason attached.
- **The dials** — Pace (how much silence is left) · caption look · captions on/off · music and sound-effect levels · transition · what stills do · the safe zone · output shapes. Set once as house defaults; any run can override one.

### The elements it is made of

- **The kit** — What production hands over, now written automatically from a video machine run: talking clips with their own sound, B-roll with the words it covers or the voice slice it sits over, music, sound effects, format and style ids.
- **The cut sheet** — Layers on one clock: hook text · captions · B-roll · A-roll · voice · music · sound effects · end card. Every cut carries a one-line 'why'.
- **What you've taught it** — A short file of your rules that outranks the cut prompt. On file today: the headline is there from frame one; talking A-roll is never rebuilt in the edit. Filed as observations, not yet rules: the scroll stopper covers the opening clause, not the whole sentence; text should know where the face is.
- **Caption looks** — A bank, like styles: Bold highlight, Clean lower, One word so far — and 'match the swipe', which builds a one-off look from the teardown's read of the original's captions. Now in your element library; an unknown look is refused.
- **Transitions** — Hard cut is the house default — cut on the line, audio leading. Flash and punch-in are on the list; anything else gets added by name.
- **Sound rules** — Voice levelled to a phone-friendly loudness on a copy. Music 18 dB under. A sound effect lands two frames before its picture.
- **The engine** — HyperFrames. Only one file in the tool knows it exists — swap engines later and only that file changes.

### Editing rules

1. **Nothing moves in a straight line** — Every move eases in or out. Linear motion is the fastest 'a computer made this' tell.
2. **Never a lone fade** — Things arrive with two or three properties moving together — fade plus slide plus scale — and groups arrive staggered, not all at once.
3. **Exits are twice as fast as entrances** — And everything that enters also exits.
4. **One loud colour per frame** — One highlight, everything else neutral. Same rule for glow.
5. **No frozen pictures** — Any still gets a slow push or drift, alternating direction shot to shot. Anything on screen over two seconds breathes.
6. **Captions: 2–4 words, one highlight, two-thirds up** — Timed per word, inside the safe middle of a 9:16 frame where the app's buttons don't cover it.
7. **Sound lands a hair early** — A sound effect hits two or three frames before the thing it belongs to. Music sits about 18 dB under the voice.
8. **The contrast check** — OpenEdit's best idea: measure caption legibility over every one-second window, not once. Catches the bright-counter problem in the proof above automatically.
9. **Render, look, fix, render** — The machine pulls frames from its own export and checks them before you ever see it.

### Prompts

- The cut prompt — stage 2 · v2: `video-edit/prompts/stage-2-cut/stage2-cut-v2-damon.md`
- The learning prompt — stage 9 · v1: `video-edit/prompts/stage-9-learn/stage9-learn-v1-damon.md`

### Honest list: what is not joined up yet

- No production run has approved clips yet, so the join has only been proven on the pigment run's record (1 clip made, 0 approved, 12 scenes to go — it reported exactly that).
- Music and sound effects have no station upstream yet, so those layers have never carried real files.
- Copying a swipe's caption style, the 4:5 and 1:1 shapes, the per-second contrast check, the Drive copy and naming at the end, headline placement that knows where the face is.
- The teardown still needs A-roll / B-roll labels per beat — that is what tells the cut which B-roll to ask for in the first place.

## Tools mined

### [HyperFrames — HeyGen](https://github.com/heygen-com/hyperframes) — installed

The edit engine. A video is written as a web page and rendered the same way every time.

- How it works: a video is a plain web page with timing marks; it renders frame by frame, so the same input always gives the same video. A script can write that page with no person in the loop.
- Around 400 ready blocks: lower thirds, transitions, social-proof cards, charts, end-card parts — for hooks and product end cards.
- 17 caption components (word-by-word highlight, karaoke, kinetic slam) plus the 35-look caption catalogue we tested.
- It turns any transcript into word timings — exactly what your voice step already produces.
- The design for our side: the machine writes one cut sheet per ad (clip order, trims, caption words, overlays); a small adapter turns it into the page; then check, check, render — all automatic.
- Limits found: no speed ramps (any slow-mo has to be baked into the clip first), and one trim setting that desyncs audio if used wrong. Both noted for the adapter.
- Open licence. Its usage pings are anonymous and never include your video or project names; switched off anyway.

### [Open Edit — VEED](https://github.com/veedstudio/open-edit) — mined for parts

An agent-driven caption and motion-graphics pipeline.

- The contrast check: caption legibility judged over every one-second window with a tunable pass bar, not once per video.
- A two-frame 'is anything wrong here' probe per caption beat — catches dead air and unreadable captions for almost nothing.
- 41 caption treatments with exact fonts, colours and motion curves — a caption swipe file for our own looks.
- A letter-spacing formula that sets tracking from the type size instead of guessing.
- Seeded variation: the same run always draws the same 'random' caption look, so a re-render never changes under you.

### [Claude Code Video Toolkit](https://github.com/digitalsamba/claude-code-video-toolkit) — mined for parts

A full kit of commands, transitions and components around Remotion.

- The scene-review stop: approve / edit / refine / flag per scene, and nothing expensive runs until every scene is cleared — the shape of your review stops.
- Seven transitions with exact settings: glitch, colour split, zoom blur, light leak, clock wipe, pixelate, checkerboard.
- A per-brand pair of small files — one for visual tokens sized for video, one for voice settings.
- A lookup of each platform's size, length and audio limits.
- Its screen-recording helper (cookie-banner dismissal, visible cursor) for swiping landing pages.
- Not useful: its 'local' music, voice and video models all need rented graphics cards. None run on your Mac.

### [Remotion skills](https://www.remotion.dev/docs/ai/skills) — rules only

The older, bigger way to do what HyperFrames does. We took its craft, not its engine.

- The nine editing rules on the edit-hand tab come mostly from here.
- Safe text sizes for a 1080-wide frame: about 84 for a headline, 44 for body, 80–100 margin.
- Fit text by measuring it, never by eye.
- HyperFrames wins for you: it takes plain web pages, which is what your page and swipe work already produces. Remotion wins on 3D, maps and audio visualisers — none needed yet.
- Note: the community skill link going round points to the wrong account; the real one is haidrrrry/claude-remotion-skill.

### [Awesome Ad Video Prompts](https://github.com/LichAmnesia/awesome-ad-video-prompts) — mined for parts

Beat-timed ad prompts with camera language and 'don't warp the product' guards.

- Its prompt skeleton: subject and light → timed beats → a 'don't break it' clause → an implied-sound tag. It drops straight onto your first-frame / last-frame / voice-slice scenes.
- A de-duplicated guard list to append to every motion prompt: no deformation, drift, melting, warping, doubling, ghosting, flicker, smearing — plus extra fingers, duplicate hands, label drift.
- Formats it has that your bank doesn't: unboxing/ASMR and before/after as their own shapes.
- A full camera-move vocabulary, de-duplicated, saved with the report.

### [Seedance prompt libraries](https://github.com/YouMind-OpenLab/awesome-seedance-2-prompts) — mined for parts

Four libraries for the exact motion model you print on. One advertises 6,403 prompts but only 107 are actually in the repo — the read covers about 270 real prompts in all.

- 42 distinct styles found. Eight were new and worth having — they're on the board now: macro beauty commercial, studio product hero, dark luxury, 16mm archival, neon noir, fashion editorial, oil painting, ink wash.
- Worth knowing: claymation, felt puppet and brick figure appear in NONE of these libraries. The handmade styles are still thin out there.
- The exact grammar for telling Seedance 'this picture is the first frame, this one the last, this audio is the voice' — instead of hoping it guesses.
- Style-exclusion negatives ('forbidden: 3D render, photoreal…'): a way to pin a style shut so it can't drift mid-clip. Goes into every style lock.
- Pacing negatives ('no slow motion, no freezes, no posing') — a guard category your prompts don't have yet.
- Hard limits to respect before a call is made: 12 files in all — 9 images, 3 video, 3 audio — and 4 to 15 seconds out.
- A 'don't copy the reference picture' clause that stops the model cloning a reference's background when you only wanted the face.
- Several things those libraries call styles are really shot tricks — one-take, freeze-and-rewind, exploded view. Kept out of the bank on purpose.

## How we find the next style before anyone packages it

Two doors into the banks, and two things to read off every post she watches: what it LOOKS like (the style) and what SHOW it is (the format — its cast, its big moment, its voice, its ending). The first door keeps you level with everyone. The second is the one nobody else has, because it starts from her screen and not from an agency's list.

- **Door A — what the AI ad world is already printing** — A weekly sweep of the places styles get published: skill pages like that Notion, the free prompt libraries, Higgsfield's own presets, and AI-made ads in the Meta ad library. Anything found is, by definition, already makeable.
- **Door B — what each sub-avatar already watches** — You already have one entertainment feed per sub-avatar, refilled every morning. Read the STYLE off the posts she actually watches, count it, test it, bank it. A 61-year-old who watches felted-wool miniatures and a 19-year-old who watches low-poly edits should not get the same ad.

### Door B, step by step

1. **Pull her top posts** — From each sub-avatar's feed, the posts with the strongest signal, entertainment lane first. Already collected — nothing new to scrape.
2. **Two reads per post: the look, and the show** — One small prompt answers 'what does it look like?' against the style bank. A second answers 'what kind of show is this?' — who is in it, what the big moment is, who does the talking, how it ends. Each must pick from its bank or say 'not in the bank' and describe it. Kept apart so a style never gets filed as a format again.
3. **Ask what she watches off the phone, too** — Her feed is only her phone. Older women also have daytime TV: cooking shows, soaps, home shopping, courtroom, game shows. The research gatherer already pulls her own words from her own rooms — add one question to it: what shows does she name, quote and joke about? A show she references without explaining is a show she knows by heart.
4. **Count it, with the denominator** — Per sub-avatar: what share of her scroll is each style, and does that style out-pull her feed's average. 'Crochet: 14 of 210 posts, 2.1× her average' — never a percentage on its own.
5. **Run the three tests** — Can we make it, does it hold in motion, does it keep the proof. Below.
6. **Fill the six roles** — For a show that passes: hero, villain, the move, the voice, the replay, the verdict — filled from the brand's avatar, named problem, product, mechanism and offer. If a role has nothing to put in it, the show is wrong for this product.
7. **Bank it with a picture and her name on it** — New row, same frame restyled so it sits on the board beside the others, tagged with which sub-avatars watch it. Unreviewed until you sign it.
8. **Print one and let the ad account vote** — Take an ad that already works, restyle it through the variation chain — same script, same cast, same beats — and run it against the original. The result goes on the style's row.

### The three tests

- **Can we make it?** One approved frame through the image door with the style lock. If the picture on the board looks right, yes. Costs cents.
- **Does it hold in motion?** One five-second clip on the motion model. Some styles look great still and melt when they move.
- **Does it keep the proof?** For skincare this is the one that matters. Claymation kept her spots; a style that smooths skin away can carry a hook or a mechanism scene but never a before-and-after. The row records which.
- **Does the show have a replay?** A show format only works for you if it has a natural moment to zoom in — the slow-motion replay, the overhead bowl shot, the evidence photo, the telestrator. That is where the mechanism goes. No replay, no mechanism, no sale.

| Piece | State | Missing |
|---|---|---|
| One feed per sub-avatar, refilled daily | running | Nothing. |
| Structure reader on swiped posts | running | It reads beats, not style. Style read is a sibling prompt. |
| The style bank + board | built today | 24 rows, none signed. |
| Show format candidates | 11 drafted today | Every 'who watches' line is a guess until her feed and her own words confirm it. |
| Variation chain (restyle an approved ad) | proven once | Should read its style lock from the bank instead of being written fresh. |
| Style read prompt | not built | The one new prompt. It goes on the prompt page like every other. |
| Weekly Door A sweep | not built | A scheduled run beside your 02:30 research. |

## Landscape

| Rung | Everyone | You |
|---|---|---|
| Models | Same models, same prices. | Behind one switch in the Video Machine. A better model is a swap. |
| Prompt packs | Thousands of free ad prompts. Good craft, no brand. | Mined — see Tools mined. |
| Style skills | Claymation, crochet and friends, given away to sell a tool. | A style bank of your own, enforced, with pictures. Each is a cheap restyle of an approved ad. |
| Machine editing | Free and open. Mostly used for generic explainers. | Installed today. Becomes the edit hand. |
| Style and format discovery | Wait for the next published list. | Read it off each sub-avatar's own feed before an agency packages it. |
| Brand injection | Generic product, generic hook. | Avatar, angle, market stage, her own words — bound into every brief. |
| The loop | No skill file knows which ad won. | Ad results and your own edits feed the next run. |
