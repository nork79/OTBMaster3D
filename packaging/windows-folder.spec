# Build the application folder consumed by packaging/windows-installer.iss.
from pathlib import Path
from PyInstaller.utils.hooks import collect_dynamic_libs

root = Path(SPECPATH).parent
qt_modules = {'QtCore','QtGui','QtWidgets','QtOpenGL','QtOpenGLWidgets'}
a = Analysis(
    [str(root/'main.py')], pathex=[str(root)],
    datas=[(str(root/'assets'),'assets'), (str(root/'licenses'),'licenses'),
           (str(root/'LICENSE'),'.'),
           (str(root/'THIRD_PARTY_NOTICES.md'),'.'), (str(root/'third_party_bom.json'),'.'),
           (str(root/'engines'/'stockfish-19'),'engines/stockfish-19'),
           (str(root/'engines'/'maia'),'engines/maia'),
           (str(root/'engines'/'README.md'),'engines'),
           (str(root/'books'/'sources'),'books/sources'),
           (str(root/'books'/'README.md'),'books'),
           *[(str(p),'books') for p in sorted((root/'books').glob('lichess-*.bin'))]],
    binaries=collect_dynamic_libs('glfw'), hiddenimports=['cozy_chess'],
    excludes=['PySide6.QtTest','PySide6.QtNetwork','OpenGL.GLUT','OpenGL.GLE'],
    module_collection_mode={'PySide6':'py','shiboken6':'py'},
    noarchive=False,
)

# The stock hooks collect optional GL DLLs and Qt plugins not used by this app.
# Keep the Windows platform and ICO decoder; PNG support is in QtGui itself.
a.binaries = [entry for entry in a.binaries
              if not any(name in Path(entry[0]).name.lower() for name in ('freeglut', 'gle32'))
              # Dependencies of removed PDF/SVG and virtual-keyboard plugins.
              and Path(entry[0]).name.lower() not in (
                  'qt6pdf.dll', 'qt6svg.dll', 'qt6network.dll', 'qt6virtualkeyboard.dll',
                  'qt6quick.dll', 'qt6qml.dll', 'qt6qmlmeta.dll', 'qt6qmlmodels.dll',
                  'qt6qmlworkerscript.dll')
              and ('plugins/' not in entry[0].replace('\\','/').lower()
                   or Path(entry[0]).name.lower() in ('qwindows.dll', 'qico.dll'))]

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
        if name not in ('qwindows.dll', 'qico.dll'):
            raise RuntimeError(f'Unreviewed plugin: {destination}')
    if 'freeglut' in name or name.startswith('gle32'):
        raise RuntimeError(f'Unneeded optional OpenGL library: {destination}')

pyz = PYZ(a.pure)
exe = EXE(pyz,a.scripts,[],exclude_binaries=True,name='OTBMaster3D',
          console=False,upx=False,contents_directory='.',
          icon=str(root/'assets'/'app-icon.ico'),
          version=str(root/'packaging'/'version-info.txt'))
coll = COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='OTBMaster3D')
