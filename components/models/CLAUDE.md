# components/models — the model registry, as data

**Curator: the developer (ruled 2026-09-01).** One place answers *which models are
approved, what each costs, and which key each spends*. Consumers read the
manifest directly; there is nothing to run and nothing to call.

This is the **degenerate case the component contract explicitly allows**
(components/CLAUDE.md rules 5–8, filed the same day): definitions with no
engine. The manifest **is** the deliverable. `validate.py` exists so a bad
entry fails loudly — it is a gate on the data, not an engine that produces
anything.

Born to consolidate four fragments that each answered "what models do we use"
differently: the chain-runner's `chain.json` model bindings, the bench menu
(`bench-models.json`), the atlas's hand-drawn model nodes, and the loose
`lora.json` files `train_identity.py` emits. **The registry is born first;
each consumer migrates by its own small card (MDL-2 (consumer migrations)) — never one big-bang
rewire.** Nothing was repointed by MDL-1 (models registry); every fragment still reads what it
always read.

> DUTY-6 FLAG (carried from the build's task-cards.md): this component was
> created directly on the developer's ruled word, skipping the lab station — the
> atlas/chain-runner precedent. A ruled exception, not a precedent-widening.

## New-resident checklist (components/CLAUDE.md, ruled 2026-09-01)

| question | answer |
|---|---|
| **engine + owner** | **validator only — the developer.** `validate.py` is the whole of the code and it produces nothing; there is no engine to own. A component with no engine is deliberate here, not an omission |
| **definitions + curator** | the two manifests — `models.json` (what we may call) and `trained-assets.json` (what we have trained). **Curator: the developer**, holding the approval gate (rule 6). the owner certifies the training SETS behind the trained assets, as ruled with IDT-1 (identity extraction) — that is a different act from blessing the registry entry |
| **the plane it emits** | **none — the manifest is the product.** No run, no `--out`, no `platform/data/…` folder. Reading the registry needs no credential and no permission, which is rule 7 working as intended |
| **what the manifest declares per entry** | **`id` · `modality` · `cost` · `status` · `key_env` (the env var NAME).** Plus, as provenance rather than contract: `label`, `vendor`, `aliases`, `transport`, `cost_reason`, `sources`, `note` |

## Contract (components/CLAUDE.md rule 2)

Three surfaces are dependable and they are the only three.

### 1. `models.json` — one entry per model

A **list**, not a map: a duplicate `id` has to be *possible* before a
validator can refuse it, and refusing it is the point.

| field | means |
|---|---|
| `id` | the registry's canonical name. Unique across the file, **including against every alias** |
| `aliases` | other names the same model already answers to in code that predates the registry (the chain seam's `opus`, …). This is what makes MDL-2 (consumer migrations) a migration rather than an archaeology exercise |
| `modality` | a **list** from `text` · `image` · `video` · `audio`. A list because a model is not one thing — `gemini-3-flash-preview` is bound to video stages *and* a text stage in the same chain |
| `cost` | **either** the literal `"unpriced"` — which *requires* `cost_reason` in words — **or** an object of named numeric rates |
| `status` | `draft` · `approved` · `deprecated` (rule 6). The curator's gate |
| `key_env` | the **NAME** of the env var the model spends, or `null` when it spends none |
| `transport` | `claude-cli` · `api` · `local` (weights run on our own machine: `key_env` null, cost 0 with its reason — B2 (triage design calls), 2026-10-08). Why `key_env` is `null` for the claude family and for local weights, and a real cost fact: the CLI measures no per-run spend |
| `vendor_id` | optional — the name the **vendor** answers to when it differs from `id`. An OpenRouter id carries a slash (`z-ai/glm-5.3-flash`), which the id shape forbids. A consumer sends `vendor_id` to the vendor and never a string of its own; absent means `id` is the vendor's name (MDL-4 (openrouter vendor)) |
| `request` | optional — the **request-level controls** this entry declares, in the vendor's own spelling, carried onto the request body **unchanged**. Exactly two: `reasoning` (`effort` · `max_tokens` · `exclude` · `enabled` · `context` · `mode`; effort and max_tokens are mutually exclusive) and `provider` (`order` · `allow_fallbacks`). **Absent = today's payload, byte for byte** (MDL-5 (reasoning budget)) |
| `default_max_tokens` | optional — the output budget a request that names none inherits **for this model**. A text model spends its budget on output; a reasoning model spends an unbounded prefix of it on thinking, so one global default cannot be right for both. The consumer's `max_tokens_cap` still bounds it and is never raised to fit an entry; a request's own `max_tokens` still wins (MDL-5 (reasoning budget)) |

### 2. `trained-assets.json` — the index for what we have trained

The home the `lora.json` records emitted by
`components/identity-training/train_identity.py` did not have. That
component's own CLAUDE.md says the records *are* the index "until MDL-1 (models registry)
lands" — this is the landing.

**An index references; it never copies.** Each entry points at a `lora.json`
by repo-relative `record` path and stops. Weights stay on fal (workspace rule
3); records stay beside their brand source, exactly where the engine put them.
`validate.py` refuses an entry that inlines a `lora_url` and refuses one whose
`record` does not exist — a second copy of a url is a copy that will drift,
and a dangling reference is the failure an index exists to prevent.

Fields: `id` · `kind` (`character`/`product`) · `brand` · `trigger` ·
`record` · `trained` · `status` · `certified_by`.

### 3. `validate.py` — the only code

```
python3 components/models/validate.py              # both manifests
python3 components/models/validate.py --selftest   # prove the rejections
```

| exit | means |
|---|---|
| `0` | everything checked is valid |
| `2` | a manifest is invalid — **every** finding printed, **each naming its entry** |
| `3` | a manifest is missing or unreadable |

`--selftest` runs inline fixtures through the same functions the real files go
through, including a **CONTROL case that must pass** — a validator that
rejected everything would otherwise go green on rejections alone. Selftest
reads no real manifest and writes nothing, ever.

## Rules

- **Key NAMES, never key values.** `key_env` is shape-enforced:
  `^[A-Z][A-Z0-9_]{0,23}$` and no run of 3+ digits. Both prongs are
  load-bearing — a lowercase hyphenated `sk-…` key fails the shape,
  `ZZQA1234567890ABCD` passes the shape and fails the digit run. (Both test
  fixtures use invented prefixes, never a real vendor's, so a secret scanner
  never has to think about them.) A field literally named `key`, `api_key`,
  `token`, `secret`, `password` or `credential` is refused outright.
  Consequence of workspace rule 6: nobody is ever asked to put a secret here.
- **An `api` transport names its key.** `key_env: null` is the claude-cli
  answer (a login, not a key). On a `transport: api` entry it is refused by
  name (MDL-4 (openrouter vendor)): an api model whose key nobody wrote down
  fails at call time, in a worker, on someone else's job.
- **`null` and absent are different answers.** `key_env: null` means *this
  model spends no key* (it runs on the claude CLI's own login). A missing
  `key_env` means *nobody wrote it down*, and that fails.
- **`unpriced` needs words; `$__` is never asserted.** A bare cost number is
  refused (a figure with no unit is not an answer), and a rate of zero must
  carry a `cost_reason`. This is the bench's own doctrine held as a schema
  rule: a zero and an unknown are different answers.
- **Everything seeds `draft`.** The definition owner holds the gate (rule 6).
  A consumer that filters to `approved` finds this registry empty until the developer
  blesses entries — deliberately, not as a bug.
- **The registry never guesses.** There are no defaults and no fallbacks. A
  model whose cost or key was guessed is worse than a model that is absent.
- **Data, never code.** Edit a manifest and commit, and the next consumer
  sees it — no restart, no code change. Anything that wants to *run* a model
  is a consumer, and lives outside this folder.
- **Brand-agnostic** (workspace rule 7): no brand name appears in
  `models.json`. `trained-assets.json` carries a `brand` field because a
  trained identity *is* brand-specific — it is a pointer to the brand folder,
  never brand content.

## OpenRouter — the standing inference vendor (MDL-4 (openrouter vendor), 2026-09-09)

the developer's word: "a parallel to fal.ai but for inference models … include it in
the models component to be used more generally." OpenRouter is a **vendor**
here, the way fal is for images: many models, one key, one bill. Every entry
below spends `OPENROUTER_API_KEY` (the name; the value lives in the worker's
env file by the developer's own act), rides `transport: api`, and is **reached only
through the worker's `infer` action** (WM-34 (infer action)) — no second
OpenRouter client anywhere in the org, and no id resolved from anything but
this file.

The OpenRouter entries themselves — ids, `vendor_id`, prices, context and status —
are in `models.json` (every entry with `"vendor": "openrouter"`); read them there:
`python3 -c "import json;[print(m['id'],m['status']) for m in json.load(open('components/models/models.json')) if m['vendor']=='openrouter']"`.

Prices are OpenRouter's public list (`GET /api/v1/models`, read
2026-09-09T04:33Z, no key needed) — the first priced **text** entries in the
registry. The list price is a headline, not the spend: the infer record
carries what the vendor's usage block reports per call. DeepSeek's
per-provider figure read in the browser the same day ($__/$__) differs;
the list price is recorded and the disagreement is in the entry's
`cost_reason`.

**Data policy.** DeepSeek's first-party endpoint trains on prompts. The
account's Data Policies exclude training providers (the developer's click, 2026-09-09).
Whether a non-training provider serves `deepseek-v4-flash-0731` under that
policy is **unchecked until the first `infer` call**; a `no provider` answer
means the entry comes out (MDL-4 (openrouter vendor)'s kill), never that the policy loosens.

**Seeding rule.** A new entry is seeded `draft`; that is the gate, not a
placeholder. the developer blesses each by name (`approved_by` on the entry), and a
consumer filtering to `approved` does not see it until he does. Each entry's
current status is in `models.json`.

### The request-level controls (MDL-5 (reasoning budget), 2026-09-09)

A REASONING model's output budget is not a text model's. On 2026-09-09 both
reviewers returned `finish_reason: length` with **0 characters of reply** — at
`max_tokens: 4000`, then again at **16000, `infer.json`'s `max_tokens_cap` at the time**
(the current cap is in `platform/workers/mini-worker/infer.json`): 59,707 characters of hidden reasoning, $__, no
answer. Raising the cap is **struck as the fix** — the failing retry was at it.

Then the identical request ran a second time (WM-40 (claim release order)'s
duplicate execution) and **answered**: 2,087 characters, `stop`, near-identical
reasoning volume. The only difference was the upstream OpenRouter routed to —
`Relace` returned nothing, `OpenInference` answered. So the budget is
survivable and **the route decides**, which makes the provider pin the
load-bearing half and a single successful probe worth nothing on its own (it
may only mean a lucky route).

| entry | reasoning | provider | based on |
|---|---|---|---|
| `deepseek-v4-flash-0731` | `{"enabled": false}` | `{"order": ["OpenInference"], "allow_fallbacks": false}` | **one measured success** — `stop`, 2,087 chars through OpenInference; `length`, 0 chars through Relace. Thin, but real |
| `glm-5.3-flash` | `{"enabled": false}` | **none — no known good route** | 0 characters through Z.AI at 16000 tokens. A route is not invented; when one answers, that record pins it |

Read the vendor's own table before reading anything into the reasoning half:
`effort` is **OpenAI/Grok only**, `reasoning.max_tokens` is **Anthropic/Gemini
only**, and `exclude` decides whether the reasoning is *returned*, never
whether it is *spent*. Neither of our two reviewers is reached by either knob,
so `enabled: false` — the one field the vendor's table marks as supported by
all models — **may bound nothing here**. It is declared so the pilot's
two-size probe measures a bounded attempt, never as evidence one worked.

The pin slugs are the names the vendor **reported back** on the records
(`provider: OpenInference`); they were not checked against OpenRouter's
provider-slug list, which needs network the maker had none of. A wrong slug
fails **closed** — with `allow_fallbacks: false` the call is refused naming
the route, never silently rerouted.

Consumer half: `platform/workers/mini-worker/infer_run.py` `payload()` puts
the declaration on the request body unchanged, and `plan()` refuses a
malformed one **by name before any call**. An entry that declares neither
control produces the payload that function produced before this card — byte
for byte, the seeded five included.

## Not in scope (ruled with the package)

**Any shared model gateway.** Not a library, not a proxy, not a client. Its
trigger is the **third duplicated caller**, and its first question is
**adopt-vs-build**, not build. Until then, a consumer reads this manifest and
makes its own call with its own credential.

Also deliberately out for now, each named so the hole is visible rather than
silent, each folding in under its own MDL-2 (consumer migrations) card:

1. The **mini-worker's fal IMAGE menu** (`platform/workers/mini-worker/models.json`
   + `prices.json`) — 17 endpoints carrying the only *billed* price data the
   org has. It is a fourth fragment MDL-2 (consumer migrations) did not enumerate; folding it in is
   a real card, not a tidy, because its per-model payload profiles are engine
   config and only the id/cost/key/status slice belongs here.
2. The **atlas's hand-drawn model nodes** — MDL-2 (c).
3. The bench's **`chain-head` arm**, which is not a model at all (it is the
   chain's own runner inside the pinned clone) and should never gain an entry.

## Known fragment disagreement, surfaced not resolved

`bench-models.json` declares `key_env: ANTHROPIC_API_KEY` for the claude
models while *also* declaring `transport: claude-cli` — i.e. it names a key
the CLI path never spends. The registry records `null` (the CLI login) and
leaves the reconciliation to the curator. **MDL-2 (a)** is where the bench
either drops the key name or explains it. Surfacing the conflict is what a
registry is for; silently picking a side is not.

## The declared tests

```
python3 new-workflow-design/builds/models-registry/test_models_registry.py
python3 new-workflow-design/builds/models-registry/test_model_budget.py
```

No pytest, no network, no dependencies, and it must pass on
`/usr/bin/python3` (3.9) as well as `python3` — so **no 3.10+ syntax anywhere
in this component**.

It runs `validate.py` against the real manifests, runs `--selftest` and checks
its CONTROL case passed, then exercises the three rejections the card names —
a value-shaped `key_env` (both prongs), an unknown `status`, a duplicate `id`
— end to end through the CLI on inline fixtures in a temp dir, asserting exit
`2` *and* that the finding names the offending entry. It also proves the
component is definitions-only (`validate.py` is the only `.py`, no
subfolders), that no key-shaped token is in either manifest, that every
trained-asset `record` exists and its `trigger`/`kind` match the record it
points at, that every status is a gate value, and that both manifests are
byte-identical after every run.

Since MDL-4 (openrouter vendor) it also proves the two OpenRouter entries
(vendor, transport, key_env NAME, slash-namespaced `vendor_id`, priced cost),
that an api-transport entry with `key_env: null` is refused by name, and that
the five MDL-1 (models registry) entries are unchanged in every field but `status`.

`test_model_budget.py` (MDL-5 (reasoning budget)) is the second, and it asserts
on **the body the wire seam is handed**, never on the plan — a control that
never reaches the wire is exactly the defect it exists to catch. It runs the
worker's `payload()` against a FROZEN literal of the pre-card body (key order
included) for every entry declaring no controls, the seeded five read off the
real manifest; it puts a table of malformed declarations through the worker's
checker **and** this validator, so the two cannot drift apart in silence; it
proves a request's own `max_tokens` still beats both defaults and that neither
the cap nor the global default moved; and it proves the captured reasoning is
still never returned as the reply. No network: the one HTTPS seam is poisoned
at import and replaced case by case with a fake that records what it was handed.

It deliberately does **not** assert that everything is still `draft`. Moving
an entry off draft is the gate working; a test that went red on a legitimate
blessing would be a test against the feature. It prints the status
distribution instead.

## Kill-condition

**KEPT 2026-10-08** (the developer, relayed verbatim by ◆ PLAN [1cc25f] before 04:32:36Z: "go on B1, 2, 3"; decision log 2026-10-08 B2 (triage design calls)). The 2026-10-01 clause ("if nothing beyond the
bench reads this registry by then, fold it back") is spent: the worker's
`infer_run.py` and `shadow_judge.py`, language-layer's test and qc-checks'
`text_check.py` read `models.json`. **Kill (restated for those readers): the
registry falls back to a single reader → fold it into that reader's file and
retire the component.** A registry with one reader is a file with extra steps.
The five draft rows (#4) and `trained-assets.json` (#9) come back to the developer as a
short list.

Second, inherited from the contract addendum: if the curator's approval queue
exceeds a week, the gate has become a bottleneck — add deputies or narrow the
approved set, never bypass the gate.
