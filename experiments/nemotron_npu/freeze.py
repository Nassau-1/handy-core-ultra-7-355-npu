"""Build a standalone Windows runtime; keep PyTorch out of daily inference."""
import argparse
import subprocess
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--onedir',
           '--name', 'nemotron-npu', '--distpath', str(args.output / 'dist'),
           '--workpath', str(args.output / 'build'), '--specpath', str(args.output),
           '--collect-all', 'openvino', '--collect-all', 'tokenizers']
for excluded in ['torch', 'transformers', 'librosa', 'scipy', 'sklearn', 'numba', 'accelerate']:
    command += ['--exclude-module', excluded]
subprocess.run(command + [str(Path(__file__).with_name('runtime.py'))], check=True)
