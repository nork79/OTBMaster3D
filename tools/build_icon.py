"""Render the original vector app icon into PNG and Windows ICO sizes."""
from pathlib import Path
from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


def build():
    folder = Path(__file__).resolve().parents[1] / "assets"
    renderer = QSvgRenderer(str(folder / "app-icon.svg"))
    if not renderer.isValid():
        raise ValueError("Invalid app icon SVG")
    image = QImage(1024, 1024, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    image.save(str(folder / "app-icon.png"))
    with Image.open(folder / "app-icon.png") as source:
        source.save(folder / "app-icon.ico", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])


if __name__ == "__main__":
    build()
