# Fixtures

`render-check/` is a hand-written stage 5 and stage 8 output, not a real run.
It exists so `render.py` can be checked without spending a chain:

```
python3 render.py fixtures/render-check
```

It deliberately contains three things that must not silently pass: a button
with an `[UNFILLED: destination]`, an image block with no picture, and a block
type (`carousel`) that is not in the vocabulary. All three should be visible on
the page. If any of them renders as nothing, `render.py` has regressed.
