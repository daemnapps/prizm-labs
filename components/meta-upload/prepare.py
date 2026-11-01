#!/usr/bin/env python3
"""Steps 2 and 3 of the drop: images into the library, ad sets into the account.

    prepare.py --brand <brand> --kit <dir> --campaign-id <id>

Does the two things the bulk sheet does badly and the API does well, then
writes the two files that make the sheet a single text file:

    <kit>/hashes.json     ad name  -> image hash
    <kit>/adsets.json     ad set name -> its id

Feed both back to `build.py --hashes ... --adset-ids ...` and the rebuilt
sheet needs no images folder, creates no duplicate ad sets, and creates no
duplicate campaign.

**Why the API and not the sheet.** Two reasons, both learned on 2026-09-11:

  images    Uploading files with the sheet is capped at 10 MB per browser
            upload. A 51 MB drop is eight chunks, and every chunk is another
            chance for Meta to make a second campaign. By hash it is one
            158 KB text file. Re-uploading the same bytes returns the same
            hash, so this is safe to re-run.

  ad sets   The template has no pixel column and no conversion-event column,
            so an ad set the sheet creates arrives without either and has to
            be fixed by hand, one at a time. An ad set created here carries
            `promoted_object` from birth.

Resumable: everything already done is read back from the two files and
skipped, so a network failure costs only what had not finished.

Nothing here names a brand. Account, Page, pixel, targeting and the
conversion event all come from `brands/<brand>/meta/account.json`.
"""
import argparse, csv, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from brand import Brand
from meta import Meta


def targeting(b):
    """Broad, always. The avatar is creative separation, not who we buy.

    Splitting ad sets by avatar and by the man in the picture makes Meta show
    each of them; it is not a statement about who should see them. Every ad
    set in every brand goes out on the brand's countries, its age band and
    nothing else.
    """
    return {
        "age_min": b.age[0], "age_max": b.age[1],
        "geo_locations": {"countries": b.countries,
                          "location_types": ["frequently_in", "home", "recent"]},
        "publisher_platforms": b.platforms,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--kit", required=True, help="a dir build.py wrote")
    ap.add_argument("--campaign-id", required=True,
                    help="the campaign the ad sets hang under")
    ap.add_argument("--images-only", action="store_true")
    ap.add_argument("--adsets-only", action="store_true")
    a = ap.parse_args()

    b = Brand(a.brand)
    m = Meta(b)
    kit = Path(a.kit)
    rows = list(csv.DictReader((kit / "import.csv").open(encoding="utf-8-sig")))
    print(f"{b} · {len(rows)} rows")

    hf, af = kit / "hashes.json", kit / "adsets.json"
    hashes = json.loads(hf.read_text()) if hf.is_file() else {}
    adsets = json.loads(af.read_text()) if af.is_file() else {}

    # -- ad sets ----------------------------------------------------------
    if not a.images_only:
        for name in dict.fromkeys(r["Ad Set Name"] for r in rows):
            if name in adsets:
                continue
            res = m.post(f"act_{m.ACCOUNT}/adsets",
                         name=name, campaign_id=a.campaign_id, status="PAUSED",
                         billing_event="IMPRESSIONS",
                         optimization_goal=b.optimization_goal,
                         destination_type="UNDEFINED",
                         targeting=targeting(b),
                         promoted_object={"pixel_id": b.pixel_id,
                                          "custom_event_type": b.conversion_event},
                         attribution_spec=[{"event_type": "CLICK_THROUGH",
                                            "window_days": 7}])
            adsets[name] = res["id"]
            af.write_text(json.dumps(adsets, indent=1))
            print(f"  ad set  {name} -> {res['id']}", flush=True)

    # -- images -----------------------------------------------------------
    # Keyed by ad name, which is what build.py's --hashes expects, but the
    # upload is keyed by file: two ads never share a picture in this pipeline,
    # and if they ever did, Meta would return the same hash anyway.
    if not a.adsets_only:
        for i, r in enumerate(rows, 1):
            if r["Ad Name"] in hashes:
                continue
            f = r.get("Image File Name")
            if not f:
                continue                      # already bound by hash upstream
            hashes[r["Ad Name"]] = m.upload_image(kit / "images" / f,
                                                  name=r["Ad Name"][:100])
            hf.write_text(json.dumps(hashes, indent=1))
            if i % 10 == 0:
                print(f"  images  {i}/{len(rows)}", flush=True)

    print(f"\n{len(adsets)} ad sets -> {af}")
    print(f"{len(hashes)} hashes  -> {hf}")
    print(f"\nrebuild the sheet with:\n"
          f"  build.py --brand {b.name} --lane <lane> --run <run> --out <dir> \\\n"
          f"      --hashes {hf} --adset-ids {af} --campaign-id {a.campaign_id}")


if __name__ == "__main__":
    main()
