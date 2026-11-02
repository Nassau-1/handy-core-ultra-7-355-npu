"""Bundle only the inference engine; the approved FP32 model downloads from HF."""
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
    parser.add_argument('--output', type=Path, default=ROOT / 'src-tauri/resources/npu')
    args = parser.parse_args()
    resources = args.output
    if resources.exists():
        raise RuntimeError(f'Output must be absent to avoid mixing model payloads: {resources}')
    resources.mkdir(parents=True)
    run('freeze.py', '--output', ROOT / 'build/npu/frozen')
    shutil.copytree(ROOT / 'build/npu/frozen/dist/nemotron-npu', resources / 'worker')
    shutil.copy2(ROOT / 'packaging/OPENMDW-1.1.txt', resources / 'MODEL-LICENSE.txt')
    shutil.copy2(EXPERIMENT / 'TRANSFORMERS-LICENSE.txt', resources / 'TRANSFORMERS-LICENSE.txt')
    shutil.copy2(Path(sys.base_prefix) / 'LICENSE.txt', resources / 'worker/PYTHON-LICENSE.txt')
    shutil.copy2(ROOT / 'THIRD-PARTY-NPU.md', resources / 'THIRD-PARTY-NPU.md')
    for name in ['managed-policy.json', 'finance-glossary.json', 'managed-model-lock.json']:
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
