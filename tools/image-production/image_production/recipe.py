"""The recipe: the picture's variable sheet, and the gate that keeps a blank from reaching any door.

the owner, 2026-10-26: every picture must pass a check where EVERY variable is filled in (or explicitly "not applicable", with
a reason) before it reaches an image generator, so there are no unexpected pictures. The sheet and its validator are
written in components/model-inputs (`validate_recipe`, else `validate`); until a validator is there, the blank rule below
is the rule. A recipe maps a variable name to a value, or to {"na": "<reason>"}.
"""
from . import paths as P, route as R


class RecipeRefused(ValueError):
    """The picture's recipe is not complete: nothing was sent and nothing was spent."""


def _rules():
    import sys as _sys
    root = str(P.sibling("model-inputs"))
    if root not in _sys.path:
        _sys.path.append(root)
    import input_rules
    return input_rules


def is_filled(v):
    if isinstance(v, dict) and "na" in v:
        return False
    if v is None:
        return False
    if isinstance(v, (str, list, tuple, dict)):
        return bool(v if not isinstance(v, str) else v.strip())
    return True


def is_sheet_shape(recipe):
    """The prompt-generator's shape: {"brief": {...}, "sheet": {variable: {"state", "value", "reason", "source"}}}. The
    flat shape (variable -> value | {"na": reason}) is the engine's own."""
    return isinstance(recipe, dict) and isinstance(recipe.get("sheet"), dict)


_PREVIEW = []


def _preview():
    """components/model-inputs/preview.py (`validate`, `gate`), loaded by path. None when it cannot be loaded."""
    if not _PREVIEW:
        import importlib.util
        try:
            _rules()                                        # puts model-inputs on the path
            f = P.sibling("model-inputs", "preview.py")
            spec = importlib.util.spec_from_file_location("ip_mi_preview", f)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _PREVIEW.append(mod)
        except Exception:                                   # noqa: BLE001
            _PREVIEW.append(None)
    return _PREVIEW[0]


def validate_recipe(recipe):
    """Problems with a recipe, [] when it is complete. The sheet and its validator live in components/model-inputs
    (`validate_recipe`, else `validate`) when they exist; until then the rule is the blank rule: every variable is
    filled or says `{"na": "<reason>"}`. Never raises."""
    if not isinstance(recipe, dict):
        return ["the recipe must be a mapping of variable to value (or {'na': reason})"]
    if is_sheet_shape(recipe):                               # the variable sheet: its own validator is the rule
        mod = _preview()
        if mod is not None:
            # a chain run's cost approval is the chain's own production approval, not a person pressing Make: the chain
            # marks its recipe `_for_make: False`; a Bench recipe is validated with the person's approval included
            got = mod.validate(recipe, bool(recipe.get("_for_make", True)))
            return [str(x.get("say") if isinstance(x, dict) else x) for x in (got or [])]
        recipe = {k: ({"na": e.get("reason") or ""} if (e or {}).get("state") == "not_applicable" else
                      (e.get("value") if (e or {}).get("state") == "filled" else None))
                  for k, e in recipe["sheet"].items()}
    IR = _rules()
    fn = getattr(IR, "validate_recipe", None) or getattr(IR, "validate", None)
    if fn:
        got = fn(recipe)
        if got in (None, True, [], (), {}):
            return []
        if isinstance(got, dict):
            got = got.get("problems") or got.get("errors") or ([] if got.get("ok") else [str(got)])
        return [str(x.get("say") if isinstance(x, dict) else x) for x in (got if isinstance(got, (list, tuple)) else [got])]
    out = []
    for k, v in recipe.items():
        if isinstance(v, dict) and "na" in v:
            if not str(v["na"]).strip():
                out.append(f"{k}: not applicable needs a reason")
        elif not is_filled(v):
            out.append(f"{k} is blank: fill it, or mark it not applicable with a reason")
    return out


def required_for(t=None, scope="plain", purpose=None, edit=False, kind="picture"):
    """Whether this call must carry a recipe. `plain` (statics, carousels, the Bench) always, once the gate is on. The
    engine only for the purposes the table lists (`recipe_required_purposes`: ad, video-still) and only for a NEW picture:
    an edit of a picture is governed by its approved base and its own change request, and an email picture has no sheet."""
    if not R.recipe_required(t):
        return False
    if scope == "plain":
        return kind not in (((t or R.table()).get("gate") or {}).get("recipe_kinds_without_sheet") or [])
    purposes = ((t or R.table()).get("gate") or {}).get("recipe_required_purposes") or []
    return purpose in purposes and not edit


def gate(recipe, t=None, scope="plain", purpose=None, edit=False, kind="picture"):
    """The engine's refusal: a call whose recipe fails validate never reaches a door. With the gate on, no recipe is also
    refused (for the calls `required_for` names). Raises RecipeRefused naming every problem."""
    if recipe is None:
        if required_for(t, scope, purpose, edit, kind):
            raise RecipeRefused("tools/image-production refuses this picture: it carries no recipe (the variable "
                                "sheet), and every new picture must. Nothing was sent and nothing was spent.")
        return
    bad = validate_recipe(recipe)
    if bad:
        raise RecipeRefused("tools/image-production refuses this picture: the recipe is not complete: "
                            + "; ".join(bad) + ". Nothing was sent and nothing was spent.")


def na_of(recipe):
    """{variable: reason} for every not-applicable variable: left out of the prompt, kept in the record."""
    if is_sheet_shape(recipe):
        return {k: (e or {}).get("reason") for k, e in recipe["sheet"].items() if (e or {}).get("state") == "not_applicable"}
    return {k: v["na"] for k, v in (recipe or {}).items() if isinstance(v, dict) and "na" in v}


