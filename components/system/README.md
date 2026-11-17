# system

The system's own definition: its words, every component placed once, and the check that keeps anything new connected. Brand-agnostic.

```
Workflow › Stage › Component › Chain › Step
```

A workflow is the components that make one type of output, in order. A stage is a component's place in that order. A component is one folder that does one job. A chain is the steps inside a component. A step is one prompt or action.

## What is here

| File | What it is |
|---|---|
| `system.json` | The words. One word, one meaning, where its list lives, and the other uses to retire |
| `components.json` | Every component, once: its kind, what it does, the role that owns it, its workflow and stage |
| `system.py` | The check, and the look-ups |

The roles are in `components/roles/`. A component names its role here, once; the role file does not list components.

## The words

24 operating words. Where a meaning was already written down it is taken as written, and `source` says where. Where written sources disagree, `disagreements` lists the sides and this file's pick; each one is the owner's call.

This file does not define the creative words (angle, concept, framework, format, hook). Their home is named under `elsewhere`.

A use listed under `retire` is renamed in the place that owns it, on the owner's yes. Nothing is renamed from here.

## How anything new joins

Nothing joins the system without one row in `components.json`. The row is the connection.

| A row says | |
|---|---|
| `path` | the folder |
| `kind` | tool, engine, library or definitions |
| `does` | what it does, in a few words |
| `role` | the role that owns it |
| `workflow` | video, image, email, page, every workflow, or the system itself |
| `stage` | where in the workflow |
| `steps` | the named steps inside it, if any |

`"basis": "draft"` marks a row placed as a first proposal.

## Use it

Say what you want in plain words; Claude runs these.

| You want | What runs |
|---|---|
| Is everything connected, named once, owned once? | `system.py check` |
| What does this word mean here? | `system.py word <term>` |
| What does a new component need before it joins? | `system.py place <folder>` |
| Show every component by workflow and stage | `system.py map` |

`check` fails when a folder has no row, a row has no folder, a row names a role, workflow, stage or kind that does not exist, two rows claim one folder, a listed tool is missing, or a word is given two meanings. It also runs the role check.

## Keys this tool needs

None.
