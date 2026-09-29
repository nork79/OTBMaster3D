"""Metadata editing preserves game content and remembers only chosen identity."""
from datetime import date
import unittest
from unittest.mock import Mock
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QLineEdit, QComboBox, QDialogButtonBox
from tests import test_desktop_ui as fixture
from otb_chess.core.documents import read_pgn
from otb_chess.services import settings
from otb_chess.services.pgn_details import defaults, validate


class DetailsTests(unittest.TestCase):
    setUpClass = classmethod(fixture.DesktopTests.setUpClass.__func__)
    setUp = fixture.DesktopTests.setUp
    tearDown = fixture.DesktopTests.tearDown

    def test_defaults_both_engine_colors_and_persistent_name(self):
        g = self.game
        g.cfg['player_name'] = 'Alice'
        g.persist()
        self.assertEqual(settings.load_config()['player_name'], 'Alice')
        g.engine_enabled = True
        g.cfg['engine_elo'] = 1900
        g.engine_manager.engine = Mock(id={'name': 'Stockfish 19'})
        for side in ('White', 'Black'):
            g.engine_side_var.set(side)
            g.start_game()
            fields = g.game_details()
            self.assertEqual(fields[side], 'Stockfish 19 (1900 Elo)')
            self.assertEqual(read_pgn(g.export_pgn())[0].headers[side + 'Elo'], '1900')
            self.assertEqual(fields['Black' if side == 'White' else 'White'], 'Alice')
            self.assertEqual(fields['Date'], date.today().strftime('%Y.%m.%d'))
        g.engine_manager.engine = None
        g.start_game()
        self.assertEqual(g.game_details()['White'], 'Alice')
        self.assertEqual(g.game_details()['Black'], '?')

    def test_practice_rating_and_unlimited_engine(self):
        g = self.game
        g.engine_enabled = True
        g.engine_side = False
        g.engine_manager.engine = Mock(id={'name': 'Fairy-Stockfish'})
        g.engine_manager.loaded_configuration = {'engine_id': 'fairy-stockfish', 'profile': 'level_600', 'settings': {'rating': 600}}
        g.cfg['engine_elo'] = 600
        g.initialize_game_details()
        headers = read_pgn(g.export_pgn())[0].headers
        self.assertEqual(headers['Black'], 'Fairy-Stockfish (600 Elo)')
        self.assertEqual(headers['BlackElo'], '600')
        g._pgn_document = None
        g.engine_manager.loaded_configuration = {'name': 'Stockfish'}
        g.engine_manager.engine = Mock(id={'name': 'Stockfish 19'})
        g.cfg['engine_elo'] = None
        g.initialize_game_details()
        headers = read_pgn(g.export_pgn())[0].headers
        self.assertEqual(headers['Black'], 'Stockfish 19 (Full strength)')
        self.assertNotIn('BlackElo', headers)

    def test_pregame_switch_swaps_names_and_rating_and_keeps_setup(self):
        g = self.game
        g.cfg['player_name'] = 'Alice'
        g.engine_enabled = True
        g.engine_side = False
        g.engine_side_var.set('Black')
        g.engine_manager.engine = Mock(id={'name': 'Stockfish'})
        g.engine_manager.thinking = False
        g.cfg['engine_elo'] = 1900
        g.initialize_game_details()
        g.set_game_details({**g.game_details(), 'Event': 'Club match'})
        g.switch_sides()
        headers = read_pgn(g.export_pgn())[0].headers
        self.assertEqual(headers['White'], 'Stockfish (1900 Elo)')
        self.assertEqual(headers['Black'], 'Alice')
        self.assertEqual(headers['WhiteElo'], '1900')
        self.assertNotIn('BlackElo', headers)
        g.start_game()
        self.assertEqual(g.game_details()['Black'], 'Alice')
        self.assertEqual(g.game_details()['Event'], 'Club match')

    def test_untimed_play_recovery_and_button_position(self):
        import time
        import chess
        g, w = self.game, self.window
        layout = w.sidebar.layout()
        self.assertEqual(layout.indexOf(w.play_button), layout.indexOf(w.black_clock) + 1)
        g.time_control_var.set('Infinite (clocks disabled)')
        g.clock_mode_var.set('OTB')
        g.start_game()
        for uci in ('e2e4', 'e7e5'):
            move = chess.Move.from_uci(uci)
            self.assertTrue(g.try_move(move.from_square, move.to_square))
            self.assertFalse(g.awaiting_clock_press)
        g.last_clock_tick = time.perf_counter() - 999999
        g.update_clock()
        self.assertFalse(g.game_over)
        self.assertEqual(g.white_time, 0)
        w.black_clock.refresh(g)
        self.assertEqual(w.black_clock.digits.text(), '∞')
        w.session.save(g, force=True)
        self.assertIsNone(w.session.error)
        g.clocks_disabled = False
        self.assertTrue(w.session.restore(g))
        self.assertTrue(g.clocks_disabled)
        g.stop_clock()
        g.update_clock()
        self.assertFalse(g.game_over)

    def test_edited_black_human_name_is_remembered_automatically(self):
        g, w = self.game, self.window
        g.engine_enabled = True
        g.engine_side = True
        g.engine_manager.engine = Mock(id={'name': 'Stockfish'})
        g.cfg['player_name'] = 'Alice'
        g.initialize_game_details()
        def save():
            dialog = QApplication.activeModalWidget()
            dialog.findChild(QLineEdit, 'pgnBlack').setText('Alex')
            dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Save).click()
        QTimer.singleShot(0, save)
        w.edit_game_details()
        self.assertEqual(settings.load_config()['player_name'], 'Alex')
        self.assertEqual(g.game_details()['Black'], 'Alex')

    def test_dialog_save_cancel_and_annotation_recovery(self):
        g, w = self.game, self.window
        original = read_pgn('[Event "Imported"]\n[White "Old"]\n[Black "Other"]\n[Date "1999.01.01"]\n\n1. e4 {keep comment} (1. d4 d5) e5 *')[0]
        g.load_document(original.history, original)
        menu = next(a.menu() for a in w.menuBar().actions() if a.text() == 'Game')
        action = next(a for a in menu.actions() if a.text() == 'Edit Game Details')
        fields = dict(Event='Club evening', Site='Sydney', Date='2026.09.28', White='Alice', Black='Bob', Round='2')
        def save():
            dialog = QApplication.activeModalWidget()
            for key, value in fields.items():
                dialog.findChild(QLineEdit, 'pgn' + key).setText(value)
            self.assertIsNone(dialog.findChild(QComboBox, 'rememberPlayer'))
            dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Save).click()
        QTimer.singleShot(0, save)
        action.trigger()
        exported = g.export_pgn()
        self.assertIn('keep comment', exported)
        self.assertIn('( 1. d4 d5 )', exported)
        self.assertEqual(read_pgn(exported)[0].history, original.history)
        self.assertEqual(g.game_details(), fields)
        self.assertEqual(settings.load_config()['player_name'], 'Alice')
        self.assertTrue(w.session.restore(g))
        self.assertEqual(g.game_details(), fields)
        def cancel():
            dialog = QApplication.activeModalWidget()
            dialog.findChild(QLineEdit, 'pgnWhite').setText('Discard me')
            dialog.reject()
        QTimer.singleShot(0, cancel)
        action.trigger()
        self.assertEqual(g.game_details(), fields)

    def test_validation_and_imported_details_stay_unchanged(self):
        g = self.game
        doc = read_pgn('[Event "Old event"]\n[Date "2001.??.??"]\n\n*')[0]
        g.load_document(doc.history, doc)
        self.assertEqual(g.game_details()['Date'], '2001.??.??')
        fields = g.game_details()
        for bad in ('2026.02.30', 'today', '2026.13.01'):
            with self.assertRaises(ValueError):
                g.set_game_details({**fields, 'Date': bad})
        with self.assertRaises(ValueError):
            g.set_game_details({**fields, 'Event': 'bad\nheader'})
        self.assertEqual(g.game_details(), fields)
        self.assertEqual(validate({**fields, 'Date': ''})['Date'], '????.??.??')
