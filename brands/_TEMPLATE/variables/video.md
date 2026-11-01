# {{brand}} — video variables

**One map per brand, per surface.** A machine reads ONLY its own surface's
map — copy never loads email's variables, video never loads copy's. Nothing
brand-specific lives in any machine; the workflow reads this file at run time
for whatever brand it is pointed at.

**A run declares an avatar.** Everything avatar-shaped resolves through it,
and there is no default: a run that does not declare one is writing to nobody.

| Variable | Resolves to |
|---|---|
| `{avatar}` | `core-avatars/<avatar>/profile.md` |
| `{language_bank}` | `core-avatars/<avatar>/language/rules.md` |
| `{product_file}` | `products/` |
| `{objection_bank}` | `core-avatars/objection-bank.md` |
| `{offer_file}` | `offers/offer-bank.md` |
| `{identity_anchors}` | `brand-identity/identity-anchors.md` |

WIRED 2026-08-31: the video machine reads this map at run time — any
variable named here outranks its chain config's conventional path, and
avatar-shaped rows resolve once stage 1b decides who the run speaks to.
