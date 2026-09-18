"""A lightweight, clickable static-evaluation history chart."""
import math

from PySide6.QtCore import Qt, QPointF, QRectF, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QWidget

from otb_chess.core.evaluation import evaluate_position
from otb_chess.chess_backend import rules as chess
from otb_chess.chess_backend import notation


class EvaluationChart(QWidget):
    selected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.values = []
        self.current = 0
        self.setMinimumSize(320, 180)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName('Static evaluation by move; click to review a position')

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
        self.labels = []
        self.setWindowTitle('Evaluation Graph')
        self.resize(580,300)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Static evaluation · pawns · positive favours White'))
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
        signature = (history.root().fen(),tuple(move.uci() for move in history.move_stack))
        if signature != self.signature:
            board = history.root()
            values,labels = [],[]
            move_label = 'Starting position'
            for index in range(len(history.move_stack)+1):
                evaluation = evaluate_position(board)
                values.append(evaluation.centipawns/100 if evaluation.centipawns is not None
                              else (-math.inf if board.turn == chess.WHITE else math.inf))
                labels.append(f'{move_label}  ·  {evaluation.text}')
                if index < len(history.move_stack):
                    move = history.move_stack[index]
                    move_label = f'{board.fullmove_number}{"." if board.turn == chess.WHITE else "..."} {notation.san(board.fen(),chess.owned_move(move))}'
                    board.push(move)
            self.chart.values,self.labels = values,labels
            self.signature = signature
        self.chart.current = len(self.owner.game.board.move_stack)
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
