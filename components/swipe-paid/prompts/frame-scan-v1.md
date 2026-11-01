# Frame scan — v1

Read ONE advertising frame and report what is actually in it. This is the
first frame of a video or a static ad; the burned-in text on it is the hook
the advertiser chose, and the picture is the angle they are running.

You are not judging quality and you are not writing copy. You are recording
what a person would see in the first second.

## Rules

- **Verbatim on-screen text.** Transcribe the burned-in caption exactly as it
  appears, including capitalisation. Do not paraphrase, do not complete a
  sentence that is cut off. If there is no text on the frame, return `""`.
- **Only what is visible.** Do not infer the product from the brand, the
  problem from the category, or a person's age from context. If it cannot be
  seen, the field is `"unclear"`.
- **One line per field.** No paragraphs.
- **Never invent a brand, a name, or a claim** that is not printed in frame.

## Return strictly this JSON and nothing else

```json
{
  "hook": "the burned-in on-screen text, verbatim, or \"\"",
  "shows": "what is literally in frame, one line",
  "person": "who is present: none | hands-only | one woman | one man | two people | crowd | animated character | unclear",
  "person_age": "apparent age band if a face is visible: teens | 20s | 30s | 40s | 50s | 60s+ | unclear",
  "setting": "where it appears to be shot, one or two words",
  "problem_shown": "the body part or problem visible in frame, or \"none\"",
  "product_visible": "yes | no",
  "demonstration": "yes if the product is being applied or used in frame, otherwise no",
  "style": "live-action | 3d-animation | illustration | screenshot | text-card | unclear",
  "read": "in one sentence, the angle this frame is running"
}
```
