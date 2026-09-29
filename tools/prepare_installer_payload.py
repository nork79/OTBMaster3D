"""Add source, exact runtime versions and licence evidence to the frozen folder."""
import importlib.metadata as metadata
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = ("LICENSE", "COPYRIGHT.md", "THIRD_PARTY_LICENSES.md",
             "THIRD_PARTY_NOTICES.md", "SOURCE_ACCESS.md", "third_party_bom.json")


def stage_notices(target):
    """Keep upstream bytes with short installed paths for Windows installers."""
    destination = target / 'licenses'
    if destination.resolve().parent != target.resolve():
        raise ValueError('Notice destination escapes payload')
    if destination.exists():
        shutil.rmtree(destination)
    (destination / 'documents').mkdir(parents=True)
    index = []
    for path in sorted((ROOT / 'licenses').rglob('*')):
        if not path.is_file():
            continue
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        name = digest + '.txt'
        (destination / 'documents' / name).write_bytes(content)
        index.append({'original': path.relative_to(ROOT).as_posix(),
                      'installed': 'licenses/documents/' + name, 'sha256': digest})
    (destination / 'notice-index.json').write_text(json.dumps(index, indent=2), encoding='utf-8')


def write_application_source(source):
    """Archive reviewed project files independently of a frozen build."""
    source.mkdir(parents=True, exist_ok=True)
    if (ROOT / ".git").exists():
        tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT).decode().splitlines()
    else:
        # A distributed source archive must remain buildable without Git history.
        snapshot = json.loads((ROOT / "release-source.json").read_text(encoding="utf-8"))
        tracked = snapshot["files"]
        revision = snapshot["base_commit"]
        status = ["Source archive build; file hashes identify any local modifications"]
    paths = set(filter(None, tracked)) | set(DOCUMENTS) | {
        "CODE_OF_CONDUCT.md", "SECURITY.md", "CONTRIBUTING.md", "README.md", ".gitattributes"}
    # Include newly added project files before staging, without collecting user data.
    for folder in ("otb_chess", "otb_chess_core", "tests", "tools", "packaging", "docs", "licenses"):
        for path in (ROOT / folder).rglob("*"):
            if path.is_file() and (folder == "licenses" or path.suffix in {
                    ".py", ".ps1", ".md", ".spec", ".iss", ".txt", ".json", ".csv", ".html", ".docx"}):
                paths.add(path.relative_to(ROOT).as_posix())
    source_hashes = {}
    with zipfile.ZipFile(source / "OTBMaster3D-source.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(paths):
            path = ROOT / name
            if not path.resolve().is_relative_to(ROOT.resolve()):
                raise ValueError(f"Source path escapes project: {name}")
            if path.is_file():
                content = path.read_bytes()
                source_hashes[name] = hashlib.sha256(content).hexdigest()
                archive.writestr("OTBMaster3D/" + name, content)
        archive.writestr("OTBMaster3D/release-source.json", json.dumps({
            "base_commit": revision, "working_tree_status": status,
            "files": sorted(source_hashes),
        }, indent=2))
    (source / "application-files.sha256.json").write_text(
        json.dumps(source_hashes, indent=2), encoding="utf-8")
    return revision, status


def prepare():
    target = ROOT / "dist" / "OTBMaster3D"
    if not (target / "OTBMaster3D.exe").is_file():
        raise RuntimeError("Build the application with PyInstaller first")
    from check_external_runtime import check_folder
    check_folder(target)
    for name in DOCUMENTS:
        shutil.copy2(ROOT / name, target / name)
    stage_notices(target)
    source = target / "source"
    source.mkdir(exist_ok=True)
    revision, status = write_application_source(source)
    versions = {}
    for name in ("PySide6", "PySide6_Essentials", "PySide6_Addons", "shiboken6",
                 "glfw", "PyOpenGL", "Pillow", "chess", "cozy-chess-py", "pyinstaller"):
        distribution = metadata.distribution(name)
        versions[name] = distribution.version
        for entry in distribution.files or ():
            if '.dist-info/' in str(entry) and any(word in entry.name.lower() for word in ('license', 'licence', 'copying', 'notice')):
                destination = target / "licenses" / "build" / name / str(entry).split('.dist-info/', 1)[1]
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(distribution.locate_file(entry), destination)
    python_licence = Path(sys.base_prefix) / "LICENSE.txt"
    shutil.copy2(python_licence, target / "licenses" / "build" / "CPython-LICENSE.txt")
    version_scope = {}
    exec((ROOT / "otb_chess" / "version.py").read_text(encoding="utf-8"), version_scope)
    # Frozen python-chess bytecode also requires the matching preferred source form.
    chess_source = source / "python-chess"
    chess_dist = metadata.distribution("chess")
    for entry in chess_dist.files or ():
        if str(entry).startswith("chess/") and str(entry).endswith((".py", ".typed")):
            destination = chess_source / str(entry)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(chess_dist.locate_file(entry), destination)
    shutil.copy2(ROOT / "licenses" / "chess" / "LICENSE.txt", chess_source / "LICENSE.txt")
    manifest = {"version": version_scope["__version__"], "python": sys.version, "packages": versions,
                "commit": revision,
                "working_tree_status": status,
                "source": "source/OTBMaster3D-source.zip",
                "source_sha256": hashlib.sha256((source / "OTBMaster3D-source.zip").read_bytes()).hexdigest(),
                "source_scope": "Application snapshot; dependency source closure still requires release review",
                "publication_status": "BLOCKED; see source archive docs/OPEN_SOURCE_RELEASE_READINESS.md"}
    (target / "build-info.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    prepare()
