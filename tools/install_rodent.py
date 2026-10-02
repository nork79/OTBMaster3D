"""Build pinned Rodent IV for Windows with MinGW g++, retaining source and notices."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REVISION = "e8d84c8c8c189a1cf4eb27c578fc573af3b916d2"
SOURCE_SHA256 = "5d35c65bfccd58fe74a73b58434ec1542f4aabc45b343163b277870c681f7773"
SOURCE_URL = f"https://codeload.github.com/nescitus/rodent-iv/zip/{REVISION}"


def install(archive=None, compiler=None):
    archive = Path(archive) if archive else ROOT / "release-materials/rodent-iv/source.zip"
    if not archive.exists():
        archive.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(SOURCE_URL, timeout=120) as response:
            content = response.read()
        if hashlib.sha256(content).hexdigest() != SOURCE_SHA256:
            raise ValueError("Rodent source checksum mismatch")
        archive.write_bytes(content)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("Rodent source checksum mismatch")
    compiler = compiler or shutil.which("g++")
    if not compiler:
        raise RuntimeError("Install MinGW-w64 g++ or pass --compiler PATH.")
    target = ROOT / "engines/rodent-iv"
    build = ROOT / "build/rodent-iv"
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as source:
        source.extractall(build)
    source_root = build / ("rodent-iv-" + REVISION)
    for directory in ("personalities", "books"):
        shutil.copytree(source_root / directory, target / directory, dirs_exist_ok=True)
    for book in (source_root / "exe").glob("*.bin"):
        shutil.copy2(book, target / "books" / book.name)
    # No aliases: expose PersonalityFile consistently and keep Elo independent.
    (target / "personalities/basic.ini").write_text(
        "HIDE_OPTIONS\nPERSONALITY_BOOKS\nELO_SLIDER\n", encoding="utf-8")
    flags = ["-std=c++14", "-O2", "-DNDEBUG", "-DNO_MM_POPCNT", "-static", "-pthread", "-s"]
    command = [compiler, *flags, *map(str, sorted((source_root / "sources/src").glob("*.cpp"))),
               "-o", str(target / "rodent-iv.exe")]
    environment = dict(os.environ)
    environment["PATH"] = str(Path(compiler).parent) + os.pathsep + environment.get("PATH", "")
    subprocess.run(command, check=True, env=environment)
    shutil.copy2(archive, target / "rodent-iv-source.zip")
    shutil.copy2(source_root / "LICENSE", target / "LICENSE")
    shutil.copy2(source_root / "README.md", target / "UPSTREAM-README.md")
    shutil.copy2(__file__, target / "install_rodent.py")
    manifest = {"revision": REVISION, "source_sha256": SOURCE_SHA256,
                "compiler": subprocess.check_output([compiler, "--version"], text=True).splitlines()[0],
                "flags": flags,
                "files": {str(path.relative_to(target)): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in sorted(target.rglob("*")) if path.is_file() and path.name != "manifest.json"}}
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Rodent IV ready: {target}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--compiler")
    args = parser.parse_args()
    install(args.archive, args.compiler)
