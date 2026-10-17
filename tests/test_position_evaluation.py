"""Background evaluation scheduling, cancellation and engine lifetime."""
import threading
import time
import unittest
from unittest.mock import Mock

from otb_chess.chess_backend.position import ChessPosition
from otb_chess.engine_state import EngineEvaluation, EngineScore
from otb_chess.services.position_evaluation import PositionEvaluator


class PositionEvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.evaluator = PositionEvaluator()
        self.engine = Mock()
        self.evaluator._engine = self.engine
        self.addCleanup(self.evaluator.close)
        self.history = ChessPosition().history()

    def result(self):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            result = self.evaluator.poll()
            if result is not None:
                return result
            time.sleep(.01)
        self.fail('Background evaluation did not finish')

    def test_search_is_bounded_full_strength_and_not_repeated_for_same_position(self):
        info = EngineEvaluation(self.history.final_fen, EngineScore(centipawns=842))
        self.engine.analyse_variations.return_value = (info,)
        self.evaluator.request(self.history, 1)
        self.assertEqual(self.result(), (1, info, None))
        self.evaluator.request(self.history, 1)
        self.engine.analyse_variations.assert_called_once_with(
            self.history, seconds=2.0, depth=0, multipv=1, threads=1, hash_mb=32)
        self.evaluator.close()
        self.engine.quit.assert_called_once()
        self.assertFalse(self.evaluator._thread.is_alive())

    def test_latest_request_replaces_pending_positions_and_discards_old_score(self):
        entered, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        info = EngineEvaluation(self.history.final_fen, EngineScore(centipawns=34))
        def analyse(*args, **kwargs):
            entered.set()
            release.wait(3)
            return (info,)
        self.engine.analyse_variations.side_effect = analyse
        self.evaluator.request(self.history, 1)
        self.assertTrue(entered.wait(2))
        self.evaluator.request(self.history, 2)
        self.evaluator.request(self.history, 3)
        release.set()
        self.assertEqual(self.result(), (3, info, None))
        self.assertEqual(self.engine.analyse_variations.call_count, 2)
        self.assertTrue(self.engine.stop_search.called)

    def test_failed_engine_reports_error_and_quits(self):
        self.engine.analyse_variations.side_effect = RuntimeError('engine exited')
        self.evaluator.request(self.history, 1)
        self.assertEqual(self.result(), (1, None, 'engine exited'))
        self.engine.quit.assert_called_once()

    def test_close_during_search_stops_engine_and_discards_result(self):
        entered, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        def analyse(*args, **kwargs):
            entered.set()
            release.wait(3)
            return (EngineEvaluation(self.history.final_fen, EngineScore(mate=3)),)
        self.engine.analyse_variations.side_effect = analyse
        self.evaluator.request(self.history, 1)
        self.assertTrue(entered.wait(2))
        self.engine.stop_search.side_effect = release.set
        self.evaluator.close()
        self.assertIsNone(self.evaluator.poll())
        self.engine.quit.assert_called_once()
        self.assertFalse(self.evaluator._thread.is_alive())
