import sys, os, json
from playwright.sync_api import sync_playwright
url, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
steps = []
with sync_playwright() as pw:
    br = pw.chromium.launch(channel="chrome", headless=True)
    ctx = br.new_context(viewport={"width":390,"height":844}, device_scale_factor=2,
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
    pg = ctx.new_page()
    pg.goto(url, timeout=60000, wait_until="domcontentloaded"); pg.wait_for_timeout(2500)
    seen = set()
    for i in range(1, 25):
        txt = pg.inner_text("body").strip()
        key = txt[:120]
        if key in seen and i > 1:
            break
        seen.add(key)
        pg.screenshot(path=f"{out}/step-{i:02d}.png", full_page=True)
        open(f"{out}/step-{i:02d}.txt","w").write(txt)
        steps.append({"step": i, "text": txt})
        print(f"--- step {i} ---"); print(txt[:340]); print()
        # click the first plausible answer / advance control
        clicked = False
        for sel in ["button:visible", "[role=button]:visible", "a:visible", "label:visible", ".option:visible"]:
            els = pg.query_selector_all(sel)
            for e in els:
                t = (e.inner_text() or "").strip()
                if t and len(t) < 60 and not any(w in t.lower() for w in
                        ("privacy","terms","cookie","back","previous")):
                    try:
                        e.click(timeout=3000); clicked = True; break
                    except Exception:
                        continue
            if clicked: break
        if not clicked:
            # loader screens auto-advance with no control; wait them out
            pg.wait_for_timeout(7000)
            if pg.inner_text("body").strip()[:120] != key:
                continue
            print("[no advance control — funnel ends here]"); break
        pg.wait_for_timeout(2200)
    br.close()
json.dump(steps, open(f"{out}/steps.json","w"), indent=1)
print(f"captured {len(steps)} steps -> {out}")
