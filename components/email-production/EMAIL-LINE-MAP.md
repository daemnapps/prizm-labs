# How an email gets made (the email line map)

Markdown copy of the **Email Line Map** page ((private page)), 18 Oct 2026, both
brands. The page is now a twelve-level walkthrough game with real <brand> and <brand> emails in a "spot the levels"
boss level. the team presses one button, the chain does the work, the team makes the pictures and design better, the team does the final
wording and schedules it, and every fix makes the next run better.

## The chain, twelve stations

| # | Station | Who | What happens |
|---|---|---|---|
| 1 | Calendar plans the sends | machine | real dates, holidays, the avatar's culture moments; main, promo and cultural sends; each marked designed or letter |
| 2 | the team approves and presses **Write it** | the team (taste) | in Outlier → Calendar; her note rides along |
| 3 | Copy is written | machine | thirteen writing steps; checked for wrong facts and invented offers |
| 4 | The moment is researched | creativity | on a holiday or sale send: what she is doing that week, sourced; concept seeds and blow-out key visuals |
| 5 | The concept is chosen | creativity | one job, one belief, one proof, one button; a concept from her culture; never repeated in a batch |
| 6 | The email is laid out | design | clean sections from the brand's look and visual DNA; real people and product shots from the tagged index first; the product as its product file says |
| 7 | Pinterest mood board | creativity | for each picture still to make, a Pinterest search keeps three pins for light, styling, props and mood; they ride into the picture engine as inspiration only, never copied (`design/pins.py`, about $0.06 a search, `PINS_OFF=1` skips it) |
| 8 | Pictures are made | design | only the key visual and gift pictures, from the real product photos plus the pins, judged |
| 9 | Built for Klaviyo | machine | sections as pictures, live text and buttons, tracking on every link |
| 10 | Checked | machine | prices, claims, links, sizes, nothing repeated; anything wrong holds the email |
| 11 | the team makes the pictures and design better | the team (taste) | swap or edit a picture, adjust the design, send it back with a note, give the Go (a Klaviyo draft) |
| 12 | the team does the final wording and schedules it | the team (taste) | last pass on every line, then she schedules it in Klaviyo; nothing sends on its own |

Every change the team or the team makes (the team's wording, the team's pictures and design) becomes a learning (a DO or a NEVER) that every later run reads, for every brand and
every line (`runs/learnings/`, `components/run-kit/run_kit/learnings.py`).

## Where it runs out

- No offer in the offer bank, no sale in the copy: the email is held until a person sets the offer.
- Real people are scarce for <brand> (37 real customer selfies with the tube, 18 pictures of women 55 to 70).
- The picture judge holds some good pictures (mostly for the product's own label); held pictures wait for a person.
- The chain runs on the Mac with the keys and the drive.
- Final polish happens in the Klaviyo draft.

## Where it lives: Outlier (127.0.0.1:8880)

- **the team · Calendar:** pick the brand, open a send in the email drawer, approve, edit or cut it, press **Write it**.
- **the team · Decide → Emails:** open an email, swap a picture, describe one change to it or adjust the design, give the
  **Go** or send it back with a note.
- **the team · final wording:** last pass on the words, then she schedules it in Klaviyo.

Designed emails now wait in Outlier → Decide with Go (makes the Klaviyo draft) and Send back (a note that
becomes a learning, then a redesign); every wording or picture change made there is saved as a learning. Still
open: <brand>'s Black Friday offer must be set.

Walkthrough video: https://www.tella.tv/video/email-marketing-automation-walkthrough-hmyj38tf
