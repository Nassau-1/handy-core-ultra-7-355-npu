"""Download pinned public reference files with resumable integrity checks."""
import argparse
import hashlib
import json
import time
import urllib.request
from pathlib import Path

repo = 'nvidia/nemotron-3.5-asr-streaming-0.6b'
revision = 'ea30d66debe3740a08b573244286791d423d6b3e'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
root = parser.parse_args().output
root.mkdir(parents=True, exist_ok=True)
with urllib.request.urlopen(f'https://huggingface.co/api/models/{repo}/tree/{revision}', timeout=45) as response:
    entries = json.load(response)
names = {'config.json','generation_config.json','processor_config.json','tokenizer.json','tokenizer_config.json','model.safetensors','README.md'}
manifest = [x for x in entries if x['path'] in names]
if {x['path'] for x in manifest} != names:
    raise RuntimeError('Pinned repository does not contain every required file')
for entry in manifest:
    destination = root / entry['path']
    partial = destination.with_suffix(destination.suffix + '.partial')
    def verify(path):
        if not path.exists() or path.stat().st_size != entry['size']:
            return False
        if 'lfs' in entry:
            with path.open('rb') as stream:
                return hashlib.file_digest(stream, 'sha256').hexdigest() == entry['lfs']['oid']
        return hashlib.sha1(f"blob {entry['size']}\0".encode()+path.read_bytes()).hexdigest() == entry['oid']
    if verify(destination):
        continue
    for attempt in range(4):
        offset = partial.stat().st_size if partial.exists() else 0
        if offset >= entry['size']:
            offset = 0
        request = urllib.request.Request(f"https://huggingface.co/{repo}/resolve/{revision}/{entry['path']}",
            headers={'Range':f'bytes={offset}-'} if offset else {})
        print(f"Fetching {entry['path']} from byte {offset}", flush=True)
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                if response.status != 206:
                    offset = 0
                elif not response.headers.get('Content-Range','').startswith(f'bytes {offset}-'):
                    raise RuntimeError('Unexpected range response')
                with partial.open('ab' if offset else 'wb') as stream:
                    while block := response.read(8 * 1024 * 1024):
                        stream.write(block)
            if verify(partial):
                partial.replace(destination)
                print(f"Verified {entry['path']}", flush=True)
                break
        except (OSError, TimeoutError) as error:
            print(type(error).__name__, flush=True)
        time.sleep(1)
    else:
        raise RuntimeError(f"Download/integrity failure: {entry['path']}")
(root / 'source-manifest.json').write_text(json.dumps({'repo':repo,'revision':revision,'files':manifest},indent=2),encoding='utf-8')
print('Verified model ready:', root, flush=True)
