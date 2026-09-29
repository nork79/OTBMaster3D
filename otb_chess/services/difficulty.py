"""Plain-language practice levels backed by Fairy-Stockfish or Stockfish."""
from dataclasses import dataclass
from otb_chess.services import settings


@dataclass(frozen=True)
class Difficulty:
    label: str
    engine: str
    rating: int | None
    skill: int | None = None

    @property
    def description(self):
        if self.skill is not None:
            return f'Stockfish practice skill {self.skill}/20; uncalibrated, not a measured Elo rating.'
        if self.engine == 'fairy-stockfish':
            return f'Practice target {self.rating}; engine strength setting, not a certified human Elo rating.'
        return 'Stockfish at full strength.' if self.rating is None else f'Stockfish target rating {self.rating}; ratings are estimates.'


DIFFICULTIES = {
    # Stable selection IDs; bookmarked engines keep their own identity.
    # Fairy-Stockfish's native limiter covers 500–2850; no model files needed.
    'beginner_500': Difficulty('Beginner · ~500', 'fairy-stockfish', 500),
    **{f'level_{rating}': Difficulty(f'Beginner · ~{rating}', 'fairy-stockfish', rating)
       for rating in (600, 700, 800, 900, 1100)},
    **{f'level_{rating}': Difficulty(f'Club · ~{rating}', 'fairy-stockfish', rating)
       for rating in (1300,1400,1500)},
    **{f'level_{rating}': Difficulty(f'Club Advanced · ~{rating}', 'stockfish', rating)
           for rating in (1600, 1700, 1800, 1900)},
    'cm_practice': Difficulty('CM Level · ~2000','stockfish',2000),
    'master': Difficulty('IM Level · ~2200','stockfish',2200),
    'expert': Difficulty('GM Level · ~2500','stockfish',2500),
    'full': Difficulty('SuperGM Level','stockfish',None),
}


def engine_path(key):
    preset = DIFFICULTIES[key]
    if preset.engine == 'fairy-stockfish':
        return settings.ENGINE_DIR/'fairy-stockfish-14'/'fairy-stockfish_x86-64.exe'
    return next(iter(sorted(settings.ENGINE_DIR.rglob('stockfish*.exe'))),None)


def missing_files(key):
    path = engine_path(key)
    missing = [] if path is not None and path.is_file() else ['Engine executable']
    return missing
