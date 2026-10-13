<!-- rendered from components/marketing-doctrine/frameworks.json by render.py — do not hand-edit -->

# Visual language — how each frame is made

Bound as `{visual}`. Source: the doctrine component; refs are line pointers into the book, for verification only.

Visual language — how a director decides what each frame looks like: how close, from where, how the camera moves, where the eye goes, where the light comes from, what colour the world is and what it was captured on. The emotional map says what a beat must make the viewer feel; this layer is how the picture makes them feel it. The style id says what world the piece is drawn in; this layer says how each shot inside that world is made.

**The master rule.** THE SWIPE'S CAMERA, THE BEAT'S FEELING. Every visual value starts as the swipe's own — read off the frame map, shot by shot — and ours keeps it, because how a format is shot is part of why it works. Inside that, each shot's choices are made for the feeling its beat carries in the emotional map: closer for intimacy, wider for watching, a change in light or framing to carry the turn. A visual choice that serves neither the swipe nor the feeling is decoration, and decoration is where the average gets in.

_Every example here is illustrative — the shape of a choice, never content for a brief._

## 1. The rules

- **read-off-the-swipe** — Every visual value starts as the swipe's own, read from the frame map shot by shot. Ours keeps it; a change is a SWAP with a reason, never a drift. _(craft)_
- **feeling-picks-the-frame** — Within the swipe's shots, the beat's feeling in the emotional map picks the frame: closer as it builds, the closest on the peak, a change of light or framing on the turn. _(research — block-2008)_
- **contrast-is-intensity** — Visual contrast between shots — in size, angle, light, colour, movement — raises intensity; sameness lowers it. Keep shots alike through a calm stretch and break them at the turn and the peak. _(research — block-2008)_
- **one-camera** — One camera per piece. Scenes never argue with it. _(craft)_
- **motivated-movement** — The camera moves only when something motivates it. _(research — mascelli-1965)_
- **light-has-a-source** — Every light comes from something in the place, and the world block names it. _(craft)_
- **one-thing-per-frame** — Composition, focus and light all point at the one thing the beat is about. _(research — mascelli-1965)_
- **continuity** — Light direction, time of day, wardrobe and the state of the room hold from shot to shot unless the story moves them. _(research — mascelli-1965)_
- **one-real-detail** — Every frame carries one specific real detail from the swipe's room or the avatar's world — the average frame has none. _(craft)_

## 2. A frame, spelled

```
<shot id> · <angle id> · <camera id> — then the specific: how close, what fills the frame, where the eye goes; light: <light id> — where it comes from; colour: <colour id>
```

| Dimension | Values |
|---|---|
| **Shot size** (`shot`) | `extreme-close` · `close` · `medium` · `wide` · `insert` |
| **Angle** (`angle`) | `eye-level` · `high` · `low` · `top-down` · `pov` |
| **Camera** (`camera`) | `handheld-selfie` · `handheld-rear` · `propped` · `locked-off` · `walk-and-talk` · `push-in` |
| **Composition** (`composition`) | `off-centre` · `centred` · `foreground-frame` · `negative-space` · `lived-in` |
| **Light** (`light`) | `window` · `overhead-room` · `practical-lamp` · `golden-hour` · `car-daylight` · `ring-light` |
| **Colour** (`colour`) | `true` · `warm` · `cool` · `mixed` · `punchy` |
| **Capture** (`capture`) | `phone` · `camera` · `screen` |

## Shot size (`shot`)

How much of the subject the frame holds — which is how close the viewer stands.

**Rule.** Shot size is distance: the closer the frame, the more personal the moment. Cut closer as the feeling builds and hold the closest frame for the peak.

- **`extreme-close`** — One detail fills the frame — an eye, a texture, a drop. _Real:_ Phone macro: slight focus hunting, the texture itself sharp. _Serves:_ `surprise`, `satisfaction`, `unease`. _(research — hall-1966)_
- **`close`** — The face, or the hands and the product, fill the frame. _Real:_ Selfie distance: arm's length, slight wide-lens stretch near the edges. _Serves:_ `recognition`, `empathy`, `relief`, `trust`. _(research — hall-1966)_
- **`medium`** — Waist up — a person and what they are doing. _Real:_ A propped phone on a counter or shelf, framed a little loose. _Serves:_ `curiosity`, `hope`, `amusement`. _(research — hall-1966)_
- **`wide`** — The whole person in their place. _Real:_ Phone propped across the room; the place's clutter in frame. _Serves:_ `calm`, `belonging`, `frustration`. _(research — hall-1966)_
- **`insert`** — A cutaway to an object or an action — the product, the hands, the screen. _Real:_ Rear camera held over the action, shadow of the hand sometimes in frame. _Serves:_ `curiosity`, `satisfaction`. _(craft)_

## Angle (`angle`)

Where the camera is relative to the subject's eyes.

**Rule.** Eye level is the default and reads as equal. A high angle makes the subject smaller, a low angle bigger; a top-down angle is a demonstration's angle. Change angle only with the beat.

- **`eye-level`** — Level with the eyes — talking to an equal. _Real:_ The phone at face height, held or propped. _Serves:_ `recognition`, `trust`, `empathy`. _(research — mascelli-1965)_
- **`high`** — Looking down on the subject — small, exposed. _Real:_ The selfie held above the face, the classic phone angle. _Serves:_ `empathy`, `unease`, `frustration`. _(research — mascelli-1965)_
- **`low`** — Looking up — bigger, confident. _Real:_ Phone low on a counter, tilted up. _Serves:_ `desire`, `belonging`, `urgency`. _(research — mascelli-1965)_
- **`top-down`** — Straight down on a surface — a demonstration. _Real:_ Phone held flat over the counter, the light from the room above. _Serves:_ `satisfaction`, `curiosity`. _(craft)_
- **`pov`** — The subject's own eyes — the viewer's hands in frame. _Real:_ Arms enter from the bottom edge, elbows off frame. _Serves:_ `recognition`, `satisfaction`. _(craft)_

## Camera (`camera`)

What the camera is held on and how it moves.

**Rule.** One camera per piece, taken from the swipe. A move happens only when something motivates it — the subject moves, the beat turns. A move for its own sake is the floating camera.

- **`handheld-selfie`** — Front camera, held at arm's length; small natural shake. _Real:_ Micro-shake, the frame drifting with the breath, a re-frame now and then. _Serves:_ `recognition`, `empathy`, `trust`. _(craft)_
- **`handheld-rear`** — Rear camera held by someone, or by the subject over an action. _Real:_ Shake, a quick re-focus, auto-exposure catching up. _Serves:_ `curiosity`, `satisfaction`. _(craft)_
- **`propped`** — Phone leaned on something; the frame does not move. _Real:_ Slightly crooked horizon, the subject a little off-centre. _Serves:_ `calm`, `amusement`, `trust`. _(craft)_
- **`locked-off`** — Tripod; a composed, still frame. _Real:_ Level and still, the only movement inside the frame. _Serves:_ `calm`, `trust`, `satisfaction`. _(craft)_
- **`walk-and-talk`** — The camera moves with a walking subject. _Real:_ Footstep bounce, the background passing, wind noise. _Serves:_ `urgency`, `curiosity`, `belonging`. _(craft)_
- **`push-in`** — The frame moves closer during the shot. _Real:_ Done by a hand on a phone: uneven speed, a small overshoot. _Serves:_ `unease`, `desire`, `surprise`. _(research — block-2008)_

## Composition (`composition`)

Where things sit in the frame and where the eye goes first.

**Rule.** The eye goes to ONE thing per frame — the thing the beat is about — and composition, focus and light all point at it. Off-centre is the default; centred is for direct address and for a format that is centred in the swipe.

- **`off-centre`** — The subject on a third, room on the other side. _Real:_ Never perfectly on the third — a little loose, as a person frames it. _Serves:_ `calm`, `curiosity`, `recognition`. _(research — mascelli-1965)_
- **`centred`** — The subject dead centre, square to camera. _Real:_ Only for direct address to the lens; the selfie is naturally centred. _Serves:_ `trust`, `urgency`. _(craft)_
- **`foreground-frame`** — Something in the foreground frames the subject — a doorway, a shelf, a shoulder. _Real:_ The foreground soft and slightly out of focus. _Serves:_ `curiosity`, `empathy`. _(craft)_
- **`negative-space`** — Empty space around a small subject. _Real:_ A real empty wall or sky, never a backdrop. _Serves:_ `unease`, `calm`. _(research — block-2008)_
- **`lived-in`** — A full, real frame — the place's clutter around the subject. _Real:_ The objects the avatar actually owns, a little untidy. _Serves:_ `recognition`, `belonging`. _(craft)_

## Light (`light`)

Where the light comes from and what it does.

**Rule.** Every light has a source in the place — a window, a lamp, the ceiling, the sun — and the world block names it. Changing the light is one of the strongest ways to carry the turn: flat and cool for the low, warm and open for the after.

- **`window`** — Daylight from one side through a window. _Real:_ One side brighter, a soft shadow on the other, the window sometimes blown out. _Serves:_ `calm`, `trust`, `relief`, `hope`. _(craft)_
- **`overhead-room`** — The room's own ceiling light. _Real:_ Top-down, slightly green or yellow, shadows under the eyes. _Serves:_ `frustration`, `unease`, `recognition`. _(craft)_
- **`practical-lamp`** — A lamp in the shot lighting the scene. _Real:_ Warm pool of light, dark corners, mixed with the screen's glow. _Serves:_ `calm`, `empathy`, `belonging`. _(craft)_
- **`golden-hour`** — Low warm sun. _Real:_ Long shadows, lens flare, faces warm on one side. _Serves:_ `hope`, `desire`, `belonging`. _(craft)_
- **`car-daylight`** — Daylight through a car windscreen. _Real:_ Even but directional, the seat and window in frame. _Serves:_ `recognition`, `amusement`, `trust`. _(craft)_
- **`ring-light`** — A creator's ring light — even, frontal, a ring in the eyes. _Real:_ Only where the swipe is a creator at a desk; catchlight ring visible. _Serves:_ `trust`, `urgency`. _(craft)_

## Colour (`colour`)

The temperature and saturation of the world.

**Rule.** Colour is the place's, not a grade laid on top. Real rooms mix temperatures — daylight and a lamp, a screen's blue. A colour shift across the piece can carry the arc; a grade that matches no room anyone lives in is a tell.

- **`true`** — The colours as the phone saw them. _Real:_ Auto white balance, slightly off in mixed light. _Serves:_ `trust`, `recognition`. _(craft)_
- **`warm`** — Leaning yellow-orange. _Real:_ From the light source — a lamp, the sun — never from a filter. _Serves:_ `calm`, `belonging`, `relief`, `desire`. _(research — block-2008)_
- **`cool`** — Leaning blue. _Real:_ Morning light, a screen, an overcast window. _Serves:_ `unease`, `frustration`. _(research — block-2008)_
- **`mixed`** — Two temperatures in one frame. _Real:_ Window daylight and a warm lamp together, as real rooms are. _Serves:_ `recognition`, `curiosity`. _(craft)_
- **`punchy`** — High saturation, bright — the meme and entertainment register. _Real:_ Only where the swipe runs it; phone 'vivid' mode, not a cinema grade. _Serves:_ `amusement`, `surprise`, `urgency`. _(craft)_

## Capture (`capture`)

What the picture was recorded on — the texture of the image itself.

**Rule.** The capture is the swipe's. A phone format keeps the phone's texture — deep focus, grain in the shadows, compression, exposure that shifts — and never gets shallow cinema focus or a film grade.

- **`phone`** — A phone camera. _Real:_ Deep focus, wide lens, sensor noise in the shadows, auto-exposure shifts, compression. _Serves:_ `recognition`, `trust`, `empathy`. _(craft)_
- **`camera`** — A dedicated camera — a produced piece. _Real:_ Shallow focus, clean shadows, a chosen lens. _Serves:_ `desire`, `satisfaction`, `calm`. _(craft)_
- **`screen`** — A screen recording. _Real:_ The interface, the notification, the thumb tapping. _Serves:_ `curiosity`, `trust`. _(craft)_

## Receipts

- `block-2008` — Block, B. (2008). The Visual Story: Creating the Visual Structure of Film, TV and Digital Media (2nd ed.). Focal Press. https://www.routledge.com/The-Visual-Story-Creating-the-Visual-Structure-of-Film-TV-and-Digital-Media/Block/p/book/9781138014152 The principle of contrast and affinity: visual contrast between shots raises the audience's emotional intensity, visual affinity lowers it — in space, line, colour, tone and movement.
- `mascelli-1965` — Mascelli, J. V. (1965). The Five C's of Cinematography: Motion Picture Filming Techniques. Cine/Grafic Publications. https://archive.org/search?query=%22Five+C%27s+of+Cinematography%22 Camera angles, continuity, cutting, close-ups and composition — the working grammar of the shot: what each angle does to the subject, why a move must be motivated, how continuity holds a scene together.
- `hall-1966` — Hall, E. T. (1966). The Hidden Dimension. Doubleday. https://archive.org/search?query=%22The+Hidden+Dimension%22+Hall Proxemics: intimate, personal, social and public distance carry different relationships — the logic behind shot size as how close the viewer stands.
