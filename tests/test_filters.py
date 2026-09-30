import unittest

from autopilot import filters

CFG = {
    "search": {"title_must_match": [r"\bintern"],
               "title_exclude": [r"\b(fall|spring|winter)\b(?!.*\bsummer\b)", r"\bphd\b", r"\bsenior\b"]},
    "eligibility": {"us_only": True, "skip_citizenship_required": True, "skip_if_f1_excluded": True,
                    "skip_phd_only": True, "note_no_sponsorship": True, "extra_skip_patterns": []},
}


def posting(title="Software Engineer Intern", sponsorship=""):
    return {"title": title, "sponsorship": sponsorship}


class TitleAndLocationTests(unittest.TestCase):
    def test_title_filters(self):
        self.assertTrue(filters.title_ok("Software Engineer Intern - Summer 2027", CFG))
        self.assertFalse(filters.title_ok("Senior Software Engineer", CFG))
        self.assertFalse(filters.title_ok("Fall 2026 Software Intern", CFG))
        self.assertTrue(filters.title_ok("Fall/Summer Software Intern", CFG))

    def test_us_location(self):
        self.assertTrue(filters.location_ok("Seattle, WA; NYC", CFG))
        self.assertTrue(filters.location_ok("Remote in USA", CFG))
        self.assertFalse(filters.location_ok("London, UK", CFG))

    def test_role_type(self):
        self.assertEqual(filters.role_type("Machine Learning Engineer Intern"), "MLE")
        self.assertEqual(filters.role_type("Data Scientist Intern"), "Data")
        self.assertEqual(filters.role_type("Research Intern, Robotics"), "Research")
        self.assertEqual(filters.role_type("Backend Engineer Intern"), "SWE")


class EligibilityTests(unittest.TestCase):
    def check(self, jd, sponsorship=""):
        return filters.eligibility(posting(sponsorship=sponsorship), jd, CFG)

    def test_citizenship_required(self):
        self.assertIsNotNone(self.check("Candidates must be a U.S. citizen.")[0])
        self.assertIsNotNone(self.check("", sponsorship="U.S. Citizenship is Required")[0])

    def test_clearance_required(self):
        self.assertIsNotNone(self.check("An active secret clearance is required.")[0])

    def test_f1_excluded(self):
        self.assertIsNotNone(self.check("This position is not eligible for F1 and J1 students.")[0])

    def test_phd_only(self):
        self.assertIsNotNone(self.check("You must be currently pursuing a PhD in Computer Science.")[0])
        self.assertIsNone(self.check("Currently enrolled in a PhD or Master's program.")[0])

    def test_no_sponsorship_is_kept_with_note(self):
        reason, note = self.check("We will not sponsor visas for this role.")
        self.assertIsNone(reason)
        self.assertIn("CPT", note)

    def test_cpt_welcome_note(self):
        reason, note = self.check("F-1 students are eligible if they are using CPT.")
        self.assertIsNone(reason)
        self.assertIn("eligible", note)


if __name__ == "__main__":
    unittest.main()
