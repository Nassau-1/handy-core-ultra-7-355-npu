import unittest

from validation_policy import accepted, words


class ValidationPolicyTests(unittest.TestCase):
    def test_only_case_and_punctuation_are_ignored(self):
        self.assertEqual(words('demain the deadline'), words('demain. The deadline'))
        for changed in ['demain the deadlines', 'demain deadline', 'demain the dead line',
                        'demain the 2 deadlines', 'demain thé deadline']:
            self.assertNotEqual(words('demain the deadline'), words(changed))

    def test_numeric_and_short_exact_checks_remain_required(self):
        good = dict(frontend_parity=True, lexical_equal=True, audio_samples=9600000,
                    tokens_equal=False, relative_l2_error=0.024, global_relative_l2_error=0.006)
        self.assertTrue(accepted(good))
        for key, value in [('frontend_parity', False), ('lexical_equal', False),
                           ('audio_samples', 640000), ('relative_l2_error', 0.03),
                           ('global_relative_l2_error', 0.01)]:
            self.assertFalse(accepted({**good, key:value}))
        self.assertFalse(accepted({}))


if __name__ == '__main__':
    unittest.main()
