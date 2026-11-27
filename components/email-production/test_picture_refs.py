"""picture_refs: every picture an email asks for is found, and a relative one is a problem (email_lead, 2026-11-13).

The case is brand_b-nov-10a's hero as it went out on 2026-11-12: a background picture with a live button on top,
its <img>s and Outlook copy hosted, its background attribute and CSS url() still at assets/s02.jpg. No network.
"""
import re
import unittest

import picture_refs as P

HOSTED = "https://cdn.klaviyomail.com/company/X/images/"
SENT = ('<img src="%slogo.jpeg" width="600">'
        '<!--[if gte mso 9]><v:rect><v:fill type="frame" src="%shero.jpeg" color="#D9D8CF"/><![endif]-->'
        '<td bgcolor="#D9D8CF" background="assets/s02.jpg" style="background-color:#D9D8CF;'
        'background-image:url(assets/s02.jpg);background-size:cover">'
        '<a href="https://shop.example/x" class="cta-btn">SEE THE FACE SCRUB</a></td>'
        '<img src="%sgrid.jpeg">') % (HOSTED, HOSTED, HOSTED)
BUILT = ('<img src="assets/s01.jpg" width="600">'
         '<!--[if gte mso 9]><v:rect><v:fill type="frame" src="assets/s02.jpg" color="#D9D8CF"/><![endif]-->'
         '<td bgcolor="#D9D8CF" background="assets/s02.jpg" style="background-image:url(assets/s02.jpg)">x</td>'
         '<img src="assets/s03.jpg">')


class PictureRefs(unittest.TestCase):
    def test_every_kind_is_found(self):
        kinds = [k for k, _ in P.refs(SENT)]
        self.assertEqual(kinds, ["img", "outlook picture", "background attribute", "css url()", "img"])

    def test_the_sent_hero_is_held(self):
        probs = P.problems(SENT, fetch=False)
        self.assertEqual(len(probs), 2)
        self.assertTrue(all("assets/s02.jpg" in p for p in probs))

    def test_fully_hosted_passes(self):
        fixed = re.sub(r"(?<=[\"'(])assets/s02\.jpg(?=[\"')])", HOSTED + "hero.jpeg", SENT)
        self.assertEqual(P.problems(fixed, fetch=False), [])
        self.assertEqual(P.missing_from(BUILT, fixed), [])

    def test_a_dropped_picture_is_named(self):
        dropped = SENT.replace('<img src="%sgrid.jpeg">' % HOSTED, "")
        self.assertEqual(P.missing_from(BUILT, dropped), ["the build has 2 img picture(s), the hosted email 1"])

    def test_merge_tags_and_data_are_left_alone(self):
        self.assertEqual(P.refs('<img src="{{ organization.logo }}"><img src="data:image/png;base64,AA">'), [])


if __name__ == "__main__":
    unittest.main()
