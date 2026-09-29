"""Install the reviewed official Fairy-Stockfish 14 Windows x64 engine and source."""
import hashlib
from pathlib import Path
import shutil
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '14'
EXE_NAME = 'fairy-stockfish_x86-64.exe'
SOURCE_NAME = 'fairy-stockfish-14.zip'
EXE_URL = 'https://github.com/fairy-stockfish/Fairy-Stockfish/releases/download/fairy_sf_14/' + EXE_NAME
SOURCE_URL = 'https://codeload.github.com/fairy-stockfish/Fairy-Stockfish/zip/refs/tags/fairy_sf_14'
EXE_SHA256 = '28d5c18fd7352d66800d13e1fdd57ba7d64d95c38d93642fd12cbd89e9d0ed73'
SOURCE_SHA256 = 'ba21ae5681cfa365293abe34301e7e645f3ce6a49db00d42cf2830585879e2d8'
SOURCE_PREFIX = 'Fairy-Stockfish-fairy_sf_14/'


def verified_file(path, url, digest):
    if path.exists():
        content = path.read_bytes()
    else:
        request = urllib.request.Request(url, headers={'User-Agent': 'OTBMaster3D'})
        with urllib.request.urlopen(request, timeout=90) as response:
            content = response.read()
    if hashlib.sha256(content).hexdigest() != digest:
        raise ValueError(f'Fairy-Stockfish checksum mismatch: {path.name}')
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(content)
    return path


def install():
    cache = ROOT / 'release-materials/1.4.0-beta.2'
    executable = verified_file(cache / 'engine-downloads' / EXE_NAME, EXE_URL, EXE_SHA256)
    source = verified_file(cache / 'sources' / SOURCE_NAME, SOURCE_URL, SOURCE_SHA256)
    target = ROOT / 'engines/fairy-stockfish-14'
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(executable, target / EXE_NAME)
    shutil.copy2(source, target / SOURCE_NAME)
    notices = ROOT / 'licenses/Fairy-Stockfish'
    notices.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as archive:
        for name in ('Copying.txt', 'AUTHORS', 'README.md'):
            content = archive.read(SOURCE_PREFIX + name)
            (target / name).write_bytes(content)
            (notices / name).write_bytes(content)
    print(f'Fairy-Stockfish {VERSION} and matching source ready: {target}')


def verify_installation():
    target = ROOT / 'engines/fairy-stockfish-14'
    for name, digest in ((EXE_NAME, EXE_SHA256), (SOURCE_NAME, SOURCE_SHA256)):
        if not (target / name).is_file() or hashlib.sha256((target / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError('Missing or changed Fairy-Stockfish input; run tools/install_fairy_stockfish.py')
    with zipfile.ZipFile(target / SOURCE_NAME) as archive:
        for name in ('Copying.txt', 'AUTHORS', 'README.md'):
            if (target / name).read_bytes() != archive.read(SOURCE_PREFIX + name):
                raise RuntimeError('Changed Fairy-Stockfish notice: ' + name)


if __name__ == '__main__':
    install()
