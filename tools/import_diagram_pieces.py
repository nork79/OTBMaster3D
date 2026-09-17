"""Build textbook and Chessnut PNGs from local Cburnett SVG artwork and Chessnut checkout.

Usage: python tools/import_diagram_pieces.py path/to/chess/svg.py path/to/chessnut-pieces path/to/Firi-pieceset
Only the Cburnett artwork dictionary is extracted, not python-chess program code.
"""
import ast
from pathlib import Path
import shutil
import sys
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


def rasterize(svg, destination):
    destination.with_suffix('.svg').write_text(svg,encoding='utf-8')
    renderer = QSvgRenderer(QByteArray(svg.encode('utf-8')))
    if not renderer.isValid():
        raise ValueError(str(destination))
    image = QImage(256,256,QImage.Format.Format_RGBA8888)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    if not image.save(str(destination.with_suffix('.png'))):
        raise RuntimeError(str(destination))


def main(svg_module, chessnut, firi):
    tree = ast.parse(svg_module.read_text(encoding='utf-8'))
    pieces = next(ast.literal_eval(node.value) for node in tree.body
                  if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PIECES' for t in node.targets))
    root = Path(__file__).resolve().parents[1]/'assets'/'pieces_2d'
    for style in ('textbook','chessnut','firi'):
        target = root/style
        target.mkdir(parents=True,exist_ok=True)
        for side in 'wb':
            for piece in 'pnbrqk':
                if style=='textbook':
                    content = pieces[piece.upper() if side=='w' else piece]
                    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 45 45">'+content+'</svg>'
                elif style=='chessnut':
                    svg = (chessnut/(side+piece.upper()+'.svg')).read_text(encoding='utf-8')
                else:
                    svg = (firi/'out'/(side+piece+'.svg')).read_text(encoding='utf-8')
                rasterize(svg,target/(side+piece))
    shutil.copyfile(chessnut/'LICENSE.txt',root/'chessnut'/'LICENSE')
    shutil.copyfile(chessnut/'COPYRIGHT.txt',root/'chessnut'/'COPYRIGHT.txt')
    shutil.copyfile(firi/'LICENSE.txt',root/'firi'/'LICENSE')


if __name__=='__main__':
    main(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]))
