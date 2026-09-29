"""Owned document transfers with the unchanged PGN/SAN provider."""
import dataclasses
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import unittest

from otb_chess.document_state import Document, History
from otb_chess.chess_backend import notation, rules
from otb_chess.core.documents import GameDocuments
from otb_chess.services.session import SessionStore, FIELDS
from otb_chess.services import settings
from otb_chess_core import Move


TEXT = '[Event "Imported"]\n[White "Alice"]\n[Black "Bob"]\n[Result "*"]\n\n1. e4 {main} (1. d4 {side} d5 (1... Nf6 {nested})) e5 2. Nf3 $1 *'


class NotationBoundaryTests(unittest.TestCase):
    def host(self):
        host = GameDocuments()
        host.board = rules.Board()
        host.game_started = host.game_over = False
        host.clock_paused = True
        host.clocks_disabled = False
        host.clock_history = []
        host.refresh_move_list = Mock()
        return host

    def test_document_values_and_recursive_roundtrip(self):
        document = notation.read_pgn(TEXT)[0]
        def owned(value):
            self.assertIn(type(value), (Document, History, Move, dict, tuple, str, int, type(None)))
            if dataclasses.is_dataclass(value):
                for field in dataclasses.fields(value):
                    owned(getattr(value, field.name))
            elif isinstance(value, dict):
                for key, item in value.items():
                    owned(key)
                    owned(item)
            elif isinstance(value, tuple):
                for item in value:
                    owned(item)
        owned(document)
        exported = notation.export_pgn(document.history, document)
        self.assertEqual(exported, document.annotated_pgn)
        for token in ('main', 'side', 'nested', 'Nf6', '$1'):
            self.assertIn(token, exported)
        self.assertEqual(notation.read_pgn(exported)[0], document)
        self.assertEqual(document.headers['White'], 'Alice')

    def test_simple_and_multiple_games(self):
        games = notation.read_pgn('1. e4 *\n\n1. d4 *')
        self.assertEqual(len(games), 2)
        self.assertEqual(games[0].history.moves, (Move(12, 28),))
        self.assertEqual(games[1].history.moves, (Move(11, 27),))
        for document in games:
            self.assertEqual(notation.read_pgn(notation.export_pgn(document.history))[0].history, document.history)

    def test_special_owned_moves_and_header_edits(self):
        for fen, move, expected_san in (
            ('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1', Move(4, 6), 'O-O'),
            ('4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1', Move(36, 43), 'exd6'),
            ('7k/P7/8/8/8/8/8/7K w - - 0 1', Move(48, 56, 2), 'a8=N'),
        ):
            with self.subTest(move=move):
                self.assertEqual(notation.san(fen, move), expected_san)
                board = rules.Board(fen)
                board.push(rules.Move(move.from_square, move.to_square, move.promotion))
                history = rules.snapshot_history(board)
                document = notation.read_pgn(notation.export_pgn(history))[0]
                self.assertEqual(document.history, history)
                self.assertEqual(document.history.moves, (move,))
                document.headers['Event'] = 'Updated metadata'
                self.assertEqual(notation.read_pgn(notation.export_pgn(history, document))[0].headers['Event'],
                                 'Updated metadata')

    def test_fen_root_black_turn_and_san_conversion(self):
        fen = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 17'
        text = f'[SetUp "1"]\n[FEN "{fen}"]\n\n17... e5 18. Nf3 *'
        document = notation.read_pgn(text)[0]
        self.assertEqual(document.history.root_fen, fen)
        self.assertEqual(document.history.moves[0], Move(52, 36))
        self.assertEqual(notation.san(fen, document.history.moves[0]), 'e5')
        host = self.host()
        host.load_document(document.history, document)
        self.assertEqual(host.board.fullmove_number, 18)
        self.assertEqual(rules.snapshot_history(host.board), document.history)
        self.assertEqual(notation.read_pgn(host.export_pgn())[0].history, document.history)

    def test_review_live_and_changed_game_metadata(self):
        document = notation.read_pgn(TEXT)[0]
        host = self.host()
        host.load_document(document.history, document)
        final = host.board.fen()
        for ply in (1, 0, 2):
            self.assertTrue(host.navigate_to_ply(ply))
            self.assertEqual(len(host.board.move_stack), ply)
            self.assertEqual(host.export_pgn(), document.annotated_pgn)
        host.return_to_live()
        self.assertEqual(host.board.fen(), final)
        host.board.push_uci('b8c6')
        changed = notation.read_pgn(host.export_pgn())[0]
        self.assertEqual(changed.headers['Event'], 'Imported')
        self.assertEqual(len(changed.history.moves), 4)
        self.assertNotIn('nested', changed.annotated_pgn)  # existing changed-mainline policy

    def test_imported_review_session_roundtrip(self):
        host = self.host()
        document = notation.read_pgn(TEXT)[0]
        host.load_document(document.history, document)
        state = dict(white_time=41.5, black_time=32.5, increment=2,
                     active_clock_color=False, game_started=True, game_over=False,
                     awaiting_clock_press=False, awaiting_clock_color=None,
                     clock_mode='Online', clock_binding='Spacebar', clock_history=[], result_text='Imported')
        for key in FIELDS:
            setattr(host, key, state[key])
        host.clock_mode_var = Mock()
        host.clock_binding_var = Mock()
        host.navigate_to_ply(1)
        with tempfile.TemporaryDirectory() as folder, patch.object(settings, 'CONFIG_PATH', Path(folder)/'config.json'):
            store = SessionStore()
            store.save(host, force=True)
            self.assertIsNone(store.error)
            _, decoded, history = store.decode(store.path)
            self.assertIs(type(decoded), Document)
            self.assertIs(type(history), History)
            host.load_document(rules.Board())
            self.assertTrue(SessionStore().restore(host))
            self.assertEqual(len(host.board.move_stack), 1)
            self.assertEqual(len(host.history_board().move_stack), 3)
            self.assertEqual(host.export_pgn(), document.annotated_pgn)
            self.assertEqual((host.white_time, host.black_time), (41.5, 32.5))
            self.assertTrue(host.clock_paused)
            host.return_to_live()
            self.assertEqual(host.board.fen(), document.history.final_fen)
