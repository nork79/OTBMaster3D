"""Non-modal presentation of engine results; no engine lifecycle ownership."""
from PySide6.QtCore import Qt, Signal, QByteArray
from PySide6.QtGui import QShortcut, QKeySequence, QTextCursor, QColor
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QPlainTextEdit, QTextEdit, QFormLayout, QSpinBox, QDoubleSpinBox, QSplitter, QWidget
from otb_chess.chess_backend.position import ChessPosition


class VariationText(QPlainTextEdit):
    selected_move = Signal(int, int)
    move_spans = ()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            position = self.cursorForPosition(event.position().toPoint()).position()
            for line, spans in enumerate(self.move_spans):
                for ply, (start, end) in enumerate(spans, 1):
                    if start <= position < end:
                        self.selected_move.emit(line, ply)
                        return


class EngineAnalysisWindow(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.setWindowTitle('Engine Analysis')
        self.setModal(False)
        self.resize(780, 1160)
        self.setMinimumSize(380, 230)
        self.lines = []
        self.best_lines = []
        self.candidates = {}
        self.candidate_position = None
        layout = QVBoxLayout(self)
        self.content_layout = layout
        self.line_view = VariationText()
        self.line_view.setMinimumHeight(150)
        self.line_view.setReadOnly(True)
        self.line_view.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        self.line_view.setPlaceholderText('Engine variations will appear here. Click a move to preview its position.')
        self.line_view.selected_move.connect(self.select_move)
        self.best_view = VariationText()
        self.best_view.setMinimumHeight(150)
        self.best_view.setReadOnly(True)
        self.best_view.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        self.best_view.setPlaceholderText('The best three moves found for this position will appear here.')
        self.best_view.selected_move.connect(lambda index, ply: self.select_move(index, ply, best=True))
        self.selected_variation = None
        self.context = QLabel('Click a variation move to preview its position on the board.')
        self.context.setWordWrap(True)
        self.previous = QPushButton('Previous Move')
        self.next = QPushButton('Next Move')
        self.return_button = QPushButton('Return to Current Position')
        self.previous.clicked.connect(lambda: self.step(-1))
        self.next.clicked.connect(lambda: self.step(1))
        self.return_button.clicked.connect(self.return_to_current)
        self.navigation = QHBoxLayout()
        for button in (self.previous, self.next, self.return_button):
            self.navigation.addWidget(button)
        for key, callback in (('Left', lambda: self.step(-1)), ('Right', lambda: self.step(1)),
                              ('Escape', self.return_to_current)):
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(callback)
        geometry = owner.game.cfg.get('engine_analysis_geometry')
        if isinstance(geometry, str):
            self.restoreGeometry(QByteArray.fromHex(geometry.encode('ascii', errors='ignore')))

    def finish_layout(self):
        self.analysis_splitter = QSplitter(Qt.Orientation.Vertical)
        for title, view in (('Best three moves found', self.best_view), ('Live analysis', self.line_view)):
            pane = QWidget()
            layout = QVBoxLayout(pane)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(QLabel(title))
            layout.addWidget(view)
            self.analysis_splitter.addWidget(pane)
        self.analysis_splitter.setChildrenCollapsible(False)
        self.analysis_splitter.setSizes([300, 300])
        self.analysis_splitter.setStretchFactor(0, 1)
        self.analysis_splitter.setStretchFactor(1, 1)
        self.content_layout.addWidget(self.analysis_splitter, 1)
        self.content_layout.addWidget(self.context)
        self.content_layout.addLayout(self.navigation)
        form = QFormLayout()
        self.options = {}
        saved = self.owner.game.cfg.get('analysis_options', {})
        for key, label, low, high, default in (
                ('multipv', 'Variation lines', 1, 20, 3),
                ('depth', 'Maximum depth (0 = unlimited)', 0, 99, 20),
                ('seconds', 'Time per search (seconds)', .1, 60, 1),
                ('threads', 'CPU threads', 1, 64, 1),
                ('hash_mb', 'Hash memory (MB)', 16, 4096, 64)):
            control = QDoubleSpinBox() if key == 'seconds' else QSpinBox()
            # Reserve space for Windows' side-by-side arrows in the themed stylesheet.
            control.setObjectName('analysisOption')
            control.setRange(low, high)
            control.setValue(saved.get(key, default))
            control.setKeyboardTracking(False)
            control.valueChanged.connect(self.change_options)
            self.options[key] = control
            form.addRow(label, control)
        self.content_layout.addLayout(form)
        self.content_layout.addWidget(QLabel('Search stops at the time or depth limit, whichever comes first.'))
        self.refresh_preview()

    def change_options(self):
        game = self.owner.game
        game.cfg['analysis_options'] = {key: control.value() for key, control in self.options.items()}
        game.analysis_revision += 1
        game.engine_output = None
        game.analysis_stamp = 0
        if game.analysis_engine is not None:
            game.analysis_engine.stop_search()
        game.persist()

    def present(self, source, evaluations, token, prefix=''):
        self.lines = self.render_lines(self.line_view, source, evaluations, token)
        if token is not None and token == self.owner.game.analysis_position_token():
            position_key = (source, token)
            if position_key != self.candidate_position:
                self.candidates.clear()
                self.candidate_position = position_key
            position = ChessPosition(source)
            for info in evaluations:
                if (info.source_fen != source or not info.pv or info.score is None
                        or (info.score.mate is None and info.score.centipawns is None)):
                    continue
                if len(position.variation_positions(info.pv[:1], truncate=True)) < 2:
                    continue
                # Retain each move's best score, even when deeper analysis revises it down.
                move = info.pv[0]
                key = (move.from_square, move.to_square, move.promotion)
                previous = self.candidates.get(key)
                if previous is None or (
                        self.rank_score(info, position.turn), info.depth or 0) > (
                        self.rank_score(previous, position.turn), previous.depth or 0):
                    self.candidates[key] = info
            best = sorted(self.candidates.values(),
                          key=lambda info: self.rank_score(info, position.turn), reverse=True)[:3]
            self.best_lines = self.render_lines(self.best_view, source, best, token)
        self.refresh_preview()

    @staticmethod
    def rank_score(info, white_to_move):
        score = info.score
        side = 1 if white_to_move else -1
        if score.mate is not None:
            mate = side * score.mate
            return (2, -mate) if mate > 0 else (0, -mate)
        return (1, side * score.centipawns)

    def render_lines(self, view, source, evaluations, token):
        lines, texts, all_spans = [], [], []
        offset = 0
        for info in evaluations:
            if info.source_fen != source:
                continue
            position = ChessPosition(source)
            moves, san = [], []
            positions = position.variation_positions(info.pv, truncate=True)
            for position, move in zip(positions[:-1], info.pv):
                if position.turn:
                    san.append(f'{position.fullmove_number}.')
                elif not san:
                    san.append(f'{position.fullmove_number}...')
                san.append(position.san(move))
                moves.append(move)
            score = info.score
            value = ('—' if score is None else f'Mate {score.mate:+d}' if score.mate is not None
                     else f'{score.centipawns / 100:+.2f}' if score.centipawns is not None else '—')
            text = f"{value}   Depth {info.depth if info.depth is not None else '-'}   "
            spans = []
            for word in san:
                start = offset + len(text)
                text += word + ' '
                if not word.endswith('.'):
                    spans.append((start, start + len(word)))
            text = text.rstrip()
            texts.append(text)
            all_spans.append(spans)
            offset += len(text) + 1
            lines.append((source, tuple(moves), token))
        view.setPlainText('\n'.join(texts))
        view.move_spans = all_spans
        return lines

    def select_move(self, index, ply, best=False):
        if self.select_line(index, best=best):
            self.owner.toggle_analysis(False)
            self.owner.game.step_variation(ply)
            self.refresh_preview()

    def select_line(self, index, best=False):
        lines = self.best_lines if best else self.lines
        if 0 <= index < len(lines):
            source, moves, token = lines[index]
            if not self.owner.game.begin_variation(source, moves, token, index+1):
                self.context.setText('This variation is stale or unavailable. Wait for current analysis.')
                return False
            self.selected_variation = lines[index]
            self.refresh_preview()
            return True
        return False

    def step(self, delta):
        self.owner.game.step_variation(delta)
        self.refresh_preview()

    def return_to_current(self):
        self.owner.game.end_variation()
        self.refresh_preview()

    def refresh_preview(self):
        g = self.owner.game
        g.validate_variation()
        if self.candidate_position is not None and self.candidate_position[1] != g.analysis_position_token():
            self.candidates.clear()
            self.candidate_position = None
            self.best_lines = []
            self.best_view.clear()
        if any(token is not None and token != g.analysis_position_token() for _, _, token in self.lines):
            self.lines = []
            self.line_view.clear()
        state = g.variation_preview
        for view, lines in ((self.line_view, self.lines), (self.best_view, self.best_lines)):
            selections = []
            if state is not None and self.selected_variation in lines:
                line = lines.index(self.selected_variation)
                ply = state['index']
                if 0 < ply <= len(view.move_spans[line]):
                    start, end = view.move_spans[line][ply-1]
                    selection = QTextEdit.ExtraSelection()
                    selection.cursor = QTextCursor(view.document())
                    selection.cursor.setPosition(start)
                    selection.cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
                    selection.format.setBackground(QColor('#d5944a'))
                    selection.format.setForeground(QColor('#161a20'))
                    selections.append(selection)
            view.setExtraSelections(selections)
        self.context.setText(g.preview_description or 'Click a variation move to preview its position on the board.')
        self.previous.setEnabled(state is not None and state['index'] > 0)
        self.next.setEnabled(state is not None and state['index'] < len(state['positions'])-1)
        self.return_button.setEnabled(state is not None)
        if hasattr(self.owner, 'preview_status'):
            self.owner.preview_status.setText(g.preview_description)
            self.owner.preview_status.setVisible(state is not None)
        self.owner.board_widget.update()

    def remember_geometry(self):
        self.owner.game.cfg['engine_analysis_geometry'] = bytes(self.saveGeometry().toHex()).decode('ascii')

    def closeEvent(self, event):
        self.return_to_current()
        self.remember_geometry()
        self.owner.engine_toggle.blockSignals(True)
        self.owner.engine_toggle.setChecked(False)
        self.owner.engine_toggle.blockSignals(False)
        self.owner.game.persist()
        event.accept()

    def reject(self):
        # Escape returns to play without closing the analysis window.
        self.return_to_current()
