"""The Generative Model House reader — every generative tool asks here which model does a job (the owner, 2026-10-20).

    import model_house as MH
    MH.model("pictures.edit")          -> {"model": "gpt-image-2.5-sunburst", "door": "openai", "registry_id": ...}
    MH.model("clips.seedance")["id"]   -> the clip model id
    MH.choices("pictures.edit")        -> the house default first, then every eligible registry model, one per door
    MH.pick("pictures.edit", "seedream-5-pro-edit@fal")  -> a PERSON's explicit pick, its key checked
    MH.house()                         -> the whole models.json, as written (registry ids, not vendor names)

    python3 model_house.py                              # print the house
    python3 model_house.py pictures.generate            # one job
    python3 model_house.py --choices pictures.edit      # what a person may pick for it

THE RULE: a TOOL calls model(job) and gets the house default, only. A tool never picks a non-default model on its
own — not for cost, not because a key is missing. Only a PERSON's explicit pick goes through pick().

Each job names its model by REGISTRY ID (components/models/models.json), with the door it is sold through and the
capability it needs (MDL-8 (registry-linked house), 2026-10-22). model(job) answers what it always answered — the
vendor's name under `model` (pictures, sound, behind rows) or `id` (clips, swipe_footage rows), a bare string for
behind.judge / upscale / 3d, a list under `models` for behind.judge_busy — now resolved from the registry for the
row's door, and every dict answer ADDS `registry_id`, `key_env`, `transport` and `cost`. A registry id the registry
lacks, a deprecated one, a door the entry does not sell or a capability it does not have is refused by name, never
answered with a guess. `purpose` on choices() is accepted and ignored today: it is the seam for ranking by logged
evidence, a later card.

Stdlib only, no credential, writes nothing. The rule people read is MODEL-HOUSE.md beside this file.
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOUSE = HERE / "models.json"
RULE = HERE / "MODEL-HOUSE.md"
REGISTRY = HERE.parent / "models" / "models.json"

# Today's return shape, frozen for every caller (MDL-8 (registry-linked house)): these jobs answered a bare
# string before the registry link, and still do. Every other row answers a dict.
_BARE = ("behind.judge", "behind.upscale", "behind.3d")
# The key a row's vendor name sits under, by section; any other section uses "model".
_ID_KEY = {"clips": "id", "swipe_footage": "id"}


def house() -> dict:
    return json.loads(HOUSE.read_text())


def registry() -> dict:
    """components/models/models.json, the registry every house job names its model in."""
    return json.loads(REGISTRY.read_text())


def _is_row(node) -> bool:
    return isinstance(node, dict) and "registry" in node


def _own_door(entry: dict) -> str:
    return "local" if entry.get("transport") == "local" else entry.get("vendor")


def doors_of(entry: dict) -> dict:
    """{door: {"vendor_id", "key_env"}} for every door that sells a registry entry. `doors`, when the entry
    declares it, is the whole list; otherwise the entry is sold at its own door under its top-level names."""
    if isinstance(entry.get("doors"), dict) and entry["doors"]:
        return {d: {"vendor_id": (s.get("vendor_id") or entry["id"]), "key_env": s.get("key_env")}
                for d, s in entry["doors"].items()}
    return {_own_door(entry): {"vendor_id": entry.get("vendor_id") or entry["id"], "key_env": entry.get("key_env")}}


def _entry(job: str, rid: str, door: str, capability: str, models: dict) -> dict:
    """The registry entry a house row names, and its door — refused by name when it cannot be used."""
    entry = models.get(rid)
    if entry is None:
        raise KeyError(f"the Generative Model House job '{job}' names registry id '{rid}', which {REGISTRY} does "
                       f"not have — see {RULE}")
    if entry.get("status") == "deprecated":
        raise KeyError(f"the Generative Model House job '{job}' names registry id '{rid}', which the registry has "
                       f"deprecated — the house must name another model; see {RULE}")
    sold = doors_of(entry)
    if door not in sold:
        raise KeyError(f"the Generative Model House job '{job}' names registry id '{rid}' at door '{door}', which "
                       f"that entry does not sell (its doors: {', '.join(sorted(sold))}) — see {RULE}")
    if capability not in (entry.get("capability") or []):
        raise KeyError(f"the Generative Model House job '{job}' needs '{capability}', which registry id '{rid}' "
                       f"does not list in its capability — see {RULE}")
    return entry


def _resolve(job: str, row: dict, models: dict):
    """One house row, answered in today's shape with the vendor's name for the row's door."""
    door, capability = row.get("door"), row.get("capability")
    ids = row["registry"] if isinstance(row["registry"], list) else [row["registry"]]
    entries = [_entry(job, rid, door, capability, models) for rid in ids]
    vendor = [doors_of(e)[door]["vendor_id"] for e in entries]
    if job in _BARE:
        return vendor[0]
    out = dict(row)
    if isinstance(row["registry"], list):
        out["models"] = vendor
        out["registry_id"] = list(ids)
        out["key_env"] = [doors_of(e)[door]["key_env"] for e in entries]
        out["transport"] = [e.get("transport") for e in entries]
        out["cost"] = [e.get("cost") for e in entries]
        return out
    out[_ID_KEY.get(job.split(".")[0], "model")] = vendor[0]
    out["registry_id"] = ids[0]
    out["key_env"] = doors_of(entries[0])[door]["key_env"]
    out["transport"] = entries[0].get("transport")
    out["cost"] = entries[0].get("cost")
    return out


def _resolve_tree(path: str, node, models: dict):
    if _is_row(node):
        return _resolve(path, node, models)
    if isinstance(node, dict):
        return {k: _resolve_tree(f"{path}.{k}", v, models) for k, v in node.items()}
    return node


def _models() -> dict:
    return {m["id"]: m for m in registry().get("models", []) if isinstance(m, dict) and "id" in m}


def model(job: str):
    """A job is a dotted path into models.json, e.g. 'pictures.edit', 'clips.seedance', 'sound.voice'.
    An unknown job is refused by name, never answered with a guess. The answer is the house default — the only
    model a tool may use without a person's pick."""
    node, models, walked = house(), None, []
    for part in job.split("."):
        if _is_row(node):
            models = models or _models()
            node = _resolve(".".join(walked), node, models)
        if not isinstance(node, dict) or part not in node:
            raise KeyError(f"the Generative Model House has no job '{job}' — see {RULE}")
        node = node[part]
        walked.append(part)
    if _is_row(node) or isinstance(node, dict):
        return _resolve_tree(job, node, models or _models())
    return node


def _row(job: str) -> dict:
    node = house()
    for part in job.split("."):
        if not isinstance(node, dict) or part not in node:
            raise KeyError(f"the Generative Model House has no job '{job}' — see {RULE}")
        node = node[part]
    if not _is_row(node):
        raise KeyError(f"the Generative Model House names no model for '{job}' — see {RULE}")
    return node


def _choice(entry: dict, door: str, reason: str) -> dict:
    spec = doors_of(entry)[door]
    return {"registry_id": entry["id"], "vendor_id": spec["vendor_id"], "door": door,
            "key_env": spec["key_env"], "status": entry.get("status"), "reason": reason}


def choices(job: str, purpose=None) -> list:
    """What a PERSON may pick for a job: the house default first (reason "house default"), then every
    non-deprecated registry model whose capability includes the job's, one per door, ordered by registry id then
    door (reason "eligible: <capability>"). `purpose` is accepted and ignored today — the seam for ranking by
    logged evidence (a later card)."""
    row, models = _row(job), _models()
    door, capability = row.get("door"), row.get("capability")
    ids = row["registry"] if isinstance(row["registry"], list) else [row["registry"]]
    out = [_choice(_entry(job, rid, door, capability, models), door, "house default") for rid in ids]
    taken = {(c["registry_id"], c["door"]) for c in out}
    for rid in sorted(models):
        entry = models[rid]
        if entry.get("status") == "deprecated" or capability not in (entry.get("capability") or []):
            continue
        for d in sorted(doors_of(entry)):
            if (rid, d) not in taken:
                out.append(_choice(entry, d, f"eligible: {capability}"))
    return out


def _label(c: dict) -> str:
    return f"{c['registry_id']}@{c['door']}"


def pick(job: str, model=None, env=None) -> dict:
    """A PERSON's explicit pick for a job, resolved: `model` is a registry id, or `<registry id>@<door>` when the
    id is sold at more than one door; None means the house default. A model not in choices(job) is refused by
    name; so is a pick whose door key is not in `env` (os.environ by default) — never silently swapped."""
    options = choices(job)
    if model is None:
        found = [c for c in options if c["reason"] == "house default"]
        if len(found) != 1:
            raise KeyError(f"'{job}' names an ordered list of models ({', '.join(_label(c) for c in found)}); "
                           f"pick one by name")
    else:
        rid, _, door = str(model).partition("@")
        found = [c for c in options if c["registry_id"] == rid and (not door or c["door"] == door)]
        if not found:
            raise KeyError(f"'{model}' is not a choice for '{job}' — its choices: "
                           f"{', '.join(_label(c) for c in options)}")
        if len(found) > 1:
            raise KeyError(f"'{model}' is sold at more than one door for '{job}' — say which: "
                           f"{', '.join(_label(c) for c in found)}")
    chosen = dict(found[0])
    env = os.environ if env is None else env
    keys = chosen["key_env"] if isinstance(chosen["key_env"], list) else (
        [chosen["key_env"]] if chosen["key_env"] else [])
    missing = [k for k in keys if not env.get(k)]
    if missing:
        raise KeyError(f"{_label(chosen)} needs {' and '.join(missing)}, which this machine does not have")
    entry = _models()[chosen["registry_id"]]
    chosen.update(job=job, capability=_row(job).get("capability"), transport=entry.get("transport"),
                  cost=entry.get("cost"))
    return chosen


def main(argv=None) -> int:
    a = list(sys.argv[1:] if argv is None else argv)
    if a[:1] == ["--choices"] and len(a) == 2:
        print(json.dumps(choices(a[1]), indent=1, ensure_ascii=False))
        return 0
    print(json.dumps(model(a[0]) if a else house(), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
