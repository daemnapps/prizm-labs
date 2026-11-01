# {{brand}} — image variables

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
| `{offer_file}` | `offers/offer-bank.md` |

NOTE: drafted — wired when the image lane adopts the convention.
