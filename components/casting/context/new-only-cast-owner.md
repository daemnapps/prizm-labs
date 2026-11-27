# New only cast

2 Nov 2026. Old cast, old sets and old product shots are out of the video and image chains. Moved to `runs/_removed-2026-11-02/`, nothing deleted. List per brand: `runs/ai-elements/<brand>/new-only.json`.

| Door | What it does now |
|---|---|
| Starting a video | Refuses a brief that names an old person or set |
| Video start pictures | Refuses any old face, set or product shot sent as a reference |
| Every clip | Refuses a clip tied to an old person |
| Face swaps | Refuses an old person by name |
| Board and ad pictures | Refuses old references on every picture |
| Who plays this role | Never answers with an old person |
| Character picks | Refuses an old person's folder |
| Building a new character | Refuses an old face as the starting picture |
| Resting product, end cards, packshots | Goes to the 30 Oct casting sheet first |
| Avatar profile Face links | Struck from every profile and sub-avatar file. No chain ever read them as pictures |
| Cast rosters | Already clean. Brand B is Margo, a creator, Yai, Brand B. Brand A is empty |

**Out:** Brand A 115 people (including the old core: Baddie Barber, Pastor Barber, Nia, Man Clear Neck, and Curtis Bell) and 21 sets. Brand B 38 entries: everyone but Margo, Yai, a creator, Brand B; Becky, Joanna, Luciana and Pam are blocked until each creator gives a written yes.

**Cast now:** Brand A: Dez, Finn, His Boy, Little Brother, Mateo, Nico, Otis, Sami, The Singer, The Woman, Tre, Wes. Brand B: Margo, Yai, a creator, Brand B. A new name passes.

**Product:** every lookup goes to the 30 Oct casting sheet first, one picture per side in each kit (`model/sheet/current/`). FLEX in-use shots use the current back view plus the real hold; store video frames are refused. 34 old store photos left the kits. King Set, Vitals Set, Basics Set, Clear Skin Set and the gift card have no sheet yet, so their store photo is refused and no ad picture can be made of them until one exists. Email pictures are exempt.

**Open:** Curtis Bell stays on file until ad 0299 finishes. Drive copies and old Higgsfield elements remain; the chains refuse them. Old Face links are struck from every Brand A profile and sub-avatar file.

**Proof:** `components/casting/tests/test_new_only.py`, 15 tests.
