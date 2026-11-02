"""Driver and reboot gates are pure and testable without NPU hardware."""
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[2] / 'experiments/nemotron_npu/preflight.py'
spec = importlib.util.spec_from_file_location('preflight', path)
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


class PreflightTests(unittest.TestCase):
    def test_absent_old_malformed_and_newer_drivers(self):
        for version in [None, '', 'unknown', '32.0.100.4509', '32.0.100', '32.0.100.5539']:
            with self.subTest(version=version):
                self.assertIsNotNone(preflight.compatibility_error({'driver': version}))
        for version in ['32.0.100.5540', '32.0.100.6000', '33.0.1.1']:
            self.assertIsNone(preflight.compatibility_error({'driver': version}))

    def test_reboot_required_even_when_new_version_is_visible(self):
        info = {'driver': '32.0.100.5540', 'boot': 'boot1', 'pending_boot': 'boot1'}
        self.assertIn('Restart Windows', preflight.compatibility_error(info))
        info['boot'] = 'boot2'
        self.assertIsNone(preflight.compatibility_error(info))


if __name__ == '__main__':
    unittest.main()
