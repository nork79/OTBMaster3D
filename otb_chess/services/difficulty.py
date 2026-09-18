"""Named practice levels and their bundled engine/model choices."""
from dataclasses import dataclass
from otb_chess.services import settings


@dataclass(frozen=True)
class Difficulty:
    label: str
    engine: str
    rating: int | None
    model: int | None = None
    mistakes: float = 0.0

    @property
    def description(self):
        if self.mistakes:
            return f'Maia 1100 with extra mistakes. {self.rating} is an uncalibrated practice label.'
        if self.engine == 'maia':
            return f'Maia {self.model} human-move model; its training rating is not a measured playing Elo.'
        return 'Stockfish at full strength.' if self.rating is None else f'Stockfish target rating {self.rating}; ratings are estimates.'


DIFFICULTIES = {
    'beginner': Difficulty('Beginner · ~300','maia',300,1100,.8),
    'novice': Difficulty('Novice · ~600','maia',600,1100,.55),
    'casual': Difficulty('Casual · ~900','maia',900,1100,.3),
    'improver': Difficulty('Improver · ~1100','maia',1100,1100),
    'intermediate_1300': Difficulty('Intermediate · ~1300','maia',1300,1300),
    'intermediate': Difficulty('Intermediate+ · ~1400','maia',1400,1400),
    'club_1500': Difficulty('Club · ~1500','maia',1500,1500),
    'club': Difficulty('Club 2 · ~1600','maia',1600,1600),
    'advanced_club': Difficulty('Advanced Club · ~1800','maia',1800,1800),
    'cm_practice': Difficulty('CM Level · ~2000','stockfish',2000),
    'master': Difficulty('IM Level · ~2200','stockfish',2200),
    'expert': Difficulty('GM Level · ~2500','stockfish',2500),
    'full': Difficulty('SuperGM Level','stockfish',None),
}


def engine_path(key):
    preset = DIFFICULTIES[key]
    if preset.engine == 'maia':
        return settings.ENGINE_DIR/'maia'/'lc0.exe'
    return next(iter(sorted(settings.ENGINE_DIR.rglob('stockfish*.exe'))),None)


def weights_path(key):
    return settings.ENGINE_DIR/'maia'/f'maia-{DIFFICULTIES[key].model}.pb.gz'


def missing_files(key):
    path = engine_path(key)
    missing = [] if path is not None and path.is_file() else ['Engine executable']
    if DIFFICULTIES[key].engine == 'maia' and not weights_path(key).is_file():
        missing.append('Maia model')
    return missing
