# Image editing skills

Targeted skills an editor pulls into Higgsfield (or Claude) to change ONE thing
on a finished picture, fast. Each one names the model it runs on and checks for
a newer version of that model before every run. The engine that runs the same edits as
commands is this tool, [`tools/image-edit`](../).

| Skill | What it does | Model | Tested |
|---|---|---|---|
| [resize-9x16](resize-9x16.md) | any shape in, 9:16 out, picture untouched inside the 4:5 safe zone | FLUX.2 Pro Outpaint | yes, 29 Sep (4:5 and 2:3) |
| [logo-swap](logo-swap.md) | the brand's real logo where a wrong one sits | GPT Image 2.5 | partly (everything else held) |
| [avatar-swap](avatar-swap.md) | same ad, a different person from the brand's cast | GPT Image 2.5 | not yet |
| [element-swap](element-swap.md) | one product, prop, badge or background changed, or one thing removed | GPT Image 2.5 | yes, 29 Sep |

The video side's edit commands are the [Edit kit](../../video-edit-kit/).

## Put them in Higgsfield (paste once)

> Pull these skills from our GitHub and save each one as one of my skills, named as the file:
> https://github.com/daemnapps/prizm-labs/blob/main/tools/image-edit/skills/resize-9x16.md
> https://github.com/daemnapps/prizm-labs/blob/main/tools/image-edit/skills/logo-swap.md
> https://github.com/daemnapps/prizm-labs/blob/main/tools/image-edit/skills/avatar-swap.md
> https://github.com/daemnapps/prizm-labs/blob/main/tools/image-edit/skills/element-swap.md
>
> Follow each one exactly whenever I use its trigger words. Always use the model the skill names, after its model check. Change one thing per run, never crop, never add bars. When a skill file on GitHub changes, pull it again.
