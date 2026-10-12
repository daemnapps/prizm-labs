# Brand check — brand-b vs brand-a

Shapes, not contents. Different offers is the point; a different SHAPE is a bug waiting to be noticed.

| | brand-b | brand-a | |
|---|---|---|---|
| **email/email-types.json** | `yes` | `yes` | the kinds of send this brand knows |
| **email/audience-matrix.json** | `yes` | `yes` | who it can target |
| **products/offer-bank.md** | `yes` | `yes` | what it may sell |
| **calendar/moments.json** | `yes` | `yes` | its claim on the year |
| **email/affiliates.json** | `yes` | `yes` | partners it features |
| **email/classified.json** | `yes` | `yes` | its own sends, typed — the formats |
| **email/format-sources.json** | `yes` | `yes` | where it borrows formats when it has none |
| **email/ledger.json** ⚠ | `yes` | `MISSING` | every send, with its campaign |
| **email/performance.json** ⚠ | `yes` | `MISSING` | what each send earned |
| **email/learnings.md** ⚠ | `yes` | `MISSING` | the evidence, as findings |
| **types · count** ⚠ | `47` | `46` |  |
| **types · brand-a is MISSING** | `pharmacist-dad` | | a type another brand has and this one does not |
| **types · role** ⚠ | `{"asks": 10, "closes": 2, "earns": 30, "recovers": 4, "sets-up": 1}` | `{"asks": 10, "closes": 2, "earns": 29, "recovers": 4, "sets-up": 1}` |  |
| **types · well** ⚠ | `{"affiliate": 2, "ask": 13, "belong": 6, "brand": 8, "help": 10, "real": 8}` | `{"affiliate": 2, "ask": 13, "belong": 6, "brand": 7, "help": 10, "real": 8}` |  |
| **types · shared types that DISAGREE** | `0` | `0` | none — a shared type means the same thing in both |
| **offer bank · shape** | `flat` | `flat` | how the file is laid out — BOTH must be readable by the same rule |
| **offer bank · usable offers** ⚠ | `11` | `8` |  |
| **products · shape** ⚠ | `flat` | `folder` | flat = products/<slug>.md, folder = products/<slug>/product.md — the reader takes both; `none` means every send reads as productless |
| **products · count** ⚠ | `15` | `3` |  |
| **affiliates · the key holding the roster** | `affiliates` | `affiliates` | the reader knows `affiliates`; any other name is invisible to it |
| **affiliates · partners** ⚠ | `4` | `0` |  |
| **segments** | `8` | `8` |  |
| **segments · with a size** ⚠ | `8 of 8 counted` | `0 of 8 counted` | an uncounted segment cannot be split into variants |
| **avatars** ⚠ | `4 (3 with language)` | `1 (1 with language)` |  |
| **moments** ⚠ | `44 · proposed:9 proven:28 territory:7` | `8 · proposed:8` | proven = the brand's own sends prove it |
| **formats to write from** ⚠ | `308 sends covering 33 types` | `90 sends covering 20 types` |  |
| **formats · brand-b types with NO example** | `15 of 47` | | affiliate-feature, affiliate-roundup, availability, channel-invite, content-request, guarantee, opinion, peer-advice, product-finder, product-spotlight… |
| **formats · brand-a types with NO example** | `26 of 46` | | affiliate-feature, affiliate-roundup, availability, bundle, channel-invite, content-request, early-access, gift-guide, guarantee, milestone… |

**14 row(s) differ.** A difference is not automatically wrong — read each one.

