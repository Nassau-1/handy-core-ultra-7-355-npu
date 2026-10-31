"""Install a validated local payload without changing the shared Handy package."""
import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
from validation_policy import POLICY, accepted


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--artifact', type=Path, required=True)
    p.add_argument('--worker', type=Path, required=True, help='Frozen onedir directory')
    p.add_argument('--model', type=Path, required=True)
    p.add_argument('--validation', type=Path, required=True)
    args = p.parse_args()
    validation = json.loads(args.validation.read_text(encoding='utf-8'))
    if any(validation.get(k) != 'NPU' for k in ['device', 'joint_device', 'predictor_device']):
        raise ValueError('All neural graphs must have been validated on NPU')
    metadata = json.loads((args.artifact / 'metadata.json').read_text(encoding='utf-8'))
    if metadata['reference_revision'] != 'ea30d66debe3740a08b573244286791d423d6b3e':
        raise ValueError('The Handy pilot requires the pinned reference revision')
    streaming = metadata.get('mode') == 'cached-streaming'
    results = validation.get('results', [])
    if not results or not all(accepted(r) if streaming else
            r['tokens_equal'] and r['relative_l2_error'] < 0.02 for r in results):
        raise ValueError('Reference parity did not pass')
    if streaming:
        if (metadata['encoder_frames'] != 64 or metadata['max_samples'] != 9600000
                or validation.get('policy') != POLICY
                or validation.get('mode') != 'cached-streaming'
                or not any(r.get('audio_samples') == 9600000 for r in validation['results'])
                or not all(r.get('frontend_parity') for r in validation['results'])):
            raise ValueError('The streaming pilot requires validated full ten-minute audio')
        artifact_files = [f'{name}.{extension}' for name in ['encoder_stream',
            'subsampler_first', 'subsampler_step', 'predictor', 'joint'] for extension in ['xml', 'bin']]
        artifact_files += ['frontend.npz', 'metadata.json']
        for name in artifact_files:
            with (args.artifact/name).open('rb') as source:
                digest = hashlib.file_digest(source, 'sha256').hexdigest()
            if validation.get('artifact_sha256', {}).get(name) != digest:
                raise ValueError(f'Artifact changed after reference validation: {name}')
    else:
        if metadata['frames'] != 4096:
            raise ValueError('The original pilot requires the 4,096-frame export')
        artifact_files = ['encoder.xml', 'encoder.bin', 'predictor.xml', 'predictor.bin',
            'joint.xml', 'joint.bin', 'frontend.npz', 'metadata.json', 'reference.npz']
    if not (args.worker / 'nemotron-npu.exe').is_file():
        raise ValueError('Missing frozen executable')
    app_data = Path(os.environ['LOCALAPPDATA']) / 'com.nassau.handy.ultra355npu'
    directory = 'nemotron-npu-streaming' if streaming else 'nemotron-npu-pilot'
    destination = app_data / directory
    staging = app_data / (directory+'.staging')
    if destination.exists() or staging.exists():
        raise FileExistsError('A pilot or staging directory already exists; preserve it and review before replacing')
    staging.mkdir(parents=True)
    shutil.copytree(args.worker, staging / 'worker')
    (staging / 'artifact').mkdir()
    for name in artifact_files:
        shutil.copy2(args.artifact / name, staging / 'artifact' / name)
    (staging / 'tokenizer').mkdir()
    for name in ['tokenizer.json', 'processor_config.json']:
        shutil.copy2(args.model / name, staging / 'tokenizer' / name)
    shutil.copy2(args.validation, staging / 'validation.json')
    shutil.copy2(Path(__file__).with_name('TRANSFORMERS-LICENSE.txt'), staging / 'TRANSFORMERS-LICENSE.txt')
    shutil.copy2(args.model / 'README.md', staging / 'NVIDIA-MODEL-CARD.md')
    inventory = []
    for file in sorted(staging.rglob('*')):
        if file.is_file():
            with file.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            inventory.append({'path': file.relative_to(staging).as_posix(),
                              'size': file.stat().st_size, 'sha256': digest})
    (staging / 'inventory.json').write_text(json.dumps(inventory, indent=2), encoding='utf-8')
    staging.rename(destination)
    print(json.dumps({'installed': str(destination), 'files': len(inventory)}), flush=True)


if __name__ == '__main__':
    main()
