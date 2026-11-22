"""A lightweight, clickable Stockfish evaluation history chart."""
import math

from PySide6.QtCore import Qt, QPointF, QRectF, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QWidget

from otb_chess.core.evaluation import evaluate_position
from otb_chess.chess_backend import rules as chess
from otb_chess.chess_backend import notation
from otb_chess.chess_backend.position import ChessPosition


def _format_score(score):
    if score.mate is not None:
        return f"Mate {score.mate:+d}"
    return f"{score.centipawns / 100:+.2f}"


def _score_pawns(score):
    if score.centipawns is not None:
        return score.centipawns / 100
    return math.inf if score.mate > 0 else -math.inf


def _parse_bar_evaluation(text: str) -> tuple[float, str]:
    clean = (text or "").strip()
    if not clean or clean == "—":
        return 0.5, ""
    if clean.startswith("Mate "):
        try:
            mate = int(clean.removeprefix("Mate ").strip())
        except ValueError:
            return 0.5, clean
        return (1.0 if mate > 0 else 0.0), f"M{abs(mate)}"
    lower = clean.lower()
    if "white wins" in lower or clean.endswith("1-0"):
        return 1.0, "1-0"
    if "black wins" in lower or clean.endswith("0-1"):
        return 0.0, "0-1"
    if "draw" in lower or "stalemate" in lower or clean.endswith("1/2-1/2"):
        return 0.5, "½-½"
    try:
        pawns = float(clean)
    except ValueError:
        return 0.5, clean
    ratio = 1.0 / (1.0 + math.exp(-0.4 * pawns))
    return max(0.03, min(0.97, ratio)), clean


class EvaluationBar(QWidget):
    """Lichess-style vertical evaluation bar reflecting the Move List score."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("evaluationBar")
        self.setFixedWidth(17)
        self.setMinimumHeight(180)
        self.score_text = ""
        self.badge_text = ""
        self.white_ratio = 0.5
        self.facing = "white"
        self.setAccessibleName("Vertical position evaluation bar")
        self.setToolTip("Stockfish searches each new position for two seconds. Positive values favour White.")

    def set_facing(self, facing: str):
        normalized = "black" if facing == "black" else "white"
        if normalized != self.facing:
            self.facing = normalized
            self.update()

    def set_evaluation(self, text: str, tooltip: str = "", *, facing: str | None = None):
        clean_text = (text or "").strip()
        ratio, badge = _parse_bar_evaluation(clean_text)
        changed = (
            clean_text != self.score_text
            or badge != self.badge_text
            or abs(ratio - self.white_ratio) > 1e-6
        )
        self.score_text = clean_text
        self.badge_text = badge
        self.white_ratio = ratio
        if facing is not None:
            norm_facing = "black" if facing == "black" else "white"
            if norm_facing != self.facing:
                self.facing = norm_facing
                changed = True
        if tooltip and tooltip != self.toolTip():
            self.setToolTip(tooltip)
        if changed:
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0.5, 0.5, max(1.0, self.width() - 1.0), max(1.0, self.height() - 1.0))
        white_color = QColor("#e8e6e3")
        black_color = QColor("#262421")
        if self.facing == "white":
            black_h = rect.height() * (1.0 - self.white_ratio)
            painter.fillRect(QRectF(rect.left(), rect.top(), rect.width(), black_h), black_color)
            painter.fillRect(
                QRectF(rect.left(), rect.top() + black_h, rect.width(), rect.height() - black_h),
                white_color,
            )
            badge_at_bottom = self.white_ratio >= 0.5
        else:
            white_h = rect.height() * self.white_ratio
            painter.fillRect(QRectF(rect.left(), rect.top(), rect.width(), white_h), white_color)
            painter.fillRect(
                QRectF(rect.left(), rect.top() + white_h, rect.width(), rect.height() - white_h),
                black_color,
            )
            badge_at_bottom = self.white_ratio < 0.5

        mid_y = rect.center().y()
        painter.setPen(QPen(QColor(180, 120, 70, 170), 1.2))
        painter.drawLine(QPointF(rect.left(), mid_y), QPointF(rect.right(), mid_y))

        if self.badge_text:
            font = QFont(self.font())
            font.setPointSizeF(5.5)
            font.setBold(True)
            painter.setFont(font)
            white_advantage = self.white_ratio >= 0.5
            painter.setPen(black_color if white_advantage else white_color)
            text_rect = (
                QRectF(rect.left(), rect.bottom() - 16, rect.width(), 14)
                if badge_at_bottom
                else QRectF(rect.left(), rect.top() + 2, rect.width(), 14)
            )
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.badge_text)

        painter.setPen(QPen(QColor("#4a4744"), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)


class EvaluationChart(QWidget):
    selected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.values = []
        self.current = 0
        self.setMinimumSize(320, 180)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName('Stockfish evaluation by move; click to review a position')

    def plot_rect(self):
        return QRectF(52, 20, max(1, self.width()-72), max(1, self.height()-58))

    def point(self, index, value, limit):
        rect = self.plot_rect()
        return QPointF(rect.left()+rect.width()*index/max(1,len(self.values)-1),
                       rect.center().y()-rect.height()*.5*value/limit)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.values:
            rect = self.plot_rect()
            fraction = max(0, min(1, (event.position().x()-rect.left())/rect.width()))
            self.selected.emit(round(fraction*(len(self.values)-1)))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.plot_rect()
        ink = self.palette().text().color()
        grid = QColor(ink)
        grid.setAlpha(55)
        finite = [abs(value) for value in self.values if math.isfinite(value)]
        limit = max(1, math.ceil(max(finite, default=0)))
        for value in (-limit,0,limit):
            y = self.point(0,value,limit).y()
            painter.setPen(QPen(grid,1))
            painter.drawLine(QPointF(rect.left(),y),QPointF(rect.right(),y))
            painter.setPen(ink)
            painter.drawText(QRectF(0,y-10,46,20),Qt.AlignmentFlag.AlignRight,f'{value:+.0f}')
        painter.drawText(QRectF(rect.left(),rect.bottom()+8,70,22),'Start')
        painter.drawText(QRectF(rect.right()-110,rect.bottom()+8,110,22),
                         Qt.AlignmentFlag.AlignRight,f'{max(0,len(self.values)-1)} plies')
        if not self.values:
            return
        path = QPainterPath()
        points = [self.point(i,max(-limit,min(limit,v)),limit) for i,v in enumerate(self.values)]
        path.moveTo(points[0])
        for point in points[1:]:
            path.lineTo(point)
        painter.setPen(QPen(QColor('#dba35e'),2.2))
        painter.drawPath(path)
        point = points[min(self.current,len(points)-1)]
        painter.setPen(QPen(ink,1,Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(point.x(),rect.top()),QPointF(point.x(),rect.bottom()))
        painter.setBrush(QColor('#dba35e'))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(point,4,4)


class EvaluationGraph(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.signature = None
        self._scores_version = -1
        self.labels = []
        self.setWindowTitle('Evaluation Graph')
        self.resize(580,300)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Stockfish evaluation · pawns · positive favours White'))
        self.chart = EvaluationChart(self)
        layout.addWidget(self.chart,1)
        self.position_label = QLabel()
        self.position_label.setWordWrap(True)
        layout.addWidget(self.position_label)
        layout.addWidget(QLabel('Click to review a position. Live play pauses; Resume clock continues play.'))
        self.chart.selected.connect(self.select_ply)
        self.timer = QTimer(self)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.refresh)
        self.refresh()

    def showEvent(self, event):
        self.refresh()
        self.timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def refresh(self):
        history = self.owner.game.history_board()
        root_fen = history.root().fen()
        signature = (root_fen, tuple(move.uci() for move in history.move_stack))
        scores_cache = getattr(self.owner, "_stockfish_scores", {})
        scores_version = getattr(self.owner, "_stockfish_scores_version", 0)
        if signature != self.signature or scores_version != self._scores_version:
            pos = ChessPosition(root_fen)
            values, labels = [], []
            move_label = 'Starting position'
            has_uncached = False
            for index in range(len(history.move_stack) + 1):
                board = pos.legacy_board
                static_eval = evaluate_position(board)
                key = (root_fen, pos.moves)
                cached = scores_cache.get(key)
                if static_eval.result:
                    values.append(
                        static_eval.centipawns / 100
                        if static_eval.centipawns is not None
                        else (-math.inf if board.turn == chess.WHITE else math.inf)
                    )
                    score_text = static_eval.text
                elif cached is not None:
                    score = cached[0]
                    values.append(_score_pawns(score))
                    score_text = _format_score(score)
                else:
                    has_uncached = True
                    values.append(static_eval.centipawns / 100)
                    score_text = static_eval.text
                labels.append(f'{move_label}  ·  {score_text}')
                if index < len(history.move_stack):
                    move = history.move_stack[index]
                    move_label = f'{board.fullmove_number}{"." if board.turn == chess.WHITE else "..."} {notation.san(board.fen(), chess.owned_move(move))}'
                    pos.apply(chess.owned_move(move))
            self.chart.values, self.labels = values, labels
            self.signature = signature
            self._scores_version = scores_version
            if has_uncached:
                request_fn = getattr(self.owner, "request_game_evaluation", None)
                if callable(request_fn):
                    request_fn()
        hist_moves = self.owner.game.history_position().moves
        cur_moves = self.owner.game.position.moves
        common = 0
        while common < len(cur_moves) and common < len(hist_moves) and cur_moves[common] == hist_moves[common]:
            common += 1
        self.chart.current = min(common, max(0, len(self.labels) - 1))
        self.position_label.setText(self.labels[self.chart.current])
        self.chart.update()

    def select_ply(self, ply):
        game = self.owner.game
        # Refresh first in case the game changed since the last timer event.
        self.refresh()
        if not 0 <= ply < len(self.chart.values):
            return
        if game.game_started and not game.game_over and not game.clock_paused:
            game.update_clock()
            game.stop_clock()
        if game.navigate_to_ply(ply):
            game.move_animation = None
            self.owner.refresh_moves()
            self.owner.board_widget.update()
        self.refresh()
