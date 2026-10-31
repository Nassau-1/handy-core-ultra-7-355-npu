"""Exercise the actual persistent PCM protocol, including feature extraction."""
import argparse
import json
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np
import soundfile as sf


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--artifact', type=Path, required=True)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--model', type=Path, required=True)
    p.add_argument('--audio', type=Path, nargs='+', required=True)
    p.add_argument('--report', type=Path, required=True)
    p.add_argument('--device', choices=['NPU', 'CPU'], default='NPU')
    p.add_argument('--joint-device', choices=['CPU', 'NPU'])
    p.add_argument('--predictor-device', choices=['CPU', 'NPU'])
    p.add_argument('--executable', type=Path, help='Use the frozen runtime instead of Python')
    args = p.parse_args()
    command = ([str(args.executable)] if args.executable else
               [sys.executable, str(Path(__file__).with_name('runtime.py'))])
    command += ['--artifact', str(args.artifact), '--cache', str(args.cache),
               '--model', str(args.model), '--device', args.device,
               '--joint-device', args.joint_device or args.device,
               '--predictor-device', args.predictor_device or args.device, '--worker']
    messages = queue.Queue()
    start = time.perf_counter()
    with args.report.with_suffix('.stderr.log').open('wb') as errors:
        child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors)

        def read():
            for line in child.stdout:
                messages.put(line)
            messages.put(None)

        threading.Thread(target=read, daemon=True).start()

        def response():
            line = messages.get(timeout=180)
            if line is None:
                raise RuntimeError('Worker exited before its response; inspect stderr')
            return json.loads(line)

        try:
            ready = response()
            while ready.get('stage'):
                ready = response()
            if not ready.get('ready'):
                raise RuntimeError(ready)
            result = {'ready': ready, 'startup_seconds': time.perf_counter()-start, 'utterances': []}
            for audio_path in args.audio:
                audio, sr = sf.read(audio_path, dtype='float32')
                if sr != 16000 or audio.ndim != 1:
                    raise ValueError('Expected mono 16 kHz WAV')
                for repetition in range(2):
                    start = time.perf_counter()
                    child.stdin.write((json.dumps({'samples': len(audio)})+'\n').encode('utf-8'))
                    child.stdin.write(np.asarray(audio, dtype='<f4').tobytes())
                    child.stdin.flush()
                    reply = response()
                    if not reply.get('ok'):
                        raise RuntimeError(reply)
                    result['utterances'].append({'file': audio_path.name, 'repetition': repetition,
                        'audio_seconds': len(audio)/sr, 'wall_seconds': time.perf_counter()-start, **reply})
                    print(json.dumps(result['utterances'][-1]), flush=True)
            child.stdin.close()
            if child.wait(timeout=10):
                raise RuntimeError('Worker failed after EOF')
            args.report.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
        finally:
            if child.poll() is None:
                child.kill()
                child.wait()


if __name__ == '__main__':
    main()
