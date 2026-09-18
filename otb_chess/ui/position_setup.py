"""Position editor with live FEN import/export and explicit chess state."""
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QIcon, QCursor
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QToolButton, QButtonGroup, QLineEdit, QComboBox,
    QCheckBox, QFormLayout, QDialogButtonBox, QApplication)
from otb_chess.chess_backend import rules as chess
from otb_chess.services.settings import APP_DIR


class SetupSquare(QToolButton):
    erase_requested = Signal()
    toggle_requested = Signal()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self.erase_requested.emit()
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self.toggle_requested.emit()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() in (Qt.MouseButton.MiddleButton, Qt.MouseButton.RightButton):
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class PositionSetup(QDialog):
    def __init__(self, parent, fen):
        super().__init__(parent)
        self.setWindowTitle('Setup Position')
        self.setObjectName('positionSetup')
        self.board = chess.Board(fen)
        self.selected_piece = 'P'
        self.picked_square = None
        self.piece_icons = {symbol: QIcon(str(APP_DIR/'assets'/'pieces_2d'/'textbook'/
                            (('w' if symbol.isupper() else 'b')+symbol.lower()+'.png')))
                            for symbol in 'KQRBNPkqrbnp'}
        self.syncing = False
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        for title, callback in (('Starting position',lambda: self.replace_board(chess.Board())),
                                ('Empty board',lambda: self.replace_board(chess.Board(None))),
                                ('Paste FEN',lambda: self.fen.setText(QApplication.clipboard().text().strip()))):
            button = QPushButton(title)
            button.clicked.connect(callback)
            top.addWidget(button)
        layout.addLayout(top)
        body = QHBoxLayout()
        grid = QGridLayout()
        grid.setSpacing(0)
        self.squares = {}
        for row in range(8):
            for file in range(8):
                square = chess.square(file,7-row)
                button = SetupSquare()
                button.setIconSize(QSize(42,42))
                button.setFixedSize(46,46)
                name = f'{chr(97+file)}{8-row}'
                button.setAccessibleName(name)
                button.setToolTip(name+' — left-click to pick up or drop; right-click to toggle colour; middle-click to erase')
                button.setStyleSheet('QToolButton { border: none; border-radius: 0; padding: 0; background: '+('#ead8b6' if (file+row)%2 == 0 else '#a98560')+'; }')
                button.erase_requested.connect(lambda s=square: self.place(s,erase=True))
                button.clicked.connect(lambda checked=False,s=square: self.click_square(s))
                button.toggle_requested.connect(lambda s=square: self.toggle_colour(s))
                button.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
                grid.addWidget(button,row,file)
                self.squares[square] = button
            grid.addWidget(QLabel(str(8-row)),row,8)
        for file in range(8):
            label = QLabel(chr(97+file))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(label,8,file)
        body.addLayout(grid)
        palette = QVBoxLayout()
        palette.addWidget(QLabel('Left-click a piece to pick it up, then click to drop.\nDropping replaces any piece on that square.\nRight-click to toggle colour; middle-click to erase.'))
        pieces = QGridLayout()
        group = QButtonGroup(self)
        for row,symbols in enumerate(('KQRBNP','kqrbnp')):
            for column,symbol in enumerate(symbols):
                piece = chess.Piece.from_symbol(symbol)
                button = QPushButton()
                button.setIcon(self.piece_icons[symbol])
                button.setIconSize(QSize(32,32))
                button.setFixedSize(38,42)
                button.setStyleSheet('padding: 2px;')
                button.setAccessibleName(('White ' if piece.color else 'Black ')+symbol.upper())
                button.setCheckable(True)
                button.setChecked(symbol == self.selected_piece)
                button.clicked.connect(lambda checked=False,s=symbol: self.select_piece(s))
                group.addButton(button)
                pieces.addWidget(button,row,column)
        palette.addLayout(pieces)
        form = QFormLayout()
        self.turn = QComboBox()
        self.turn.addItems(['White','Black'])
        form.addRow('Side to move',self.turn)
        rights = QHBoxLayout()
        self.castling = {}
        for label,square in (('K',7),('Q',0),('k',63),('q',56)):
            check = QCheckBox(label)
            check.setToolTip(('White' if label.isupper() else 'Black')+(' kingside' if label.lower()=='k' else ' queenside')+' castling')
            self.castling[square] = check
            rights.addWidget(check)
            check.toggled.connect(self.metadata_changed)
        form.addRow('Castling rights',rights)
        self.turn.currentIndexChanged.connect(self.metadata_changed)
        palette.addLayout(form)
        palette.addStretch()
        body.addLayout(palette)
        layout.addLayout(body)
        layout.addWidget(QLabel('FEN — paste or edit to update the board immediately'))
        self.fen = QLineEdit()
        self.fen.setObjectName('setupFen')
        self.fen.textChanged.connect(self.fen_changed)
        layout.addWidget(self.fen)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Use position')
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.refresh()

    def replace_board(self, board):
        self.picked_square = None
        self.board = board
        self.refresh()

    def select_piece(self, symbol):
        self.picked_square = None
        self.selected_piece = symbol
        self.refresh()

    def click_square(self, square):
        if self.picked_square is not None:
            source = self.picked_square
            self.picked_square = None
            piece = self.board.remove_piece_at(source)
            self.board.set_piece_at(square,piece)
            self.refresh()
        elif self.board.piece_at(square):
            self.picked_square = square
            self.refresh()
        else:
            self.place(square)

    def toggle_colour(self, square):
        piece = self.board.piece_at(square)
        if piece:
            self.board.set_piece_at(square,chess.Piece(piece.piece_type,not piece.color))
            self.refresh()

    def place(self, square, erase=False):
        if square == self.picked_square:
            self.picked_square = None
        piece = None if erase else chess.Piece.from_symbol(self.selected_piece)
        self.board.set_piece_at(square,piece)
        self.refresh()

    def metadata_changed(self, *args):
        if self.syncing:
            return
        self.board.turn = self.turn.currentIndex() == 0
        self.board.castling_rights = sum(1 << square for square,check in self.castling.items() if check.isChecked())
        self.refresh()

    def fen_changed(self, text):
        if self.syncing:
            return
        try:
            self.board = chess.Board(text.strip())
        except ValueError as error:
            self.status.setText('Invalid FEN: '+str(error))
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            return
        self.picked_square = None
        self.refresh()

    def refresh(self, update_fen=True):
        self.board.ep_square = None
        self.board.halfmove_clock = 0
        self.board.fullmove_number = 1
        self.syncing = True
        try:
            held = self.board.piece_at(self.picked_square) if self.picked_square is not None else None
            cursor = (QCursor(self.piece_icons[held.symbol()].pixmap(36,36),18,18)
                      if held else QCursor(Qt.CursorShape.ArrowCursor))
            for square,button in self.squares.items():
                piece = self.board.piece_at(square)
                button.setIcon(self.piece_icons[piece.symbol()] if piece and square != self.picked_square else QIcon())
                button.setCursor(cursor)
            self.turn.setCurrentIndex(0 if self.board.turn else 1)
            for square,check in self.castling.items():
                check.setChecked(bool(self.board.castling_rights & (1 << square)))
            if update_fen:
                # Preserve explicitly selected rights even while the position is incomplete.
                fields = self.board.fen(en_passant='fen').split()
                fields[2] = ''.join(label for label,square in (('K',7),('Q',0),('k',63),('q',56)) if self.board.castling_rights & (1<<square)) or '-'
                self.fen.setText(' '.join(fields))
            valid = self.board.is_valid()
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(valid)
            self.status.setText('Ready — use this position, then press Start game.' if valid else
                'Incomplete or illegal position. Check both kings, pawn ranks, side to move and castling.')
        finally:
            self.syncing = False

    def accept(self):
        try:
            board = chess.Board(self.fen.text().strip())
        except ValueError:
            return
        board.ep_square = None
        board.halfmove_clock = 0
        board.fullmove_number = 1
        if board.is_valid():
            self.board = board
            super().accept()
