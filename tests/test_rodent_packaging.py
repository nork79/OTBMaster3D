"""Release payload validation without requiring a compiler or engine process."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import install_rodent


class RodentPackagingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.target = Path(temporary.name)
        names = ["rodent-iv.exe", "rodent-iv-source.zip", "LICENSE", "UPSTREAM-README.md",
                 "install_rodent.py", "personalities/basic.ini", "books/guide.bin", "books/rodent.bin"]
        names += [f"personalities/{key}.txt" for key in
                  ("tal", "kasparov", "morphy", "karpov", "petrosian", "default")]
        files = {}
        for name in names:
            path = self.target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(name.encode())
            files[name.replace("/", "\\")] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.manifest = dict(revision=install_rodent.REVISION,
                             source_sha256=files["rodent-iv-source.zip"], files=files)
        self.write_manifest()
        patcher = patch.object(install_rodent, "SOURCE_SHA256", files["rodent-iv-source.zip"])
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_manifest(self):
        (self.target / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def test_complete_payload_with_windows_manifest_paths(self):
        install_rodent.verify_installation(self.target)

    def test_missing_personality_rejected(self):
        (self.target / "personalities/tal.txt").unlink()
        with self.assertRaisesRegex(RuntimeError, "Rodent IV payload"):
            install_rodent.verify_installation(self.target)

    def test_changed_book_rejected(self):
        (self.target / "books/rodent.bin").write_bytes(b"changed")
        with self.assertRaisesRegex(RuntimeError, "Rodent IV payload"):
            install_rodent.verify_installation(self.target)

    def test_omitted_source_rejected_even_if_manifest_matches(self):
        del self.manifest["files"]["rodent-iv-source.zip"]
        self.write_manifest()
        with self.assertRaisesRegex(RuntimeError, "Rodent IV payload"):
            install_rodent.verify_installation(self.target)

    def test_wrong_revision_rejected(self):
        self.manifest["revision"] = "old-revision"
        self.write_manifest()
        with self.assertRaisesRegex(RuntimeError, "Rodent IV payload"):
            install_rodent.verify_installation(self.target)
