"""Owned interface around the unchanged python-chess UCI transport."""
import chess as _chess
import chess.engine as _engine
import subprocess
import sys
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
