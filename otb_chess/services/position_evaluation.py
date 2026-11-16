"""Short, independent Stockfish searches, retaining only the latest request."""
from collections import deque
import threading

from otb_chess.chess_backend import uci
from otb_chess.services import settings


def _open_stockfish_engine():
    path = next(iter(sorted(settings.ENGINE_DIR.rglob('stockfish*.exe'))), None)
    if path is None:
        raise RuntimeError('Stockfish is unavailable in the engines folder.')
    return uci.Engine.open(str(path))


def _valid_eval(info, expected_fen):
    if (info is None or info.source_fen != expected_fen or info.score is None
            or (info.score.mate is None and info.score.centipawns is None)):
        raise RuntimeError('Stockfish returned no position score.')
    return info


class _BaseEvaluator:
    def __init__(self):
        self._condition = threading.Condition()
        self._thread = None
        self._engine = None
        self._pending = None
        self._closed = False

    def _ensure_thread_locked(self):
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def _ensure_engine(self):
        if self._engine is None:
            engine = _open_stockfish_engine()
            with self._condition:
                if self._closed:
                    try:
                        engine.quit()
                    except Exception:
                        pass
                    return None
                self._engine = engine
        return self._engine

    def _stop(self):
        if self._engine is not None:
            try:
                self._engine.stop_search()
            except Exception:
                pass  # A failed transport is reported by the worker.

    def close(self):
        with self._condition:
            self._closed = True
            self._pending = None
            self._stop()
            self._condition.notify()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def _quit_engine(self):
        with self._condition:
            engine, self._engine = self._engine, None
        if engine is not None:
            try:
                engine.quit()
            except Exception:
                pass


class PositionEvaluator(_BaseEvaluator):
    def __init__(self):
        super().__init__()
        self._token = None
        self._result = None

    def request(self, history, token):
        with self._condition:
            if self._closed or token == self._token:
                return
            self._token = token
            self._result = None
            self._pending = (history, token)
            self._stop()
            self._ensure_thread_locked()
            self._condition.notify()

    def poll(self):
        with self._condition:
            result, self._result = self._result, None
            return result

    def _run(self):
        try:
            while True:
                with self._condition:
                    self._condition.wait_for(lambda: self._closed or self._pending is not None)
                    if self._closed:
                        return
                    history, token = self._pending
                    self._pending = None
                info, error = None, None
                try:
                    engine = self._ensure_engine()
                    if engine is None:
                        return
                    with self._condition:
                        if self._closed:
                            return
                        if token != self._token:
                            continue
                    results = engine.analyse_variations(
                        history, seconds=2.0, depth=0, multipv=1, threads=1, hash_mb=32)
                    info = _valid_eval(results[0] if results else None, history.final_fen)
                except Exception as exc:
                    error = str(exc)
                    self._quit_engine()
                with self._condition:
                    if not self._closed and token == self._token:
                        self._result = (token, info, error)
        finally:
            self._quit_engine()


class GameReviewEvaluator(_BaseEvaluator):
    """Sequential background Stockfish evaluator for full-game review and evaluation graphs."""

    def __init__(self):
        super().__init__()
        self._signature = None
        self._results = deque()

    def request_game(self, signature, items):
        items = tuple(items)
        with self._condition:
            if self._closed or not items or signature == self._signature:
                return
            self._signature = signature
            self._results.clear()
            self._pending = (signature, items)
            self._stop()
            self._ensure_thread_locked()
            self._condition.notify()

    def clear(self):
        with self._condition:
            self._signature = None
            self._pending = None
            self._results.clear()
            self._stop()

    def poll_all(self):
        with self._condition:
            items = list(self._results)
            self._results.clear()
            return items

    def _run(self):
        try:
            while True:
                with self._condition:
                    self._condition.wait_for(lambda: self._closed or self._pending is not None)
                    if self._closed:
                        return
                    signature, items = self._pending
                    self._pending = None
                for key, history in items:
                    with self._condition:
                        if self._closed:
                            return
                        if signature != self._signature:
                            break
                    try:
                        engine = self._ensure_engine()
                        if engine is None:
                            return
                        with self._condition:
                            if self._closed or signature != self._signature:
                                break
                        results = engine.analyse_variations(
                            history, seconds=0.35, depth=14, multipv=1, threads=1, hash_mb=32)
                        info = _valid_eval(results[0] if results else None, history.final_fen)
                        with self._condition:
                            if not self._closed and signature == self._signature:
                                self._results.append((signature, key, info, None))
                    except Exception as exc:
                        self._quit_engine()
                        with self._condition:
                            if not self._closed and signature == self._signature:
                                self._results.append((signature, key, None, str(exc)))
                        break
        finally:
            self._quit_engine()
