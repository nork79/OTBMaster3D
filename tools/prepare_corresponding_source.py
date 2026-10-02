# Copyright (C) 2026 nork79
# SPDX-License-Identifier: GPL-3.0-only
"""Verify and package the inventoried release sources without publishing them.

Use --fetch to obtain missing, hash-pinned upstream archives. This does not make
the package legally complete: the inventory's unresolved items remain blocking.
"""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile

from prepare_installer_payload import ROOT, write_application_source


def build(output, fetch=False):
    inventory_path = ROOT / 'docs/licensing/source-inventory.json'
    inventory = json.loads(inventory_path.read_text(encoding='utf-8'))
    output.mkdir(parents=True, exist_ok=True)
    cache = output / 'sources'
    cache.mkdir(exist_ok=True)
    for entry in inventory['sources']:
        name = entry['file']
        if Path(name).name != name:
            raise ValueError('Source inventory must contain plain filenames')
        path = cache / name
        if not path.exists() and fetch:
            if not entry.get('url'):
                raise ValueError('Restore this retained original from the supplied source bundle: ' + name)
            request = urllib.request.Request(entry['url'], headers={'User-Agent': 'OTBMaster3D-source-archive'})
            with urllib.request.urlopen(request, timeout=120) as response:
                content = response.read()
            if hashlib.sha256(content).hexdigest() != entry['sha256']:
                raise ValueError('Downloaded source hash mismatch: ' + name)
            path.write_bytes(content)
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('Missing or changed source archive: ' + name)
    revision, status = write_application_source(output)
    dependency_zip = output / 'OTBMaster3D-1.4.0-beta.2-dependency-sources.zip'
    with zipfile.ZipFile(dependency_zip, 'w', zipfile.ZIP_STORED) as archive:
        archive.write(inventory_path, 'source-inventory.json')
        for entry in inventory['sources']:
            archive.write(cache / entry['file'], 'sources/' + entry['file'])
        for name in ('SOURCE_ACCESS.md', 'docs/licensing/REMEDIATION.md',
                     'docs/licensing/BUILD_AND_REPLACE.md',
                     'docs/licensing/LICENSING-CLOSURE.md',
                     'docs/licensing/RELEASE-COMPLIANCE.md'):
            archive.write(ROOT / name, name)
    files = {}
    for path in (output / 'OTBMaster3D-source.zip', dependency_zip):
        files[path.name] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                            'bytes': path.stat().st_size}
    manifest = {'version': '1.4.0-beta.2', 'base_commit': revision,
                'working_tree_status': status, 'archives': files,
                'publication_status': 'BLOCKED',
                'remaining_issues': inventory['remaining_issues'],
                'source_access': 'Publish these exact archives freely beside the installer link after approval'}
    frozen_manifest = ROOT / 'dist/OTBMaster3D/source/application-files.sha256.json'
    if frozen_manifest.exists():
        previous = json.loads(frozen_manifest.read_text(encoding='utf-8'))
        current = json.loads((output / 'application-files.sha256.json').read_text(encoding='utf-8'))
        changed = sorted(name for name in set(previous) | set(current)
                         if (name == 'main.py' or name.startswith(('otb_chess/', 'otb_chess_core/', 'packaging/', 'tools/')))
                         and previous.get(name) != current.get(name))
        manifest['frozen_payload_pairing'] = {
            'matches_staged_source_manifest': not changed, 'changed_code_or_build_files': changed,
            'meaning': 'Different code/build files require rebuilding; matching source staging alone does not prove frozen bytecode identity'}
    (output / 'source-release-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({'archives': files, 'publication_status': 'BLOCKED'}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'release-materials/1.4.0-beta.2')
    parser.add_argument('--fetch', action='store_true')
    args = parser.parse_args()
    build(args.output, args.fetch)
