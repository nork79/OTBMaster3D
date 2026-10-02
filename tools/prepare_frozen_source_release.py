"""Prepare public source archives paired to an existing frozen build.

Preserves the application ZIP embedded in that build. Does not publish files.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def prepare(frozen, installer, cache, output, repository, tag):
    info = json.loads((frozen / 'build-info.json').read_text(encoding='utf-8'))
    version = info['version']
    source = frozen / info['source']
    if sha256(source) != info['source_sha256']:
        raise ValueError('Application source does not match frozen build-info.json')
    with zipfile.ZipFile(source) as archive:
        if archive.testzip():
            raise ValueError('Corrupt application source archive')
        snapshot = json.loads(archive.read('OTBMaster3D/release-source.json'))
        if snapshot['base_commit'] != info['commit']:
            raise ValueError('Application source revision mismatch')
        hashes = json.loads((frozen / 'source/application-files.sha256.json').read_text())
        for name, expected in hashes.items():
            if hashlib.sha256(archive.read('OTBMaster3D/' + name)).hexdigest() != expected:
                raise ValueError('Application source file mismatch: ' + name)
    inventory = json.loads((ROOT / 'docs/licensing/source-inventory.json').read_text())
    for entry in inventory['sources']:
        if Path(entry['file']).name != entry['file']:
            raise ValueError('Unsafe source filename')
        path = cache / entry['file']
        if path.stat().st_size != entry['bytes'] or sha256(path) != entry['sha256']:
            raise ValueError('Dependency source mismatch: ' + entry['file'])
    inventory.update(version=version, status='HASH_VERIFIED_SOURCE_MATERIALS',
                     remaining_issues=['Clean Windows installer validation remains pending.'])
    output.mkdir(parents=True, exist_ok=True)
    app = output / f'OTBMaster3D-{version}-application-source.zip'
    dependencies = output / f'OTBMaster3D-{version}-dependency-sources.zip'
    shutil.copy2(source, app)
    with zipfile.ZipFile(dependencies, 'w', zipfile.ZIP_STORED) as archive:
        archive.writestr('source-inventory.json', json.dumps(inventory, indent=2))
        for entry in inventory['sources']:
            archive.write(cache / entry['file'], 'sources/' + entry['file'])
        archive.write(ROOT / 'docs/releases/1.6.0-source.md', 'SOURCE_RELEASE.md')
    with zipfile.ZipFile(dependencies) as archive:
        for entry in inventory['sources']:
            with archive.open('sources/' + entry['file']) as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != entry['sha256']:
                    raise ValueError('Packaged dependency mismatch: ' + entry['file'])
    shutil.copy2(frozen / 'build-info.json', output / 'build-info.json')
    shutil.copy2(frozen / 'source/application-files.sha256.json', output / 'application-files.sha256.json')
    manifest = dict(version=version, base_commit=info['commit'],
                    application_archive_matches_installer=True,
                    installer=dict(file=installer.name, sha256=sha256(installer),
                                   bytes=installer.stat().st_size, published=False),
                    dependency_source_count=len(inventory['sources']),
                    packages=info['packages'], archives={},
                    publication_status='LOCAL_ONLY; hosting decision deferred by maintainer',
                    public_downloads_verified=False,
                    release_scope='Source publication; clean Windows installer validation pending')
    base_url = f'https://github.com/{repository}/releases/download/{tag}/'
    for path in (app, dependencies):
        manifest['archives'][path.name] = dict(sha256=sha256(path), bytes=path.stat().st_size,
                                             proposed_url=base_url + path.name)
    manifest_path = output / 'source-release-manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    files = (app, dependencies, output / 'build-info.json',
             output / 'application-files.sha256.json', manifest_path)
    (output / 'SHA256SUMS.txt').write_text(
        ''.join(f'{sha256(path)}  {path.name}\n' for path in files), encoding='ascii')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frozen', type=Path, default=ROOT / 'dist/OTBMaster3D')
    parser.add_argument('--installer', type=Path, default=ROOT / 'installer-output/OTBMaster3D-1.6.0-Setup.exe')
    parser.add_argument('--cache', type=Path, default=ROOT / 'release-materials/1.4.0-beta.2/sources')
    parser.add_argument('--output', type=Path, default=ROOT / 'release-materials/1.6.0')
    parser.add_argument('--repository', default='norKI79/OTBMaster3D')
    parser.add_argument('--tag', default='v1.6.0-source-87d30dc')
    args = parser.parse_args()
    prepare(args.frozen, args.installer, args.cache, args.output, args.repository, args.tag)
