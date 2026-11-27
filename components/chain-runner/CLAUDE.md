# components/chain-runner — the chain engine, as a component

**Owner: the developer for now; the owner consulted on return.** Created 2026-08-31 on
the developer's ruling relayed through ◆ PLAN · dev-the developer — "start component
chain-runner for video-teardown, a workflow duplicate running WITHOUT a
person's machine; chain managed WITHIN the component". A deliberate, flagged
skip of the lab station on his explicit word (the atlas precedent); see the
duty-6 flag in `new-workflow-design/builds/chain-runner/task-cards.md`.

**Definitions + curator — the developer** (the developer, 2026-10-07, triage action 3 (definition lines and registry rows)): the chains under
`chains/` are the definitions (components rule 6), and he holds their
approval gate.

Runs by: both

What it is: an engine that runs a STAGED PROMPT CHAIN — stage ordering,
prompt-version resolution, `@stage` piping, per-stage model binding — from a
spec, on any machine, writing only where it was told to write. What it is
not: a video tool, a brand tool, or anybody's workflow. Chains are data under
`chains/`; the engine is chain-agnostic and brand-agnostic and has no branch
for either.

**chain-runner** — the chain engine. It takes a chain key under `chains/` (or a
`chain.json` by `--chain-file`), a run-config (`--config`, `--var`) and an
`--out` directory, makes `run.json`, `stamp.json` (unless `--no-stamp`), each
stage's rendered prompt and output under `stages/<key>/`, and `FAILED.txt` on a
failed run, all under `--out`. Does not write anywhere but `--out` (exit 3),
call a model unless `--model-runner vendor` is given, or file a record (the
platform's `chain_records.py` does that). Triggered by
`python3 components/chain-runner/runner/run.py <chain> --out <dir>`.

**CHAIN WITHIN THE COMPONENT** is a ruling, not a preference (the developer,
2026-08-31; PLAN had recommended chains-as-external-data). It is settled and
not to be re-raised: `chains/` is a subdirectory so that a second chain costs
a directory.

## Contract (per components/CLAUDE.md rule 2)

Three surfaces are dependable, and they are the only three: **the command**,
**the `chain.json` schema**, and **the run directory's shape**. Nothing
outside this folder may depend on anything else here — not `runner/`'s
modules, not their functions, not the order they read files in. A consumer
needing a fact these do not carry gets a card, not a peek inside.

### 1. A run is ONE COMMAND

```
python3 components/chain-runner/runner/run.py <chain> --out <dir>
```

`<chain>` is a directory name under `chains/`. Flags:

| flag | means |
|---|---|
| `--out DIR` | where the run lands. **Required, and the only place a run writes.** No default, ever |
| `--config FILE` | run-config: a flat JSON object, `name` → scalar |
| `--var NAME=VALUE` | one run-config variable; repeatable; beats `--config` |
| `--chains-dir DIR` | where chains live (default `chains/`). Fixture trees use this |
| `--chain-file PATH` | run a `chain.json` directly instead of by key |
| `--member NAME` | one member of this run's group; repeatable, and **order is the fan-in order**. None given = one unnamed member |
| `--root NAME=PATH` | one named content root, overriding the chain's declared default of that name; repeatable. Opaque name, checked path — see rule-9 below |
| `--model-runner NAME` | the model seam's implementation. `stub` (default, calls nothing) or `vendor` (real — Gemini + the Claude CLI; **spends money**) |
| `--check` | validate and report. **Writes nothing**, does not create `--out` |
| `--no-stamp` | skip `stamp.json`, the run's only wall clock |
| `--quiet` | no progress on stderr; the exit code still speaks |

Exit codes, because a caller must be able to tell the failures apart:
`0` ran · `2` malformed spec, nothing written · `3` **out-dir violation** ·
`4` valid chain, bad invocation or config · `1` unforeseen. A rule-9 (brand
home) finding rides those same two codes by ORIGIN — `2` when the chain
declares the offending root, `4` when this invocation does.

### 2. OUT-DIR DISCIPLINE — the hard rule

**A run writes ONLY under `--out`. Any attempted write outside it fails the
run loudly.** This is a done-when of the card that created this component, not
a preference, and it is enforced **structurally**: every byte this component
writes goes through `runner/outdir.py`'s `OutDir`, which resolves the
candidate against the out root and refuses

- absolute paths, including ones that happen to land under the root;
- parent traversals that leave the root;
- any path crossing an existing **symlink**, at any depth;
- a path resolving to the out root itself.

There is no second write call site in `runner/`. The refusal names the
offending path, exits `3`, and says the run is over.

The jail holds against the **model seam** as well as against the chain file: a
stage's runtime artifacts go through the same check, so a runner returning
`"../../escape.md"` fails the run rather than writing there. A wall that only
inspected `chain.json` would be schema validation wearing a wall's clothes.

Two further rules, on top of the jail and deliberately separate from it
(the jail is absolute; these are policy, and policy hidden inside a wall is
policy nobody can find):

- **Refused:** an `--out` inside this component's own folder. A component that
  stores runs in itself stops being a capability and becomes a run store.
- **Warned, not refused:** an `--out` inside a git working tree. That is the
  `runs_root`-inside-the-tree flaw this component exists to cure — but a
  records adapter writing under `platform/data/` is legitimate and deliberate
  (components/CLAUDE.md rule 3), so it is a loud warning with its reason
  attached rather than a wall across the intended use.
  The one exception is `<repo>/runs/`, the ruled run home (runs/README.md:25):
  no warning there. The worker files a chain run under
  `runs/chain-runner/<brand>/<label>/`, and a request that names no brand
  under `runs/chain-runner/_unsorted/<label>/` (runs/README.md:59) —
  CR-9 (chain-runner runs home), 2026-10-07.

Why it matters at all: when the run root sits inside the tree it runs from,
"the run" and "the repo" become one place — a run dirties git, a git operation
can eat a run, and nothing wrapping the engine can say what a run produced.
That is what makes this engine **bench-runnable natively**, which is the whole
point of owning it.

### 3. `chain.json` — schema 1. THE SCHEMA IS THE CONTRACT

```
chains/<chain>/chain.json

{
  "schema": 1,                  always 1; a consumer checks it and refuses otherwise
  "chain": "<key>",             kebab-case, and MUST equal the directory name
  "label": "<human name>",      required — people name a chain by its label
  "note": "<free text>",        optional
  "prompts_dir": "prompts",     optional, relative, may not leave the chain dir
  "placeholder_style": "at-brace",   optional — "at-brace" (default), "curly"
                                     or "single-curly"

  "provenance": {               optional; CR-2 FILLS THIS
    "source":    "<repo-relative path the chain was copied from>",
    "sha":       "<the git sha it was pinned at>",
    "pinned_on": "<YYYY-MM-DD>",
    "note":      "<why, in words>",
    "route":     "<the route the snapshot was taken under, if any>",
    "resolver":  "<the entrypoint that was executed to pick these files>",
    "picks":     [ { "stage": "<key>", "engine": "<source's engine name>",
                     "version": <int>, "source": "<repo-relative file>",
                     "source_filename": "<its name at the source>",
                     "sha256": "<64 hex>", "copied_to": "<under prompts_dir>" } ],
    "gaps":      [ "<something the source expressed and this chain cannot>" ] },

  "defaults": { "model": "<id>", "prompt_version": "<v>" },   optional

  "roots": { "<name>": "<path>" },   optional — named CONTENT ROOTS this chain
                                     reads from, overridable per run with
                                     `--root <name>=<path>`. A relative path is
                                     read against the chain's own checkout

  "stages": [                   ARRAY ORDER IS THE RUN ORDER. Non-empty.
    { "key":            "<kebab key, unique, never 'config', NO DOT>",
      "label":          "<human name>",
      "kind":           "model" | "assemble",   optional, default "model"
      "scope":          "member" | "group",     optional, default "member"
      "prompt":         "<path stem under prompts_dir>",
      "prompt_version": "<v>",        optional -> defaults.prompt_version
      "model":          "<model id>", required unless defaults.model;
                                      FORBIDDEN when kind is "assemble"
      "inputs":  { "<name>": "@<earlier-stage-key>"          its output
                           | "@<earlier-stage-key>.<field>"  one extracted fact
                           | "@<earlier-stage-key>#pick"     its control version
                           | "@<earlier-stage-key>*"         every member's
                           | "@config.<var>" },
      "media":   { "<name>": { "kind": "video"|"image"|"audio",
                               "ref":  "@config.<var>" } },   optional
      "fields":  { "<name>": { "from": "labelled-line", "label": "<LABEL>" }
                           | { "from": "regex", "pattern": "<one group>" } },
                                                              optional
      "when":    { "field": "@<earlier-stage>.<field>",       optional — the
                   "equals": "<value>" }                      STAGE GATE
                | { "field": "@<earlier-stage>.<field>",
                    "in": [ "<value>", … ] },
      "output":  "<path relative to --out>",   default stages/<key>/output.md
      "note":    "<free text>" } ]
}
```

#### Stage kinds — `model` and `assemble` (CR-2b)

A `model` stage renders its prompt and calls the seam. An **`assemble` stage
renders its prompt and is done**: the rendered text IS its output, no model is
bound, nothing is called and nothing is spent. Everything else about the two is
identical — inputs, media, the rendered prompt on disk, the jail, the record
row — which is what makes it a stage KIND rather than a special case.

Binding a `model` on an assemble stage is a **malformed chain**, not an ignored
field: it claims a vendor call that never happens. Before this kind existed, a
chain with such a stage had to invent a placeholder model id, which put a stage
costing nothing in the same column as the stages costing the most.

#### `#pick` — the control version out of a stage's output

`@<stage>#pick` yields the block headed by the **lowest-numbered `VERSION <n>`
heading** in that stage's output, running to the next heading of any kind. A
heading is an ATX line (`## …`) or a wholly-bold line (`**…**`), because a model
asked for numbered sections answers in either.

An output with **no version heading is a fatal error**, naming the stage. There
is no fallback to the whole output: piping everything where a chain asked for
one version is the same class of silent failure as shipping an unsubstituted
`@{token}` to a model. Where a human pick exists it outranks this rule; the
engine has no human, so it takes the control — which is exactly what the
machines these chains are imported from record as the no-human-picked deviation.

#### Members and `*` fan-in

A run may declare **members** — `--member NAME`, repeatable, order preserved
because it is the fan-in order. Members are opaque names: a group of videos, of
SKUs, of anything. The engine knows none of them, the same way it knows no
brand.

| | |
|---|---|
| `"scope": "member"` (default) | runs once per member, writing under `members/<name>/` |
| `"scope": "group"` | runs once, for the whole group |
| `@<stage>*` | every member's output of `<stage>`, in member order |

A run declaring **no members has exactly one, unnamed**, and every path is what
it was before members existed — the feature costs an existing chain nothing.
On such a run `@x*` and `@x` are **byte-identical**, deliberately: a chain can
declare the fan-in it really means and still be run, unchanged, on one item.

Three shapes are refused. Two in the spec, because they can never mean
anything: `*` on a group stage (it runs once — nothing to fan in), and `*` on a
member stage (it is already inside one member). One at **run time**, because it
depends on the run: a group stage reading a member stage **without** `*` is
fine on a one-member run and fails loudly on a many-member one, naming the
count — picking a member silently is how a brief for six videos quietly
describes whichever ran last.

#### `roots` and rule-9 (brand home) — a COMPILE FINDING (CR-7)

A chain may declare named **content roots** — where its content comes from —
and a run may override any of them with `--root NAME=PATH`. To this engine a
root name is opaque, exactly like a run-config variable name: nothing reads it,
branches on it or interprets it.

The PATH is a different matter. components/CLAUDE.md rule 9 says brand content
comes from `brands/<brand>/` and nowhere else, and `runner/brandhome.py` — the
only file in `runner/` that knows the word — enforces it at compile time:

| the root resolves… | verdict |
|---|---|
| under its checkout's `brands/` | passes |
| elsewhere, through a **second `brands/` tree** (`lab/<person>/brands/<x>`) | **FINDING** |
| elsewhere, with a segment that **is a brand with a home** (`.../copy/<brand>/`) | **FINDING** |
| anywhere else — under no checkout, a directory named nothing in particular | nothing |

`--check` prints every finding and exits non-zero; an ordinary run is refused
by the same step, before `--out` is created, so a refused run has written
nothing. **Detection is by path shape, never by content**, and the fourth row
is the point: prose review still covers what a path cannot say, while a check
that fires on legitimate roots gets routed around and takes the real findings
with it. False positives are worse than misses here.

The rule binds **definitions, not execution**. `spec.py` carries `roots` as
names and paths and knows nothing else; the engine never calls this check and
stays brand-blind, which is the other half of the ruling (PLAN rider (2)).
And no brand name is written in the component: the names in the third row are
read out of the home tree at check time (workspace rule 7).

#### `media` — non-text inputs (CR-2b)

A stage declares media by name, kind and a run-config reference. Each entry
resolves to a **location** — a path or a URI — which

1. rides the model seam as a typed, validated `MediaInput`, and
2. is **also substituted into the prompt** under its own name.

Both, deliberately. The seam is what a vendor needs; the substitution is what
the machines these prompts were copied from do with an image path, and dropping
it would invent a parity difference. **The engine never opens the file**:
reading a video into memory to cross a function boundary is how a chain engine
becomes a media tool, and a location is what an upload handle, a file path or a
signed URL all already are. What to do with it — upload, glob a directory of
frames, hand it to a queue — is the runner's business, below the seam.

`ref` may only be `@config.<var>`: a stage output is text this engine wrote, and
calling it a video would make the type a label rather than a fact. One entry is
one location; a stage wanting many declares many, or one location naming a
directory. A name used by both `inputs` and `media` is a malformed chain.

#### `fields` — typed facts out of a stage's own output (CR-6)

A stage output used to be one opaque text: a downstream stage could reference
the whole thing and never a fact inside it. A stage may now declare **fields**
— a name, and one flat way to parse it out of that stage's own output:

```json
"fields": { "lane":   { "from": "labelled-line", "label": "LANE" },
            "format": { "from": "regex", "pattern": "^FORMAT:\\s*(\\S+)$" } }
```

and a later stage references one as **`@<stage>.<field>`**, like any other
input. Two forms and deliberately no third: a **labelled line** reads
`LABEL: value` off the output — the shape a prompt gets back when it asks for
one answer on its own line, read through the markdown decoration a model
actually writes (`**LANE:** ORGANIC`, `## LANE: ORGANIC`), first non-empty
answer wins — and a **regex** captures exactly one group, `re.M` so `^` and `$`
are line boundaries. A pattern with anything other than one capture group, or
one that will not compile, is a **malformed chain**: a pattern that could hand
back a tuple is refused at load rather than at spend time.

**No code in a definition.** A field declaration is data, so a reader of
`chain.json` can see what a run will pull out of a stage without running it,
and `runner/` still never executes anything under `chains/`.

**Extraction failure fails the stage, loudly, by name.** A declared field is a
claim that the stage's output carries it, so it is checked whether or not
anyone reads it this run, and there is no default and no empty string: a later
stage routing on a silently empty value is a run that takes the wrong branch
and looks fine doing it. The two failures are told apart — the label that never
appears, and the label that appears carrying nothing — because one is a prompt
to fix and the other is a chain to fix. The stage's output stays on disk beside
`FAILED.txt`: after a failure the question is what the stage actually said.

Three refusals in the spec, each because its silent version is worse: a
reference to a field the producing stage **never declared** (a chain routing on
a fact nobody arranged to extract); a **field carrying a selector**
(`@a.lane#pick`, `@a.lane*` — neither `#pick` nor `*` has a reading over one
extracted value); and a **stage key containing a dot**, which was loadable
before fields existed and cannot be now, since `@one.two` would be both "stage
`one.two`" and "field `two` of stage `one`". Field names carry no dot either,
and for the same reason: `@<stage>.<field>` splits on the first one.

A field is **opaque to the engine**, exactly as a run-config variable name is.
`lane`, `format`, `avatar` are names it substitutes and records; there is no
branch anywhere on what one means, and no field kind through which a brand or
any other domain fact could enter this code.

**A chain that declares no fields is untouched by all of this** — no `fields`
key on its stage rows, no `extracted` block in its record, not even empty ones.
That is the members-feature guarantee in the only form a record can hold it,
and the declared test holds the pre-CR-6 record shape as a written-down list to
diff against.

#### `when:` — the stage gate (CR-5)

A stage may carry an optional **`when:`**, and then it runs only if that
predicate holds:

```json
{ "key": "organic-only", "label": "Organic lane only", "prompt": "organic",
  "when": { "field": "@triage.lane", "equals": "ORGANIC" } }
```

The predicate is **flat, and that is a ruled wall rather than a first cut**:
one field, one test. `equals` or `in`, exactly one of them, over exactly one
`@<earlier-stage>.<field>` reference. There is no `and`, no `or`, no `not`, no
second field and no expression string — a chain needing one is a chain asking
for a dependency graph, and the standing kill line says the bespoke runner
stands as-is and this is reopened at the third chain, rather than an expression
evaluator being grown here one operator at a time. Comparison is exact string
equality; nothing lowercases or trims, because an engine deciding that
`Organic` means `ORGANIC` is an engine deciding what a chain's author meant.

**A gated-off stage is a STATED FACT, never a missing row.** `run.json` carries
its row with `"skipped_by_gate": true` and a `gate` block holding the predicate
as written and **the value it read**, and the record grows a `skipped` roll-up
so "what did this run not do, and why" is answerable without reading fifteen
rows. The row carries no `prompt`, `inputs` or `output` keys, because there was
no prompt and no output: a row full of nulls would read as a stage that ran and
produced nothing. Nothing is written for that stage, and `outputs` does not list
it. A stage whose gate **held** carries the same `gate` block with
`"passed": true` — "this ran because lane was ORGANIC" and "this ran" are
different records, and only the first survives being read six weeks later.

Three refusals at **compile**, each because its silent version is worse: a gate
on a field the producing stage **never declared** (the same refusal a field
reference gets, and for the same reason — a chain deciding whether to run a
stage on a fact nobody arranged to extract); a gate on a **whole output or on
`@config.<var>`** (run-config is known before the run starts, so gating on it is
a flag the caller already holds — the point of `when` is a stage deciding at run
time); and a gate **carrying a selector**, forward, or self-referential, by the
same ordering rules any input answers to.

**A downstream reference to a gated-off stage's output fails loudly, by name**,
naming the stage, the predicate and the value that skipped it. It never resolves
to an empty value and it never quietly skips the reader: a stage handed nothing
writes confident prose about a stage that never ran. The chain either gates the
reader on the same field, or does not read that stage.

Member-scoped gates are judged **per member**, so a stage can run for one member
and be gated off for another; a `*` fan-in that meets a gated-off member fails
by name for the same reason. And a gate whose own field cannot be reached — the
producing stage was itself gated off — **fails the run**: there is no "gate
unreadable, so run it anyway" and no "so skip it", because both are the engine
deciding a routing question the chain asked its own output to decide.

**A chain declaring no gate is untouched by all of this** — no `when` key, no
`gate` or `skipped_by_gate` on any row, no `skipped` roll-up, not even empty
ones. Same members-feature guarantee as fields, held against the same
written-down record shape in the declared test.

**Unknown keys are an error**, top level and per stage. `promt_version`
silently doing nothing is how a chain runs the wrong prompt for a month.

**Failure is part of the schema.** A malformed `chain.json` exits `2`, names
the file and **every** problem found (not just the first — an author fixing
one typo per run stops reading the errors), and **writes nothing**: validation
completes before `--out` is so much as created.

#### Stage ordering

Array order is run order. There is no dependency graph and no `after` field:
a stage may only read what has already run, and that is checked in the spec,
so a forward or self reference is a malformed chain rather than a runtime
surprise. Two stages declaring the same `output` is also an error — the second
would silently overwrite the first.

**Fields and gates change none of this.** `@<stage>.<field>` is a reference to
an EARLIER stage like any other and is bound by the same rule, and a `when:`
gate reads one of those same references — so neither extractable facts nor
conditional stages buy a chain new ordering power or a graph. A gate decides
WHETHER a stage runs, never WHEN. That is the CR-6 (extract fields) kill-condition held
in the schema: the day these extensions start needing a dependency graph, the
bespoke runner stands as-is and this is reopened at the third chain.

#### Prompt-version resolution

A stage names a path **stem**, and optionally a version. The ladder, in order:

| declared | tried first | tried second |
|---|---|---|
| version `v2` | `<stem>/v2.md` | `<stem>.v2.md` |
| no version | `<stem>/prompt.md` | `<stem>.md` |

Two shapes because both are reasonable — a directory per stage holding its
versions, or a flat file per stage. Nothing resolves outside `prompts_dir`.
The **resolved path and its sha256** are recorded in `run.json`, so nobody
re-derives which file a run actually read.

**There is no "latest".** A version is declared or absent; the engine never
picks the highest-numbered file it can find. Implicit latest is how a chain
changes behaviour with nobody having changed the chain.

#### `@stage` piping — DECLARED, never discovered

A stage declares what it consumes, in `chain.json`:

```json
"inputs": { "transcript": "@stage-0", "tone": "@config.tone" }
```

and its prompt body references those **names** in the chain's **declared
dialect**:

| `placeholder_style` | token | escape |
|---|---|---|
| `at-brace` (default) | `@{name}` | `@@{name}` |
| `curly` | `{{name}}` | none |
| `single-curly` | `{name}` | none |

The dialect is **declared per chain and never sniffed from the text** (the developer's
CR-2 (VT parity) ruling 3). The other two spellings exist because CR-2 (VT parity) imports prompts
copied at a pinned sha, and a copy whose tokens had to be rewritten is not the
copy whose sha was pinned. There is no engine-wide default change and no branch
on any particular chain: the engine looks a chain's declaration up in one table
and does nothing else with it.

`single-curly` matches **only `[a-z0-9_]`** inside the braces. That is not a
style choice — it is character-for-character the token grammar of the machine
those prompts were copied from, so `{Scene 3}` and `{CamelCase}` stay text on
both sides. A stricter matcher here would fail runs on prose the source renders
fine, which is a parity difference invented by us rather than inherited, and
inventing one is the single thing an imported chain must never do.

Declaring the piping in the spec rather than scraping it out of prompt text is
what makes this file the contract: the data flow is readable without opening a
single prompt, and stage ordering is machine-decidable.

- An **undeclared placeholder** in a prompt body is fatal, naming the stage
  and the token. The alternative is shipping the literal text `@{transcript}`
  to a model and getting confident nonsense — the most expensive silent
  failure a chain has.
- A **declared input nobody references** is recorded in `run.json` as
  `unused_inputs` and is not fatal.
- A missing `@config` variable fails the run at that stage, naming the
  variable and the flag that supplies it.

#### Model binding

Per stage, with `defaults.model` as the fallback. A stage resolving to no
model is a malformed chain — a stage whose model depends on whatever the
caller happened to have configured is not a bound stage.

The engine calls exactly one thing per `model` stage: the **model seam**,
`runner(ModelRequest) -> ModelResponse(text, artifacts)`. `ModelRequest` carries
the chain and stage keys, the bound model, the rendered prompt, the substituted
inputs and the stage's typed `media` tuple. Above it is chain
logic; below it is a vendor call, a queue job, a recording or a stub. That
seam is what lets a bench wrap this engine — swap the runner, change nothing
else — and it is the same seam CR-4 (runner dispatch)'s worker adapter dispatches on.

**Two runners: `stub` (default) and `vendor` (CR-2b (real model runner)).** CR-1 (engine core) could say "no code
path reaches a vendor" because no real runner existed. One exists now, and the
guarantee is kept in the strongest form still available: `runner/vendors.py` is
registered **lazily**, so a run that does not name `vendor` never imports it —
no HTTP client in the import graph, no credential read, `--check` included. The
declared test asserts that in a fresh interpreter rather than promising it.

| runner | binds | credential |
|---|---|---|
| `stub` | nothing — deterministic echo | none |
| `vendor` | `gemini-*` over REST; `opus`/`sonnet`/`haiku`/`claude-*` over the `claude` CLI | `GEMINI_API_KEY` from the env, at CALL time. Claude rides the CLI's own login — no Anthropic key is in the grant row and none is read |

Three refusals, and each exists because its silent version is worse than a
failed run: a model id that routes to no vendor **fails** rather than guessing;
media on a Claude stage **fails** rather than being dropped (answering
confidently about a video the model never saw is the expensive failure); and a
busy Gemini **fails** rather than falling back to a second model, because a
stage that silently bound something else makes `run.json` a record of a chain
that did not run. `--model-runner` naming anything unregistered — or naming a
runner whose module will not import — is a hard, named failure. A silent
fallback to the stub would let a "real" run quietly produce fixtures.

**Media crosses to a vendor by location, never by content.** A URI goes to
Gemini by reference; a local file is uploaded as the bytes on disk and
referenced by the uri that comes back. Nothing is transcoded, resized, sampled
or frame-extracted — the moment this component opens a video to do something
clever with it, the kill-condition below has fired.

### 4. The run directory — what `--out` holds

```
<out>/
  run.json                     THE RUN RECORD. Deterministic — no wall clock
  stamp.json                   the wall clock, and the only one (--no-stamp omits it)
  stages/<key>/prompt.txt      the rendered prompt, exactly as the model saw it
  <stage output paths>         default stages/<key>/output.md
  members/<name>/…             the same two, per member, for member-scoped
                               stages when a run declares members
  <artifact paths>             whatever the seam returned, all jailed
  FAILED.txt                   only on a failed run: how far it got, and why
```

`run.json` carries: the chain key, label, spec sha256, `placeholder_style`
and **provenance block**; the model runner's name; the run-config's variables;
and per stage — key, label, **bound model**, the prompt's declared stem,
version, resolved path and sha256, the rendered prompt's path and sha256, the
declared inputs, `unused_inputs`, the output path, its sha256 and length, and
any artifacts. Plus `files`, the manifest of what the stages produced.

A stage that declared `fields` also carries `fields` — the values it actually
extracted — and the record grows an **`extracted`** roll-up listing them in
execution order, so "what did this run route on" is answerable without reading
fifteen stage rows. Both keys are **absent, not empty**, when no stage declared
a field.

A stage that declared a `when:` gate carries a **`gate`** block — the predicate
as written, the value it read, and whether it passed — and a stage the gate
skipped carries `skipped_by_gate` instead of a prompt and an output, with a
**`skipped`** roll-up beside `extracted`. Absent, not empty, when no stage
declared a gate. `outputs` lists what the run PRODUCED, so a gated-off stage is
not in it; `stages` lists what the run DECIDED, so it is.

**Determinism is part of the contract.** `run.json` carries no wall clock and
no elapsed time, so the same chain over the same config produces byte-identical
output and "did this run change anything" is a diff rather than a judgement.
`files` lists what the STAGES produced and therefore does not list itself — a
manifest containing its own hash cannot exist, and saying so beats letting a
reader discover it.

**A failed run keeps its partial output** and writes `FAILED.txt` beside it.
After a failure the question is always how far it got, and a tidy empty
directory answers that with nothing.

### 5. An IMPORTED chain — what a pin has to say (CR-2)

A chain under `chains/` may be **authored here** or **imported from another
component at a sha**. An imported one is data like any other; what makes it
trustworthy is that its `provenance` block answers the question a pin alone
cannot.

A sha alone is not enough when the source resolves its own shape at RUN TIME —
scanning prompt folders for a highest version, picking a lane from a route flag.
The same sha then yields different chains under different routes, so provenance
records the `route` the snapshot was taken under, the `resolver` **entrypoint
that was executed** to take it, and one `picks` row per stage naming the file
chosen, its version, and its sha256.

Three rules follow, and they are the whole discipline:

- **The source's own resolver decides, not us.** An import runs the source's
  resolution logic read-only, with no model calls, and writes down what it
  picked. Re-deriving a source's version scan in our own code is a fork with a
  provenance block bolted on.
- **Copies are byte-identical, tokens included.** The dialect is declared
  (`placeholder_style`); a copied prompt is never rewritten to suit this engine.
  Every pick's digest must match its copy, and the declared test checks that and
  catches a one-byte edit. Whether the SOURCE still hashes the same is reported,
  not enforced — the source moving on is its owner working, and re-pinning is a
  human call.
- **Gaps are recorded, never smoothed.** Anything the source expressed that a
  `chain.json` cannot — a route-conditional skip, a run-time lane override —
  goes in `provenance.gaps` verbatim, and `--check` prints them. A reader has to
  meet a gap in the file, not discover it in a parity diff.
  **A gap that gets a form stops being a gap.** The first import recorded two —
  a derived pick and a fan-in over every group member — and CR-2b (real model runner) gave both
  real forms (`#pick`, `*`), so the import now spells them and the gap lines
  are gone. Leaving them would warn a reader about a difference that is no
  longer there, which costs exactly as much trust as hiding a real one.

The video-teardown import and the parity procedure that judges it live in
`new-workflow-design/builds/chain-runner/` (`import_vt_at_pin.py`,
`PARITY-HARNESS.md`) — build machinery, deliberately not part of this
component's dependable surface.

### 6. Where a run SURFACES (CR-3) — outside this component, by contract

components/CLAUDE.md rule 3 says every component gets a records adapter. This
one's is `platform/workers/mini-worker/chain_records.py`: it scans the machine's
runs area, reads the `run.json` this contract's §4 promises, and files one
`teardown-runs` record per finished run carrying **`engine: "chain-runner"`** —
the same kind and the same teardowns view as the owner's machine's runs (the developer ruled
2026-09-02, "CR 3 yes": one view, runs tagged by engine).

It lives on the platform and not here, and it reads **only the three dependable
surfaces**. Nothing in `runner/` knows it exists, no run writes a record, and
this component's contract is unchanged by it — which is the test of whether the
adapter is on the right side of the wall. A run's WORDS are not copied to the
plane: the run directory is outside every checkout, so the record carries stage
metadata and `out: null`, never a path no reader could fetch.

## Rules

- **Brand-agnostic (workspace rule 7).** Nothing in `runner/` knows any brand,
  and there is no field where one could be named. Brand-shaped facts enter as
  run-config variables, which are opaque names the engine substitutes and
  records. A brand-specific chain is a chain, or a config file — never a
  branch in this code. The one file that knows the word is
  `runner/brandhome.py`, which is VALIDATION and names no brand: it reads
  declared root paths and refuses ones that take brand content from outside
  `brands/<brand>/` (rule-9, above). Nothing in the execution path calls it.
  Since BH-1 (2026-09-02) it keeps all of that FINDING logic and takes only
  the LOCATOR — `HOME`, and the upward probe for `.git` — from
  `components/brand-finder/`, the one home for a question that had three
  implementations. Behaviour is unchanged and the CR-7 (rule-9 check) table is re-proven
  against the component in that card's declared test.
- **Credentials are never run-config.** Run-config is recorded verbatim in
  `run.json`, so a secret passed as `--var` lands on disk in the clear. Vendor
  keys reach a real model runner through the environment, scoped by the job's
  grant row in `platform/workers/mini-worker/job_env.py` — `chain-runner`:
  `GEMINI_API_KEY`, `APIFY_TOKEN`, `FAL_KEY`. `GDRIVE_SA_KEY` is **not**
  granted: CR-1 (engine core) keeps no Doc-write stage, and an advisory key nothing reads is
  a grant with no reader. **Declared dependency (chain-runner#8):** the vendor runner's
  Claude stages load `platform/workers/mini-worker/job_env.py` by path for
  `scoped_env('claude')` (`runner/vendors.py`, WM-101 (every spawn scoped)); a
  missing file stops the stage.
- **A chain is data.** `runner/` never imports, executes or branches on
  anything under `chains/`.
- **Nothing outside this folder reads these internals** — the three surfaces
  above are the whole dependable surface (components/CLAUDE.md rule 2).

## The declared test

`python3 new-workflow-design/builds/chain-runner/test_chain_runner.py` — a
**2-stage fixture chain built in the test's own temp directory**, never a real
chain and never anyone's machine. It proves: E2E byte-determinism across two
runs; an out-dir violation caught from **both** vectors (a chain declaring an
escaping `output`, and the model seam returning an escaping artifact path at
runtime) with the run failing loudly; a malformed `chain.json` exiting non-zero
naming the file with nothing written; `@stage` piping — stage 2's rendered
prompt contains stage 1's output; per-stage model binding reaching the stub
with the right model id, including the `defaults.model` fallback; both rungs of
the prompt-version ladder; and a sentinel fingerprint of the tree AROUND
`--out`, byte-unchanged across every run including the failing ones.

CR-2b (real model runner) adds, on a two-member fixture chain that carries all four forms: **media
reaches the seam typed** (read off the stub's own echo, not off the engine's
record) and its location is substituted into the prompt; the **assemble stage
executes with no model and no seam call** — proven by its output being exactly
its rendered prompt, which the stub could not have produced; **`#pick` takes the
control version** and neither the variation nor the trailing section; **`*` fans
both members in, in order**, with member-scoped stages writing under
`members/<name>/`; two such runs are **byte-identical**; and the run-time
refusals — a group stage reading a member stage without `*` on a many-member
run, a member name that is not a path segment, a `#pick` over an output with no
versions. Two members and not one on purpose: with one member, fan-in and a
plain pipe are byte-identical by design, so a one-member fixture would pass
whether or not fan-in worked at all.

CR-2b-ii adds, and the first is the one that matters: in a **fresh
interpreter**, a stub run and a `--check --model-runner vendor` both leave
`runner.vendors` absent from `sys.modules`, and an unregistered name fails by
name — the import guard asserted rather than argued. Then the binding path end
to end with a **fake runner injected**: `--model-runner <name>` reaches the
seam once per model stage and never for the assemble stage, the run record
names the runner that actually ran, media arrives at the runner as typed
`MediaInput`s, and a runner's artifacts go through the jail like any other
write. Finally the vendor module is **read and never imported** — parsed for
stdlib-only imports, its registered entry point, and no credential read at
module level. No network anywhere, on either rail.

CR-2 (VT parity) adds: all three **declared placeholder dialects** render on the chain's
own declaration, declaring one does not enable another, and `single-curly`
produces character-for-character what the source machine's own substitution
produces — stated as an identity, because if those two ever disagree a parity
run is measuring our renderer rather than the imported chain. Plus
**copied-prompt fidelity**: every provenance pick's digest against its copy,
with a one-byte edit proven to go red. The live video-teardown chain is checked
when it exists and reported as a **SKIP** line when it does not — a skip
counted as a pass is how a suite goes green over work nobody did.

CR-6 (extract fields) adds the field seam and its members-feature guarantee: a downstream
prompt read **off disk** holds the extracted VALUES and nothing else (a field
that quietly resolved to the whole output would still look right in a record
that only listed names); `run.json` carries the per-stage values and the
`extracted` roll-up; extraction failure fails the stage by name, proven from
**both** shapes — the label that never appears and the label that appears
carrying nothing; every compile refusal (bad `from`, a pattern with the wrong
group count or one that will not compile, a field name or stage key with a dot,
a reference to an undeclared field, a field carrying a selector). Then
**byte-unchanged**: the pre-CR-6 record shape is written down as a list of
keys, a fields-less chain must still produce exactly it, and the live imported
chain must declare no fields, leave its own directory byte-identical across a
run of it, still complete on the stub, and produce a record of that same shape
twice over. Absent chain, a SKIP line.

CR-5 (when gate) adds the `when:` gate, proven off ONE chain run TWICE — the lane comes
from run-config, so both directions are measured against the same stages. A
gate that holds runs its stage and records the value it read; a gate that does
not produces a `skipped_by_gate` row carrying the predicate and the value, with
nothing written for that stage, no entry in `outputs`, and the row still in
`stages` in order; a membership gate that never holds is skipped on the run
where the others ran; an ungated stage in the same chain grows no gate key at
all. Then the loud ones: a downstream stage reading a gated-off stage's output
fails naming the stage, the predicate and the value, and the same chain runs end
to end when the gate holds — so the failure is proven to be the gate rather than
the chain. Plus the compile refusals, one malformed chain each: a gate on an
undeclared field, on a whole output, on run-config, carrying a selector, with
two tests, with none, with a compound `and` key, forward, self, an empty `in`,
and a `when` that is not an object. The imported chain must declare no gate,
which is the byte-unchanged promise stated for CR-5 (when gate) in the same place it is
stated for CR-6 (extract fields).

CR-7 (rule-9 check) adds the rule-9 (brand home) findings, proven against a **miniature
checkout built by the test** — its own `.git`, its own home tree with two
INVENTED brand names in it, and content trees outside it. A root inside
`brands/` passes; a chain-declared root in a `brands/` tree outside the home is
a finding exiting 2; a `--root` override with the same shape exits 4; an
ad-hoc copy named after a brand that has a home is caught, which is also the
proof that the names come from the tree and not from the code; and an ambiguous
path — plus one under no checkout at all — yields NOTHING, the check's most
load-bearing behaviour. A run carrying an offending root is refused with `--out`
never created.

CM-1 (copy resolution) adds the second real chain, `chains/copy-general`, resolved from
`lab/the owner/copy` at its 2026-09-02 pin (that machine has lived at
`components/copywriter` since 2026-09-19; CR-10 (copy resolver home) repoints
the resolver) — and it is where the two extensions above are proven on a
chain somebody actually runs rather than on a fixture. It validates and
`--check`s clean with no rule-9 finding; every stage has a provenance pick
behind it and every pick's digest matches its copy (an UNFILLED digest is a
named failure, not a skip — the resolver is what fills them); it declares
exactly one gate, reading exactly one field of an earlier stage; its stage
count is the eleven his `STAGES` list runs, which is the reference-hygiene fix
the card asked for; the parts of his runner schema 1 cannot say are in
`provenance.gaps`; and it holds **zero brand-substituted text**, checked
against the brand names READ OUT OF `brands/` as data, never written in the
test. Then both gate directions off the same chain — the lane is read out of
the triage stage's own output, so the two runs differ by one run-config value
— with two identical runs, the chain directory byte-unchanged across all of
them, and his lab byte-unchanged too. Absent chain, a SKIP line.

No pytest, no network, no dependencies. **It must pass on `/usr/bin/python3`
(3.9)** — the declared-test rail runs 3.9.6, so no 3.10+ syntax or kwargs
anywhere in this component.

## Kill-condition

Inherited from the build's own KILL (PLAN's design fold, seen by the developer): if
CR-2 (VT parity) parity forces wholesale copying of another component's domain tools
instead of binding them as stage adapters at the model seam, the engine/recipe
split is leaking — stop before CR-3 (vt-runner registration) and re-look. A chain engine that has to
absorb one workflow's tools to run it is not an engine.
