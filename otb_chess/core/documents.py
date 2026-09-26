"""Notation import/export and non-destructive move-history browsing."""

from otb_chess.document_state import History
from otb_chess.chess_backend.position import ChessPosition


def read_pgn(text):
    return ChessPosition.read_pgn(text)


def read_fen(text):
    return ChessPosition.from_fen(text).legacy_board


class GameDocuments:
    _review_live = None
    _pgn_document = None
    _declared_result = None

    @property
    def position(self):
        """Authoritative chess state for the currently displayed controller board."""
        return self._position

    @property
    def board(self):
        # TODO extraction: migrate legacy consumers, then remove native exposure.
        return self.position.legacy_board

    @board.setter
    def board(self, board):
        self._position = ChessPosition.from_board(board)

    def history_position(self):
        return ChessPosition.from_board(self.history_board())

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
            self.board = self.history_position().at_ply(ply).legacy_board
            self.selected = self.drag_piece = self.drag_world = None
            self.result_text = "Reviewing moves — return to latest move to continue play"
            self.refresh_move_list()
        return True

    def load_document(self, board, document=None):
        board = (ChessPosition.from_history(board).legacy_board if isinstance(board, History)
                 else ChessPosition.from_board(board, copy=True).legacy_board)
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
        ending = self.position.termination()
        if ending is not None:
            self.game_over = True
            self.result_text = ending.reason
        elif self._declared_result is not None:
            self.game_over = True
            self.result_text = 'Imported result - ' + self._declared_result
        self.refresh_move_list()

    def export_pgn(self):
        position = self.history_position()
        result = self._declared_result if self.game_over else None
        ending = position.termination() if self.game_over else None
        if ending is not None:
            result = ending.result
        return position.export_pgn(self._pgn_document, result)
