"""UCI engine lifecycle and background move requests."""

from otb_chess.chess_backend import uci
from otb_chess.chess_backend import rules

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
            self.engine = uci.Engine.open(path)
            self.engine.configure_strength(self.app.cfg.get("engine_elo"))
            self.path = path
            return True, f"Loaded engine: {Path(path).name}"
        except Exception as e:
            self.unload()
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
        position = rules.snapshot_history(self.app.board)

        def worker():
            try:
                with self.lock:
                    if not self.engine:
                        return
                    self.engine.configure_strength(self.app.cfg.get("engine_elo"))
                    result = self.engine.play(position, style=self.app.cfg.get("engine_style", "Balanced"))
                self.app.last_engine_search = (position.final_fen, result.info)
                self.app.pending_engine_position = position.final_fen
                self.app.pending_engine_move = result.move
            except Exception as e:
                self.app.pending_engine_error = str(e)
            finally:
                self.thinking = False

        threading.Thread(target=worker, daemon=True).start()

