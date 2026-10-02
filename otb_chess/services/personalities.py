"""Curated Rodent IV opponents and their reproducible resources."""
from pathlib import Path
import re

from otb_chess.services import settings


PERSONALITIES = {
    "tal": ("Tal — Attacking", "Initiative, king attacks and tactical complications."),
    "kasparov": ("Kasparov — Dynamic", "Active pieces and sustained pressure."),
    "morphy": ("Morphy — Open play", "Rapid development and open lines."),
    "karpov": ("Karpov — Positional", "Patient improvement and restricting your pieces."),
    "petrosian": ("Petrosian — Defensive", "Preventing threats and protecting weaknesses."),
    "default": ("Default — Balanced", "A general-purpose opponent."),
}
BOOK_MODES = {"personality": "Personality repertoire", "none": "No book", "custom": "Custom book"}


def engine_path():
    return settings.ENGINE_DIR / "rodent-iv" / "rodent-iv.exe"


def personality_path(key):
    if key not in PERSONALITIES:
        raise ValueError("Unknown Rodent personality: " + str(key))
    return settings.ENGINE_DIR / "rodent-iv" / "personalities" / (key + ".txt")


def profile_settings(key, book_mode, custom_book=""):
    path = personality_path(key)
    if not path.is_file():
        raise ValueError("Rodent personalities are missing. Run tools/install_rodent.py.")
    if book_mode not in BOOK_MODES:
        raise ValueError("Unknown Rodent opening choice")
    if book_mode == "custom" and not Path(custom_book).is_file():
        raise ValueError("Choose an existing custom opening book.")
    resources = []
    if book_mode == "personality":
        books = {"guidebookfile": "guide.bin", "mainbookfile": "rodent.bin"}
        for line in path.read_text(encoding="utf-8").splitlines():
            match = re.match(r"\s*setoption name (GuideBookFile|MainBookFile) value (.+)", line, re.I)
            if match:
                books[match[1].lower()] = match[2].strip()
        resources = [str((path.parent.parent / "books" / book).resolve()) for book in books.values()]
        if any(not Path(resource).is_file() for resource in resources):
            raise ValueError("This personality's opening repertoire is missing. Run tools/install_rodent.py.")
    return {"personality": key, "personality_file": str(path.resolve()),
            "book_mode": book_mode, "custom_book": custom_book if book_mode == "custom" else "",
            "book_resources": resources}


def configure(engine, profile, elo):
    """Load style before strength; the personality can reset engine options."""
    if profile["personality"] not in PERSONALITIES or profile["book_mode"] not in BOOK_MODES:
        raise ValueError("Unsupported Rodent opponent")
    path = Path(profile["personality_file"])
    if not path.is_file():
        raise ValueError("Saved Rodent personality is unavailable.")
    if profile["book_mode"] == "custom" and not Path(profile["custom_book"]).is_file():
        raise ValueError("Saved opening book is unavailable.")
    if any(not Path(resource).is_file() for resource in profile.get("book_resources", [])):
        raise ValueError("Saved personality repertoire is unavailable.")
    engine.restore_options({"PersonalityFile": str(path)})
    engine.restore_options({"UseBook": profile["book_mode"] == "personality"})
    limits = engine.strength_range()
    if not limits or (elo is not None and not limits[0] <= elo <= limits[1]):
        raise ValueError("Rodent does not support this target Elo.")
    engine.configure_strength(elo)
