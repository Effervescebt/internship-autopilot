import unittest

from autopilot import schedule


class QuotaTests(unittest.TestCase):
    def test_even_split(self):
        self.assertEqual(schedule.quotas([10, 21], 20), {10: 10, 21: 10})

    def test_remainder_goes_to_earliest_runs(self):
        self.assertEqual(schedule.quotas([21, 10, 15], 20), {10: 7, 15: 7, 21: 6})

    def test_single_run(self):
        self.assertEqual(schedule.quotas([10], 20), {10: 20})


class SlotTests(unittest.TestCase):
    def test_before_first_run(self):
        self.assertIsNone(schedule.current_slot(8, [10, 21]))

    def test_morning_slot(self):
        self.assertEqual(schedule.current_slot(15, [10, 21]), 10)

    def test_evening_slot(self):
        self.assertEqual(schedule.current_slot(23, [10, 21]), 21)

    def test_slot_name(self):
        self.assertEqual(schedule.slot_name(9), "09h")


class TargetTests(unittest.TestCase):
    def test_on_schedule(self):
        self.assertEqual(schedule.target(10, [10, 21], 20, done_today=0), 10)
        self.assertEqual(schedule.target(21, [10, 21], 20, done_today=10), 10)

    def test_evening_makes_up_missed_morning(self):
        self.assertEqual(schedule.target(21, [10, 21], 20, done_today=0), 20)

    def test_never_below_own_quota(self):
        self.assertEqual(schedule.target(21, [10, 21], 20, done_today=25), 10)


if __name__ == "__main__":
    unittest.main()
