"""Short, independent Stockfish searches, retaining only the latest request."""
import threading

from otb_chess.chess_backend import uci
from otb_chess.services import settings


class PositionEvaluator:
    def __init__(self):
        self._condition = threading.Condition()
        self._thread = None
        self._engine = None
        self._pending = None
        self._token = None
        self._result = None
        self._closed = False

    def request(self, history, token):
        with self._condition:
            if self._closed or token == self._token:
                return
            self._token = token
            self._result = None
            self._pending = (history, token)
            self._stop()
            if self._thread is None:
                self._thread = threading.Thread(target=self._run, daemon=True)
                self._thread.start()
            self._condition.notify()

    def poll(self):
        with self._condition:
            result, self._result = self._result, None
            return result

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
                    if self._engine is None:
                        path = next(iter(sorted(settings.ENGINE_DIR.rglob('stockfish*.exe'))), None)
                        if path is None:
                            raise RuntimeError('Stockfish is unavailable in the engines folder.')
                        engine = uci.Engine.open(str(path))
                        with self._condition:
                            self._engine = engine
                    with self._condition:
                        if self._closed:
                            return
                        if token != self._token:
                            continue
                    results = self._engine.analyse_variations(
                        history, seconds=2.0, depth=0, multipv=1, threads=1, hash_mb=32)
                    info = results[0] if results else None
                    if (info is None or info.source_fen != history.final_fen or info.score is None
                            or (info.score.mate is None and info.score.centipawns is None)):
                        raise RuntimeError('Stockfish returned no position score.')
                except Exception as exc:
                    error = str(exc)
                    self._quit_engine()
                with self._condition:
                    if not self._closed and token == self._token:
                        self._result = (token, info, error)
        finally:
            self._quit_engine()

    def _quit_engine(self):
        with self._condition:
            engine, self._engine = self._engine, None
        if engine is not None:
            try:
                engine.quit()
            except Exception:
                pass
