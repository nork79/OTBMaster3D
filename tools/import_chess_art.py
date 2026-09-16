"""Convert a local maurimo/chess-art checkout to bundled 2D PNG sets.

Usage: python tools/import_chess_art.py path/to/chess-art
QtSvg is used only by this build tool, not by the game renderer.
"""
from pathlib import Path
import shutil
import sys
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


def main(source):
    destination = Path(__file__).resolve().parents[1]/'assets'/'pieces_2d'
    for name in ('fantasy','celtic','spatial','skulls','eyes'):
        target = destination/name
        target.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source/'LICENSE',target/'LICENSE')
        for side in 'wb':
            for piece in 'pnbrqk':
                fancy = name in ('skulls','eyes')
                origin = source/'fancy'/name/(side+piece+'.svg') if fancy else source/name/(piece+'.svg')
                svg = origin.read_text(encoding='utf-8')
                if not fancy:
                    colours = ('#292723','#eee7d6','#fffaf0','#c8bda4') if side=='w' else ('#d6d2c8','#343b43','#59616d','#171b22')
                    for old,new in zip(('#ff0000','#00ff00','#ffffff','#00ffff'),colours):
                        svg = svg.replace(old,new)
                (target/(side+piece+'.svg')).write_text(svg,encoding='utf-8')
                renderer = QSvgRenderer(QByteArray(svg.encode('utf-8')))
                if not renderer.isValid():
                    raise ValueError(str(origin))
                image = QImage(256,256,QImage.Format.Format_RGBA8888)
                image.fill(Qt.GlobalColor.transparent)
                painter = QPainter(image)
                renderer.render(painter)
                painter.end()
                if not image.save(str(target/(side+piece+'.png'))):
                    raise RuntimeError('Could not save '+str(target))
        print('Imported',name)


if __name__ == '__main__':
    main(Path(sys.argv[1]))
