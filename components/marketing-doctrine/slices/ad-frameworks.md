<!-- rendered from components/marketing-doctrine/frameworks.json by render.py — do not hand-edit -->

# Ad frameworks — the second door

Bound as `{ad_frameworks}`. Source: the doctrine component; refs are line pointers into the book, for verification only.

The assembled frameworks — an ad's plan, chosen rather than read off a swipe. A row names the sections it runs, in order, and for each one the technique that builds it and the scene shape that beat takes. It is the SECOND door into the machine: the first starts from somebody else's asset and abstracts it, this one starts from a choice (avatar x awareness x format x framework) and composes.

A framework is a PLAN, never a law. The order is the intended order; the market state outranks it — a section the chosen awareness level does not call for is dropped, and the drop is stated. Every section id here is a section id in frameworks.json and every technique is one of the seven. Nothing here names a brand, a product, an avatar or a platform.

**Status.** **draft** — not yet signed by the definition owner (rule 6) — every seed row, and every row promoted from a run. **approved** — the owner signed it — every proven row is approved. **deprecated** — retired by the definition owner (rule 6); the row stays so a run that names it still resolves.

**State.** **seed** — read off the doctrine, or promoted from one observed run — a plan that has not yet been judged as an ad. **proven** — the owner signed it after the ads it produced were judged. Only the owner moves a row to proven — and its status is approved.

**Promotion.** framework_bank.py --promote <run-label> copies the framework a run OBSERVED (its doctrine.json) into this file as a new row, status 'draft', state 'seed', source 'observed — <label>'. A session runs it only on the owner's word: the bank is a compiled projection of runs, this file is curated doctrine, and a bank row walking in unasked is how the two stop being different things. NO COINED NAMES — an observed row takes its crosswalk row's name, or a plain description of what it does, never an invented one.

| Framework | Status | State | Sections (technique) | Awareness | Sophistication | Formats it fits | Source |
|---|---|---|---|---|---|---|---|
| PAS (problem · agitate · solve) (`pas`) | draft | seed | `hook` (intensification), `problem` (intensification), `agitation` (intensification), `solution` (intensification), `unique-mechanism` (mechanization), `proof` (intensification), `product` (redefinition), `offer` (intensification), `objections` (redefinition), `call-to-action` (gradualization) | `problem-aware`→`product-aware` | stage-1, stage-2 | single-presenter, micro-drama, testimonial-montage | seed — crosswalk row PAS (problem · agitate · solve) |
| AIDA (attention · interest · desire · action) (`aida`) | draft | seed | `hook` (intensification), `identification` (identification), `problem` (intensification), `transformation` (intensification), `proof` (intensification), `product` (identification), `offer` (intensification), `urgency` (intensification), `call-to-action` (gradualization) | `problem-aware`→`product-aware` | stage-1, stage-2 | any | seed — crosswalk row AIDA (attention · interest · desire · action) |
| BAB (before · after · bridge) (`bab`) | draft | seed | `hook` (intensification), `problem` (intensification), `transformation` (intensification), `unique-mechanism` (mechanization), `proof` (intensification), `product` (redefinition), `offer` (intensification), `call-to-action` (gradualization) | `problem-aware`→`solution-aware` | stage-2, stage-3 | demonstration, single-presenter | seed — crosswalk row BAB (before · after · bridge) |
| Story / testimonial (life · tried · found · now) (`story-testimonial`) | draft | seed | `hook` (camouflage), `identification` (identification), `problem` (intensification), `failed-solutions` (concentration), `root-cause` (redefinition), `product` (identification), `unique-mechanism` (mechanization), `proof` (intensification), `transformation` (intensification), `objections` (redefinition), `offer` (intensification), `call-to-action` (gradualization) | `solution-aware`→`product-aware` | stage-2, stage-3, stage-4 | testimonial-montage, single-presenter, micro-drama | seed — crosswalk row Story / testimonial (life · tried · found · now) |
| Mechanism-led (the new way) (`mechanism-led`) | draft | seed | `hook` (intensification), `problem` (intensification), `root-cause` (redefinition), `unique-mechanism` (mechanization), `proof` (intensification), `solution` (intensification), `product` (redefinition), `objections` (redefinition), `offer` (intensification), `call-to-action` (gradualization) | `problem-aware`→`product-aware` | stage-3, stage-4 | demonstration, single-presenter, expert-consult | seed — crosswalk row Mechanism-led (the new way) |
| Us-vs-them / comparison (`us-vs-them`) | draft | seed | `hook` (intensification), `problem` (intensification), `failed-solutions` (concentration), `root-cause` (redefinition), `unique-mechanism` (mechanization), `proof` (intensification), `product` (redefinition), `objections` (redefinition), `offer` (intensification), `call-to-action` (gradualization) | `solution-aware`→`product-aware` | stage-2, stage-3, stage-4 | demonstration, single-presenter, expert-consult, meme | seed — crosswalk row Us-vs-them / comparison |
| Direct offer (most-aware) (`direct-offer`) | draft | seed | `hook` (intensification), `offer` (redefinition), `proof` (intensification), `urgency` (intensification), `call-to-action` (gradualization) | `most-aware`→`most-aware` | stage-1, stage-2 | single-presenter, meme | seed — crosswalk row Direct offer (most-aware) |
| Identification-only (unaware) (`identification-only`) | draft | seed | `hook` (camouflage), `identification` (identification), `problem` (gradualization), `transformation` (intensification), `solution` (intensification), `product` (identification), `call-to-action` (gradualization) | `unaware`→`problem-aware` | stage-5 | micro-drama, single-presenter, testimonial-montage | seed — crosswalk row Identification-only (unaware) |

## PAS (problem · agitate · solve) (`pas`)

Name the need, show what it costs to leave it alone, then the thing that ends it.

| # | Section | Technique | Scene shape |
|---|---|---|---|
| 1 | `hook` | intensification | The problem as one concrete picture in the viewer's world, no product, no claim — the beat exists to make the next one unmissable. |
| 2 | `problem` | intensification | The need named in the viewer's own words, specific enough that they see their own situation before anything is offered. |
| 3 | `agitation` | intensification | The cost of leaving it alone — the black side pictured across time: what it takes, what it keeps taking, what it becomes if nothing changes. |
| 4 | `solution` | intensification | The turn: what changes and what it feels like when the want is met — the same desire, one fresh picture, brighter than the beat before. |
| 5 | `unique-mechanism` | mechanization | Why this works when the rest did not — named at the depth the market's stage demands: named only, described, or featured. |
| 6 | `proof` | intensification | Evidence at the beat where doubt peaks: a result, a number with its denominator, a real person, a before-and-after — placed here, not front-loaded. |
| 7 | `product` | redefinition | What it actually is — the physical facts that make the mechanism true, relabelled inside the beat, never a list. |
| 8 | `offer` | intensification | The terms set against a bigger anchor, and the guarantee restating every promise made so far. |
| 9 | `objections` | redefinition | The one flinch this viewer has at this point, named and resolved before the ask — the room's own objection words, answered. |
| 10 | `call-to-action` | gradualization | The single step left once every prior beat has been agreed to. |

- **Ref:** [L830-872] [L2761] [L4377] [L4485-4518]

## AIDA (attention · interest · desire · action) (`aida`)

Stop the scroll, make the need felt, make the result wanted, ask for the step.

| # | Section | Technique | Scene shape |
|---|---|---|---|
| 1 | `hook` | intensification | Attention: one arresting image or line that stops the thumb — built from the viewer's world, never from the category's stock line. |
| 2 | `identification` | identification | Interest: the viewer named to themselves — the behaviour, the moment, the workaround only they would recognise. |
| 3 | `problem` | intensification | The need made explicit now that the viewer is inside the piece — in their words, one level deeper than the hook. |
| 4 | `transformation` | intensification | Desire: the after, pictured across time — the fulfilled want and the role the viewer gets to play in it. |
| 5 | `proof` | intensification | The claim confirmed exactly where wanting turns to doubting: a result, a witness, a demonstration. |
| 6 | `product` | identification | What it is, carried as a marker of the person the viewer wants to be seen as — physical facts only where they sharpen the picture. |
| 7 | `offer` | intensification | The terms against an anchor, the guarantee as the final restatement of every promise. |
| 8 | `urgency` | intensification | Action's reason to be now, real and receipted — a date, a run, a season — never invented scarcity. |
| 9 | `call-to-action` | gradualization | One step, one line, the conclusion of the chain. |

- **Ref:** [L603-645] [L830-872] [L2448-2645] [L4485-4518]

## BAB (before · after · bridge) (`bab`)

The life before, the life after, and the mechanism that is the only way across.

| # | Section | Technique | Scene shape |
|---|---|---|---|
| 1 | `hook` | intensification | The before, as one picture the viewer already lives in — no product yet. |
| 2 | `problem` | intensification | The before in detail: what it costs day to day, in the viewer's own words, so the after has something to be measured against. |
| 3 | `transformation` | intensification | The after, pictured across time — the same life with the want met, escalating in vividness beat to beat. |
| 4 | `unique-mechanism` | mechanization | The bridge: how you get from before to after — the mechanism demonstrated, cause to effect, at the depth the market's stage needs. |
| 5 | `proof` | intensification | The bridge shown to hold: a real crossing — result, witness or demonstration — at the beat doubt would otherwise creep in. |
| 6 | `product` | redefinition | What the bridge is made of — the physical facts, relabelled inside the beat as the reason the after is real. |
| 7 | `offer` | intensification | Terms against an anchor; the guarantee restates the after as a promise. |
| 8 | `call-to-action` | gradualization | The one step that starts the crossing. |

- **Ref:** [L830-872] [L2448-2645] [L4896-5132]

## Story / testimonial (life · tried · found · now) (`story-testimonial`)

One person's own account: what life was, what failed, what they found, what it is now.

| # | Section | Technique | Scene shape |
|---|---|---|---|
| 1 | `hook` | camouflage | A person talking, in the platform's own register — the first line of a story, not an ad's first line. |
| 2 | `identification` | identification | 'I was you': the teller names the viewer through their own past self — the same behaviours, the same words. |
| 3 | `problem` | intensification | The problem as it was lived — specific moments, not a diagnosis. |
| 4 | `failed-solutions` | concentration | What was tried and how each failed at a recognisable moment — every weakness answered later by the matching strength, never a bare complaint. |
| 5 | `root-cause` | redefinition | What the teller finally understood — the real reason those failed, relabelling the problem in the same beat. |
| 6 | `product` | identification | The find — how it entered the story, carried as part of who the teller became, not as a pitch. |
| 7 | `unique-mechanism` | mechanization | Why it worked when the rest did not, in the teller's own explanation — named or described, never lectured. |
| 8 | `proof` | intensification | What happened: the result with its time frame, the visible change, the number with its denominator. |
| 9 | `transformation` | intensification | 'Now': life with the want met, pictured across time — the role the teller plays now and the viewer could. |
| 10 | `objections` | redefinition | 'What I'd tell you': the doubt the teller had, answered from experience. |
| 11 | `offer` | intensification | The terms as the teller would say them, with the guarantee as the promise they would make a friend. |
| 12 | `call-to-action` | gradualization | The one thing the teller says to do. |

- **Ref:** [L462-473] [L5136-5432] [L5694-5808] [L3253-3872]

## Mechanism-led (the new way) (`mechanism-led`)

Lead on HOW the result happens, not on the result — the answer to a market that has stopped believing claims.

| # | Section | Technique | Scene shape |
|---|---|---|---|
| 1 | `hook` | intensification | The new way named in the opening beat — one concrete picture of the mechanism, never the old claim restated. |
| 2 | `problem` | intensification | The problem the viewer already carries, named in their words, one beat — enough to make the cause worth hearing. |
| 3 | `root-cause` | redefinition | The feared frame appears and is relabelled inside the same beat — the problem turns out to be a different problem; the emotion is relief. |
| 4 | `unique-mechanism` | mechanization | The mechanism featured as the lead claim — a clear demonstration of it working, cause to effect, unexplained to understood. |
| 5 | `proof` | intensification | The mechanism shown to hold in a real case — result, witness or demonstration — placed exactly where the viewer asks 'does it, though?' |
| 6 | `solution` | intensification | What the mechanism produces, stretched across time — the same desire at escalating vividness. |
| 7 | `product` | redefinition | The physical facts that make the mechanism true, relabelled inside the beat rather than listed. |
| 8 | `objections` | redefinition | The one reason not to believe the new way, in the room's own words, answered before the terms. |
| 9 | `offer` | intensification | Price set against a bigger anchor, the guarantee restating every promise already made. |
| 10 | `call-to-action` | gradualization | The one step left once the mechanism has been accepted. |

- **Ref:** [L1405-1470] [L4544-4894] [L4896-5132]

## Us-vs-them / comparison (`us-vs-them`)

The old way and this one, side by side, with the mechanism as the reason the comparison goes this way.

| # | Section | Technique | Scene shape |
|---|---|---|---|
| 1 | `hook` | intensification | The contrast in one picture: the old way and the new way side by side, no verdict yet. |
| 2 | `problem` | intensification | What the viewer lives with under the old way, in their own words. |
| 3 | `failed-solutions` | concentration | The old way failing at a relatable moment, each weakness sourced from real speech — and in the same beat, the new way at that exact moment. |
| 4 | `root-cause` | redefinition | Why the old way fails — the real reason, relabelled so the comparison is about cause, not preference. |
| 5 | `unique-mechanism` | mechanization | The new way's mechanism demonstrated — the how that the old way lacks. |
| 6 | `proof` | intensification | Side by side, receipted: the same task, opposite outcome, shown or measured. |
| 7 | `product` | redefinition | What the new way is made of — the facts that explain the difference, inside the beat. |
| 8 | `objections` | redefinition | 'But the old way is cheaper / easier / what I know' — the switch cost named and reframed against the real anchor. |
| 9 | `offer` | intensification | Terms against the anchor the comparison already set; the guarantee closes the gap. |
| 10 | `call-to-action` | gradualization | The one step that switches. |

- **Ref:** [L5136-5432] [L2723] [L4896-5132]

## Direct offer (most-aware) (`direct-offer`)

The product, the terms, the reason to act now, and stop. Nothing is explained and nothing is re-sold.

| # | Section | Technique | Scene shape |
|---|---|---|---|
| 1 | `hook` | intensification | The product and the deal in the first beat — the most-aware viewer wants nothing explained. |
| 2 | `offer` | redefinition | The terms, set against a bigger anchor — what it would cost otherwise, what is included, the guarantee in one line. |
| 3 | `proof` | intensification | One line of trust at the moment of the decision — a count with its denominator, a rating, a name. |
| 4 | `urgency` | intensification | Why now, real and receipted — the run, the date, the season — never invented scarcity. |
| 5 | `call-to-action` | gradualization | One step, one line. |

- **Ref:** [L667-695] [L3013-3065]

## Identification-only (unaware) (`identification-only`)

A portrait before anything is named — the viewer described to themselves until they are recognised, and only then a need.

| # | Section | Technique | Scene shape |
|---|---|---|---|
| 1 | `hook` | camouflage | A picture of the viewer's own moment, shot like the platform's organic content — no problem named, no claim, no product. |
| 2 | `identification` | identification | The viewer described to themselves — the behaviour, the workaround, the private moment they thought no one noticed — in the room's own words. |
| 3 | `problem` | gradualization | Only now the need is named, as the next accepted step from the recognition — never earlier, at this level a named problem too soon is the must-not. |
| 4 | `transformation` | intensification | The after pictured for this person specifically — the want met, the role they get to play. |
| 5 | `solution` | intensification | What to do instead, in plain terms, one fresh picture. |
| 6 | `product` | identification | What it is, carried as a marker of the person just described — no price, no terms at this level. |
| 7 | `call-to-action` | gradualization | A soft single step — the next thing to watch, read or try, not yet the buy. |

- **Ref:** [L873-972] [L1522-1649] [L3253-3872]
