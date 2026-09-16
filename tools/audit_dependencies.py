"""Rebuild the dependency inventory from source imports and installed metadata.

Run from the project environment: python tools/audit_dependencies.py
This inventories evidence, not legal clearance or the final deployed DLL closure.
"""
import ast
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ('PySide6','PySide6_Essentials','PySide6_Addons','shiboken6','glfw','PyOpenGL','Pillow','chess')
SOURCES = {
    'PySide6':'https://doc.qt.io/qtforpython-6/licenses.html',
    'PySide6_Essentials':'https://doc.qt.io/qtforpython-6/licenses.html',
    'PySide6_Addons':'https://doc.qt.io/qt-6/licensing.html',
    'shiboken6':'https://doc.qt.io/qtforpython-6/licenses.html',
    'glfw':'https://github.com/FlorianRhiem/pyGLFW',
    'PyOpenGL':'https://github.com/mcfletch/pyopengl',
    'Pillow':'https://pillow.readthedocs.io/en/stable/about.html',
    'chess':'https://python-chess.readthedocs.io/en/stable/',
}


def audit():
    imports = []
    paths = [ROOT/'main.py']
    for directory in ('otb_chess','tests','tools'):
        paths.extend((ROOT/directory).rglob('*.py'))
    for path in sorted(paths):
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            names = [a.name for a in node.names] if isinstance(node,ast.Import) else [node.module] if isinstance(node,ast.ImportFrom) and node.module else []
            for name in names:
                imports.append(dict(file=path.relative_to(ROOT).as_posix(),line=node.lineno,module=name,
                                    scope='test' if 'tests' in path.parts else 'tool' if 'tools' in path.parts else 'runtime'))
    records = []
    for package in PACKAGES:
        dist = metadata.distribution(package)
        license_name = dist.metadata.get('License-Expression') or dist.metadata.get('License') or 'requires verification before release'
        copies = []
        for file in dist.files or []:
            if '.dist-info/' not in str(file) or not any(word in str(file).lower() for word in ('license','copying','notice')):
                continue
            source = Path(dist.locate_file(file))
            if not source.is_file():
                continue
            destination = ROOT/'licenses'/package/source.name
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,destination)
            copies.append(dict(path=destination.relative_to(ROOT).as_posix(),source=str(file),sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
        records.append(dict(name=package,version=dist.version,apparent_license=license_name,
                            category='runtime',redistribution='NO: replace before proprietary release' if package=='chess' else 'Selected runtime files only; not whole Addons wheel' if package=='PySide6_Addons' else 'intended',
                            source=SOURCES[package],evidence='installed distribution metadata; selected licence route requires review',license_files=copies,
                            requires=list(dist.requires or [])))
    extras = [
        ('Qt runtime and plugins','6.11.2','LGPLv3 available for used modules; per-file third-party notices required','runtime','selected DLLs only','https://doc.qt.io/qt-6/licensing.html'),
        ('GLFW native library','3.4.0','zlib/libpng licence (upstream); bundled binary provenance requires verification before release','runtime','intended','https://www.glfw.org/license.html'),
        ('CPython',sys.version.split()[0],'PSF and bundled component licences; requires verification before release','runtime','intended','https://docs.python.org/3/license.html'),
        ('Tcl/Tk','requires verification before release','Tcl/Tk licence; requires verification before release','runtime','currently reachable through legacy UI imports','https://www.tcl-lang.org/software/tcltk/license.html'),
        ('Windows VC runtimes','requires verification before release','Microsoft redistribution terms; requires verification before release','runtime','as required by native binaries; includes installed glfw msvcr120.dll','https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files'),
        ('Pillow native codecs','requires verification before release','Multiple; requires verification before release','runtime','only exact wheel/deployed closure','https://pillow.readthedocs.io/en/stable/installation/building-from-source.html'),
        ('OpenGL/GLU system drivers','OS/vendor supplied','OS/vendor terms; requires verification before release','runtime','not redistributed','https://learn.microsoft.com/en-us/windows/win32/opengl/opengl'),
        ('PyOpenGL optional freeglut/GLE binaries','requires verification before release','See installed COPYING files; not needed by this app','runtime','exclude','https://github.com/mcfletch/pyopengl'),
        ('Staunton models','2014 source; converted meshes','MIT','asset','yes','https://github.com/clarkerubber/Staunton-Pieces'),
        ('ambientCG board maps','Marble012, Wood049, Fabric030; see assets/boards/sources.json','CC0-1.0','asset','yes','https://docs.ambientcg.com/license/'),
        ('Generated sounds / procedural geometry','application source','Application-owned; audit provenance of any replacement files','asset','yes; regenerate sounds in clean build','otb_chess/services/audio.py'),
        ('User UCI engines and books','user supplied','varies; requires verification before release if bundled','runtime','not bundled','docs/chess-backend-migration.md'),
        ('PyInstaller','not installed / not pinned','GPL with bootloader exception; requires verification before release','build','bootloader only if draft adopted','https://pyinstaller.org/en/stable/license.html'),
    ]
    for name,version,lic,category,ship,source in extras:
        records.append(dict(name=name,version=version,apparent_license=lic,category=category,redistribution=ship,source=source))
    for dist in metadata.distributions():
        if dist.metadata['Name'].lower().replace('-','_') in {p.lower().replace('-','_') for p in PACKAGES}:
            continue
        records.append(dict(name=dist.metadata['Name'],version=dist.version,
                            apparent_license=dist.metadata.get('License-Expression') or dist.metadata.get('License') or 'requires verification before release',
                            category='development environment',redistribution='no; not an application dependency'))
    result = dict(schema_version=1,status='development inventory, NOT release clearance',components=records,imports=imports,
                  qt_modules=sorted({i['module'] for i in imports if i['module'].startswith('PySide6.')}))
    (ROOT/'third_party_bom.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    target = ROOT/'licenses'/'assets'
    target.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT/'assets/pieces/tournament/LICENSE',target/'Staunton-MIT.txt')
    print(f'Audited {len(paths)} Python files, {len(records)} components')


if __name__ == '__main__':
    audit()
