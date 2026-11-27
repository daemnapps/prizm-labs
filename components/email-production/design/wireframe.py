"""A wireframe the team page can show before any picture exists (editor, 2026-11-20).

    wireframe.make(brand, run_dir)    design/wireframe/email.html + card.json, drawn from design/email.json with
                                      "PICTURE TO MAKE" boxes; nothing under klaviyo/ is written, ever.

The team page (adapter/sync.py) lists an email from its built version. A wireframe has no built version, because the build
refuses while a picture is still to make. So the layout step also writes this folder, and the page shows it, marked held, until a
real build (klaviyo/email.html, newer than design/email.json) takes its place. It is never uploaded to Klaviyo and never approvable:
its card carries a designer hold, "the pictures are not made yet". Stdlib only.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOLD = "Wireframe: the pictures are not made yet. Give the art direction and make the pictures; the built email then replaces this."


def make(brand, run_dir, lk=None):
    import engine as EN
    import look as L
    run_dir = Path(run_dir)
    spec = json.loads((run_dir / "design" / "email.json").read_text())
    lk = lk or L.load(brand, run_dir)
    secs = EN.sections(spec, lk)
    th = spec.get("theme")
    head = "<style>%s\n%s .pk{display:none}</style>" % (EN.fonts(lk), EN.css(lk, th))
    rows = "".join('<tr data-sec="%d"><td style="padding:0"><div class="em%s%s" style="width:400px;zoom:1.5;margin:0">%s</div></td></tr>'
                   % (i, (" th-%s" % th) if th else "", EN.root_classes(lk), h) for i, (_, h) in enumerate(secs))
    page = ('<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=600"><body style="margin:0;background:#fff">%s'
            '<table class="wrap" width="600" cellpadding="0" cellspacing="0" style="width:600px;margin:0 auto;border-collapse:collapse"><tbody>%s</tbody></table></body>'
            % (head, rows))
    out = run_dir / "design" / "wireframe"
    out.mkdir(parents=True, exist_ok=True)
    (out / "email.html").write_text(page)
    base = {}
    old = run_dir / "klaviyo" / "card.json"
    if old.is_file():                    # keep the card's words (subject, date, audience); never its hold or its Klaviyo state
        try:
            base = {k: v for k, v in json.loads(old.read_text()).items()
                    if k in ("brand", "label", "date", "send_local", "recipient_time_zone", "kind", "format", "theme", "concept", "culture",
                             "audience", "segments", "subjects", "links")}
        except ValueError:
            base = {}
    base.setdefault("brand", brand)
    base.setdefault("label", run_dir.name)
    base.setdefault("date", spec.get("date"))
    base.setdefault("subjects", [{"subject": spec.get("subject") or "", "preview": spec.get("preview") or ""}])
    base.update({"wireframe": True, "status": "wireframe", "pictures": [], "product_check": [],
                 "final_check": [{"result": "problem", "about": "picture", "detail": HOLD}]})
    (out / "card.json").write_text(json.dumps(base, indent=1, ensure_ascii=False) + "\n")
    return out
