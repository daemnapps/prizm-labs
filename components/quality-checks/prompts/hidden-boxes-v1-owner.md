# Where things sit on the frame (v1)

Look at this 9:16 ad frame. Find every face, the product, and every block of
on-screen text. Give each a box in coordinates from 0 to 1000, where (0,0) is
the top-left corner and (1000,1000) is the bottom-right of the whole frame.

Only list what is actually there. Don't guess at things you can't see.

Return JSON only:
{"items": [{"what": "face|product|text", "label": "<a few words, e.g. 'man's face', 'the product', 'headline'>",
  "box": [x_min, y_min, x_max, y_max]}]}
