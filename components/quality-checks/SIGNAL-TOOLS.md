# Ad Signal Tools — what we use (simplified 2 Oct 2026)

Page: `signal-tools.html`. The full research list of 39 tools is in the page's earlier versions (v1–v6).

## What we use (phone-first, open)
1. **Hidden by the app?** No model needed; it's a rule in our tool. Each frame is checked against the TikTok, Reels and Shorts button and caption zones.
2. **Where do eyes go?** MVFormer, trained on phone videos (UNISAL until MVFormer's code is out). Input is the video; output is a moving heat map.
3. **Will they keep watching?** LMM-EVQA, trained on Snapchat phone videos. Output is how many people will keep watching past the first seconds.
4. **What does the face show?** HSEmotion. Output is the emotion on the face, moment by moment, checked against the brief.

**Cut:** page on a phone (the owner, 2 Oct), paid services, real-people panels, VideoScore2 (production's motion QC already checks clips), the brain model, memorability, and anything not made for phones.

## How it runs in the cloud (option A, proposed)
- **One rented cloud computer with a graphics chip.** It holds our chains, the phone checks, Blender, editing and rendering, and the files.
- **Outside services.** Higgsfield, fal and Gemini are called from that computer. Finished ads land in Google Drive.
- **Access.** the owner and the video editors use it from any laptop. Nothing runs on the owner's Mac.
- **Cost.** About $__/hour while on and $0 when switched off. One ad from start to finish is roughly 15 minutes and about $__. These are ballpark example figures.
- **Who builds it.** It goes through the developer.

## What the avatar viewers already check (the viewer check, live)
Stop in 2s against the real feed · the second they leave, plus a retention curve · when it felt like an ad and why · tap or tell a friend · what they'd remember. They read a description and don't see pixels, so they can't say where the eyes go, read the face, or see what's under the app's buttons. The models cover those three. "Will they keep watching" overlaps with the viewers, but reads the real video.

## Test it
The page has a working safe-zone tester: drop in a 9:16 picture or video and pick Reels, TikTok or Shorts. Reels uses Meta's numbers; TikTok and Shorts are approximate. The other three checks are locked until their models are installed.
