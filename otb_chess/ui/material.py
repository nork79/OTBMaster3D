"""Captured pieces from recorded moves and material on the displayed board."""
from collections import Counter

from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QLabel, QSizePolicy

from otb_chess.chess_backend import rules as chess


VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
          chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
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
        painter.setPen(self.palette().windowText().color())
        metrics = painter.fontMetrics()
        width = max(metrics.horizontalAdvance(piece) for piece in self.text())
        step = min(width * .68, max(0, self.width()-width) / max(1, len(self.text())-1))
        baseline = (self.height() + metrics.ascent() - metrics.descent()) // 2
        for index, piece in enumerate(self.text()):
            painter.drawText(round(index * step), baseline, piece)
        painter.end()


def material_summary(board):
    captured = {chess.WHITE: Counter(), chess.BLACK: Counter()}
    history = board.copy()
    while history.move_stack:
        move = history.pop()
        if history.is_en_passant(move):
            captured[history.turn][chess.PAWN] += 1
        else:
            piece = history.piece_at(move.to_square)
            if piece is not None and piece.color != history.turn:
                captured[history.turn][piece.piece_type] += 1
    rows = {}
    for color in (chess.WHITE, chess.BLACK):
        pieces = []
        for kind in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT, chess.PAWN):
            count = captured[color][kind]
            if count:
                symbol = SYMBOLS[not color][6-kind]
                pieces.append(symbol * count)
        rows[color] = ''.join(pieces)
    balance = sum(VALUES[piece.piece_type] * (1 if piece.color else -1)
                  for piece in board.piece_map().values())
    return rows, balance
