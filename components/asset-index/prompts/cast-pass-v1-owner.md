You are looking at one clip of footage a brand owns, so production can cast people and pick shots from an index
without opening the clip. Observation only: say what is on screen. Never judge whether it is good, never say what it
should become. Never name a real person from their face. Never guess race, ethnicity or nationality. Skin tone is
only the visible shade of the skin, nothing more.

The clip was already cut into scenes. Here they are, with their seconds and what an earlier pass said each shows:
{scenes}

The brand's own products and what they look like:
{products}

First list every distinct person who appears anywhere in the clip, so the same person keeps one letter across scenes.
Then answer per scene.

Return exactly one JSON object, nothing outside it:

{
 "persons": one entry per distinct person seen in the clip (hands-only people count only if no face is ever shown),
   [{"p": "A" | "B" | ...,
     "gender": "man" | "woman" | "unclear",
     "age": "teen" | "20s" | "30s" | "40s" | "50+" | "unclear",
     "skin_tone": "light" | "medium" | "tan" | "deep" | "unclear",
     "look": a few words to tell this person apart (hair, facial hair, build, glasses), no clothing,
     "main": true for the person the clip is about (the one filming themselves or most on screen), else false}],
 "letterbox": true | false (black or blurred bars above and below or beside the picture),
 "scenes": one entry per scene above, in the same order:
   [{"n": scene number,
     "on_screen": letters of the persons visible in this scene; [] if nobody; ["hands"] if only hands or arms,
     "face_visible": true | false (a face is clearly seen, not turned away, cropped or covered),
     "couple": true | false (a man and a woman together in the scene, interacting),
     "action": one short line, verb first, of what the people do (for example "scrubs face with a silicone brush at the sink"),
     "action_tags": any of {actions}; [] if none fit,
     "product_in_use": a product key from the list above that is clearly being used or held up, else "none",
     "competitor": the brand name of any other grooming or skincare product clearly shown and readable, else null,
     "room": one of {rooms},
     "framing": "extreme-close-up" | "close-up" | "medium" | "wide",
     "angle": "selfie" | "eye-level" | "high" | "low" | "overhead" | "pov" | "mirror",
     "camera": "static" | "handheld" | "pan" | "tilt" | "push-in" | "pull-out" | "tracking" | "whip",
     "emotion": one of {emotions}}]
}

Two rules above everything: when you cannot tell, say "unclear" or leave the list empty; and use only the words and
ids given here.
