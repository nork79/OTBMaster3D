"""External runtime packaging rejects accidental redistribution without deletion."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools import check_external_runtime as policy


class ExternalRuntimeTests(unittest.TestCase):
    def test_runtime_names_and_bootstrappers_are_rejected(self):
        for name in ('VCRUNTIME140.dll', 'msvcp140_2.dll', 'msvcr120.dll',
                     'ucrtbase.dll', 'concrt140.dll', 'api-ms-win-crt-runtime-l1-1-0.dll',
                     'D3DCompiler_47.dll', 'vc_redist.x64.exe', 'vcredist_x64.exe'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / name
                path.write_bytes(b'fixture')
                with self.assertRaises(ValueError):
                    policy.validate_files([path])
                self.assertEqual(path.read_bytes(), b'fixture')

    def test_renamed_microsoft_binary_is_rejected_by_version_resource(self):
        table = SimpleNamespace(entries={b'CompanyName': b'Microsoft Corporation'})
        pe = SimpleNamespace(FileInfo=[[SimpleNamespace(StringTable=[table])]],
                             parse_data_directories=lambda **kwargs: None)
        with patch.object(policy.pefile, 'PE') as constructor:
            constructor.return_value.__enter__.return_value = pe
            with self.assertRaisesRegex(ValueError, 'renamed.exe'):
                policy.validate_files([Path('renamed.exe')])

    def test_third_party_binary_is_not_rejected_for_importing_runtime(self):
        table = SimpleNamespace(entries={b'CompanyName': b'The Qt Company Ltd.'})
        pe = SimpleNamespace(FileInfo=[[SimpleNamespace(StringTable=[table])]],
                             parse_data_directories=lambda **kwargs: None)
        with patch.object(policy.pefile, 'PE') as constructor:
            constructor.return_value.__enter__.return_value = pe
            policy.validate_files([Path('Qt6Core.dll')])

    def test_missing_payload_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                policy.check_folder(folder)

    def test_non_binary_notices_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'Microsoft-terms.txt'
            path.write_text('Original licence text')
            policy.validate_files([path])
            self.assertEqual(path.read_text(), 'Original licence text')
