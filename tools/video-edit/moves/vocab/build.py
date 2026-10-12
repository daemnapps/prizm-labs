"""Builds index.html (the page) and VOCAB.md (the team mirror) from one list.
Edit TERMS below, then run: python3 build.py"""
import html, os
HERE = os.path.dirname(os.path.abspath(__file__))

# Times are on the finished AI Slop video's clock (42.3s = 3.6s opener + 38.7s loop).
GROUPS = [
 ("cuts", "Cuts", "How one shot hands over to the next, with no effect in between."),
 ("transitions", "Transitions", "Moves that carry you from one shot or place into another."),
 ("time", "Time", "Playing with how fast, which way and how often time runs."),
 ("motion", "Motion", "How things move inside the frame: the feel of the movement itself."),
 ("compositing", "Tracking & compositing", "Putting things into footage so they look like they were always there."),
 ("sound", "Sound-led", "Picture decisions made by the music."),
 ("camera", "Camera", "Where the camera is and how it travels."),
]

# (group, id, term, definition, you'd say, visual, where-in-AI-Slop)
# visual: ("clip", file) = cut from the finished AI Slop video; ("demo", file) = not in AI Slop, so a short demo
# built by demos.py from our own plates and 3D objects (labelled "demo, not in the video"); where = what it shows.
# Every time is on the finished video's clock (42.3s: the 3.6s opener, then the 38.7s loop).
TERMS = [
 # CUTS
 ("cuts","hard-cut","Hard cut","One shot stops and the next starts instantly, with nothing in between.",
  "Hard cut from the falls straight into the next shot, no fade.",("clip","hard-cut"),"0:27.9 — one shot straight into the next"),
 ("cuts","match-shape","Match cut — shape","The cut lands so a shape in one shot sits in the exact same spot as a similar shape in the next.",
  "Match cut the stone him into the stone him — same size, same spot.",("clip","match-shape"),"0:32.7 — stone him into stone him"),
 ("cuts","match-motion","Match cut — motion","A movement that starts in one shot carries on in the same direction and speed in the next.",
  "Swap the outfit mid-move so the gesture carries straight through.",("clip","match-motion"),"0:24.7 — robe into silk shirt, same move"),
 ("cuts","match-colour","Match cut — colour","The last colour of one shot is the first colour of the next, so the eye doesn't feel the jump.",
  "Colour-match out of the purple iris into the purple galaxy.",("clip","match-colour"),"0:06.8 — purple iris into purple galaxy"),
 ("cuts","jump-cut","Jump cut","Cutting inside the same shot so it skips ahead (or back) in time, and the picture visibly jumps.",
  "Jump-cut him on the kick — skip a beat of the shot.",("clip","jump-cut"),"0:35.1 — skips ahead on the kick"),
 ("cuts","smash-cut","Smash cut","A sudden cut from one mood to the opposite — calm to loud, or loud to silent — with no warning.",
  "Smash cut from the quiet river to his face pulling a tongue at the lens.",("clip","smash-cut"),"0:12.9 — calm river into the tongue"),
 ("cuts","j-cut","J-cut","You hear the next shot before you see it: its sound starts early, under the current picture.",
  "J-cut it — let the crowd noise come in before we cut to the court.",("demo","j-cut"),"the court's sound starts before the picture cuts"),
 ("cuts","l-cut","L-cut","The sound of a shot keeps going after the picture has already cut away to the next one.",
  "L-cut the falls — keep their sound running over the court.",("demo","l-cut"),"the falls' sound runs on over the court"),
 ("cuts","cutaway","Cutaway","A short shot of something else (what he's looking at, his hands, the place) dropped in, before returning to the main shot.",
  "Give me a cutaway to his hands, then back to the wide.",("demo","cutaway"),"main shot, a close shot of his hands, back"),
 ("cuts","insert","Insert / B-roll burst","Short extra shots dropped in to add texture — details, places, objects — often a fast run of them.",
  "Hit me with a B-roll burst — quick shots of the city, one per beat.",("clip","insert"),"0:10.1–12.9 — the city burst"),
 ("cuts","cut-beat","Cut on the beat","Every cut lands exactly on a beat in the music, so you feel the edit in your body.",
  "Cut on the kick — every change lands on the beat.",("clip","cut-beat"),"0:19.8 / 0:20.6 — cuts on the kick"),
 ("cuts","flash-frame","Flash frame","A single frame of white (or colour) between two shots — a blink of light on a hit.",
  "Flash the president in for four frames on the kick.",("clip","flash-frame"),"0:19.0 — 4 frames of a persona (a picture, not white)"),
 # TRANSITIONS
 ("transitions","whip-pan","Whip pan","The camera swings sideways so fast it blurs, and comes out of the blur somewhere new.",
  "Whip pan off the monument and land on the falls.",("demo","whip-pan"),"the monument whips to the falls"),
 ("transitions","zoom-transition","Zoom transition","The camera zooms into or out of something (a screen, an eye) and that carries you into the next picture.",
  "Suck everything into one point and zoom out of his eye.",("clip","zoom-transition"),"0:03.6 — into one point, out of his eye"),
 ("transitions","punch-in","Punch-in","The frame jumps a little closer in one hard step, usually on a beat, then settles.",
  "Land every cut punched in, then let it settle.",("clip","punch-in"),"0:16.6 — lands close, then settles"),
 ("transitions","object-wipe","Object wipe","Something passes across the lens and fills the frame, and when it clears we're in a new shot.",
  "Fly the helmet into the lens and wipe us onto the monument.",("clip","object-wipe"),"0:18.1 — the helmet fills the lens"),
 ("transitions","hand-off","Object hand-off","An object leaves one shot through the edge of the frame and arrives in the next shot, so it carries you across.",
  "Hand the koi off — out of space and into the pond.",("clip","hand-off"),"0:08.5 — the koi, space into the pond"),
 ("transitions","morph","Morph","One shape or face melts smoothly into another, with no cut.",
  "Morph the stone statue into him, flesh coming through the stone.",("clip","morph"),"0:33.3 — stone becomes him"),
 ("transitions","iris","Iris transition","The picture opens or closes through a circle — here, the eye's iris opens into another world.",
  "Push into his eye and open the iris into space.",("clip","iris"),"0:06.0 — space in the iris"),
 ("transitions","dissolve","Dissolve","One shot fades out while the next fades in on top of it, so for a moment you see both.",
  "Dissolve the phone screen into the opening frame.",("clip","dissolve"),"0:41.6 — the screen dissolves into frame one"),
 ("transitions","ramp-transition","Speed-ramp transition","The shot speeds up hard into the cut, and the next shot comes in fast and slows down.",
  "Ramp into the cut and ease out the other side.",("clip","ramp-transition"),"0:06.0–6.8 — speeds up into the cut"),
 ("transitions","invisible-cut","Invisible cut","The cut is hidden in a moment where the frame goes fully dark or blocked, so it looks like one continuous shot.",
  "Hide the cut in the black of his sunglasses so it feels like one take.",("demo","invisible-cut"),"the cut hides in the black of his sunglasses"),
 # TIME
 ("time","speed-ramp","Speed ramp","The speed changes inside one shot: fast, then suddenly slow on the key moment, then fast again.",
  "Ramp the Goja shot — backwards, forwards, stop, go.",("clip","speed-ramp"),"0:03.6–6.8 — Goja, −3.2× to 5.1×"),
 ("time","slow-mo","Slow motion","Time runs slower than real life so you can see every detail of a moment.",
  "Put the forehand in slow-mo so you see the ball leave the racket.",("demo","slow-mo"),"the forehand at real speed, then ¼ speed"),
 ("time","bullet-time","Time freeze / bullet time","Time almost stops, and the camera keeps moving around the frozen moment.",
  "Freeze him in stone and let the camera drift round him — bullet time.",("clip","bullet-time"),"0:29.5–32.7 — bullet time"),
 ("time","reverse","Reverse","The footage plays backwards.",
  "Reverse the falls so the water climbs back up.",("clip","reverse"),"0:26.3–29.5 — played backwards"),
 ("time","loop","Seamless loop","The last frame hands straight back into the first, so it plays forever with no visible seam.",
  "Make the end hand back into the start so it loops forever.",("clip","loop"),"0:42.3 → 0:00 — the seam"),
 ("time","stutter","Stutter","The same few frames repeat quickly, so the picture looks like it's skipping or stamping.",
  "Stutter three frames of him on the kick.",("demo","stutter"),"the same three frames, four times over"),
 ("time","echo","Echo / trails","A moving thing leaves fading copies of itself behind it.",
  "Give him an echo trail as he dances.",("demo","echo"),"fading copies of him trail behind"),
 # MOTION
 ("motion","keyframe","Keyframe","A point where you pin down where something is at a certain moment; the computer fills in the movement between the pins.",
  "Pin the temple at the lens at both ends and let it travel between.",("clip","keyframe"),"0:18.2–19.7 — the temple, lens to lens"),
 ("motion","linear","Linear","Movement at one constant speed from start to stop — feels robotic.",
  "It feels linear — give it some ease.",("demo","linear"),"the headphones at one speed: evenly spaced dots"),
 ("motion","ease-in","Ease-in","Starts slow and speeds up — like something being pulled away.",
  "Ease-in so the bag accelerates out at the lens.",("clip","ease-in"),"0:29.3 — the bag speeds up and leaves"),
 ("motion","ease-out","Ease-out","Starts fast and slows down to a stop — like something landing.",
  "Ease-out as the basket lands in the shot.",("clip","ease-out"),"0:23.0 — the basket slams in and settles"),
 ("motion","ease-in-out","Ease-in-out","Starts slow, speeds up in the middle, slows down at the end — the most natural feel.",
  "Ease-in-out on the headphones so they don't jerk.",("demo","ease-in-out"),"the headphones ease in and out: dots bunch at the ends"),
 ("motion","anticipation","Anticipation","A small move in the opposite direction just before the main move, like winding up before a throw.",
  "Give it anticipation — the racket drops back before it swings.",("clip","anticipation"),"0:21.5 — the racket winds back"),
 ("motion","overshoot","Overshoot","Something goes a bit past where it should stop, then settles back — it feels bouncy and alive.",
  "Pop the headphones in with a little overshoot.",("demo","overshoot"),"the headphones pop past full size, then settle"),
 ("motion","follow-through","Follow-through","When the main thing stops, the loose parts (hair, a strap, a tail) keep moving for a moment.",
  "Let the headphones keep swinging after they stop.",("demo","follow-through"),"the headphones stop; the swing carries on"),
 ("motion","motion-blur","Motion blur","Fast movement smears into a streak, the way a real camera sees speed.",
  "More smear on the disco ball so it feels fast.",("clip","motion-blur"),"0:11.7 / 12.4 — the disco ball smears"),
 ("motion","parallax","Parallax","Near things slide past faster than far things, which makes a flat picture feel deep.",
  "As the camera drifts, the railing should slide faster than the falls.",("clip","parallax"),"0:30.2 — railing vs the falls"),
 ("motion","camera-shake","Camera shake","The picture jolts as if the camera took the hit.",
  "Shake the camera on the hit.",("demo","camera-shake"),"the frame jolts on the hit"),
 ("motion","orbit","Orbit","The camera circles around the subject while he stays in the middle.",
  "Orbit him while the objects float.",("clip","orbit"),"0:35.9 — the objects circle him"),
 # COMPOSITING
 ("compositing","match-move","Motion tracking / match-move","The software follows a point in real footage so a 3D object can be stuck to it and move with it.",
  "Track the shot so the headphones ride his selfie like they're really there.",("clip","match-move"),"0:13.3 — the headphones ride his selfie"),
 ("compositing","roto","Rotoscoping / matte","Cutting a person or object out of the footage, frame by frame; the cut-out shape is called the matte.",
  "Roto him out so the objects can go behind him.",("demo","roto"),"the footage, his matte, him on a new background"),
 ("compositing","keying","Keying / chroma key","Removing one flat colour (usually green) from the picture so you can put anything behind.",
  "Put him on green and key it out later.",("demo","keying"),"him on green, then the green keyed out"),
 ("compositing","compositing","Compositing / layering","Stacking separate layers — footage, 3D objects, text — into one finished picture.",
  "Composite the 3D layer over the footage.",("clip","compositing"),"0:18.3 — before the layers (left), finished (right)"),
 ("compositing","occlusion","Occlusion","When something closer blocks something further away — getting it right is what makes a 3D object feel really there.",
  "The koi should pass behind him, not over him — fix the occlusion.",("demo","occlusion"),"the koi passes behind him"),
 ("compositing","grade","Colour grade / colour match","Adjusting colour and contrast for a mood, or so different shots and layers look like they belong together.",
  "Grade it warmer, with more punch.",("demo","grade"),"before and graded, wiping across"),
 ("compositing","dof","Depth of field / rack focus","How much of the picture is sharp; a rack focus moves the sharp spot from one thing to another.",
  "Shallow focus — only the carousel sharp, the lights behind melting.",("clip","dof"),"0:39.1 — only the carousel is sharp"),
 # SOUND
 ("sound","hit-point","Hit point","The exact moment in the music a picture event must land on — a hit, a drop, a snare.",
  "The ball has to reach the lens right on the hit point.",("clip","hit-point"),"0:23.0 — ball at the lens on the bar"),
 ("sound","downbeat","Downbeat","The first and strongest beat of each bar — the \"ONE\" in 1-2-3-4.",
  "Land the big change on the downbeat, not the 3.",("clip","downbeat"),"0:26.3 — new bar, new shot"),
 ("sound","sync","Sync","Picture and sound lined up so they happen at exactly the same moment.",
  "Every skip and every flash lands on a kick — keep it in sync.",("clip","sync"),"0:15.1 / 15.5 / 15.7 — on the kicks"),
 ("sound","sound-off","Sound-off design","Making the video work even with the sound off — captions, clear visuals, the story told in pictures.",
  "It has to read sound-off — put the words on screen.",("demo","sound-off"),"the words on screen carry it with no sound"),
 # CAMERA
 ("camera","dolly","Dolly in / dolly out","The camera physically moves closer or further — near things grow faster than far ones, unlike a zoom.",
  "Dolly back off the carousel, don't zoom — let the table open up.",("clip","dolly"),"0:40.1 — the 3D camera travels back"),
 ("camera","push-in","Push-in","A slow, steady move toward the subject that builds tension or focus.",
  "Slow push-in on his eye.",("clip","push-in"),"0:05.6 — into the eye"),
 ("camera","pull-back","Pull-back reveal","The camera pulls back to show something we couldn't see — often that the world was smaller or different than we thought.",
  "Pull back to reveal the whole thing was a toy carousel.",("clip","pull-back"),"0:39.1–41.6 — it was a toy"),
 ("camera","pov","POV","Point of view: the camera is someone's eyes, so we see what he sees.",
  "Give me a POV off the back of the moto — road rushing at us.",("clip","pov"),"0:16.6 — riding pillion"),
 ("camera","locked-off","Locked-off","The camera doesn't move at all — only the subject and the world move inside the frame.",
  "Locked-off on the footbridge — only he changes.",("clip","locked-off"),"0:23.0 — the footbridge"),
]

def esc(s): return html.escape(s, quote=True)

def card(t):
    g, id_, term, dfn, say, vis, where = t
    f = vis[1]
    extra = " contain" if f == "compositing" else ""
    if vis[0] == "clip":
        label = f"{term}: {where}, from AI Slop"
        src = f'<span class="src slop">AI SLOP · {esc(where)}</span>'
        hay_where = where
    else:
        label = f"{term}: demo, not in the video. {where}"
        src = f'<span class="src demo">DEMO, NOT IN THE VIDEO · {esc(where)}</span>'
        hay_where = "demo not in the video " + where
    v = f'<video class="clip{extra}" muted loop playsinline preload="none" poster="clips/posters/{f}.jpg" src="clips/{f}.mp4" aria-label="{esc(label)}"></video>'
    hay = esc(f"{term} {dfn} {say} {hay_where}".lower())
    return f'''<article class="card" id="{id_}" data-hay="{hay}">
<div class="vis">{v}</div>
<div class="body">{src}<h3>{esc(term)}</h3><p class="def">{esc(dfn)}</p><p class="say"><span>you'd say</span>“{esc(say)}”</p></div>
</article>'''

def build_html():
    css = open(os.path.join(HERE, "style.css")).read()
    js = open(os.path.join(HERE, "page.js")).read()
    nav = "".join(f'<a href="#g-{k}" class="chip" data-g="{k}">{esc(n)} <b>{sum(1 for t in TERMS if t[0]==k)}</b></a>' for k,n,_ in GROUPS)
    secs = []
    for k, n, blurb in GROUPS:
        cards = "\n".join(card(t) for t in TERMS if t[0] == k)
        secs.append(f'<section class="group" id="g-{k}" data-g="{k}"><header class="gh"><h2>{esc(n)}</h2><p>{esc(blurb)}</p></header><div class="grid">{cards}</div></section>')
    nclip = sum(1 for t in TERMS if t[5][0]=="clip")
    return f'''<meta charset="utf-8">
<title>Motion Vocabulary</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=Instrument+Sans:wght@400;500;600&family=JetBrains+Mono:wght@500&display=swap">
<style>{css}</style>
<div class="wrap">
<header class="top">
  <p class="eyebrow">DAEMN · EDIT BAY</p>
  <h1>Motion Vocabulary</h1>
  <p class="lede">{len(TERMS)} words editors and motion designers use, each one moving. {nclip} are real moments cut from the finished <b>AI Slop</b> video, with the time on its clock. The other {len(TERMS)-nclip} aren't in AI Slop, so each gets a short demo built from our own footage and objects, marked <b>demo, not in the video</b>. Read the name, watch it, steal the sentence.</p>
</header>
<div class="bar">
  <label class="search" for="q"><span class="sr">Search terms</span><input id="q" type="search" placeholder="Search — try “cut”, “slow”, “ball”…" autocomplete="off"></label>
  <nav class="chips" aria-label="Groups">{nav}</nav>
</div>
<p class="none" id="none" hidden>No term matches that. Try a simpler word.</p>
{"".join(secs)}
<footer class="foot">AI Slop clips are cut from the finished video (42.3s: the 3.6s opener, then the 38.7s loop); times are on that clock. Demos are built from the same shoot's plates and the piece's 3D objects, and are not in the video. Source: tools/moves/vocab/ · Mirror: VOCAB.md</footer>
</div>
<script>{js}</script>
'''

def build_md():
    out = ["# Motion Vocabulary — the owner's visual dictionary", "",
           "Editing & motion-design terms. Examples on the HTML page are real moments cut from the finished AI Slop video; terms with no moment in AI Slop get a short demo built from our own footage and 3D objects, marked \"demo, not in the video\".",
           "Times are on the finished video's clock (42.3s: the 3.6s opener, then the 38.7s loop). Clips live in `tools/moves/vocab/clips/`.",
           "Page: (team page)", ""]
    for k, n, blurb in GROUPS:
        out += [f"## {n}", "", f"_{blurb}_", "",
                "| Term | What it is | You'd say it like | Where in AI Slop / visual |", "|---|---|---|---|"]
        for t in TERMS:
            if t[0] != k: continue
            vis = f"{t[6]} (`clips/{t[5][1]}.mp4`)" if t[5][0]=="clip" else f"_demo, not in the video_ — {t[6]} (`clips/{t[5][1]}.mp4`)"
            out.append(f"| **{t[2]}** | {t[3]} | “{t[4]}” | {vis} |")
        out.append("")
    return "\n".join(out)

if __name__ == "__main__":
    open(os.path.join(HERE, "index.html"), "w").write(build_html())
    open(os.path.join(HERE, "VOCAB.md"), "w").write(build_md())
    print(len(TERMS), "terms")
