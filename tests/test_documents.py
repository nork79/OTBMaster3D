"""Notation and history tests without a graphics context."""

import unittest
from unittest.mock import Mock
import chess
from otb_chess.core.documents import GameDocuments, read_pgn, read_fen


class DocumentTests(unittest.TestCase):
    def host(self):
        host = GameDocuments()
        host.board = chess.Board()
        host.game_started = False
        host.game_over = False
        host.clock_paused = False
        host.refresh_move_list = Mock()
        host.clock_history = []
        return host

    def test_pgn_roundtrip_preserves_annotations_and_variations(self):
        text = '[Event "Test"]\n\n1. e4 {Hello} (1. d4 d5) e5 2. Nf3 *'
        original = read_pgn(text)[0]
        host = self.host()
        host.load_document(original.history,original)
        exported = host.export_pgn()
        self.assertIn('Hello',exported)
        self.assertIn('d4',exported)
        self.assertEqual(read_pgn(exported)[0].history.final_fen,host.board.fen())

    def test_fen_and_multiple_games(self):
        self.assertEqual(read_fen(chess.STARTING_FEN).fen(),chess.STARTING_FEN)
        with self.assertRaises(ValueError):
            read_fen('8/8/8/8/8/8/8/8 w - - 0 1')
        with self.assertRaises(ValueError):
            read_pgn('')
        self.assertEqual(len(read_pgn('1. e4 *\n\n1. d4 *')),2)

    def test_navigation_preserves_full_history_and_export(self):
        host = self.host()
        for move in ('e2e4','e7e5','g1f3'):
            host.board.push_uci(move)
        fen = host.board.fen()
        host.game_started = True
        self.assertFalse(host.navigate_to_ply(1))
        host.clock_paused = True
        self.assertTrue(host.navigate_to_ply(1))
        self.assertEqual(len(host.board.move_stack),1)
        self.assertEqual(len(read_pgn(host.export_pgn())[0].history.moves),3)
        self.assertTrue(host.navigate_to_ply(0))
        self.assertTrue(host.navigate_to_ply(2))
        host.return_to_live()
        self.assertEqual(host.board.fen(),fen)

    def test_fen_root_preserved_in_pgn(self):
        board = chess.Board()
        board.push_uci('e2e4')
        host = self.host()
        host.load_document(read_fen(board.fen()))
        host.board.push_uci('e7e5')
        reloaded = read_pgn(host.export_pgn())[0]
        self.assertEqual(reloaded.history.root_fen,board.fen())
        self.assertEqual(reloaded.history.final_fen,host.board.fen())
