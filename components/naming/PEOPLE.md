# Names for who an ad is for (owner, 2026-11-25)

What each word means: `components/marketing-doctrine/slices/words.md` (the layers in full: `slices/people.md`). This file only says how it is named. Spelling follows the locked rule: lowercase, `-` joins words inside a value, `_` joins values.

| Layer | The name is | Pattern | Example |
|---|---|---|---|
| **Avatar** (a whole person: desire, experiences, emotions, behaviors, culture) | the problem, in the customer's own word; only the label | 1 to 3 words | `razor-bumps` |
| **Sub-avatar** | the one thing that sets them apart, opening with its kind | `<kind>-<thing>`, up to 5 words | `where-back-of-head` |
| **Demographic** | gender, age band, ethnicity; a language only when it is not English | `<gender>-<age>-<ethnicity>[-<language>]` | `male-35-44-black` |

All three together: `razor-bumps_where-back-of-head_male-35-44-black`. On a page: **Razor Bumps · Back of head · Black man 35–44**.

## The kinds of sub-avatar (a closed list)

| Kind | Answers | Example |
|---|---|---|
| `tried` | what they already tried | `tried-every-wash` |
| `when` | the situation the problem shows up in (a fresh cut). Why they want it fixed (dating) is a desire, never a `when` | `when-fresh-cut` |
| `where` | where on the body: a part or a group from `anatomy.json` | `where-back-of-head` |
| `since` | what it came from, or how long | `since-menopause` |
| `feels` | the feeling that decides it | `feels-scared-to-scrub` |
| `has` | skin or hair that drives it | `has-oily-skin` |

A sub-avatar that fits two kinds is two sub-avatars. One that fits none is not a sub-avatar.

## Rules

1. Never a character, nickname, age, race or gender in an avatar or sub-avatar name (no king, guy, kid, mom, brother). Those are the demographic.
2. Someone buying for another person is an avatar named `buying-for-<who>`.
3. Ages: 18-24, 25-34, 35-44, 45-54, 55-64, 65-plus. Ethnicity: black, white, latino, east-asian, south-asian, middle-eastern, mixed. Gender: male, female.
4. A name is unique inside its brand (avatar) and its avatar (sub-avatar). The same word may be used by two brands.
5. Nothing live is renamed. Old names stay as aliases (`people-aliases.json`) and keep working in ads, ad sets and reports; new work uses the new name.
6. Only the owner signs a new avatar or sub-avatar name. `people.py check` refuses one that breaks these rules.

## The profile (owner, 2026-11-27: "the profile is the combination of avatar, sub-avatar and some other elements")

A profile is ONE unit with ONE name: avatar + sub-avatar + demographic, written `<avatar>[_<sub-avatar>][_<demographic>]`, read from either the old or the new spelling (`people.py profile`). An ad is made for a profile, and inside it for one element.

| Part | Is | Example |
|---|---|---|
| **Profile** | `<avatar>[_<sub>][_<demographic>]`; no sub-avatar means the whole avatar; the demographic is the last part, the one that reads `<gender>-<age>-<ethnicity>` | `razor-bumps_where-back-of-head_male-35-44-black` |
| **Label** (what a page shows) | Avatar · sub-avatar · demographic in plain words | Razor bumps · Back of head · Black man 35–44 |
| **Element** | One point inside the profile: a desire, feeling, belief, role, experience, behavior or doubt, each on its real customer lines | `razor-bumps_tried-everything/desire-i-want-my-neck-to-still-look-clean-3f2a` |

- An element's address is `<profile>/<kind>-<its first six words>-<4 hex of the whole text>`. The same words refilled keep the same address; reworded is a new element. It is what an ad is made for and what results are read against (the ad name carries it).
- A profile with no demographic yet is the person; the demographic is chosen per piece and joined (the face).
- **Signed by the owner, 2026-11-27 ("Yes"):** `el-rey-cansado`, `el-jefe`, `mijo-mom` and `get-his-face-right-mom` are demographics, not sub-avatars. Each is read as its avatar plus that demographic (people-aliases.json, `demographics`): razor-bumps + male-25-34-latino, razor-bumps + male-35-44-latino-spanish, buying-for-him + female-45-54-latino, buying-for-him + female-45-54-black. Their brand folders keep the old names (and their filled profiles keep working) until the brand-folder rename, which is its own step.
- A profile is stored once, in the brand folder, in its sub-avatar's own folder. Built, never written by hand: skill `avatar-profile`.
- Library: `people.profile`, `people.parse`, `people.point_id`, `people.element`; `people.py profiles <brand>` lists every profile with its old name.

### Open before the brand folders are renamed (owner's yes)

1. Brand A `tried-every-wash-kid`, `clogged-pores-kid`, `marks-that-stay-kid` sit under the avatar folder `glow-up` (now `whole-look`), but the aliases file names them under `acne` and `dark-spots`. One of the two is stale.
2. `when-dating` (date-night-brother) breaks rule above: why someone wants it fixed (dating) is a desire, never a `when`.
3. `face-back` is a whole avatar with no sub-avatar (`wrinkles`); fine, but it holds 1,441 points as one profile.

### Tools take a profile (owner, 2026-11-27: "moving forward, tools that used to call on avatar or sub-avatars need to call on profiles")

- A tool names the person it works on by **profile**: `--profile <avatar>[_<sub>][_<demographic>]`. The one door is `people.folders(brand, name)`; `who.profile_args` wraps it. It reads old or new spelling and returns the folders the brand keeps, so nothing is renamed.
- Done: `who.py` and `ask.py new` (`--profile` is their own flag), the Galaxy filter's start step, and these 13 tools, which take `--profile` through one line before their argument parsing (`naming/profile_arg.py`, which turns it into the tool's own `--avatar`, `--sub`, `--demographic`; an explicit flag still wins; needs `--brand` in the same command): copywriter (copy_set, brief_words, copy_writer), creative-strategist keywords, research-gatherer engine, email-production email_line, image-teardown (chain, tools/run), distinct-six, page-writing write, video-teardown compose, video-writing (scratch, presenter_body).
- Not moved: swipe-organic `affinity.py` (its `--sub` is a culture-dig key, not a brand sub-avatar), and the tools with their own folder lookup (copywriter research and google_copy, swipe-organic recomment, research-gatherer comments, ad-variations format_swap, image-teardown pick_run, video-teardown research, marketing-chain-checks viewer_chain). They keep their old flags.
- A new tool takes `--profile` and no other way to name a person.
- **The standard and the door** (2026-11-27): what every profile must hold and how to check it is `components/profiles/` (`SPEC.md`, `profiles.py audit|check|doors`); a tool reads a person through `profiles.load(brand, name)`. `profiles.py doors` lists every tool still taking a person around the door.


