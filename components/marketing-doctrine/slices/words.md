<!-- rendered from components/marketing-doctrine/frameworks.json by render.py — do not hand-edit -->

# What each word means

Bound as `{words}`. Source: the doctrine component; refs are line pointers into the book, for verification only.

The one home of what these words mean. Every other file points here and never restates one. A word's list (which avatars, which angles) lives where `kept in` says.

## Who it is for

| Word | What it is | The test | Kept in |
|---|---|---|---|
| **Avatar** | who it is for: a whole person led by one desire; the problem is the label | Would a person with this problem, and none of the other problems, still be who this speaks to? | brands/<brand>/core-avatars/ (full: `components/marketing-doctrine/slices/people.md`) |
| **Sub-avatar** | that person plus ONE thing: what they tried, the situation, the body part, how long, the feeling, or their skin | Swap what they have been through. If the ad breaks, it is a sub-avatar. | brands/<brand>/core-avatars/<avatar>/sub-avatars/ (full: `components/marketing-doctrine/slices/people.md`) |
| **Demographic** | the face, the language and the place: age, gender, race | Swap race, age or language. If the ad still works, it is a demographic. Hair or skin that causes the problem belongs to the avatar or sub-avatar, not to race. | components/naming/people.py (full: `components/marketing-doctrine/slices/people.md`) |
| **Body part** | where on the body; the `where` kind of sub-avatar | Point to it. The product has to be allowed there. | components/naming/anatomy.json and brands/<brand>/products/body-parts.json |

## Why they would care

| Word | What it is | The test | Kept in |
|---|---|---|---|
| **Desire** | what they want underneath, one per piece | Same person, same problem: why do they want it fixed? (for a date, for work, to stop being stared at). Change it and the problem is still there, but the ad is about something else. | frameworks.json desire (full: `components/marketing-doctrine/slices/desire.md`) |
| **Awareness** | how much they already know, so where the ad may start | Name the first line they would not understand. | frameworks.json awareness (full: `components/marketing-doctrine/slices/awareness.md`) |
| **Market stage** | how many times they have heard this promise | Would they roll their eyes at it? | frameworks.json sophistication (full: `components/marketing-doctrine/slices/sophistication.md`) |
| **Doubt** | the one thing stopping them, closed by the piece | Close it and nothing else stands in the way. | frameworks.json belief (full: `components/marketing-doctrine/slices/belief.md`) |
| **Angle** | the argument: one sentence a customer could agree or disagree with. Also called the claim. It belongs to the brand and runs on any avatar | Say it as one sentence. Could a customer agree or disagree with it? A single word (dating, confidence) is not an angle yet. | brands/<brand>/strategy/angles.json (only the owner signs one) (full: `components/marketing-doctrine/frameworks.json claim`) |

## When

| Word | What it is | The test | Kept in |
|---|---|---|---|
| **Moment** | when it runs or when it hits: a date on the calendar, or the hour of their life it comes up | It has a when, and no argument. | brands/<brand>/strategy/moments.json |

## What the ad says

| Word | What it is | The test | Kept in |
|---|---|---|---|
| **Insight** | a true thing about this person that nobody has said to them | They say: how did you know that. | the strategist run's idea.json |
| **Idea** | the one way of seeing that insight that makes them look at themselves differently | One sentence a friend would repeat. No layout in it. | the strategist run's idea.json |
| **Hook** | the first line or first seconds, for this idea | Cover the rest. Do they stop? | the piece's own hooks or headlines stage |
| **Offer** | the price and the deal | It has a number or a guarantee in it. | brands/<brand>/products/offer-bank.md |

## How it is built

| Word | What it is | The test | Kept in |
|---|---|---|---|
| **Script format** | how the argument runs: what is said, in what order | Read it aloud with no picture. The shape is still there. | components/naming/FORMATS.md lists every format list |
| **Production format** | how it gets made: talking head, song, static, carousel | Say who or what makes it. | components/naming/FORMATS.md lists every format list |
| **Picture source** | where the picture comes from: a real customer photo, creator footage, our own footage, AI-made, 3D, or screen-native. None is the default; AI-made goes through the image process | Which one is this person likeliest to stop for? Pick that, not the one on hand. | the piece's own swaps record; AI-made through components/image-production |
| **New creative** | an ad that is 3 or more of the 7 moves away from every other one: who, awareness, angle, format, face, setting, look. Meta groups anything closer as the same ad | Put the two side by side with the words covered. If they look alike, it is one creative. | components/creative-diversity/dimensions.json |
| **Version** | the same picture with one line changed. Worth testing inside one ad; it never counts as a new creative | Only the words moved. | components/creative-diversity/dimensions.json iteration |

**Two of a kind?** The same person with a different argument is a new angle. A different problem is a new avatar. The same argument on a narrower person is a sub-avatar. The same argument in a different container is a format.
