"""PGN/SAN conversion boundary. Native trees/boards/moves never leave here."""
import io
import chess as _chess
import chess.pgn as _pgn
from otb_chess.document_state import Document, History
from otb_chess_core import Move


def _owned_move(move):
    return Move(move.from_square, move.to_square, move.promotion)


def _native_move(move):
    return _chess.Move(move.from_square, move.to_square, move.promotion)


def _history(game):
    board = game.end().board()
    return History(game.board().fen(), tuple(_owned_move(m) for m in board.move_stack), board.fen())


def _serialize(game):
    return game.accept(_pgn.StringExporter(headers=True, variations=True, comments=True)) + '\n'


def read_pgn(text):
    stream = io.StringIO(text.lstrip('\ufeff'))
    documents = []
    while (game := _pgn.read_game(stream)) is not None:
        if game.errors or not game.board().is_valid():
            raise ValueError('The PGN contains an invalid position or illegal moves.')
        documents.append(Document(dict(game.headers), _history(game), _serialize(game)))
    if not documents:
        raise ValueError('No PGN games found.')
    return documents


def export_pgn(history: History, original: Document | None = None, result=None):
    if (original is not None and original.history.root_fen == history.root_fen
            and original.history.moves == history.moves):
        # Retain the entire imported annotation/variation tree, not just mainline.
        game = _pgn.read_game(io.StringIO(original.annotated_pgn))
        game.headers.clear()
        game.headers.update(original.headers)
    else:
        board = _chess.Board(history.root_fen)
        for move in history.moves:
            board.push(_native_move(move))
        if board.fen() != history.final_fen:
            raise ValueError('History does not match its final position')
        game = _pgn.Game.from_board(board)
        if original is not None:
            for key, value in original.headers.items():
                if key not in ('FEN', 'SetUp', 'Result'):
                    game.headers[key] = value
    if result is not None:
        game.headers['Result'] = result
    return _serialize(game)


def san(fen: str, move: Move) -> str:
    return _chess.Board(fen).san(_native_move(move))
