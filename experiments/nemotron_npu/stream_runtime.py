"""Bounded NPU streaming encoder state, retaining RNNT context across fragments."""
import time

import numpy as np
import openvino as ov

from runtime import Runtime, diagnostic


class StreamingRuntime(Runtime):
    encoder_filename = 'encoder_stream.xml'

    def __init__(self, artifact, cache, device='NPU', compiler='PLUGIN', joint_device=None, predictor_device=None):
        start = time.perf_counter()
        super().__init__(artifact, cache, device, compiler, joint_device, predictor_device)
        core = ov.Core()
        props = {'CACHE_DIR': str(cache.resolve())}
        if device == 'NPU':
            props.update(NPU_COMPILER_TYPE=compiler, COMPILATION_NUM_THREADS=1)
        else:
            props.update(INFERENCE_NUM_THREADS=1, NUM_STREAMS=1, INFERENCE_PRECISION_HINT='f32')
        self.subsamplers = []
        for name in ['subsampler_first', 'subsampler_step']:
            component = core.compile_model(artifact/f'{name}.xml', device, props)
            placement = component.get_property('EXECUTION_DEVICES')
            placement = [placement] if isinstance(placement, str) else placement
            if not placement or any(not str(d).startswith(device) for d in placement):
                raise RuntimeError(f'Unexpected subsampler placement: {placement}')
            self.subsamplers.append(component)
        self.load_seconds = time.perf_counter()-start
        diagnostic('stream_ready', seconds=self.load_seconds, max_samples=self.max_samples)

    def encode_groups(self, groups, prompt):
        # Per-request state: no conversation/audio leaks into the next dictation.
        subs = [np.zeros(shape, np.float32) for shape in self.meta['subsampler_shapes']]
        state = [np.zeros(shape, np.float32) for shape in self.meta['state_shapes']]
        left, frames = self.meta['left_context'], self.meta['encoder_frames']
        q, k = np.arange(frames)+left, np.arange(left+frames)
        distance = q[:, None]//4-k[None, :]//4
        base_mask = (distance >= 0) & (distance <= left//4)
        for index, features in enumerate(groups):
            sub = self.subsamplers[min(index, 1)]
            result = sub([features, *subs])
            hidden, *subs = [result[o].copy() for o in sub.outputs]
            mask = (base_mask & (k[None, :] >= left-min(index*frames, left)))[None, None]
            result = self.encoder([hidden, prompt, mask, *state])
            encoded, *state = [result[o].copy() for o in self.encoder.outputs]
            yield encoded

    def transcribe(self, processor, audio, language='auto'):
        if not 0 < len(audio) <= self.max_samples:
            raise ValueError('Streaming dictation must contain between 1 sample and 600 seconds')
        if language not in processor.prompts:
            raise ValueError(f'Unsupported language: {language}')
        start, cpu = time.perf_counter(), time.process_time()
        groups = processor.iter_features(audio, self.meta['first_mel_frames'], self.meta['mel_frames'])
        prompt = np.array([processor.prompts[language]], np.int64)
        decoder = {}
        tokens = []
        # Match HF streaming: complete the last native 4-frame attention chunk,
        # but never decode the rest of the throughput group's padding.
        remaining = ((len(audio)//160+1+7+31)//32)*4
        count = 0
        for encoded in self.encode_groups(groups, prompt):
            valid = min(remaining, encoded.shape[1])
            tokens.extend(self.decode(encoded, valid, decoder))
            remaining -= valid
            count += 1
        if remaining != 0:
            raise RuntimeError('Streaming encoder did not cover the complete utterance')
        text = processor.batch_decode([tokens], skip_special_tokens=True)[0]
        return text, {'groups': count, 'tokens': len(tokens),
                     'end_to_end_seconds': time.perf_counter()-start,
                     'end_to_end_cpu_seconds': time.process_time()-cpu}
