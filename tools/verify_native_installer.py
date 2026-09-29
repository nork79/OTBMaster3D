"""Compare installed native bytes with the frozen inventory and hash the installer."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify():
    docs = ROOT / 'docs/licensing'
    frozen = json.loads((docs / 'native-runtime-after.json').read_text())
    installed = json.loads((docs / 'native-installed-inventory.json').read_text())
    expected = {x['path']:x['sha256'] for x in frozen['files']}
    actual = {x['path']:x['sha256'] for x in installed['files']}
    missing_or_changed = [p for p,h in expected.items() if actual.get(p) != h]
    extra = sorted(set(actual) - set(expected))
    if missing_or_changed or extra != ['unins000.exe']:
        raise RuntimeError({'missing_or_changed':missing_or_changed, 'unexpected':extra})
    if frozen['unresolved_imports'] or installed['unresolved_imports']:
        raise RuntimeError('Unresolved native imports')
    for filename in ('native-frozen-smoke.json','native-installed-smoke.json'):
        result = json.loads((docs / 'evidence' / filename).read_text())
        if not result['ok'] or not result['window_closed'] or result['event_loop_exit'] != 0:
            raise RuntimeError(filename)
    installer = ROOT / 'installer-output/OTBMaster3D-1.4.0-beta.2-Setup.exe'
    digest = hashlib.sha256(installer.read_bytes()).hexdigest()
    evidence = {'installer':installer.name,'sha256':digest,'bytes':installer.stat().st_size,
                'native_payload_files_matched':len(expected),'installed_extra':extra,
                'uninstaller_sha256':actual['unins000.exe'],
                'frozen_and_installed_smoke':'PASS', 'clean_windows_test':False,
                'release_status':'BLOCKED; see NATIVE_RUNTIME_REMEDIATION.md',
                'installed_application_source_sha256':json.loads((ROOT/'.tmp/native-installed/build-info.json').read_text())['source_sha256']}
    (docs / 'installer-verification.json').write_text(json.dumps(evidence,indent=2))
    installer.with_suffix('.exe.sha256').write_text(f'{digest}  {installer.name}\n')
    # Keep the older verification as historical evidence rather than letting its
    # unqualified ok=true appear to describe the replacement installer.
    previous = ROOT / 'installer-output/verification-1.4.0-beta.2.json'
    historical = docs / 'evidence/installer-verification-before-native.json'
    if previous.exists() and not historical.exists(): historical.write_bytes(previous.read_bytes())
    previous.write_text(json.dumps(evidence,indent=2))
    checksums = []
    for p in sorted(installer.parent.glob('*-Setup.exe')):
        checksums.append(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}')
    (installer.parent / 'SHA256SUMS.txt').write_text('\n'.join(checksums)+'\n')
    print(json.dumps(evidence,indent=2))


if __name__ == '__main__': verify()
