"""UCI engine lifecycle and background move requests."""

from otb_chess.chess_backend import uci

from pathlib import Path
import threading


class EngineManager:
    def __init__(self, app):
        self.app = app
        self.engine = None
        self.path = ""
        self.lock = threading.Lock()
        self.thinking = False

    def load(self, path):
        self.unload()
        try:
            self.engine = uci.SimpleEngine.popen_uci(path)
            self.path = path
            return True, f"Loaded engine: {Path(path).name}"
        except Exception as e:
            self.engine = None
            return False, f"Engine load failed: {e}"

    def unload(self):
        with self.lock:
            if self.engine:
                try:
                    self.engine.quit()
                except Exception:
                    pass
            self.engine = None
            self.path = ""
            self.thinking = False

    def request_move(self):
        if not self.engine or self.thinking:
            return
        self.thinking = True
        position = self.app.board.copy()

        def worker():
            try:
                with self.lock:
                    if not self.engine:
                        return
                    result = self.engine.play(
                        position, uci.Limit(time=0.12), info=uci.INFO_ALL
                    )
                self.app.last_engine_search = (position.fen(), result.info)
                self.app.pending_engine_position = position.fen()
                self.app.pending_engine_move = result.move
            except Exception as e:
                self.app.pending_engine_error = str(e)
            finally:
                self.thinking = False

        threading.Thread(target=worker, daemon=True).start()

