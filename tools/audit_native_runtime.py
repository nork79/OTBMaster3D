"""Hash every PE in a payload and resolve regular/delay imports and package origins."""
import argparse
import ast
import base64
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import pefile

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect(path):
    pe = pefile.PE(str(path))
    imports = []
    for attr, kind in [('DIRECTORY_ENTRY_IMPORT','normal'), ('DIRECTORY_ENTRY_DELAY_IMPORT','delay')]:
        for entry in getattr(pe, attr, []):
            imports.append({'dll':entry.dll.decode(), 'kind':kind,
                            'symbols':[x.name.decode() if x.name else x.ordinal for x in entry.imports]})
    versions = {}
    for group in getattr(pe, 'FileInfo', []):
        for info in group:
            for table in getattr(info, 'StringTable', []):
                versions.update({k.decode(errors='replace'):v.decode(errors='replace') for k,v in table.entries.items()})
    fixed = getattr(pe, 'VS_FIXEDFILEINFO', [])
    version = None
    if fixed:
        v = fixed[0]
        version = [v.FileVersionMS >> 16, v.FileVersionMS & 65535, v.FileVersionLS >> 16, v.FileVersionLS & 65535]
    return {'sha256':sha(path), 'architecture':hex(pe.FILE_HEADER.Machine),
            'file_version':version, 'version_resources':versions, 'imports':imports}


def audit(payload, output):
    records = {}
    for dist in importlib.metadata.distributions():
        for f in dist.files or []:
            if f.hash and f.hash.mode == 'sha256' and Path(f).suffix.lower() in ('.dll','.pyd','.exe'):
                digest = base64.urlsafe_b64decode(f.hash.value + '===').hex()
                records.setdefault(digest, []).append({'package':dist.metadata['Name'], 'version':dist.version,
                                                      'record_path':str(f), 'installed_path':str(dist.locate_file(f))})
    baseline = json.loads((ROOT / 'docs/licensing/native-components.json').read_text())
    old = {x['sha256']:x for x in baseline['files']}
    toc = ROOT / 'build/windows-folder/COLLECT-00.toc'
    origins = {}
    if toc.exists():
        def walk(obj):
            if isinstance(obj, (list, tuple)):
                if len(obj) == 3 and all(isinstance(x,str) for x in obj) and obj[2] in ('BINARY','EXTENSION'):
                    origins[obj[0].replace('\\','/')] = obj[1]
                else:
                    for x in obj: walk(x)
        walk(ast.literal_eval(toc.read_text()))
    files = []
    for path in sorted(payload.rglob('*')):
        if path.suffix.lower() not in ('.dll','.pyd','.exe'): continue
        item = inspect(path)
        item['path'] = path.relative_to(payload).as_posix()
        item['record_matches'] = records.get(item['sha256'], [])
        item['freezer_input'] = origins.get(item['path'])
        item['baseline_component'] = old.get(item['sha256'], {}).get('component')
        item['microsoft_crt'] = path.name.lower().startswith(('msvcp','msvcr','vcruntime'))
        if item['freezer_input'] and Path(item['freezer_input']).exists():
            item['freezer_input_hash_match'] = sha(Path(item['freezer_input'])) == item['sha256']
        if item['microsoft_crt']:
            item['upstream'] = 'Microsoft Visual Studio Community 2022 VC/Redist; crt-selection.json'
        elif path.name.lower() == 'glfw3.dll':
            item['upstream'] = 'GLFW 3.4; https://github.com/glfw/glfw/tree/3.4; evidence/glfw-build.json'
        elif path.name.lower() == 'opengl32sw.dll':
            item['upstream'] = 'Qt prebuilt Mesa 11.2.2 / LLVM 3.6.2; evidence/software-opengl-provenance.json'
        elif item['record_matches']:
            packages = {r['package'].lower() for r in item['record_matches']}
            item['upstream'] = ('Qt/PySide/Shiboken 6.11.2 official archives' if packages & {'pyside6_essentials','shiboken6'} else
                                'Pillow 12.3.0 PyPI sdist and upstream tag' if 'pillow' in packages else
                                'cozy-chess-py 0.1.1 PyPI sdist and Cargo.lock')
        elif path.name.lower().startswith('fairy-stockfish'):
            item['upstream'] = 'Fairy-Stockfish 14 official x64 release; evidence/fairy-stockfish-verification.json'
        elif 'stockfish' in path.name:
            item['upstream'] = 'https://github.com/official-stockfish/Stockfish/tree/sf_19; source-inventory.json'
        elif path.name == 'OTBMaster3D.exe':
            item['upstream'] = 'Application snapshot with PyInstaller 6.22.3 bootloader; build-info.json'
        elif path.name.lower().startswith('unins'):
            item['upstream'] = 'Inno Setup generated uninstaller; .build-tools/inno/ISCC.exe and licenses/InnoSetup'
        else:
            item['upstream'] = 'CPython 3.13.12 Windows installation; source-inventory.json and PCbuild dependencies'
        files.append(item)
    names = {}
    for x in files: names.setdefault(Path(x['path']).name.lower(), []).append(x['path'])
    unresolved = []
    for x in files:
        for dep in x['imports']:
            name = dep['dll'].lower()
            dep['bundled_candidates'] = names.get(name, [])
            if dep['bundled_candidates']: dep['resolution'] = 'bundled; runtime search order not proven by static inspection'
            elif name.startswith(('api-ms-win-', 'ext-ms-win-')): dep['resolution'] = 'Windows API set'
            elif name in {'msvcp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll', 'vcruntime140.dll', 'vcruntime140_1.dll'}:
                dep['resolution'] = 'Declared prerequisite: official Microsoft x64 VC++ runtime >=14.44.35211.0; clean Windows verification pending'
            elif (Path('C:/Windows/System32') / name).exists() and not name.startswith(('msvcp','vcruntime','msvcr1')):
                dep['resolution'] = 'external host System32; clean Windows verification required'
            else:
                dep['resolution'] = 'UNRESOLVED'; unresolved.append([x['path'],name])
    result = {'payload':str(payload.resolve()), 'python':sys.version, 'files':files, 'unresolved_imports':unresolved,
              'limit':'RECORD/hash and freezer input establish local package origin; not publisher authenticity. Static imports do not enumerate LoadLibrary or static libraries.'}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2))
    print(f'{len(files)} native files; {len(unresolved)} unresolved import edges; {output}')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--payload', type=Path, default=ROOT / 'dist/OTBMaster3D')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); audit(a.payload, a.output)
