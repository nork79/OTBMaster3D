"""Test byte-distinct LGPL runtime replacement in an isolated payload copy.

This tests loading without vendor hash/signature locks, not a source rebuild or
arbitrary ABI compatibility. The supplied payload is never modified.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile


def check(payload, output):
    payload = payload.resolve()
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    # Keep the isolated copy and evidence for review; do not remove user files.
    workspace = Path(__file__).resolve().parents[1] / '.tmp'
    workspace.mkdir(exist_ok=True)
    target = Path(tempfile.mkdtemp(prefix="lgpl-replacement-", dir=workspace)) / "app"
    shutil.copytree(payload, target)
    replacements = []
    for folder in ("PySide6", "shiboken6"):
        for path in sorted((target / folder).rglob("*")):
            if path.suffix.lower() not in (".dll", ".pyd"):
                continue
            if path.name.lower().startswith(("vcruntime", "msvcp")):
                continue
            if path.name.lower() == 'opengl32sw.dll':
                continue  # Mesa/LLVM are separate components, not LGPL Qt.
            original = path.read_bytes()
            # A PE overlay does not change exported interfaces or executable code.
            # Its changed hash establishes that the installed loader accepts a
            # byte-distinct replacement. It is not represented as rebuilt Qt.
            replacement = original + b"\nOTB LGPL replacement verification overlay\n"
            path.write_bytes(replacement)
            replacements.append({"path": path.relative_to(target).as_posix(),
                                 "original_sha256": hashlib.sha256(original).hexdigest(),
                                 "replacement_sha256": hashlib.sha256(replacement).hexdigest()})
    report = target.parent / "smoke.json"
    result = subprocess.run([str(target / "OTBMaster3D.exe"), "--smoke-test", str(report)],
                            cwd=target, timeout=90,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    smoke = json.loads(report.read_text(encoding="utf-8")) if report.exists() else {}
    evidence = {"scope": "Byte-distinct PE overlays; no native source rebuild",
                "payload_copy": str(target), "replacements": replacements,
                "exit_code": result.returncode, "smoke": smoke,
                "passed": result.returncode == 0 and smoke.get("ok") is True}
    output.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    return evidence["passed"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, default=Path("dist/OTBMaster3D"))
    parser.add_argument("--output", type=Path, default=Path(".tmp/lgpl-replacement.json"))
    args = parser.parse_args()
    raise SystemExit(0 if check(args.payload, args.output) else 1)
