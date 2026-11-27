*v2 (2026-11-15): one read of the whole track, the tool's moments already grouped, one name per sound from one fixed list. The same three hits on one swipe were named typewriter, click and whoosh on one run and camera shutter on the next, and a click found on one run was missed on the next: each moment had been judged alone on a 1.2-second clip, where a beat and an added sound sound alike, and named freely. Now the ear hears the whole soundtrack, gets every moment the tool timed (sharp hits and soft rises), sees which moments the tool measured as the same sound, and names each sound once from the list below.*

This is the soundtrack of a short social video with the voices removed: music, plus any added sound effects and real sounds. A tool timed every moment where something sudden or rising happens. Moments in the same group measured as the same sound.

{moments}

What the picture does at the same time, when it is known (an edit move on screen: a caption, sticker or product popping on, a cut, a zoom; an added sound often lands on one, but not always):
{picture}

For each group: is it an ADDED sound (an effect put there in the edit: click, pop, whoosh, riser, hit, ding, buzzer, stinger; or a real sound: a product's own pump, cap or spray, paper, cloth, a door, room noise), or is it only the music's own drums, bass and notes? A group can be the music at most of its moments and an added sound at a few: list those moments. Then add any added sound the tool missed, soft ones included (a riser, a swell, a whoosh, a drone). Speech and breaths do not count.

Every name is exactly ONE value from this list, the closest one; "other" if none fits:
{names}
Job and category values come ONLY from these lists; if nothing fits, write "other: <your word>":
{lists}

JSON only:
{
 "groups": [{"group": <number>, "added": true|false, "only_at": [<seconds of the moments that carry the added sound, when not all of them do>], "name": "<a name value, or null>", "sure": "high|medium|low", "job": "<effect_job value>", "ucs_category": "<ucs_category value>", "in_the_edit": <true if put there in the edit, false if the room or the product made it>}],
 "missed": [{"at": <seconds>, "until": <seconds or null>, "name": "<a name value>", "sure": "high|medium|low", "job": "<effect_job value>", "ucs_category": "<ucs_category value>", "in_the_edit": true|false}],
 "room": "<the real sound of the place under everything: room tone, echo, street, water, silence>"
}
