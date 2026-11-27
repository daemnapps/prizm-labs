# Providers — the doors (current: 2026-10-26)

> Which model does what: `../../generative-model-house/MODEL-HOUSE.md` (the only rule). How the clip is asked for: `../SEEDANCE-INPUTS.md`.

Every station is a direct door or the Higgsfield CLI; the video model is **Seedance 2.5 only, at 480p**, upscaled on this Mac (the owner, 2026-10-26; `../VIDEO-RULINGS.md` V43/V44).

| Station | Door | Code |
|---|---|---|
| voice | ElevenLabs, direct | `machine/voice.py` |
| cast · still · edit | GPT Image 2.5 (Seedream 5 Pro, then Nano Banana Pro, on a refusal) | `machine/direct_openai.py`, the Higgsfield CLI |
| song | ElevenLabs Music `music_v2_5` (Lyria 3 the alternate) | `machine/song.py`, `machine/direct_google.py` |
| clip (talking and silent) | Seedance 2.5 through Higgsfield, 480p; Kling 4.0 the silent backup | `machine/seedance.py`, `machine/kling.py` |
| — wired, blocked | Seedance 2.5 on BytePlus, direct (US billing) | `machine/direct_byteplus.py` |

`--provider higgsfield-mcp | higgsfield-ui` forces a piece into the Higgsfield house on purpose (the editor gets a submit sheet). The switch, the model per station and each model's rates and ceilings live in `../machine/providers.json`, read by `../machine/provider_platform.py` and `../machine/preflight.py`.

`research/` holds the dossiers behind the door choices. The fal house, the old per-house pages (`fal.md`, `higgsfield.md`, `MODEL-HOUSE.md`, the editor sheet) and the older version of this page are in `../archive/`.
