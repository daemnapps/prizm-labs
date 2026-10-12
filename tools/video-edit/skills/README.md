# Video editing skills

Targeted skills an editor pulls into Higgsfield (or Claude) to change ONE thing
on a finished clip, fast. Each one names the model it runs on, checks for a
newer version first, and prices the run before spending credits. The video
edit line itself (cuts, captions, timeline) is this folder's `machine/`.

| Skill | What it does | Model | Tested |
|---|---|---|---|
| [reframe-9x16](reframe-9x16.md) | any shape clip in, 9:16 out, footage kept whole | Higgsfield Reframe | not yet |
| [logo-swap](logo-swap.md) | the brand's real logo on every frame | Genjutsu replace object | not yet |
| [avatar-swap](avatar-swap.md) | same clip, a different person from the brand's cast | Genjutsu replace object (or motion control to recast into a new scene) | not yet |
| [element-swap](element-swap.md) | one product, prop or garment changed on every frame | Genjutsu replace object | not yet |

Image versions: `tools/image-edit/skills/`.

## Put them in Higgsfield (paste once)

> Pull these skills from our GitHub and save each one as one of my skills, named as the file:
> https://github.com/ecommops-team/workspace/blob/main/tools/video-edit/skills/reframe-9x16.md
> https://github.com/ecommops-team/workspace/blob/main/tools/video-edit/skills/logo-swap.md
> https://github.com/ecommops-team/workspace/blob/main/tools/video-edit/skills/avatar-swap.md
> https://github.com/ecommops-team/workspace/blob/main/tools/video-edit/skills/element-swap.md
>
> Follow each one exactly whenever I use its trigger words. Always use the model the skill names, after its model check, and tell me the credit cost before running. Change one thing per run, never crop, never add bars. When a skill file on GitHub changes, pull it again.
