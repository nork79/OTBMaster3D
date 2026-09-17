"""Install the pinned official Windows x64 Stockfish release, including its source."""
import hashlib
from pathlib import Path
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
URL = "https://github.com/official-stockfish/Stockfish/releases/download/sf_19/stockfish-windows-x86-64-universal.zip"
SHA256 = "3c8bf1f9ea66a09350a40df4f632288285ac206d99f33ab5842c408fc30b48a7"
EXE_SHA256 = "45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0"


def install():
    destination = ROOT / "engines" / "stockfish-19"
    executable = destination / "stockfish" / "stockfish-windows-x86-64-universal.exe"
    if executable.is_file() and hashlib.sha256(executable.read_bytes()).hexdigest() == EXE_SHA256:
        print(f"Stockfish 19 is ready: {executable}")
        return
    print("Downloading the official Stockfish 19 Windows x64 releaseâ€¦")
    with tempfile.TemporaryDirectory(prefix="otb-stockfish-") as temporary:
        archive = Path(temporary) / "stockfish.zip"
        with urllib.request.urlopen(URL, timeout=120) as response, archive.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
            raise ValueError("Stockfish archive checksum mismatch; nothing was installed")
        with zipfile.ZipFile(archive) as package:
            for entry in package.infolist():
                target = (destination / entry.filename).resolve()
                if not target.is_relative_to(destination.resolve()):
                    raise ValueError("Unsafe archive path")
            package.extractall(destination)
    print(f"Installed Stockfish 19: {executable}")


if __name__ == "__main__":
    install()
