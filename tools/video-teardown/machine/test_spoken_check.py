"""Every word in a spoken line is a word (2026-10-01): a transcript's stumble never reaches a voice."""
import spoken_check as sc

bad = ["So see how that really br- br- that little bit makes a huge difference.",
       "So see how that really br, br, that little bit makes a huge difference.",
       "Um-", "and th- th- then"]
good = ["Mm-hmm. Mm-hmm.", "No. No, no.", "Um...", "It's not, okay, it's not the sunscreen.",
        "So see how that really... that little bit makes a huge difference.", "Buy 2, get 1 free.",
        "A well-known, long-lasting scrub.", "Twice a week, a big tablespoon, sixty seconds."]
for t in bad:
    assert sc.fragments(t), t
for t in good:
    assert not sc.fragments(t), (t, sc.fragments(t))
assert [r["id"] for r in sc.check_lines([("S1", good[0]), ("S2", bad[1])])] == ["S2"]
print("OK")
