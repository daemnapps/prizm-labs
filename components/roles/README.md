# roles

Who owns what. A role is why it exists, what it knows, and what the work looks like when it is done. A role is given to a holder (a person or an agent). The role's agent and its sub-agents run the workflows to the end; the role's one number says whether it worked.

Agents do the work. People hold the taste and the calls. After a hand-off the holder runs everything; the owner is asked only for his four calls.

## The chain

```
Owner → Role → Holder → Agent → Sub-agents → Workflow → Number
                                                          │
            the number changes the next round  ◀──────────┘
```

## What is here

| File | What it is |
|---|---|
| `roles.json` | The truth. The model, the rules, the naming rules, and every role. It does not list components: a component names its role once, in `components/system/components.json` |
| `roles.py` | Checks the file, resolves a name, prints a role, an agent brief or a monthly brief |
| `brands/_TEMPLATE/roles.json` | Who holds each role for a brand, that brand's targets, and any call the owner has granted |

Nothing here names a brand, a person, a price or a target. Those live in each brand's own `roles.json`.

## A role card

| Part | The question it answers |
|---|---|
| Reason | Why does this role exist? |
| Knowledge | What does it know? (questions for the knowledge base, and the brand folder files it reads) |
| Application | What does the work look like when it is done? (output, how often, the standard) |
| Number | Which one number does it own? |
| Components | Which components does its agent run? |
| Taste | Which calls stay with a person? |
| Authority | What does it decide alone, and what goes to its lead? |
| Calls | Which of the owner's calls does it reach? |
| Trip-wires | What pulls the owner in? |
| Loop | What does the number change next? |

## The rules

1. Every number has one owner. Two owners is no owner.
2. A role owns an outcome, not a task list.
3. A role is named by what it does, never by who holds it.
4. A person or agent can hold several roles. A role can have several holders; the first one answers for its number.
5. After a hand-off the holder runs everything. The owner is asked only for his four calls.
6. The owner enters a workflow only when a trip-wire fires.
7. Authority grows when the number is hit and shrinks when it is missed.

## The owner's four calls

Spending past a cap, going live, sending, signing. Nothing else in a role waits for the owner. (A gate is any rule a piece must pass: a check the system decides, a stop the holder decides, a call the owner decides. The words are defined in `components/system/system.json`.)

A call can be handed to a role for one brand: `grants` in that brand's `roles.json`. A grant is the owner's own act. Nothing in the toolkit turns one on, and a session may only propose one.

## Naming

| Rule | Example |
|---|---|
| A role id is lowercase with dashes and says the job | `video-editor` |
| One name everywhere: folder, path, command, button, lane and shared drive | `handoffs/video-editor/` |
| Who holds a role is one setting, never part of a name | `holders: ["<person>", "agent:<name>"]` |
| A stage is a component's place in a workflow. A stage is held by a role | `video-edit` → `video-editor` |
| A hand-off is one folder and the work comes back inside it | `handoffs/<role>/<brand>/<brief key>/returned/` |
| Stage words come from the one stage list | `components/naming/stages.json` |
| Reuse a name that exists before making a new one | `roles.py resolve <name>` |

Names that were already in use each mean one role here. The seven hand-off roles in `components/handoff-standard/skill/roles.json` are how work arrives at a role, and each is claimed by exactly one role (`handoffs`). Older words for a role are listed under `also_called`. `roles.py resolve editor` prints `video-editor`.

## Use it

Say what you want in plain words; Claude runs these.

| You want | What runs |
|---|---|
| Is the role file true? | `roles.py check` |
| Which role does this name mean? | `roles.py resolve <name>` |
| Show me a role | `roles.py card <role>` |
| Start a role's agent | `roles.py agent <role> --brand <brand>` |
| This month's brief for a holder | `roles.py brief <role> --brand <brand>` |
| Set up roles for a new brand | copy `brands/_TEMPLATE/roles.json` into the brand folder and fill it |

`check` fails when a number has two owners, a listed tool has no owner or two, a name means two roles, a hand-off role or a stage owner lands on no role, a workflow folder is missing, or a role card has an empty part.

## Keys this tool needs

None.

## Changing it

Change `roles.json`, run `check`, then `template` so the brand template carries the same target names and calls. A number marked `"basis": "draft"` is a first proposal and waits for the owner's yes. `model.stops_today` lists every place the tools still stop for the owner and where each one lands under rule 5; moving a stop is done in the tool that owns it, on the owner's yes, never here.
