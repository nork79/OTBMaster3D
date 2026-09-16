"""Notation import/export and non-destructive move-history browsing."""

from otb_chess.chess_backend import notation
from otb_chess.chess_backend import rules as chess

import io


def read_pgn(text):
    stream = io.StringIO(text.lstrip('\ufeff'))
    games = []
    while (game := notation.read_game(stream)) is not None:
        if game.errors or not game.board().is_valid():
            raise ValueError("The PGN contains an invalid position or illegal moves.")
        games.append(game)
    if not games:
        raise ValueError("No PGN games found.")
    return games


def read_fen(text):
    board = chess.Board(text.strip())
    if not board.is_valid():
        raise ValueError("The FEN does not describe a valid chess position.")
    return board


class GameDocuments:
    _review_live = None
    _pgn_document = None

    def history_board(self):
        return self._review_live if self._review_live is not None else self.board

    def return_to_live(self):
        if self._review_live is not None:
            self.board = self._review_live
            self._review_live = None
            self.selected = self.drag_piece = self.drag_world = None
            self.refresh_move_list()

    def navigate_to_ply(self, ply):
        if self.game_started and not self.game_over and not self.clock_paused and self.board.move_stack:
            return False
        live = self.history_board()
        if not 0 <= ply <= len(live.move_stack):
            return False
        if ply == len(live.move_stack):
            self.return_to_live()
        else:
            self._review_live = live
            self.board = live.copy()
            while len(self.board.move_stack) > ply:
                self.board.pop()
            self.selected = self.drag_piece = self.drag_world = None
            self.result_text = "Reviewing moves — return to latest move to continue play"
            self.refresh_move_list()
        return True

    def load_document(self, board, document=None):
        self._review_live = None
        self._pgn_document = document
        self.board = board.copy()
        self.game_started = self.game_over = False
        self.clock_paused = True
        self.awaiting_clock_press = False
        self.awaiting_clock_color = None
        self.active_clock_color = self.board.turn
        self.clock_history.clear()
        self.pending_engine_move = self.pending_engine_position = None
        self.last_engine_search = None
        self.selected = self.drag_piece = self.drag_world = None
        self.result_text = "Loaded game/position — clocks stopped"
        self.refresh_move_list()

    def export_pgn(self):
        board = self.history_board()
        original = self._pgn_document
        if (original is not None and original.board().fen() == board.root().fen()
                and list(original.mainline_moves()) == board.move_stack):
            document = original
        else:
            document = notation.Game.from_board(board)
            if original is not None:
                for key,value in original.headers.items():
                    if key not in ('FEN','SetUp','Result'):
                        document.headers[key] = value
        return document.accept(notation.StringExporter(headers=True,variations=True,comments=True)) + '\n'
