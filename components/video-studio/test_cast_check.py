import sys,unittest; sys.path.insert(0,__import__('os').path.dirname(__file__)); import swipe_cut as S
P={"shots":{"a":{"source":"x","role":"LEAD"},"b":{"source":"y","role":"GIRL"},"c":{"source":"z"}},
   "sources":{"x":"/d/Sean Cornwall/1.mov","y":"/d/Sean Cornwall/2.mov","z":"/d/other/3.mov"},
   "people":{"cast":{"LEAD":"Sean Cornwall","GIRL":"Sean Cornwall"}}}
SC={"S1":[{"id":"a"},{"id":"b"},{"id":"c"}]}
class T(unittest.TestCase):
    def test_ok(self): S.cast_check(P,SC,{},True)
    def test_story_needs_cast(self):
        with self.assertRaises(SystemExit): S.cast_check({"shots":{}},SC,{},True)
    def test_not_story_fine(self): S.cast_check({"shots":{}},SC,{},False)
    def test_wrong_creator(self):
        import copy;q=copy.deepcopy(P);q["shots"]["c"]["role"]="LEAD"
        with self.assertRaises(SystemExit): S.cast_check(q,SC,{},True)
    def test_missing_role(self):
        import copy;q=copy.deepcopy(P);del q["shots"]["b"]["role"]
        with self.assertRaises(SystemExit): S.cast_check(q,SC,{},True)
if __name__=='__main__': unittest.main()
