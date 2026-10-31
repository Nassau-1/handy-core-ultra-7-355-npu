import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from runtime import serve


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.calls = []

        def transcribe(processor, audio, language):
            self.calls.append((audio.copy(), language))
            return 'été forecast', {'end_to_end_seconds': 0.01}

        self.runtime = SimpleNamespace(meta={'frames': 1024}, device='NPU',
            predictor_device='NPU', joint_device='NPU', transcribe=transcribe)

    def run_worker(self, data, error=None):
        output = io.BytesIO()
        with patch('sys.stdin', SimpleNamespace(buffer=io.BytesIO(data))):
            if error:
                with self.assertRaises(error):
                    serve(self.runtime, None, output)
            else:
                serve(self.runtime, None, output)
        return [json.loads(line) for line in output.getvalue().decode('utf-8').splitlines()]

    def test_persistent_utf8_and_language_requests(self):
        pcm = np.array([0.1, -0.3], dtype='<f4').tobytes()
        result = self.run_worker(b'{"samples":2,"language":"<|fr|>"}\n'+pcm+
                                 b'{"samples":2}\n'+pcm)
        self.assertEqual(result[0]['device'], 'NPU')
        self.assertEqual([r['text'] for r in result[1:]], ['été forecast', 'été forecast'])
        self.assertEqual([language for _, language in self.calls], ['fr', 'auto'])

    def test_oversized_audio_is_rejected_without_truncation(self):
        result = self.run_worker(b'{"samples":163681}\n', ValueError)
        self.assertFalse(result[-1]['ok'])
        self.assertEqual(self.calls, [])

    def test_truncated_frame_does_not_reach_inference(self):
        result = self.run_worker(b'{"samples":2}\n'+b'\0'*4, EOFError)
        self.assertIn('Truncated', result[-1]['error'])
        self.assertEqual(self.calls, [])

    def test_nonfinite_pcm_does_not_reach_inference(self):
        result = self.run_worker(b'{"samples":1}\n'+np.array([np.nan], dtype='<f4').tobytes(), ValueError)
        self.assertIn('finite', result[-1]['error'])
        self.assertEqual(self.calls, [])

    def test_translation_cannot_be_silently_ignored(self):
        result = self.run_worker(b'{"samples":1,"translate":true}\n'+b'\0'*4, ValueError)
        self.assertIn('translation', result[-1]['error'])
        self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main()
