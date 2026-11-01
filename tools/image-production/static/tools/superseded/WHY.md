# Retired, kept legible

Nothing here is called by the live chain. It is kept rather than deleted so
the mistake is recognisable if it reappears.

- `compose_ad.py` — the first compositor. It carried **one hardcoded layout**
  (centred wordmark, white square, headline box, corner sticker) and drew it
  over every swipe regardless of that swipe's format. Superseded by
  `render.py`, which draws from a template. See `image-production/README.md`,
  "The format is the swipe's, not the last one's".
