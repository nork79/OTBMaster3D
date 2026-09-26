"""UCI engine lifecycle and background move requests."""

from otb_chess.chess_backend import uci
from otb_chess.chess_backend.position import ChessPosition
from otb_chess.engine_identity import identify_engine

from pathlib import Path
from copy import deepcopy
import logging
import threading


class EngineManager:
    def __init__(self, app):
        self.app = app
        self.engine = None
        self.path = ""
        self.lock = threading.Lock()
        self.thinking = False
        self.loaded_configuration = None
        self.search_generation = 0

    def load(self, path):
        self.unload()
        try:
            from otb_chess.services.difficulty import DIFFICULTIES, engine_path, weights_path
            key = self.app.cfg.get("engine_difficulty", "custom")
            preset = DIFFICULTIES.get(key)
            if Path(path).resolve() == engine_path("club").resolve():
                if not preset or preset.engine != "maia":
                    rating = self.app.cfg.get("engine_rating",1100)
                    key = min((k for k,p in DIFFICULTIES.items() if p.engine == "maia" and not p.mistakes),
                              key=lambda k:abs(DIFFICULTIES[k].model-rating))
                    preset = DIFFICULTIES[key]
                self.engine = uci.MaiaEngine.open_model(path,weights_path(key),preset.mistakes)
                configuration = {"engine_id": "maia", "name": "Maia",
                                 "profile": key, "settings": {
                                     "model": preset.model, "weights_path": str(weights_path(key)),
                                     "mistakes": preset.mistakes,
                                     "backend": "blas", "threads": 1, "minibatch_size": 1}}
            else:
                self.engine = uci.Engine.open(path)
                reported_name = self.engine.configuration_snapshot()["name"]
                name = reported_name or Path(path).stem
                configuration = {"engine_id": identify_engine(reported_name, path), "name": name,
                                 "profile": "custom", "settings": {}}
            self.engine.configure_strength(self.app.cfg.get("engine_elo"))
            self.path = path
            self.loaded_configuration = configuration
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
            self.loaded_configuration = None
            self.thinking = False

    def stop_search(self):
        if self.engine is not None:
            try:
                self.engine.stop_search()
            except Exception:
                logging.getLogger(__name__).exception("Could not stop engine search")

    def restore_configuration(self, configuration):
        """Load a candidate first; retain the working engine on any failure.

        Caller has paused the game and drained searches/analysis/load workers.
        This method may run in a background thread; it never touches UI cells.
        """
        if configuration is None:
            self.unload()
            return True, ""
        candidate = None
        try:
            from otb_chess.engine_identity import profile_identifier
            from otb_chess.services.settings import ENGINE_DIR
            config = deepcopy(configuration)
            engine_id = config["engine_id"]
            path = Path(config.get("executable", ""))
            if not path.is_file():
                if engine_id == "maia":
                    path = ENGINE_DIR / "maia" / "lc0.exe"
                elif engine_id == "stockfish":
                    path = next(iter(sorted(ENGINE_DIR.rglob("stockfish*.exe"))), path)
            if not path.is_file():
                raise ValueError("Engine executable is unavailable.")
            settings = config.get("settings", {})
            allowed = {"uci_options"}
            if engine_id == "maia":
                allowed |= {"model", "weights_path", "mistakes", "backend", "threads", "minibatch_size"}
            if set(settings) - allowed:
                raise ValueError("This engine's saved configuration system is not supported yet.")
            options = settings.get("uci_options", {})
            if engine_id == "maia":
                weights = Path(settings.get("weights_path", ""))
                if not weights.is_file():
                    weights = ENGINE_DIR / "maia" / f"maia-{settings.get('model')}.pb.gz"
                if not weights.is_file():
                    raise ValueError("The saved Maia model is unavailable.")
                if (settings.get("backend", "blas"), settings.get("threads", 1), settings.get("minibatch_size", 1)) != ("blas", 1, 1):
                    raise ValueError("Unsupported Maia launch configuration.")
                candidate = uci.MaiaEngine.open_model(path, weights, settings.get("mistakes", 0))
                config["settings"]["weights_path"] = str(weights)
            else:
                candidate = uci.Engine.open(str(path))
                identity = identify_engine(candidate.configuration_snapshot()["name"], path)
                if identity != engine_id:
                    raise ValueError("Executable does not match the saved engine identity.")
            candidate.restore_options(options)
            # Compare persistent options after configuration, rather than guessing
            # another profile from a difficulty label or nearest Maia rating.
            actual = deepcopy(config)
            actual["settings"]["uci_options"] = candidate.configuration_snapshot()["uci_options"]
            expected_id = config.get("profile_id")
            if expected_id and profile_identifier(actual) != expected_id:
                raise ValueError("Saved engine profile cannot be reproduced exactly.")
            with self.lock:
                previous = self.engine
                self.engine, self.path, self.loaded_configuration = candidate, str(path), config
                candidate = None
                if previous is not None:
                    try:
                        previous.quit()
                    except Exception:
                        logging.getLogger(__name__).exception("Could not close previous engine")
            return True, ""
        except Exception as exc:
            logging.getLogger(__name__).warning("Bookmark engine unavailable: %s", exc)
            if candidate is not None:
                try:
                    candidate.quit()
                except Exception:
                    pass
            message = str(exc)
            if self.engine is not None:
                message += " Current engine retained."
            else:
                fallback = next(iter(sorted(ENGINE_DIR.rglob("stockfish*.exe"))), None)
                if fallback is not None and self.load(str(fallback))[0]:
                    message += " Default Stockfish loaded instead."
                else:
                    message += " No engine is available; the board is still usable."
            return False, message

    def request_move(self):
        if not getattr(self.app, "engine_enabled", True) or not self.engine or self.thinking:
            return
        self.thinking = True
        generation = self.search_generation
        position = ChessPosition.from_board(self.app.board).history()

        def worker():
            try:
                with self.lock:
                    if not self.engine or not getattr(self.app, "engine_enabled", True) or generation != self.search_generation:
                        return
                    self.engine.configure_strength(self.app.cfg.get("engine_elo"))
                    result = self.engine.play(position, style=self.app.cfg.get("engine_style", "Balanced"))
                if generation != self.search_generation:
                    return
                self.app.pending_engine_generation = generation
                self.app.last_engine_search = (position.final_fen, result.info)
                self.app.pending_engine_position = position.final_fen
                self.app.pending_engine_move = result.move
            except Exception as e:
                if generation == self.search_generation:
                    self.app.pending_engine_error = str(e)
            finally:
                self.thinking = False

        threading.Thread(target=worker, daemon=True).start()

