<!-- rendered from components/video-doctrine/frameworks.json by render.py — do not hand-edit -->

# The shot brief

Bound as `{shot_brief}`.

Every shot fills these lines. A blank line means the model picks for you. Say what the camera sees and hears; skip words you could not photograph. Write each prompt as if the model has seen nothing else, and change one thing per retry.

```
Shot: [Size, angle, lens]
Who: [Each person and object, bound to its reference]
Action: [One clear move]
Move: [What the camera does]
Where: [The set, bound to its reference, and the time]
Light: [Source, side, quality]
Color: [Palette line]
Sound: [Ambient, effects, music or none]
Line: [Exact words, or none]
Style: [The same style line as every other shot]
Length: [Seconds]
```

Source: https://developers.openai.com/cookbook/examples/sora/sora2_prompting_guide

These are defaults. The swipe's own read wins over a default, and the video rulings win over this slice.
