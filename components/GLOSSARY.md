# Words and names

What things are called and what they mean, with where to find each. `<brand>` is Brand A or Brand B. Written 2026-10-26.

**Who it is for, why they care, when, what the ad says and how it is built (avatar, angle, moment, idea, hook, format): defined once in `components/marketing-doctrine/slices/words.md`.** The rows below only point there.

Page: the Words tab on https://claude.ai/artifact/YPr6iQKvGXwj721mGsYTW9. Naming rule source: `components/naming/CONVENTION.md`.

## Names

| Word | What it means | Where to find it |
|---|---|---|
| **brand** | Brand A or Brand B. Every folder and every command names the brand it is for. | brands/<brand>/ and runs/<component>/<brand>/. Search the folder name. |
| **product** | The product inside a brand (flex, crush, a body scrub). Each brand's products start counting briefs at 1. | brands/<brand>/products/ |
| **brief number** | brief-NNNN. One number for one idea, from the teardown to the Meta ad. Counts per brand and product. The old code pNNN is the same number (p152 = brief-0152). | brands/<brand>/briefs/briefs.json. Search the number: grep -rl "brief-0221" brands runs, or ask 'where is brief 0221'. |
| **batch** | batch-YYYY-MM-DD-a. One group of finished assets made together; the letter is the nth batch that day. | In every delivery folder name. New one: python3 components/naming/names.py next-batch <brand> |
| **delivery folder** | brand_product_brief_batch. The folder finished work is dropped into. Editors and designers never rename files. | Shared Assets/meta/<brand>/1-check/<kind>/ and runs/handoffs/. Search the brief number. |
| **asset file** | The delivery folder name plus _asset-NN (asset-01, asset-02). No funnel in a file name. | Inside the delivery folder. naming.json inside it lists old name to new name. |
| **Meta ad name** | The delivery name plus the landing page: brand_product_brief_batch_funnel. One per batch per page, never an asset number. | In Ads Manager. It joins spend back to the brief. |
| **ad set** | adset_<brand>_<avatar>_<angle>. Who the ad speaks to and the claim it makes. | brands/<brand>/briefs/briefs.json (the brief's header). |
| **campaign** | campaign_<brand>_<market>_<product>_<funnel>_<objective>_cbo. The market, product and goal. | In Ads Manager. |
| **run and run label** | A run is one execution of a component. Its folder is runs/<component>/<brand>/<label>/. The label is its name, often the swipe or brief it came from. | ls runs/<component>/<brand>/ then open the newest folder. |
| **slot id** | nov-02. One email on the calendar. In review, P1 is picture 1 and S1 is part 1 of that email. | runs/marketing-calendar/<brand>/<YYYY-MM>/slots.json |
| **1-check, 2-approved, 3-live, sent-back** | The four Drive folders an ad moves through. 1-check waits for the owner. Only his click moves it on. | Shared Assets/meta/<brand>/<state>/<kind>/<ad name>/ |

## Things

Marketing routing and the distinction between chat lane, workstream, maker route, category, skill, component, workflow and checklist live in `components/WORKFLOWS.md` → Distinguish the layers. Do not maintain a second routing table here.

| Word | What it means | Where to find it |
|---|---|---|
| **swipe** | Someone else's ad, post or page that already works. A competitor's, an organic post, or one of our old winners. | runs/intake/<brand>/<date>/swipes.jsonl and Shared Assets/swipe/ |
| **teardown** | Stripping a swipe down to its structure with the brand removed: what it is, why it works. | runs/video-teardown/<brand>/ or runs/image-teardown/<brand>/ |
| **idea** | A swipe plus our angle, numbered on the storyboard board (Idea 2, key idea-2). It stays an idea until its brief is approved and given its brief number. Its production folder is idea-2 until then. The old keys brief2 and P02 still open it. | The Video Studio's list of ads; the board's matrix.json; links read idea=2. |
| **script** | The words and scenes written for an idea: the writing line's stage-5 draft. Until it is approved it is the script, never the brief. | runs/video-teardown/_work/<run>/stages/5-brief.md |
| **brief** | An approved script with its brief number: the one document a maker opens. A teardown writes it; nothing else crosses to the maker. Before approval it is the script. | runs/video-writing/<brand>/<id>/deliverable/5-brief.md or runs/image-teardown/<brand>/<label>/06-brief.md |
| **lane (creator lane, AI lane)** | Who makes it. Creator lane: a person films it. AI lane: the machine generates it. Say which when you ask. | In the brief's header and the teardown's route. |
| **injection** | Putting our brand into a swipe's structure: substitute, never rewrite. | A stage file named injection inside a video-writing or image-teardown run. |
| **hook** | The first seconds of a video, or the headline of a still. What stops the scroll. | Stage 4b hooks (video-writing) and 04-headlines (image-teardown). |
| **cast, casting** | The person who plays a role. Casting finds who is already banked, or names the gap. | runs/casting/<brand>/ and the brand's cast registry. |
| **scene, shot and clip** | A scene is one moment of the video, its shots in order (S1). A shot is one camera view inside it (S1.1). A clip is the generated or filmed footage for a shot. | runs/video-production/<brand>/<run>/ and the Video Studio's Production tab |
| **line** | One spoken line with its speaker, written NAME: words. The storyboard, production and the take sheet show the same lines, and an edit in one updates the others. | components/video-studio/script_lines.py |
| **take, take sheet, print** | A take is one printed attempt at a scene's clip (take-1). The picked take is the one in use. The take sheet is its settings: cast, lines, moves, faces and camera. To print is to make a take. | A scene's take-N.json and take.json in the Video Studio's data; components/video-studio/take.py |
| **version** | One finished cut of the whole ad. | The Video Studio's Versions tab |
| **A-roll and B-roll** | A-roll: the person talking to camera. B-roll: the cutaway footage laid over it. | Inside the kit and the cut. |
| **kit (three meanings)** | EDIT KIT: the folder of ingredients for one video (voice track, clips, music, sound effects, and edit-kit.json listing them). 'Cut this kit' means run the edit on that folder. DROP KIT: the import sheet and picture files meta-upload builds for Meta. SWIPE PACK: a zip of swipe files. | Edit kit: runs/video-edit/<brand>/<label>/kit/. Drop kit: runs/meta-upload/<brand>/<label>/. Swipe pack: runs/swipe-organic/_packs/. |
| **cut, cut sheet, stops** | The cut is the edited video. The cut sheet is the one file that IS the edit. Two stops hold it for approval: the timeline, then the captions. | runs/video-edit/<brand>/<run>/ (timeline.html, the cut sheet versions). |
| **draft** | For statics: the best of three judged tries (rolls) at a picture. If none pass after four rounds, the best ships flagged. | components/image-teardown/drafts/<brand>/vN/ |
| **baseline, variation, delta** | The baseline is the approved draft. A variation is the same ad with ONE change. The delta is that one change, written as the instruction. | runs/image-edit/<brand>/ and runs/image-teardown/<brand>/<batch>/deliverable/ |
| **plate** | The generated picture before the words and product are laid over it. | Inside an image run. |
| **judge, flagged** | The judge is the model that scores a picture or clip against the swipe. Flagged means it shipped anyway with what it failed written beside it. | flags.json and judge.json in the draft round folder. |
| **held (hold)** | Stopped because something is missing or wrong. A hold names the problem; fix it upstream and run again. It is not a failure. | check.json in the run folder. |
| **gate, check, stage check** | A gate is a rule a piece must pass. Stage check asks one question: is it done for its lane? | runs/stage-check/<brand>/<batch>/ |
| **review** | A person looks at the finished pictures or cut, says what to change, and gives a verdict (approve, fix, reject). Not the final go. | platform/data/records/review/ |
| **hand-off** | Giving a finished drop to another person to upload as one verified link. Not used in the main chains. | runs/handoffs/ |
| **deliverable** | The finished output of a run. Everything else in the folder is how it got there. | deliverable/ inside the run folder. |
| **avatar, sub-avatar, demographic** | Who it is for. Defined in `components/marketing-doctrine/slices/words.md`. | components/marketing-doctrine/slices/words.md |
| **desire, awareness, market stage, doubt, angle (claim)** | Why they would care. Defined in `components/marketing-doctrine/slices/words.md`. Only the owner signs an angle or opens an ad set. | components/marketing-doctrine/slices/words.md, brands/<brand>/strategy/angles.json |
| **offer** | The price and deal an ad may state. Prices come only from the offer bank. | brands/<brand>/offers/ |
| **format, element** | A format is a named structure for an ad or email (offer-urgency, hero-product). An element is one row of the shared library that labels things. | components/elements/ and the element labels in a teardown. |

## Skills and components

| Word | What it means | Where to find it |
|---|---|---|
| **component** | A folder in components/ that does one job and writes its results to runs/. The name is the job. | ls components/ |
| **skill** | A sentence you say that starts a component. A front-door skill has the component's exact name. A job skill says its component on its first line. | ls .claude/skills/ or the Skills and Components page. |
| **stage** | One step inside a component or a workflow, with its own prompt and its own output file. | stageN files inside a run folder. |
| **winners** | The component that carries a brand's loop from ad results back to the writing prompts, in five steps: Results, Audit, Bank, Feed, Score. | components/winners/ and runs/winners/<brand>/ |
| **audit** | Every creative that spent in a time frame, copies merged, ranked by purchases, tagged, on one board. | runs/winners/<brand>/audit/<since>_<until>/ |
| **Core** | The fewest top creatives that make 60% of purchases in an audit window, counted fresh each audit. | Marked on the board and in the bank. |
| **bank** | One record per brand of every ranked creative with its numbers and words, one snapshot per window. Each row's state is candidate or winner. | runs/winners/<brand>/bank.json |
| **bar** | The brand owner's numbers for a winner: minimum spend, maximum CPA, minimum ROAS. A row is a winner when its newest snapshot clears them. Open until set, and while open every row is a candidate. | Top of the bank. |
| **feed** | The top rows of the widest audit window with their numbers and words, for the hook prompt's {winners} slot. Once a bar is set, only rows that clear it. | runs/winners/<brand>/feed.md |
| **score** | Ad results joined to the prompts that wrote each ad, rolled up by origin, hook prompt, brief prompt and the winner each run borrowed from. |
| **origin** | Where an ad's spend traces to in a score: chain, banked, brief made outside writing, or pre-system. Every ad has one. | runs/winners/<brand>/score/<asof>/score.md | runs/winners/<brand>/score/<asof>/score.md |

## How to search

| I have | Do this |
|---|---|
| I have a brief number | grep -rl "brief-0221" brands runs  (or the old code, grep -rl "p152" brands runs). Or say: where is brief 0221 for <brand>? |
| I have an ad name | The name starts with the brand, product, brief number and batch. Search the brief number part. The same text is the folder name on the Drive under Shared Assets/meta/<brand>/. |
| I want a run's results | ls runs/<component>/<brand>/ and open the newest folder. The component name is the step's name. |
| I want to know where something is stuck | Say: is brief 0221 ready? The stage-check skill answers and names what is missing. |
| I want a skill or component | ls .claude/skills/ and ls components/. Or open Skills and Components. |
| I want footage | Say: find a shot of <what is in it> for <brand>. The asset-index skill searches what is IN the clips. |
| I want a word's meaning | components/GLOSSARY.md, or the Words tab on the workflow page. |
