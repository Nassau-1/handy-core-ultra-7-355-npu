"""RNN-T control-flow regressions, independent of model weights and NPU."""
import unittest

import numpy as np

from runtime import Runtime


class Predictor:
    outputs = [0, 1, 2]

    def __init__(self):
        self.tokens = []

    def __call__(self, inputs):
        token, hidden, cell = inputs
        self.tokens.append(int(token.item()))
        return {0: np.zeros((1, 1, 2), np.float32), 1: hidden+1, 2: cell+1}


class DecodeTests(unittest.TestCase):
    def make_runtime(self, emissions):
        runtime = object.__new__(Runtime)
        runtime.meta = {'layers': 2, 'hidden': 2, 'blank': 9, 'max_symbols': 2}
        runtime.predictor = Predictor()
        outputs = iter(emissions)
        runtime.frames = []

        def joint(inputs):
            runtime.frames.append(int(inputs[0][0, 0, 0]))
            return {0: np.array([[next(outputs)]])}

        runtime.joint = joint
        return runtime

    def test_blank_advances_without_updating_recurrent_state(self):
        runtime = self.make_runtime([4, 9, 9, 5, 9])
        encoded = np.arange(3, dtype=np.float32).reshape(1, 3, 1)
        self.assertEqual(runtime.decode(encoded, 3), [4, 5])
        self.assertEqual(runtime.frames, [0, 0, 1, 2, 2])
        self.assertEqual(runtime.predictor.tokens, [9, 4, 5])

    def test_symbol_limit_advances_and_preserves_last_token(self):
        runtime = self.make_runtime([4, 5, 6, 9])
        encoded = np.arange(2, dtype=np.float32).reshape(1, 2, 1)
        self.assertEqual(runtime.decode(encoded, 2), [4, 5, 6])
        self.assertEqual(runtime.frames, [0, 0, 1, 1])
        self.assertEqual(runtime.predictor.tokens, [9, 4, 5, 6])

    def test_padding_frames_are_not_decoded(self):
        runtime = self.make_runtime([9])
        self.assertEqual(runtime.decode(np.zeros((1, 5, 2), np.float32), 1), [])
        self.assertEqual(len(runtime.frames), 1)

    def test_fragment_boundary_preserves_predictor_state_and_blank(self):
        runtime = self.make_runtime([4, 9, 9, 5, 9])
        encoded = np.arange(3, dtype=np.float32).reshape(1, 3, 1)
        state = {}
        first = runtime.decode(encoded[:, :1], 1, state)
        second = runtime.decode(encoded[:, 1:], 2, state)
        self.assertEqual(first+second, [4, 5])
        self.assertEqual(runtime.predictor.tokens, [9, 4, 5])

    def test_independent_dictations_restart_from_blank(self):
        runtime = self.make_runtime([4, 9, 5, 9])
        encoded = np.zeros((1, 1, 1), np.float32)
        self.assertEqual(runtime.decode(encoded, 1), [4])
        self.assertEqual(runtime.decode(encoded, 1), [5])
        self.assertEqual(runtime.predictor.tokens, [9, 4, 9, 5])


if __name__ == '__main__':
    unittest.main()
