"""Owned interface around the unchanged python-chess UCI transport."""
import chess as _chess
import chess.engine as _engine
import subprocess
import sys
import random
from otb_chess_core import Move
from otb_chess.engine_state import EngineScore, EngineEvaluation, EngineResult


def _move(move):
    return None if move is None else Move(move.from_square, move.to_square, move.promotion)


def _board(history):
    board = _chess.Board(history.root_fen)
    for move in history.moves:
        board.push(_chess.Move(move.from_square, move.to_square, move.promotion))
    if board.fen() != history.final_fen:
        raise ValueError('Engine history does not match final FEN')
    return board


def _evaluation(source, info):
    value = info.get('score')
    score = None
    if value is not None:
        white = value.white()
        score = EngineScore(mate=white.mate()) if white.is_mate() else EngineScore(centipawns=white.score())
    return EngineEvaluation(source, score, info.get('depth'), info.get('seldepth'),
                            info.get('nodes'), info.get('nps'),
                            tuple(_move(move) for move in info.get('pv', ())))


class Engine:
    def __init__(self, transport):
        self._transport = transport

    @classmethod
    def open(cls, command):
        return cls(_engine.SimpleEngine.popen_uci(command, **(
            {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {})))

    def strength_range(self):
        option = self._transport.options.get("UCI_Elo")
        return (option.min, option.max) if option and "UCI_LimitStrength" in self._transport.options else None

    def configuration_snapshot(self):
        """Persistent UCI settings, excluding temporary search/analysis overrides.

        Call while holding the engine manager's lock (no active search).
        """
        return {"name": self._transport.id.get("name"),
                "uci_options": dict(self._transport.protocol.target_config)}

    def stop_search(self):
        """Request UCI stop without waiting for the manager's search lock."""
        self._transport.protocol.loop.call_soon_threadsafe(self._transport.protocol.send_line, "stop")

    def restore_options(self, options):
        # Managed options belong to the transport's per-search state.
        from pathlib import Path
        configured = {}
        for name, value in options.items():
            option = self._transport.options.get(name)
            if option is None:
                raise ValueError(f"Saved engine option is unavailable: {name}")
            if (isinstance(value, str) and value and value != option.default
                    and any(word in name.lower() for word in ("personalityfile", "weightsfile", "evalfile"))
                    and not Path(value).is_file()):
                raise ValueError(f"Saved engine resource is unavailable: {name}")
            if not option.is_managed():
                parsed = option.parse(value)
                if parsed != value:
                    raise ValueError(f"Saved engine option has changed: {name}")
                configured[name] = value
        self._transport.configure(configured)

    def configure_strength(self, elo=None):
        limits = self.strength_range()
        if limits:
            options = {"UCI_LimitStrength": elo is not None}
            if elo is not None:
                options["UCI_Elo"] = max(limits[0], min(limits[1], elo))
            self._transport.configure(options)

    @staticmethod
    def style_preference(board, move, style):
        activity = 2 * board.gives_check(move) + board.is_capture(move)
        return activity if style == "Active" else -activity

    def play(self, history, seconds=0.12, style="Balanced"):
        board = _board(history)
        result = self._transport.play(board, _engine.Limit(time=seconds), info=_engine.INFO_ALL)
        if style != "Balanced" and result.move and "MultiPV" in self._transport.options:
            candidates = self._transport.analyse(board, _engine.Limit(time=seconds), multipv=3)
            baseline = self._transport.analyse(board, _engine.Limit(time=seconds), root_moves=[result.move])
            score = baseline.get("score")
            value = score.pov(board.turn).score() if score else None
            choices = [baseline]
            if value is not None:
                choices += [item for item in candidates if item.get("score") and
                            item["score"].pov(board.turn).score() is not None and
                            abs(item["score"].pov(board.turn).score() - value) <= 35]
            choices = [item for item in choices if item.get("pv")]
            if choices:
                chosen = max(choices, key=lambda item: self.style_preference(board, item["pv"][0], style))
                return EngineResult(_move(chosen["pv"][0]), None, _evaluation(history.final_fen, chosen))
        return EngineResult(_move(result.move), _move(result.ponder), _evaluation(history.final_fen, result.info))

    def analyse(self, history, seconds=0.25):
        options = {"UCI_LimitStrength": False} if self.strength_range() else {}
        info = self._transport.analyse(_board(history), _engine.Limit(time=seconds), options=options)
        return _evaluation(history.final_fen, info)

    def quit(self):
        self._transport.quit()

    def analyse_variations(self, history, *, seconds=1.0, depth=20, multipv=3, threads=1, hash_mb=64):
        options = {"UCI_LimitStrength": False, "Skill Level": 20,
                   "Threads": threads, "Hash": hash_mb}
        info = self._transport.analyse(
            _board(history), _engine.Limit(time=seconds, depth=depth or None),
            multipv=multipv, options=options)
        return tuple(_evaluation(history.final_fen, item) for item in info)


class MaiaEngine(Engine):
    """Maia networks require policy-only (one-node) play rather than search."""

    @classmethod
    def open_model(cls, executable, weights, mistakes=0.0):
        engine = cls.open([str(executable), '--weights='+str(weights),
                           '--backend=blas', '--threads=1', '--minibatch-size=1'])
        engine.mistakes = mistakes
        return engine

    def strength_range(self):
        return None

    def configure_strength(self, elo=None):
        pass  # Strength is chosen by the network, not UCI_Elo.

    def play(self, history, seconds=0.12, style="Balanced"):
        board = _board(history)
        if self.mistakes and random.random() < self.mistakes:
            moves = list(board.legal_moves)
            chosen = _move(random.choice(moves)) if moves else None
            return EngineResult(chosen, None, EngineEvaluation(history.final_fen, pv=(chosen,) if chosen else ()))
        result = self._transport.play(board, _engine.Limit(nodes=1), info=_engine.INFO_ALL)
        return EngineResult(_move(result.move), None, _evaluation(history.final_fen,result.info))

    def analyse(self, history, seconds=0.25):
        info = self._transport.analyse(_board(history), _engine.Limit(nodes=1))
        return _evaluation(history.final_fen,info)
