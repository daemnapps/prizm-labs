#!/usr/bin/env python3
"""ad_sets — which ad sets a new ad may go into.

    ad_sets.py --brand <b>                     every open ad set, and why it is open
    ad_sets.py --brand <b> --avatar <a>        every brand angle, open or closed for that avatar

the owner, 2026-10-27: "our campaign is established so most new ads will go into
existing ad sets unless a new angle or avatar is clearly defined."

An ad set is OPEN when
  - it already takes ads: we have put an ad into it (runs/meta-upload/<brand>/ids.json,
    which every upload writes), or
  - the owner signed it new: its name is on `new_ad_sets` in brands/<brand>/meta/account.json, or
  - it is a promo ad set (`..._promo`: promo ads get their own, the owner 24 Oct 2026).
Nothing else is. The angle picker only picks angles whose ad set is open, the card's
ad set check fails on a closed one and says so, and the uploader never makes one.
Reads files only — never the ad account.
"""
import argparse, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from brand import Brand  # noqa: E402
import naming as NM  # noqa: E402

PROMO = "promo"


def live(brand, runs_root=None):
    """Ad set names we have put ads into, any campaign of the brand."""
    import upload as U
    _, ids = U.known_ids(brand, runs_root)
    return {k.split("|", 1)[1] for k in ids.get("ad_sets", {}) if "|" in k}


def signed(brand):
    """Ad set names the owner signed to open (account.json `new_ad_sets`)."""
    return set(Brand(brand).d.get("new_ad_sets") or [])


def name_for(brand, avatar, angle):
    """The ad set an avatar + angle goes into, by the brand's own template."""
    b = Brand(brand)
    nm = b.naming
    return NM.render(nm["ad_set"], {"brand": b.name, "avatar": avatar, "angle": angle},
                     NM.sep_for(nm, "ad_set"), b.pretty)


def is_promo(brand, name):
    return str(name or "").endswith(NM.sep_for(Brand(brand).naming, "ad_set") + PROMO)


def why_closed(brand, name, runs_root=None):
    """None when a new ad may go into `name`; else the reason, in plain words."""
    if not name:
        return "no ad set"
    if name in live(brand, runs_root) or name in signed(brand) or is_promo(brand, name):
        return None
    return (f"{name} is not open in Meta — new ads go into the ad sets already running; "
            f"a new one opens only when the owner signs it (new_ad_sets in brands/{brand}/meta/account.json)")


def open_angles(brand, avatar, angles, runs_root=None):
    """The angle ids, of `angles`, whose ad set for this avatar is open."""
    return [a for a in angles if why_closed(brand, name_for(brand, avatar, a), runs_root) is None]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--avatar")
    a = ap.parse_args()
    if a.avatar:
        sys.path.append(str(HERE.parent / "naming"))
        import names as N
        # every brand angle can be aimed at any avatar (the owner, 28 Oct 2026); the ad set is avatar × angle
        bank = [x["id"] for x in (N.signed_angles(a.brand) or {}).values() if not x.get("misfiled")]
        for x in dict.fromkeys(bank):
            print(f"{'open  ' if x in open_angles(a.brand, a.avatar, [x]) else 'closed'}  {x}")
        return
    for n in sorted(live(a.brand)):
        print(f"running  {n}")
    for n in sorted(signed(a.brand) - live(a.brand)):
        print(f"signed   {n}")


if __name__ == "__main__":
    main()
