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


def _parse_time_control_initial(header_value: str) -> float | None:
    raw = (header_value or "").strip()
    if not raw or raw in ("-", "?"):
        return None
    first_stage = raw.split(":", 1)[0].strip()
    if "/" in first_stage:
        first_stage = first_stage.split("/", 1)[1].strip()
    base_str = first_stage.split("+", 1)[0].strip()
    try:
        val = float(base_str)
        return val if val >= 0 else None
    except ValueError:
        return None


def extract_ply_clocks(document: Document | None) -> list[tuple[float, float]]:
    """Extract (white_seconds, black_seconds) per ply from PGN [%clk] comments and TimeControl."""
    if document is None or not document.annotated_pgn:
        return []
    game = _pgn.read_game(io.StringIO(document.annotated_pgn))
    if game is None:
        return []
    initial = _parse_time_control_initial(document.headers.get("TimeControl", ""))
    board = game.board()
    node = game
    raw_entries: list[tuple[bool, float | None]] = []
    first_white: float | None = None
    first_black: float | None = None
    while node.variations:
        next_node = node.variation(0)
        mover = board.turn
        clk = next_node.clock()
        if clk is not None:
            clk = max(0.0, float(clk))
            if mover == _chess.WHITE and first_white is None:
                first_white = clk
            elif mover == _chess.BLACK and first_black is None:
                first_black = clk
        raw_entries.append((mover, clk))
        board.push(next_node.move)
        node = next_node
    if first_white is None and first_black is None:
        return []
    w_cur = initial if initial is not None else (first_white if first_white is not None else (first_black or 0.0))
    b_cur = initial if initial is not None else (first_black if first_black is not None else (first_white or 0.0))
    ply_clocks: list[tuple[float, float]] = [(w_cur, b_cur)]
    for mover, clk in raw_entries:
        if clk is not None:
            if mover == _chess.WHITE:
                w_cur = clk
            else:
                b_cur = clk
        ply_clocks.append((w_cur, b_cur))
    return ply_clocks
