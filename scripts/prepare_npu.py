"""Build the managed Nemotron payload; never ship pilot recordings or compiled caches."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / 'experiments/nemotron_npu'


def run(script, *args):
    subprocess.run([sys.executable, str(EXPERIMENT / script), *map(str, args)], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-model', type=Path, default=ROOT / 'build/npu/source')
    parser.add_argument('--output', type=Path, default=ROOT / 'src-tauri/resources/npu')
    args = parser.parse_args()
    resources = args.output
    if resources.exists():
        raise RuntimeError(f'Output must be absent to avoid mixing model payloads: {resources}')
    run('download.py', '--output', args.source_model)
    resources.mkdir(parents=True)
    run('production_export.py', '--model', args.source_model, '--output', resources / 'artifact')
    run('freeze.py', '--output', ROOT / 'build/npu/frozen')
    shutil.copytree(ROOT / 'build/npu/frozen/dist/nemotron-npu', resources / 'worker')
    tokenizer = resources / 'tokenizer'
    tokenizer.mkdir()
    for filename in ['tokenizer.json', 'tokenizer_config.json', 'processor_config.json']:
        shutil.copy2(args.source_model / filename, tokenizer / filename)
    shutil.copy2(args.source_model / 'README.md', resources / 'NVIDIA-MODEL-CARD.md')
    shutil.copy2(args.source_model / 'source-manifest.json', resources / 'source-manifest.json')
    shutil.copy2(ROOT / 'packaging/OPENMDW-1.1.txt', resources / 'MODEL-LICENSE.txt')
    shutil.copy2(EXPERIMENT / 'TRANSFORMERS-LICENSE.txt', resources / 'TRANSFORMERS-LICENSE.txt')
    shutil.copy2(Path(sys.base_prefix) / 'LICENSE.txt', resources / 'worker/PYTHON-LICENSE.txt')
    shutil.copy2(ROOT / 'THIRD-PARTY-NPU.md', resources / 'THIRD-PARTY-NPU.md')
    for name in ['managed-policy.json', 'finance-glossary.json']:
        shutil.copy2(ROOT / 'packaging' / name, resources / name)
    probe = subprocess.run([str(resources / 'worker/nemotron-npu.exe'), '--probe'],
                           check=True, capture_output=True, text=True, timeout=60)
    result = json.loads(probe.stdout)
    if not result['openvino'].startswith('2026.2.1'):
        raise RuntimeError(f'Unexpected runtime version: {result}')
    print(json.dumps(result))
    inventory = []
    for path in sorted(resources.rglob('*')):
        if path.is_file():
            with path.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            inventory.append(dict(path=path.relative_to(resources).as_posix(),
                                  size=path.stat().st_size, sha256=digest))
    (resources / 'inventory.json').write_text(json.dumps(inventory, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
