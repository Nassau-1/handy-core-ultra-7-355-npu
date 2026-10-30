"""Build-only: download the immutable model and freeze the private Python runtime."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def digest_file(path, entry):
    algorithm = "sha256" if "sha256" in entry else "sha1"
    digest = hashlib.new(algorithm)
    if algorithm == "sha1":
        digest.update(f"blob {entry['size']}\0".encode())
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_model(destination):
    manifest = json.loads((ROOT / "packaging/model-lock.json").read_text())
    destination.mkdir(parents=True, exist_ok=True)
    for entry in manifest["files"]:
        path = destination / entry["name"]
        expected = entry.get("sha256", entry.get("git_blob_sha1"))
        if path.exists() and path.stat().st_size == entry["size"] and digest_file(path, entry) == expected:
            continue
        url = f"https://huggingface.co/{manifest['repo']}/resolve/{manifest['revision']}/{entry['name']}"
        partial = path.with_suffix(path.suffix + ".partial")
        print(f"Fetching {entry['name']}", flush=True)
        with urllib.request.urlopen(url, timeout=180) as response, partial.open("wb") as output:
            shutil.copyfileobj(response, output)
        if partial.stat().st_size != entry["size"] or digest_file(partial, entry) != expected:
            raise RuntimeError(f"Model integrity failure: {entry['name']}")
        partial.replace(path)
    shutil.copy2(ROOT / "packaging/model-lock.json", destination / "model-lock.json")
    shutil.copy2(ROOT / "packaging/WHISPER-LICENSE.txt", destination / "LICENSE.txt")


def main():
    resources = ROOT / "src-tauri/resources/npu"
    prepare_model(resources / "model")
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
        "--name", "handy-npu-worker", "--console",
        "--collect-all", "openvino", "--collect-all", "openvino_genai",
        "--collect-all", "openvino_tokenizers",
        "--copy-metadata", "openvino", "--copy-metadata", "openvino-genai",
        "--copy-metadata", "openvino-tokenizers", "--copy-metadata", "numpy",
        "--distpath", str(ROOT / "build/npu/dist"),
        "--workpath", str(ROOT / "build/npu/work"),
        "--specpath", str(ROOT / "build/npu"),
        str(ROOT / "src-tauri/src/windows_npu_worker.py"),
    ], check=True)
    shutil.copytree(ROOT / "build/npu/dist/handy-npu-worker", resources / "worker", dirs_exist_ok=True)
    shutil.copy2(Path(sys.base_prefix) / "LICENSE.txt", resources / "worker/PYTHON-LICENSE.txt")
    shutil.copy2(ROOT / "THIRD-PARTY-NPU.md", resources / "THIRD-PARTY-NPU.md")
    probe = subprocess.run([str(resources / "worker/handy-npu-worker.exe"), "--probe"],
                           check=True, capture_output=True, text=True, timeout=60)
    result = json.loads(probe.stdout)
    if not result["openvino"].startswith("2026.2.1"):
        raise RuntimeError(f"Unexpected runtime version: {result}")
    print(json.dumps(result))
    inventory = []
    for path in sorted(resources.rglob("*")):
        if path.is_file() and path != resources / "inventory.json":
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            inventory.append({"path": path.relative_to(resources).as_posix(),
                              "size": path.stat().st_size, "sha256": digest})
    (resources / "inventory.json").write_text(json.dumps(inventory, indent=2))


if __name__ == "__main__":
    main()
