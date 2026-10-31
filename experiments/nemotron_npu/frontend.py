"""Small NumPy/Rust-tokenizer frontend, numerically checked against Transformers.

Algorithm follows the Apache-2.0 Transformers 5.13.0
NemotronAsrStreamingFeatureExtractor. Exported mel filters and Hann window are
the exact reference constants. No torch/librosa import is needed at runtime.
"""
import json

import numpy as np
from tokenizers import Tokenizer


class Processor:
    def __init__(self, artifact, model):
        constants = np.load(artifact / 'frontend.npz')
        self.window = np.pad(constants['window'], (56, 56))
        self.mel = constants['mel']
        self.prompts = json.loads((model / 'processor_config.json').read_text(encoding='utf-8'))['prompt_dictionary']
        self.tokenizer = Tokenizer.from_file(str(model / 'tokenizer.json'))

    def __call__(self, audio, sampling_rate=16000, language='auto', return_tensors='np'):
        if sampling_rate != 16000 or return_tensors != 'np' or audio.ndim != 1:
            raise ValueError('Expected mono 16 kHz audio and NumPy output')
        if language not in self.prompts:
            raise ValueError(f'Unsupported language: {language}')
        signal = np.asarray(audio, dtype=np.float32).copy()
        signal[1:] = audio[1:] - np.float32(0.97)*audio[:-1]
        frames = np.lib.stride_tricks.sliding_window_view(np.pad(signal, (256, 256)), 512)[::160]
        spectrum = np.fft.rfft(frames*self.window, axis=-1)
        # Match reference sqrt(power)**2 rather than algebraically simplifying it.
        magnitude = np.sqrt(spectrum.real**2+spectrum.imag**2)**2
        # No BLAS worker pool: keep preprocessing single-threaded and predictable.
        features = np.log(np.einsum('tf,mf->tm', magnitude, self.mel, optimize=False)+np.float32(2**-24))
        valid = np.arange(len(features)) < len(audio)//160
        features *= valid[:, None]
        return {'input_features': features[None].astype(np.float32),
                'attention_mask': valid[None],
                'prompt_ids': np.array([self.prompts[language]], dtype=np.int64)}

    def batch_decode(self, sequences, skip_special_tokens=True):
        return self.tokenizer.decode_batch(sequences, skip_special_tokens=skip_special_tokens)
