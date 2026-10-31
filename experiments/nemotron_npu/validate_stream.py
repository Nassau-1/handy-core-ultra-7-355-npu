"""Compare explicit NPU streaming graphs with saved unmodified HF reference."""
import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np

from stream_runtime import StreamingRuntime


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--artifact', type=Path, required=True)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--references', type=Path, nargs='+', required=True)
    p.add_argument('--report', type=Path, required=True)
    p.add_argument('--device', choices=['NPU', 'CPU'], default='NPU')
    p.add_argument('--audio-dir', type=Path)
    p.add_argument('--model', type=Path)
    args = p.parse_args()
    if bool(args.audio_dir) != bool(args.model):
        p.error('--audio-dir and --model must be supplied together')
    processor = None
    if args.model:
        from frontend import Processor
        import soundfile as sf
        processor = Processor(args.artifact, args.model)
    runtime = StreamingRuntime(args.artifact, args.cache, device=args.device)
    results = []
    for reference in args.references:
        data = np.load(reference)
        groups = [data['first'], *data['following']]
        frontend_error = None
        if processor:
            audio_path = args.audio_dir/(reference.stem.removeprefix('reference-')+'.wav')
            audio, sr = sf.read(audio_path, dtype='float32')
            if sr != 16000 or len(audio) != int(data['samples']):
                raise ValueError('Audio does not match reference')
            production = list(processor.iter_features(audio,
                runtime.meta['first_mel_frames'], runtime.meta['mel_frames']))
            if len(production) != len(groups):
                raise ValueError('Frontend lost an audio fragment')
            frontend_error = 0.0
            for actual, expected_group in zip(production, groups):
                np.testing.assert_allclose(actual, expected_group, rtol=1e-5, atol=2e-4)
                frontend_error = max(frontend_error, float(np.max(np.abs(actual-expected_group))))
            groups = production
        expected = [int(t) for t in data['tokens'] if t != runtime.meta['blank']]
        valid_total = ((int(data['samples'])//160+1+7+31)//32)*4
        for repeat in range(2):
            start, cpu = time.perf_counter(), time.process_time()
            decoder, tokens, errors = {}, [], []
            remaining = valid_total
            for index, encoded in enumerate(runtime.encode_groups(groups, data['prompt'])):
                valid = min(remaining, encoded.shape[1])
                offset = index*runtime.meta['encoder_frames']
                target = data['encoded'][:, offset:offset+valid]
                actual = encoded[:, :valid]
                errors.append(float(np.linalg.norm(actual-target)/max(np.linalg.norm(target), 1e-10)))
                tokens.extend(runtime.decode(encoded, valid, decoder))
                remaining -= valid
            result = {'reference': reference.name, 'repeat': repeat,
                'audio_samples': int(data['samples']),
                'frontend_parity': processor is not None, 'frontend_max_abs_error':frontend_error,
                'tokens_equal': tokens == expected, 'relative_l2_error': max(errors),
                'group_errors': errors, 'tokens':tokens, 'expected_tokens':expected,
                'wall_seconds':time.perf_counter()-start, 'cpu_seconds':time.process_time()-cpu}
            results.append(result)
            print(json.dumps(result), flush=True)
    report = {'device':args.device, 'joint_device':args.device, 'predictor_device':args.device,
              'mode':'cached-streaming', 'load_seconds':runtime.load_seconds, 'results':results}
    report['artifact_sha256'] = {}
    for path in sorted(args.artifact.iterdir()):
        if path.suffix in ('.xml', '.bin') or path.name in ('metadata.json', 'frontend.npz'):
            with path.open('rb') as source:
                report['artifact_sha256'][path.name] = hashlib.file_digest(source, 'sha256').hexdigest()
    args.report.write_text(json.dumps(report, indent=2), encoding='utf-8')
    if not all(r['tokens_equal'] and r['relative_l2_error'] < 0.02 for r in results):
        raise SystemExit('Streaming parity failed')


if __name__ == '__main__':
    main()
