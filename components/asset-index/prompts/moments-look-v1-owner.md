You are looking at {n} pictures of our own footage. Each picture is ONE moment of a clip: four frames from it,
left to right, spread across the moment. Moment lengths: {seconds}.

Our products, by key:
{products}

For EACH picture, in order, answer one object. Reply with one JSON object only, {"moments": [...]}, one entry per picture:
{"moments": [{"n": the picture's number (1, 2, ...),
  "product_in_use": true | false (one of our products is clearly in view AND being used or held up, in most frames),
  "product": the key of that product from the list above, or "none",
  "text_on_screen": true | false (text laid OVER the video: a caption, subtitle, sticker, watermark, handle, title or
   app screen. Print on things in the scene, such as a bottle label, a box or a towel's logo, is NOT text on screen),
  "blur_or_transition": true | false (a whip, smear, heavy blur, flash, fade or a cut between two different pictures
   anywhere in the four frames),
  "dead": true | false (nothing happens: a person standing or sitting still, a held pose, an empty or static frame),
  "people": "none" | "hands" | "one" | "two+" (who is on screen: "hands" when only hands or arms show),
  "who": a few words on who is on screen (for example "man, 30s, beard, bathroom" or "hands only"),
  "shows": one short line on what happens in the moment,
  "why": one short line when anything above is wrong for an ad shot, else ""}]}
