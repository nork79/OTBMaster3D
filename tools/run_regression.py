"""Retain the full, unmodified unittest output and actual process exit status."""
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
log = root / 'docs/licensing/evidence/closure-regression-final.txt'
command = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v']
with log.open('wb') as output:
    result = subprocess.run(command, cwd=root, stdout=output, stderr=subprocess.STDOUT)
evidence = {'command': command, 'exit_code': result.returncode, 'raw_output': str(log)}
log.with_suffix('.json').write_text(json.dumps(evidence, indent=2))
print(json.dumps(evidence))
raise SystemExit(result.returncode)
