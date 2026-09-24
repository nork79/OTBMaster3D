"""Notation import/export and non-destructive move-history browsing."""

from otb_chess.chess_backend import notation
from otb_chess.chess_backend import rules as chess

from otb_chess.document_state import History


def read_pgn(text):
    return notation.read_pgn(text)


def read_fen(text):
    board = chess.Board(text.strip())
    if not board.is_valid():
        raise ValueError("The FEN does not describe a valid chess position.")
    return board


class GameDocuments:
    _review_live = None
    _pgn_document = None
    _declared_result = None

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
        board = chess.restore_history(board) if isinstance(board, History) else board.copy()
        self._review_live = None
        self._pgn_document = document
        self._declared_result = (document.headers.get('Result') if document is not None else None)
        if self._declared_result not in ('1-0', '0-1', '1/2-1/2'):
            self._declared_result = None
        self.board = board
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
        reason = chess.termination_reason(self.board)
        if reason is not None:
            self.game_over = True
            self.result_text = reason
        elif self._declared_result is not None:
            self.game_over = True
            self.result_text = 'Imported result - ' + self._declared_result
        self.refresh_move_list()

    def export_pgn(self):
        board = self.history_board()
        result = self._declared_result if self.game_over else None
        if self.game_over and chess.termination_reason(board) is not None:
            result = board.result()
        return notation.export_pgn(chess.snapshot_history(board), self._pgn_document, result)
