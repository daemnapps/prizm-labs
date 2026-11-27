"""idea — the one wording of a research-route idea for every chain that reads an ask (public surface).

    import idea; text = idea.block(ask_record)      "" when the ask carries no `strategy`

An ask made by the research route carries `strategy` (CONTRACT.md). image-writing and video-writing put this block on
every writing step, so a swipe that lends the form never supplies the idea. No brand is named here.
"""


def block(rec):
    s = (rec or {}).get("strategy") or {}
    if not s.get("idea"):
        return ""
    form, out = s.get("form") or {}, []
    out += ["## THIS AD'S IDEA (research route: read this before anything else)", "",
            "This ad began with research, not with a swipe. Where this block differs from anything else in this prompt, THIS WINS:",
            "the swipe's idea, any concept, theme or holiday step, the headline rule that makes a concept talk, and the creative targets.",
            "A step that asks for a concept writes this idea there. A step that asks what the swipe keeps answers: its form only.", "",
            "- **Who:** %s" % s.get("who", ""), "- **Awareness (his, not the swipe's):** %s" % s.get("awareness", ""),
            "- **The insight:** %s" % s.get("insight", ""), "- **The idea:** %s" % s["idea"], "- **What it leaves in his head:** %s" % s.get("line", ""),
            "- **What we see:** %s" % s.get("see", ""), ""]
    if s.get("truths"):
        out += ["### What is true, with its receipt. Nothing else about him may be claimed", ""]
        out += ["- %s  [%s]" % (t.get("true", ""), t.get("receipt", "")) for t in s["truths"]] + [""]
    out += ["### How it is told", "", "- The headline is the idea in words he said. He reads it cold and knows it is about him.",
            "- Every other line adds one thing: what he is looking at, the cause, why the old way missed it, where to go.",
            "- The truth or the problem is the biggest thing in the picture, on skin like his. The art style is whatever says it best.",
            "- A joke, theme or holiday stays only when it makes him recognise himself faster.",
            "- Versions keep the idea and move to another symptom, moment or man, each with its own receipt."]
    if s.get("headlines"):
        out += ["- Start from these headlines, already read cold; their plainness is the bar, and the thinking above is never copy: " + " | ".join(s["headlines"])]
    if s.get("no_price"):
        out += ["- No price, discount or deadline on the piece: at this awareness level it is the wrong thing to say."]
    for f in s.get("not_cleared") or []:
        out += ["- Not cleared, never use: %s" % f]
    if form:
        out += ["", "### The form the swipe lends", "", "%s. It lends: %s. Nothing else of the swipe comes across." % (form.get("what", ""), form.get("lends", ""))]
    return "\n".join(out + ["", "## END OF THIS AD'S IDEA", ""])
