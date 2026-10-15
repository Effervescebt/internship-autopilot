import shutil
import unittest

from autopilot import skills


class OrderingTests(unittest.TestCase):
    def test_mentions(self):
        self.assertTrue(skills.mentions("C/C++", "experience with c++ required"))
        self.assertTrue(skills.mentions("Large Language Models (LLMs)", "work on llms"))
        self.assertFalse(skills.mentions("Java", "javascript only"))

    def test_jd_items_first_and_extras_only_when_asked(self):
        g = {"label": "Languages", "items": ["Python", "Go", "SQL"], "extra": ["MATLAB", "Scala"]}
        wanted, items = skills.ordered_items(g, "sql and matlab")
        self.assertEqual(wanted, ["SQL", "MATLAB"])
        self.assertEqual(items, ["SQL", "MATLAB", "Python", "Go"])


@unittest.skipUnless(shutil.which("pdflatex"), "needs LaTeX")
class FittingTests(unittest.TestCase):
    def test_long_line_is_cut_to_one_line_keeping_jd_items(self):
        many = [f"Skill{i:02d}" for i in range(40)]
        g = {"label": "Tools", "items": many}
        lines, shown, missing = skills.fit_groups([g], "we need skill39")
        self.assertEqual(len(lines), 1)
        self.assertEqual(shown[0], "Skill39")
        self.assertLess(len(shown), 40)
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
