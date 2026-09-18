"""Install the official CPU Lc0 runtime and Maia v1 networks for local play."""
from pathlib import Path
import hashlib
import json
import urllib.request
import zipfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
LC0_URL = 'https://github.com/LeelaChessZero/lc0/releases/download/v0.32.1/lc0-v0.32.1-windows-cpu-openblas.zip'
LC0_SHA256 = 'b2caa8443f0e0cb15cf76c335c53985f2973cd6438e77d3e2366cd21d2effa38'


def download(url, path, expected=None):
    if path.is_file() and (expected is None or hashlib.sha256(path.read_bytes()).hexdigest() == expected):
        return
    print('Downloading '+url,flush=True)
    request = urllib.request.Request(url,headers={'User-Agent':'OTBMaster3D'})
    with urllib.request.urlopen(request,timeout=120) as response:
        data = response.read()
    if expected and hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('Checksum mismatch: '+url)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(data)


def install():
    destination = ROOT/'engines'/'maia'
    destination.mkdir(parents=True,exist_ok=True)
    if not (destination/'lc0.exe').is_file():
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder)/'lc0.zip'
            download(LC0_URL,archive,LC0_SHA256)
            with zipfile.ZipFile(archive) as z:
                for item in z.infolist():
                    if not (destination/item.filename).resolve().is_relative_to(destination.resolve()):
                        raise ValueError('Unsafe archive path')
                z.extractall(destination)
    sources = {'lc0':LC0_URL}
    for rating in (1100,1300,1400,1500,1600,1800):
        url = f'https://github.com/CSSLab/maia-chess/releases/download/v1.0/maia-{rating}.pb.gz'
        download(url,destination/f'maia-{rating}.pb.gz')
        sources[str(rating)] = url
    for name,url in (
        ('Maia-LICENSE.txt','https://raw.githubusercontent.com/CSSLab/maia-chess/master/LICENSE'),
        ('Lc0-COPYING.txt','https://raw.githubusercontent.com/LeelaChessZero/lc0/v0.32.1/COPYING')):
        download(url,destination/name)
    manifest = {'sources':sources,'lc0_archive_sha256':LC0_SHA256,
                'files':{str(p.relative_to(destination)):hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in destination.rglob('*') if p.is_file() and p.name != 'installation.json'}}
    (destination/'installation.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('Maia CPU installation ready.',flush=True)


if __name__ == '__main__':
    install()
