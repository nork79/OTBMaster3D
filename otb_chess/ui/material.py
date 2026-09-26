"""Captured pieces from recorded moves and material on the displayed board."""

from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QLabel, QSizePolicy

from otb_chess.chess_backend import values as chess
from otb_chess.chess_backend.position import ChessPosition


SYMBOLS = {chess.WHITE: '\u2654\u2655\u2656\u2657\u2658\u2659',
           chess.BLACK: '\u265a\u265b\u265c\u265d\u265e\u265f'}


class CapturedPieces(QLabel):
    """Tightly spaced symbols that compress to fit the available row width."""

    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(25)
        self.setStyleSheet("font-family: 'Segoe UI Symbol'; font-size: 19px;")

    def paintEvent(self, event):
        if not self.text():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        metrics = painter.fontMetrics()
        width = max(metrics.horizontalAdvance(piece) for piece in self.text())
        step = min(width * .68, max(0, self.width()-width) / max(1, len(self.text())-1))
        baseline = (self.height() + metrics.ascent() - metrics.descent()) // 2
        for index, piece in enumerate(self.text()):
            white = piece in SYMBOLS[chess.WHITE]
            # Use a solid silhouette so white pieces have an opaque white body.
            glyph = SYMBOLS[chess.BLACK][SYMBOLS[chess.WHITE].index(piece)] if white else piece
            path = QPainterPath()
            path.addText(round(index * step), baseline, painter.font(), glyph)
            painter.setPen(QPen(QColor('#202020' if white else '#eeeeee'), .7))
            painter.setBrush(QColor('#ffffff' if white else '#202020'))
            painter.drawPath(path)
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
