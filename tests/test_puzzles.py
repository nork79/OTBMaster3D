"""Unit and UI tests for Mate 1-3, Combination/Exchange, and Endgame puzzles."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtCore import Qt, QCoreApplication, QEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
import shiboken6

from otb_chess.chess_backend.position import ChessPosition
from otb_chess.services import settings
from otb_chess.services.puzzles import (
    BUILTIN_PUZZLES,
    PUZZLE_CATEGORIES,
    PuzzleProgressStore,
    PuzzleRepository,
    PuzzleSession,
)
from otb_chess.ui.desktop_ui import MainWindow, configure_graphics


class PuzzleServiceTests(unittest.TestCase):
    def test_builtin_puzzles_cover_all_categories_and_have_valid_solutions(self):
        categories_present = {p.category for p in BUILTIN_PUZZLES}
        for key, _label in PUZZLE_CATEGORIES:
            self.assertIn(key, categories_present)

        for puzzle in BUILTIN_PUZZLES:
            pos = ChessPosition.from_fen(puzzle.fen)
            self.assertTrue(puzzle.solution_uci, f"{puzzle.puzzle_id} has empty solution")
            for uci in puzzle.solution_uci:
                mv = pos.parse_uci(uci)
                self.assertTrue(pos.is_legal(mv), f"{puzzle.puzzle_id} illegal move {uci}")
                pos.apply(mv)
            if puzzle.category.startswith("mate"):
                self.assertTrue(pos.is_checkmate(), f"{puzzle.puzzle_id} does not end in checkmate")

    def test_sqlite_repository_and_lichess_csv_import(self):
        repo = PuzzleRepository()
        all_puzzles = repo.list_puzzles("all")
        self.assertGreaterEqual(len(all_puzzles), 500)
        counts = repo.count_by_category()
        for key, _ in PUZZLE_CATEGORIES:
            self.assertGreaterEqual(counts.get(key, 0), 100)
        for puzzle in all_puzzles:
            pos = ChessPosition.from_fen(puzzle.fen)
            for uci in puzzle.solution_uci:
                mv = pos.parse_uci(uci)
                self.assertTrue(pos.is_legal(mv), f"{puzzle.puzzle_id} illegal {uci}")
                pos.apply(mv)
            if puzzle.category.startswith("mate"):
                self.assertTrue(pos.is_checkmate(), f"{puzzle.puzzle_id} not mate")

        # Verify CC0 Lichess CSV import applies Moves[0] setup move
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "sample.csv"
            db_path = Path(tmp) / "test_puzzles.db"
            csv_path.write_text(
                "PuzzleId,FEN,Moves,Rating,RatingDeviation,Popularity,NbPlays,Themes,GameUrl,OpeningTags\n"
                "00abc,6k1/5ppp/8/8/8/8/5PPP/2R3K1 w - - 0 1,c1d1 g8h8 d1d8,950,70,95,100,mate mateIn1 backRankMate,,\n"
                "00def,4r1k1/5ppp/8/8/3N4/8/5PPP/4R1K1 b - - 0 1,g8f8 d4e6 f8g8,1250,70,90,50,fork crushing,,\n",
                encoding="utf-8",
            )
            tmp_repo = PuzzleRepository(db_path)
            imported = tmp_repo.import_lichess_csv(csv_path, limit_per_category=10)
            self.assertEqual(imported["mate1"], 1)
            self.assertEqual(imported["combination"], 1)
            mate1_list = tmp_repo.list_puzzles("mate1")
            self.assertEqual(len(mate1_list), 1)
            self.assertEqual(mate1_list[0].solution_uci, ("g8h8", "d1d8"))

    def test_puzzle_session_progression_and_progress_persistence(self):
        m2 = next(p for p in BUILTIN_PUZZLES if p.category == "mate2")
        session = PuzzleSession(m2)
        pos = ChessPosition.from_fen(m2.fen)

        # Wrong move
        status, reply = session.evaluate_player_move(pos, "a2a3")
        self.assertEqual(status, "wrong")
        self.assertIsNone(reply)

        # First correct move -> returns opponent reply
        mv1 = pos.parse_uci(m2.solution_uci[0])
        pos.apply(mv1)
        status, reply = session.evaluate_player_move(pos, m2.solution_uci[0])
        self.assertEqual(status, "continue")
        self.assertEqual(reply, m2.solution_uci[1])

        # Apply opponent reply and final mating move
        pos.apply(pos.parse_uci(reply))
        pos.apply(pos.parse_uci(m2.solution_uci[2]))
        status, reply = session.evaluate_player_move(pos, m2.solution_uci[2])
        self.assertEqual(status, "solved")
        self.assertIsNone(reply)
        self.assertTrue(session.solved)

        with tempfile.TemporaryDirectory() as tmp:
            progress_path = Path(tmp) / "puzzles_progress.json"
            store = PuzzleProgressStore(progress_path)
            store.mark_solved(m2.puzzle_id)
            reloaded = PuzzleProgressStore(progress_path)
            self.assertIn(m2.puzzle_id, reloaded.solved_ids)


class PuzzleUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configure_graphics()
        cls.qt = QApplication.instance() or QApplication([])

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        for attr, filename in (
            ("CONFIG_PATH", "config.json"),
            ("LICHESS_AUTH_PATH", "lichess_auth.json"),
        ):
            p = patch.object(settings, attr, Path(self.folder.name) / filename)
            p.start()
            self.addCleanup(p.stop)
        for name in ("ENGINE_DIR", "BOOK_DIR"):
            p = patch.object(settings, name, Path(self.folder.name))
            p.start()
            self.addCleanup(p.stop)
            p_ui = patch(f"otb_chess.ui.desktop_ui.{name}", Path(self.folder.name))
            p_ui.start()
            self.addCleanup(p_ui.stop)
        evaluator = patch("otb_chess.ui.desktop_ui.PositionEvaluator")
        evaluator.start().return_value.poll.return_value = None
        self.addCleanup(evaluator.stop)
        self.window = MainWindow()
        self.window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        self.window.show()
        for _ in range(3):
            self.qt.processEvents()
        self.window.timer.stop()

    def tearDown(self):
        if self.window.puzzle_panel is not None and shiboken6.isValid(self.window.puzzle_panel):
            self.window.puzzle_panel.close()
            self.window.puzzle_panel.deleteLater()
        if shiboken6.isValid(self.window):
            self.window.close()
            self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.qt.processEvents()

    def test_puzzle_menu_and_mate2_playthrough(self):
        w = self.window
        menu_titles = [a.text() for a in w.menuBar().actions()]
        self.assertIn("Puzzles", menu_titles)

        w.open_puzzle_category("mate2")
        panel = w.puzzle_panel
        self.assertIsNotNone(panel)
        puzzle = panel.current_puzzle()
        self.assertIsNotNone(puzzle)
        self.assertEqual(puzzle.category, "mate2")

        # Puzzle selector dropdown lists puzzle name + rating and jumps to selection
        self.assertGreater(panel.puzzle_combo.count(), 1)
        self.assertIn(str(puzzle.rating), panel.puzzle_combo.itemText(0))
        panel.puzzle_combo.setCurrentIndex(1)
        self.assertEqual(panel.current_puzzle().puzzle_id, panel.puzzle_combo.currentData())
        panel.puzzle_combo.setCurrentIndex(0)

        # Hint highlights piece & destination squares on the board (no text hint)
        mv1 = w.game.position.parse_uci(puzzle.solution_uci[0])
        panel.show_hint()
        self.assertEqual(w.game.hint_squares, (mv1.from_square, mv1.to_square))

        # Play correct first move -> clears hint_squares, opponent auto-replies -> play mating move
        self.assertTrue(w.game.try_move(mv1.from_square, mv1.to_square, promotion=mv1.promotion))
        self.assertEqual(w.game.hint_squares, ())
        QTest.qWait(320)
        self.qt.processEvents()

        mv2 = w.game.position.parse_uci(puzzle.solution_uci[2])
        self.assertTrue(w.game.try_move(mv2.from_square, mv2.to_square, promotion=mv2.promotion))
        self.qt.processEvents()

        self.assertTrue(w.puzzle_session.solved)
        self.assertIn(puzzle.puzzle_id, panel.progress.solved_ids)
        self.assertIn("solved", panel.status_label.text().lower())

        # Show Solution plays pieces on the board step-by-step
        panel.retry_current()
        self.assertFalse(w.puzzle_session.solved)
        panel.show_solution()
        QTest.qWait(1400)
        self.qt.processEvents()
        self.assertTrue(w.game.position.is_checkmate())


if __name__ == "__main__":
    unittest.main()
