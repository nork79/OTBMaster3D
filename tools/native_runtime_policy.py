"""Select reviewed build inputs, checking hashes, architecture and CRT exports."""
import hashlib
import json
import os
from pathlib import Path
import pefile


def apply_policy(entries, root):
    selection = json.loads((root / 'docs/licensing/crt-selection.json').read_text())
    redist = Path(os.environ.get('OTB_CRT_ROOT', selection['directory']))
    glfw = root / 'build/native-runtime/glfw3.dll'
    built = json.loads((glfw.parent / 'build.json').read_text())
    assert hashlib.sha256(glfw.read_bytes()).hexdigest() == built['sha256']
    exports = {}
    for name, info in selection['files'].items():
        path = redist / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == info['sha256'], path
        pe = pefile.PE(str(path))
        assert pe.FILE_HEADER.Machine == 0x8664
        exports[name] = {s.name.decode() if s.name else s.ordinal for s in pe.DIRECTORY_ENTRY_EXPORT.symbols}
    result = []
    for dest, source, kind in entries:
        name = Path(dest).name.lower()
        if name == 'glfw3.dll':
            source = str(glfw)
            # The wrapper's package-directory fallback unconditionally preloads
            # MSVCR120. Its first lookup loads glfw3.dll from the executable
            # directory, so use that supported path for the rebuilt DLL.
            dest = 'glfw3.dll'
        if name == 'msvcr120.dll': continue  # verified again below, after GLFW substitution
        if name in selection['files']:
            old = pefile.PE(source)
            if hasattr(old, 'VS_FIXEDFILEINFO'):
                v = old.VS_FIXEDFILEINFO[0]
                version = [v.FileVersionMS>>16,v.FileVersionMS&65535,v.FileVersionLS>>16,v.FileVersionLS&65535]
                assert version <= selection['files'][name]['file_version'], (dest,version)
            source = str(redist / name)
        result.append((dest,source,kind))
    # Match all imported CRT symbols, including delay imports. Reject any residual
    # legacy CRT dependency rather than silently dropping its provider.
    for dest, source, kind in result:
        if Path(source).suffix.lower() not in ('.dll','.pyd','.exe'): continue
        pe = pefile.PE(source)
        for attr in ('DIRECTORY_ENTRY_IMPORT','DIRECTORY_ENTRY_DELAY_IMPORT'):
            for dep in getattr(pe,attr,[]):
                name = dep.dll.decode().lower()
                assert name not in ('msvcr100.dll','msvcr120.dll'), (dest,name)
                if name in exports:
                    needed = {s.name.decode() if s.name else s.ordinal for s in dep.imports}
                    assert needed <= exports[name], (dest,name,needed-exports[name])
    required = {'glfw3.dll', '_tkinter.pyd', 'tcl86t.dll', 'tk86t.dll', 'zlib1.dll'}
    present = {Path(dest).name.lower() for dest, _, _ in result}
    if not required <= present:
        raise RuntimeError(f'Native build dropped required runtime files: {required - present}. Check Tcl/Tk initialization and desktop access.')
    # Imports were checked against this exact supported runtime above. Setup
    # requires Microsoft's separately installed central runtime before installing the app.
    # The folder build consequently requires the same runtime on its host.
    return [entry for entry in result if Path(entry[0]).name.lower() not in selection['files']]
