# DRAFT ONLY: no installer; legal/source/binary audit gates remain unresolved.
# Run from repo root after selecting a verified PyInstaller version:
#   pyinstaller packaging/windows-folder.spec
from pathlib import Path

root = Path(SPECPATH).parent
qt_modules = {'QtCore','QtGui','QtWidgets','QtOpenGL','QtOpenGLWidgets'}
a = Analysis(
    [str(root/'main.py')], pathex=[str(root)],
    datas=[(str(root/'assets'),'assets'), (str(root/'licenses'),'licenses'),
           (str(root/'THIRD_PARTY_NOTICES.md'),'.'), (str(root/'third_party_bom.json'),'.')],
    binaries=[], hiddenimports=[],
    excludes=['PySide6.QtTest','OpenGL.GLUT','OpenGL.GLE'],
    module_collection_mode={'PySide6':'py','shiboken6':'py'},
    noarchive=False,
)

# Fail closed on unexpected Qt payload. Do not copy the whole Addons wheel.
for destination,source,kind in a.binaries:
    path = Path(destination.replace('\\','/'))
    name = path.name.lower()
    if name.startswith('qt6') and name.endswith('.dll'):
        module = 'Qt'+path.stem[3:]
        if module not in qt_modules:
            raise RuntimeError(f'Unreviewed Qt library: {destination}')
    if 'pyside6' in destination.lower() and name.startswith('qt') and name.endswith('.pyd'):
        if path.stem.split('.')[0] not in qt_modules:
            raise RuntimeError(f'Unreviewed Qt binding: {destination}')
    if 'plugins/' in destination.replace('\\','/').lower() and name.endswith('.dll'):
        if name != 'qwindows.dll':
            raise RuntimeError(f'Unreviewed plugin: {destination}')
    if 'freeglut' in name or name.startswith('gle32'):
        raise RuntimeError(f'Unneeded optional OpenGL library: {destination}')

pyz = PYZ(a.pure)
exe = EXE(pyz,a.scripts,[],exclude_binaries=True,name='OTBMaster3D',
          console=False,upx=False,contents_directory='.')
coll = COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='OTBMaster3D')
