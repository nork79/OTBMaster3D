"""Reject standalone Microsoft binaries in the externally provisioned payload.

This does not detect statically incorporated code or establish its licence.
"""
from pathlib import Path
import argparse
import re
import pefile


def forbidden_name(name):
    name = name.lower()
    return bool(re.fullmatch(
        r'(?:(?:vcruntime|msvcp|msvcr|concrt|vccorlib).*|ucrtbase[d]?|'
        r'api-ms-win-.*|ext-ms-win-.*|d3dcompiler_\d+)\.dll', name)
        or re.fullmatch(r'(?:vc_redist[._-].*|vcredist.*)\.exe', name))


def validate_files(paths):
    violations = []
    for path in paths:
        path = Path(path)
        if forbidden_name(path.name):
            violations.append(str(path))
            continue
        if path.suffix.lower() not in ('.dll', '.exe', '.pyd'):
            continue
        with pefile.PE(str(path), fast_load=True) as pe:
            pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_RESOURCE']])
            for group in getattr(pe, 'FileInfo', []):
                for info in group:
                    for table in getattr(info, 'StringTable', []):
                        company = table.entries.get(b'CompanyName', b'')
                        if b'microsoft' in company.lower():
                            violations.append(str(path))
    if violations:
        raise ValueError('Standalone Microsoft binaries are excluded: ' + ', '.join(sorted(set(violations))))


def check_folder(folder):
    folder = Path(folder)
    if not folder.is_dir() or not (folder / 'OTBMaster3D.exe').is_file():
        raise ValueError('Expected a complete frozen application folder')
    validate_files(p for p in folder.rglob('*') if p.is_file())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    check_folder(parser.parse_args().folder)
    print('PASS: no standalone Microsoft binaries found; static code is outside this check.')
