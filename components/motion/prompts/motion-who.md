You are matching people for one shot of a short vertical video ad. A real reference clip is attached: footage of the
same action our shot needs. Its people are not our people; each of them stands in for one of ours. Your only job here
is to say who is who, by looking.

OUR SHOT: what happens in our ad at this point, and who is in it.
{context}

THE REFERENCE CLIP (attached): {reference}
Every person the tracker followed carries a coloured dot on their nose, joined by a short line to their tag in the
same colour, and a box of that colour round their body. The tag belongs to the person whose NOSE the dot is on, even
where two boxes overlap. The tag's number is the shot (the clip restarts its count at every cut); its letter is that
person within the shot. The tags, with where each person's head is when first seen:
{tags}

For each tag, look at the person inside that box in that shot and decide which of OUR people that reference person
plays: the one doing in the reference what our person does in our shot. Work it out from the action, shot by shot:
- The person who does the main action (walks up, leans in, inspects, kisses, reaches, squats) plays our person who does
  that action.
- People acted on play our people in the order the action reaches them: the first one approached plays the first of
  ours approached, the second plays the second, and so on. The same reference person keeps the same name in every shot
  they appear in, also when they stand in the background of someone else's shot.
- Two tags on one body in the same shot (a box that hands over to another part-way) both get that person's name.
- A tag on someone who is nobody in our shot (a passer-by, a guest at another table, a face in the crowd) is "extra".
- Never decide from the order of the letters, from clothes, or from looks. Only from who does what, and where they stand.

Then, per shot, list which of OUR people have their reference person visible in that shot at all, tagged or not (a
person in the frame whom the tracker did not box still counts), and say how the camera is held in that shot.

Give back JSON only, in exactly this shape:
{"tags": {"A1": "<a name from OUR SHOT, or extra>", "B1": "..."},
 "why": {"A1": "one short line: what the person in that box is doing, and where in the frame", "B1": "..."},
 "visible": {"1": ["<names of OUR people whose reference person is in shot 1>"], "2": ["..."]},
 "held": {"1": "how the camera is held in shot 1: a selfie at arm's length, someone else's phone, set down still", "2": "..."}}
Every tag listed above appears in "tags" and in "why".
