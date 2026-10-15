"""Build GLFW 3.4 with the installed VS2022 compiler; retain exact inputs/logs.

No source patches. The source list follows upstream src/CMakeLists.txt for
Win32 + null backends. /MD selects the shared release CRT.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VS = Path(os.environ.get('OTB_VS_ROOT', 'C:/Program Files/Microsoft Visual Studio/2022/Community'))
OUT = ROOT / 'build/native-runtime'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compiler_environment(base, output):
    """Merge cmd's environment with Windows' case-insensitive key semantics."""
    env = {key.upper(): value for key, value in base.items()}
    for line in output.splitlines():
        if '=' in line and not line.startswith('='):
            key, value = line.split('=', 1)
            env[key.upper()] = value
    return env


def resolve_build_tools(env):
    tools = {name: shutil.which(name, path=env.get('PATH', ''))
             for name in ('rc.exe', 'cl.exe', 'link.exe')}
    missing = [name for name, path in tools.items() if path is None]
    if missing:
        raise RuntimeError('Visual Studio environment is missing: ' + ', '.join(missing)
                           + '. Check the Visual Studio C++ tools and Windows SDK installation'
                           + ' and OTB_VS_ROOT.')
    return tools


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    inventory = json.loads((ROOT / 'docs/licensing/source-inventory.json').read_text())
    entry = next(x for x in inventory['sources'] if x['file'] == 'glfw-3.4.zip')
    archive = ROOT / 'release-materials/1.4.0-beta.2/sources' / entry['file']
    assert digest(archive) == entry['sha256'], 'GLFW source hash mismatch'
    with zipfile.ZipFile(archive) as z:
        z.extractall(OUT / 'source')
    source = OUT / 'source/glfw-3.4'
    vcvars = VS / 'VC/Auxiliary/Build/vcvars64.bat'
    command = f'call "{vcvars}" >nul && set'
    result = subprocess.run('cmd.exe /d /s /c "' + command + '"', capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    env = compiler_environment(os.environ, result.stdout)
    tools = resolve_build_tools(env)
    names = ('context init input monitor platform vulkan window egl_context osmesa_context '
             'null_init null_monitor null_window null_joystick win32_module win32_time '
             'win32_thread win32_init win32_joystick win32_monitor win32_window wgl_context').split()
    rc = (source / 'src/glfw.rc.in').read_text()
    for key, value in {'GLFW_VERSION_MAJOR':'3','GLFW_VERSION_MINOR':'4','GLFW_VERSION_PATCH':'0','GLFW_VERSION':'3.4.0'}.items():
        rc = rc.replace('@' + key + '@', value)
    (OUT / 'glfw.rc').write_text(rc)
    commands = [
        ['rc.exe', '/nologo', '/fo', 'glfw.res', 'glfw.rc'],
        ['cl.exe', '/nologo', '/O2', '/MD', '/DNDEBUG', '/D_GLFW_WIN32', '/D_GLFW_BUILD_DLL',
         '/I' + str(source / 'include'), '/I' + str(source / 'src'), '/LD',
         *[str(source / 'src' / (n + '.c')) for n in names], 'glfw.res',
         '/link', '/OUT:glfw3.dll', '/IMPLIB:glfw3.lib', '/MACHINE:X64',
         'user32.lib', 'gdi32.lib', 'shell32.lib'],
    ]
    with (OUT / 'build.log').open('w') as log:
        for args in commands:
            args[0] = tools[args[0]]
            log.write(subprocess.list2cmdline(args) + '\n'); log.flush()
            print('Running ' + args[0], flush=True)
            try:
                subprocess.run(args, cwd=OUT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
            except subprocess.CalledProcessError as exc:
                raise RuntimeError(f'{Path(args[0]).name} failed; see {OUT / "build.log"}') from exc
    import pefile
    pe = pefile.PE(str(OUT / 'glfw3.dll'))
    imports = [x.dll.decode() for x in pe.DIRECTORY_ENTRY_IMPORT]
    assert pe.FILE_HEADER.Machine == 0x8664
    assert 'msvcr120.dll' not in [s.lower() for s in imports]
    assert 'vcruntime140.dll' in [s.lower() for s in imports]
    evidence = {'source':entry, 'source_patches':[], 'environment_command':command,
                'toolset':env.get('VCTOOLSVERSION'), 'sdk':env.get('WINDOWSSDKVERSION'),
                'compiler_sha256':digest(Path(tools['cl.exe'])),
                'linker_sha256':digest(Path(tools['link.exe'])),
                'commands':commands, 'sha256':digest(OUT / 'glfw3.dll'), 'imports':imports,
                'architecture':'x64', 'configuration':'Release /O2 /MD; Win32 and null backends'}
    (OUT / 'build.json').write_text(json.dumps(evidence, indent=2))
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    build()
