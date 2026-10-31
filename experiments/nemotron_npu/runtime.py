"""Explicit NPU acoustic encoder / CPU RNN-T decoder proof of concept.

stdin: one utterance of signed little-endian PCM16, mono 16 kHz, ended by EOF.
stdout: UTF-8 transcription followed by newline. Diagnostics use stderr only.
This first export is bounded, whole-utterance inference, NOT streaming ASR.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import openvino as ov


def diagnostic(stage, **fields):
    print(json.dumps({'stage': stage, **fields}), file=sys.stderr, flush=True)


class Runtime:
    def __init__(self, artifact, cache, device='NPU', compiler='PLUGIN', joint_device=None, predictor_device=None):
        joint_device = joint_device or device
        predictor_device = predictor_device or device
        self.device = device
        self.joint_device = joint_device
        self.predictor_device = predictor_device
        self.meta = json.loads((artifact / 'metadata.json').read_text(encoding='utf-8'))
        core = ov.Core()
        cache.mkdir(parents=True, exist_ok=True)
        props = {'CACHE_DIR': str(cache.resolve())}
        if device == 'NPU':
            props.update(NPU_COMPILER_TYPE=compiler, COMPILATION_NUM_THREADS=1)
        elif device == 'CPU':
            props.update(INFERENCE_NUM_THREADS=1, NUM_STREAMS=1, INFERENCE_PRECISION_HINT='f32')
        start = time.perf_counter()
        diagnostic('compiling_encoder', device=device, compiler=compiler)
        self.encoder = core.compile_model(artifact / 'encoder.xml', device, props)
        placement = self.encoder.get_property('EXECUTION_DEVICES')
        if isinstance(placement, str):
            placement = [placement]
        if not placement or any(not str(d).startswith(device) for d in placement):
            raise RuntimeError(f'Unexpected execution placement: {placement}')
        diagnostic('encoder_ready', devices=placement, seconds=time.perf_counter()-start)
        cpu = {'INFERENCE_NUM_THREADS': 1, 'NUM_STREAMS': 1, 'INFERENCE_PRECISION_HINT': 'f32'}
        npu = {'CACHE_DIR': str(cache.resolve()), 'NPU_COMPILER_TYPE': compiler, 'COMPILATION_NUM_THREADS': 1}
        self.predictor = core.compile_model(artifact / 'predictor.xml', predictor_device,
            cpu if predictor_device == 'CPU' else npu)
        self.joint = core.compile_model(artifact / 'joint.xml', joint_device,
            cpu if joint_device == 'CPU' else npu)
        for component, target in [(self.predictor, predictor_device), (self.joint, joint_device)]:
            devices = component.get_property('EXECUTION_DEVICES')
            devices = [devices] if isinstance(devices, str) else devices
            if not devices or any(not str(d).startswith(target) for d in devices):
                raise RuntimeError(f'Unexpected execution placement: {devices}')
        self.load_seconds = time.perf_counter()-start
        diagnostic('ready', seconds=self.load_seconds, encoder=device, predictor=predictor_device, joint=joint_device)

    def decode(self, encoded, valid):
        hidden = np.zeros((self.meta['layers'], 1, self.meta['hidden']), np.float32)
        cell = np.zeros_like(hidden)
        blank = self.meta['blank']
        pred_result = self.predictor([np.array([[blank]], np.int64), hidden, cell])
        prediction, hidden, cell = [pred_result[o] for o in self.predictor.outputs]
        tokens = []
        for index in range(valid):
            for _ in range(self.meta['max_symbols']):
                token = int(self.joint([encoded[:, index:index+1], prediction])[0].item())
                if token == blank:
                    break
                tokens.append(token)
                result = self.predictor([np.array([[token]], np.int64), hidden, cell])
                prediction, hidden, cell = [result[o] for o in self.predictor.outputs]
        return tokens

    def infer(self, features, mask, prompt, valid):
        start, cpu = time.perf_counter(), time.process_time()
        encoded = self.encoder([features, mask, prompt])[0]
        encoder_s = time.perf_counter()-start
        tokens = self.decode(encoded, valid)
        return tokens, encoded, {'encoder_seconds': encoder_s,
            'decode_seconds': time.perf_counter()-start-encoder_s,
            'total_seconds': time.perf_counter()-start,
            'cpu_seconds': time.process_time()-cpu}

    def transcribe(self, processor, audio, language='auto'):
        start, cpu = time.perf_counter(), time.process_time()
        batch = processor(audio, sampling_rate=16000, language=language, return_tensors='np')
        features, mask = batch['input_features'], batch['attention_mask']
        valid = int(mask.sum())
        # Reference causal 3x stride-2 subsampler: floor(length / 2 + 1).
        for _ in range(3):
            valid = valid//2+1
        extra = self.meta['frames'] - features.shape[1]
        if extra < 0:
            raise ValueError('Feature sequence exceeds the exported shape')
        features = np.pad(features, ((0, 0), (0, extra), (0, 0)))
        mask = np.pad(mask, ((0, 0), (0, extra)))
        tokens, _, timing = self.infer(features, mask, batch['prompt_ids'], valid)
        text = processor.batch_decode([tokens], skip_special_tokens=True)[0]
        timing.update(end_to_end_seconds=time.perf_counter()-start,
                      end_to_end_cpu_seconds=time.process_time()-cpu)
        return text, timing


def serve(runtime, processor, writer):
    """Persistent JSON header + normalized float32 PCM protocol, like Handy's worker."""
    def send(payload):
        writer.write((json.dumps(payload, ensure_ascii=False)+'\n').encode('utf-8'))
        writer.flush()

    limit = (runtime.meta['frames']-1)*160
    send({'ready': True, 'encoder_device': runtime.device, 'predictor_device': runtime.predictor_device,
          'joint_device': runtime.joint_device, 'max_samples': limit,
          'device': 'NPU' if runtime.device == runtime.predictor_device == runtime.joint_device == 'NPU' else 'hybrid'})
    reader = sys.stdin.buffer
    while header := reader.readline(8193):
        try:
            if len(header) > 8192 or not header.endswith(b'\n'):
                raise ValueError('Invalid request header')
            request = json.loads(header)
            count = request.get('samples')
            if type(count) is not int or not 0 < count <= limit:
                raise ValueError(f'PCM sample count must be between 1 and {limit}')
            raw = bytearray()
            while len(raw) < count*4:
                block = reader.read(count*4-len(raw))
                if not block:
                    raise EOFError('Truncated PCM request')
                raw.extend(block)
            audio = np.frombuffer(raw, dtype='<f4')
            if not np.isfinite(audio).all() or np.any(np.abs(audio) > 1.01):
                raise ValueError('PCM must contain finite normalized float32 samples')
            if request.get('translate'):
                raise ValueError('This model transcribes; translation is unsupported')
            language = request.get('language') or 'auto'
            if isinstance(language, str) and language.startswith('<|') and language.endswith('|>'):
                language = language[2:-2]
            text, timing = runtime.transcribe(processor, audio, language)
            send({'ok': True, 'text': text, 'timing': timing})
        except Exception as error:
            send({'ok': False, 'error': str(error)})
            # A malformed binary frame may have desynchronized input.
            raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact', type=Path, required=True)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--model', type=Path)
    p.add_argument('--device', choices=['NPU', 'CPU'], default='NPU')
    p.add_argument('--compiler', choices=['PLUGIN', 'DRIVER'], default='PLUGIN')
    p.add_argument('--joint-device', choices=['CPU', 'NPU'], help='Default: same as --device')
    p.add_argument('--predictor-device', choices=['CPU', 'NPU'], help='Default: same as --device')
    p.add_argument('--validate', action='store_true')
    p.add_argument('--worker', action='store_true', help='Persistent framed float32 PCM protocol')
    p.add_argument('--reference', type=Path, help='Alternative reference.npz from the same export shape')
    p.add_argument('--repeat', type=int, default=2)
    p.add_argument('--report', type=Path)
    args = p.parse_args()
    # Reserve stdout for protocol/text even if native libraries print to fd 1.
    writer = os.fdopen(os.dup(sys.stdout.fileno()), 'wb')
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    if args.worker:
        writer.write(b'{"stage":"compiling"}\n')
        writer.flush()
    runtime = Runtime(args.artifact, args.cache, args.device, args.compiler, args.joint_device, args.predictor_device)
    if args.validate:
        data = np.load(args.reference or args.artifact / 'reference.npz')
        expected = [int(t) for t in data['tokens'] if t != runtime.meta['blank']]
        results = []
        for _ in range(args.repeat):
            tokens, encoded, timing = runtime.infer(data['features'], data['mask'], data['prompt'], int(data['valid']))
            valid = int(data['valid'])
            # Padded output frames are never decoded and are not a correctness target.
            reference = data['encoded'][:, :valid]
            delta = encoded[:, :valid] - reference
            timing.update(tokens_equal=tokens == expected, tokens=tokens,
                          max_abs_error=float(np.abs(delta).max()),
                          relative_l2_error=float(np.linalg.norm(delta)/max(np.linalg.norm(reference), 1e-10)))
            results.append(timing)
            diagnostic('validation', **timing)
        report = {'device': args.device, 'joint_device': runtime.joint_device,
                  'predictor_device': runtime.predictor_device, 'compiler': args.compiler,
                  'load_seconds': runtime.load_seconds, 'results': results}
        if args.report:
            args.report.write_text(json.dumps(report, indent=2), encoding='utf-8')
        if not all(r['tokens_equal'] and r['relative_l2_error'] < 0.02 for r in results):
            raise RuntimeError('Reference parity failed; do not deploy this export')
        return
    if args.model is None:
        p.error('--model is required for PCM input')
    from frontend import Processor
    processor = Processor(args.artifact, args.model)
    if args.worker:
        serve(runtime, processor, writer)
        return
    limit = (runtime.meta['frames']-1)*160
    raw = sys.stdin.buffer.read(limit*2+2)
    if len(raw) > limit*2 or len(raw) % 2:
        raise ValueError('PCM exceeds fixed-shape limit or has an incomplete sample')
    if not raw:
        raise ValueError('Empty PCM input')
    audio = np.frombuffer(raw, dtype='<i2').astype(np.float32)/32768
    text, timing = runtime.transcribe(processor, audio)
    writer.write((text+'\n').encode('utf-8'))
    writer.flush()
    diagnostic('transcribed', **timing)


if __name__ == '__main__':
    main()
