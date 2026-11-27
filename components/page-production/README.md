# page-production

**The written page, laid out and built in the brand's design, with pictures from image production.**

    python3 machine/pictures.py --brand <brand> --label <label>    # each picture slot -> a filed 3D print, or a 3D print request
    python3 machine/build.py --brand <brand> --label <label>       # site/index.html + img/ + fonts/
    python3 machine/chain_page.py <brand>/<label> [<brand>/<label> ...] --out <dir>   # every stage on one page

Pictures: every picture comes from image production's 3D process (scene built at true sizes in 3D Jutsu, printed,
filed under `runs/image-production/<brand>/sets/`). `pictures.py` matches each slot to a kept print
(`prompts/pictures-vN-owner.md`); a slot nothing fits is filed in image production's 3D print queue
(`image_production/set_queue.py`, cleared by the 3d-print skill) and the built page shows a marked frame with what the
print must hold until it lands. Nothing is generated here.

Design: the brand's own token table (`brands/<brand>/brand-identity/web-tokens.md`, read by token name), its web fonts
(`brand-identity/web-fonts/fonts.json` + files) and its logo. Agnostic: no brand is named in the code.

Nothing is deployed. Going live is a separate step through the brand's funnel repo.
