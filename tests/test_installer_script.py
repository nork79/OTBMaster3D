"""Exercise the build wrapper in an isolated tree with stub build tools."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
VERSION_FILES = ('otb_chess/version.py', 'packaging/windows-installer.iss',
                 'packaging/version-info.txt')


@unittest.skipUnless(os.name == 'nt', 'Windows PowerShell build wrapper')
class InstallerScriptTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        for name in (*VERSION_FILES, 'tools/build_installer.ps1'):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        (self.root / 'python.ps1').write_text('''
Add-Content calls.txt ($args -join ' ')
if ((Test-Path fail.txt) -and ($args -contains 'tools/install_stockfish.py')) { exit 7 }
exit 0
''')
        (self.root / 'compiler.ps1').write_text('''
$text = Get-Content packaging/windows-installer.iss -Raw
$version = [regex]::Match($text, '#define AppVersion "([^"]+)"').Groups[1].Value
New-Item -ItemType Directory -Force installer-output | Out-Null
Set-Content "installer-output/OTBMaster3D-$version-Setup.exe" 'stub installer'
exit 0
''')

    def run_build(self, *arguments):
        return subprocess.run(
            ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
             str(self.root / 'tools/build_installer.ps1'),
             '-Python', './python.ps1', '-Compiler', './compiler.ps1', *arguments],
            cwd=self.root, capture_output=True, text=True, timeout=30)

    def test_version_build_synchronizes_metadata_and_reports_success(self):
        result = self.run_build('--version', '1.7')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('[SUCCESS]', result.stdout)
        self.assertTrue((self.root / 'installer-output/OTBMaster3D-1.7-Setup.exe').is_file())
        self.assertIn('__version__ = "1.7"', (self.root / VERSION_FILES[0]).read_text())
        self.assertIn('VersionInfoVersion=1.7.0.0', (self.root / VERSION_FILES[1]).read_text())
        metadata = (self.root / VERSION_FILES[2]).read_text(encoding='utf-8')
        for field in ('filevers', 'prodvers'):
            self.assertIn(f'{field}=(1,7,0,0)', metadata)
        for field in ('FileVersion', 'ProductVersion'):
            self.assertIn(f"StringStruct('{field}', '1.7')", metadata)
        self.assertIn('Desktop Chess', metadata)

    def test_interactive_double_dash_version(self):
        for invocation in (
                '.\\tools\\build_installer.ps1 --version "1.6.7" -DryRun',
                '.\\tools\\build_installer.ps1 --version "1.6.7" -Python .\\python.ps1 -Compiler .\\compiler.ps1'):
            result = subprocess.run(
                ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', invocation],
                cwd=self.root, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('Building OTBMaster3D 1.6.7', result.stdout)
            self.assertIn('Windows numeric version: 1.6.7.0', result.stdout)
        self.assertTrue((self.root / 'installer-output/OTBMaster3D-1.6.7-Setup.exe').is_file())

    def test_failed_step_stops_build_and_returns_error(self):
        (self.root / 'fail.txt').touch()
        result = self.run_build('-Version', '1.7.2')
        self.assertEqual(result.returncode, 1)
        self.assertIn('Stockfish setup failed (exit code 7)', result.stderr)
        self.assertNotIn('install_fairy_stockfish', (self.root / 'calls.txt').read_text())
        self.assertFalse((self.root / 'installer-output').exists())

    def test_arbitrary_release_labels_build_with_numeric_windows_metadata(self):
        for label, numeric in (('test-build', '0.0.0.0'), ('1.7-beta', '1.7.0.0'),
                               ('v2.3.4.5', '2.3.4.5'), ('999999999999999999999.2', '65535.2.0.0')):
            result = self.run_build('--version', label)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn(f'VersionInfoVersion={numeric}', (self.root / VERSION_FILES[1]).read_text())
            self.assertTrue((self.root / f'installer-output/OTBMaster3D-{label}-Setup.exe').is_file())

    def test_dry_run_does_not_change_files(self):
        original = [(self.root / name).read_bytes() for name in VERSION_FILES]
        for version in ('1.7', '1.7.3', 'bad', '1.2.3.4', '65536.0', 'release/test build'):
            result = self.run_build('--version', version, '-DryRun')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(original, [(self.root / name).read_bytes() for name in VERSION_FILES])
        self.assertFalse((self.root / 'calls.txt').exists())
