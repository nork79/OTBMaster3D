"""Compiler environment must replace PATH regardless of Windows key casing."""
import unittest
from unittest.mock import patch

from tools.build_native_runtime import compiler_environment, resolve_build_tools


class NativeRuntimeBuildTests(unittest.TestCase):
    def test_vcvars_overrides_old_path_in_either_case(self):
        for original, updated in (('PATH', 'Path'), ('Path', 'PATH')):
            env = compiler_environment(
                {original: 'old-path', 'TEMP': 'temporary'},
                f'{updated}=compiler-path\nVCToolsVersion=14.44\n=C:=ignored\nVALUE=a=b')
            self.assertEqual(env['PATH'], 'compiler-path')
            self.assertEqual(sum(key.lower() == 'path' for key in env), 1)
            self.assertEqual(env['TEMP'], 'temporary')
            self.assertEqual(env['VCTOOLSVERSION'], '14.44')
            self.assertEqual(env['VALUE'], 'a=b')
            with patch('tools.build_native_runtime.shutil.which',
                       side_effect=lambda name, path: path + '/' + name):
                self.assertEqual(resolve_build_tools(env)['rc.exe'], 'compiler-path/rc.exe')

    def test_missing_tool_has_actionable_error(self):
        with patch('tools.build_native_runtime.shutil.which', return_value=None):
            with self.assertRaisesRegex(RuntimeError, 'rc.exe.*Windows SDK'):
                resolve_build_tools({'PATH': 'incomplete'})
