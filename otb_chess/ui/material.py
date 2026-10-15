"""Captured pieces from recorded moves and material on the displayed board."""

from functools import lru_cache

from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QLabel, QSizePolicy

from otb_chess.chess_backend import values as chess
from otb_chess.chess_backend.position import ChessPosition


SYMBOLS = {chess.WHITE: '\u2654\u2655\u2656\u2657\u2658\u2659',
           chess.BLACK: '\u265a\u265b\u265c\u265d\u265e\u265f'}


@lru_cache(maxsize=48)
def captured_piece_image(symbol, size=25, device_pixel_ratio=1):
    """Classic pieces, resampled once to the actual display pixel size."""
    from PIL import Image
    from otb_chess.graphics.board_2d import piece_image

    white = symbol in SYMBOLS[chess.WHITE]
    kind = 6 - SYMBOLS[white].index(symbol)
    fill = (1, 1, 1) if white else (.125, .125, .125)
    source = piece_image(kind, fill, white)
    pixels = max(1, round(size * device_pixel_ratio))
    source = source.resize((pixels, pixels), Image.Resampling.LANCZOS)
    image = QImage(source.tobytes(), pixels, pixels,
                   QImage.Format.Format_RGBA8888).copy()
    image.setDevicePixelRatio(device_pixel_ratio)
    return image


class CapturedPieces(QLabel):
    """Tightly spaced symbols that compress to fit the available row width."""

    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(25)

    def paintEvent(self, event):
        if not self.text():
            return
        painter = QPainter(self)
        width = self.height()
        step = min(width * .68, max(0, self.width()-width) / max(1, len(self.text())-1))
        for index, piece in enumerate(self.text()):
            painter.drawImage(QRectF(round(index * step), 0, width, width),
                              captured_piece_image(piece, width, self.devicePixelRatioF()))
        painter.end()


def material_summary(board):
    captured, balance = ChessPosition.from_board(board).material()
    rows = {}
    for color in (chess.WHITE, chess.BLACK):
        pieces = []
        for kind in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT, chess.PAWN):
            count = captured[color][kind]
            if count:
                symbol = SYMBOLS[not color][6-kind]
                pieces.append(symbol * count)
        rows[color] = ''.join(pieces)
    return rows, balance
