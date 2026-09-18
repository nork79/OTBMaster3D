"""Add source, exact runtime versions and licence evidence to the frozen folder."""
import importlib.metadata as metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def prepare():
    target = ROOT / "dist" / "OTBMaster3D"
    if not (target / "OTBMaster3D.exe").is_file():
        raise RuntimeError("Build the application with PyInstaller first")
    shutil.copy2(ROOT / "LICENSE", target / "LICENSE")
    source = target / "source"
    source.mkdir(exist_ok=True)
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    paths = set(filter(None, tracked)) | {"tools/prepare_installer_payload.py", "tools/build_installer.ps1",
                                        "docs/windows-installer.md"}
    with zipfile.ZipFile(source / "OTBMaster3D-source.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(paths):
            path = ROOT / name
            if path.is_file():
                archive.write(path, "OTBMaster3D/" + name)
    versions = {}
    for name in ("PySide6", "PySide6_Essentials", "PySide6_Addons", "shiboken6",
                 "glfw", "PyOpenGL", "Pillow", "chess", "cozy-chess-py", "pyinstaller"):
        distribution = metadata.distribution(name)
        versions[name] = distribution.version
        for entry in distribution.files or ():
            if '.dist-info/' in str(entry) and any(word in entry.name.lower() for word in ('license', 'licence', 'copying')):
                destination = target / "licenses" / "build" / name / entry.name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(distribution.locate_file(entry), destination)
    python_licence = Path(sys.base_prefix) / "LICENSE.txt"
    shutil.copy2(python_licence, target / "licenses" / "build" / "CPython-LICENSE.txt")
    manifest = {"python": sys.version, "packages": versions,
                "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
                "source": "source/OTBMaster3D-source.zip"}
    (target / "build-info.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    prepare()
