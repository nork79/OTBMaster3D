"""Chess puzzle repository (SQLite-backed), session evaluation, and progress persistence."""

import contextlib
import csv
from dataclasses import dataclass
import http.client
import json
import logging
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import time
from typing import Any, Iterable
import urllib.request

from otb_chess.chess_backend.position import ChessPosition
from otb_chess.services import settings

log = logging.getLogger(__name__)

PUZZLE_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("mate1", "Mate in 1"),
    ("mate2", "Mate in 2"),
    ("mate3", "Mate in 3"),
    ("combination", "Combinations & Exchanges"),
    ("endgame", "Endgame Studies"),
)

CATEGORY_LABELS: dict[str, str] = dict(PUZZLE_CATEGORIES)
LICHESS_PUZZLE_DB_URL = "https://database.lichess.org/lichess_db_puzzle.csv.zst"

_GENERIC_LICHESS_THEMES: frozenset[str] = frozenset({
    "mate",
    "mateIn1",
    "mateIn2",
    "mateIn3",
    "mateIn4",
    "mateIn5",
    "oneMove",
    "short",
    "long",
    "veryLong",
    "crushing",
    "advantage",
    "equality",
    "opening",
    "middlegame",
    "endgame",
    "master",
    "masterVsMaster",
    "superGM",
})

_THEME_DISPLAY_NAMES: dict[str, str] = {
    "backRankMate": "Back-Rank Mate",
    "smotheredMate": "Smothered Mate",
    "arabianMate": "Arabian Mate",
    "anastasiaMate": "Anastasia Mate",
    "bodenMate": "Boden's Mate",
    "doubleBishopMate": "Double Bishop Mate",
    "dovetailMate": "Dovetail Mate",
    "hookMate": "Hook Mate",
    "killBoxMate": "Kill-Box Mate",
    "fork": "Fork",
    "pin": "Pin",
    "skewer": "Skewer",
    "discoveredAttack": "Discovered Attack",
    "doubleCheck": "Double Check",
    "sacrifice": "Sacrifice",
    "deflection": "Deflection",
    "attraction": "Attraction",
    "clearance": "Clearance",
    "interference": "Interference",
    "xRayAttack": "X-Ray Attack",
    "exposedKing": "Exposed King",
    "kingsideAttack": "Kingside Attack",
    "queensideAttack": "Queenside Attack",
    "hangingPiece": "Hanging Piece",
    "trappedPiece": "Trapped Piece",
    "promotion": "Promotion",
    "underPromotion": "Underpromotion",
    "quietMove": "Quiet Move",
    "zugzwang": "Zugzwang",
    "pawnEndgame": "Pawn Endgame",
    "rookEndgame": "Rook Endgame",
    "bishopEndgame": "Bishop Endgame",
    "knightEndgame": "Knight Endgame",
    "queenEndgame": "Queen Endgame",
    "queenRookEndgame": "Queen & Rook Endgame",
    "capturingDefender": "Capturing Defender",
    "overloading": "Overloading",
    "intermezzo": "Intermezzo",
}


def _humanize_theme(theme: str) -> str:
    if theme in _THEME_DISPLAY_NAMES:
        return _THEME_DISPLAY_NAMES[theme]
    return re.sub(r"([a-z])([A-Z])", r"\1 \2", theme).strip().title()


def _format_lichess_title(category: str, themes: list[str], raw_id: str) -> str:
    informative = [_humanize_theme(t) for t in themes if t and t not in _GENERIC_LICHESS_THEMES]
    # Preserve order while deduplicating
    unique: list[str] = []
    for name in informative:
        if name not in unique:
            unique.append(name)
        if len(unique) >= 2:
            break
    base = " / ".join(unique) if unique else CATEGORY_LABELS.get(category, category.title())
    short_id = (raw_id or "").strip()[:5]
    return f"{base} #{short_id}" if short_id else base


@dataclass(frozen=True)
class Puzzle:
    """Single tactical, mating, combination, or endgame puzzle."""

    puzzle_id: str
    category: str
    title: str
    fen: str
    solution_uci: tuple[str, ...]
    rating: int = 1200
    theme: str = ""
    hint_text: str = ""
    source: str = "builtin"

    @property
    def category_label(self) -> str:
        return CATEGORY_LABELS.get(self.category, self.category.title())

    @property
    def player_color(self) -> bool:
        parts = self.fen.split()
        return len(parts) < 2 or parts[1].lower() == "w"

    @property
    def prompt_text(self) -> str:
        side = "White" if self.player_color else "Black"
        if self.category == "mate1":
            return f"{side} to move — Mate in 1"
        if self.category == "mate2":
            return f"{side} to move — Mate in 2"
        if self.category == "mate3":
            return f"{side} to move — Mate in 3"
        if self.category == "combination":
            return f"{side} to move — Win the exchange / combination"
        if self.category == "endgame":
            return f"{side} to move — Find the winning endgame plan"
        return f"{side} to move"


BUILTIN_PUZZLES: tuple[Puzzle, ...] = (
    Puzzle(
        puzzle_id="m1_back_rank",
        category="mate1",
        title="Back-Rank Rook Mate",
        fen="6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1",
        solution_uci=("d1d8",),
        rating=800,
        theme="Back-Rank Mate",
        hint_text="The black king has no escape square on the back rank.",
    ),
    Puzzle(
        puzzle_id="m2_smothered_sac",
        category="mate2",
        title="Philidor's Smothered Mate",
        fen="5r1k/6pp/7N/8/8/1Q6/8/6K1 w - - 0 1",
        solution_uci=("b3g8", "f8g8", "h6f7"),
        rating=1200,
        theme="Queen Sacrifice + Smothered Mate",
        hint_text="Force the rook to block its own king's escape square.",
    ),
    Puzzle(
        puzzle_id="m3_smothered_full",
        category="mate3",
        title="Classic Smothered Mate in 3",
        fen="r4rk1/5Npp/8/8/8/1Q6/8/6K1 w - - 0 1",
        solution_uci=("f7h6", "g8h8", "b3g8", "f8g8", "h6f7"),
        rating=1450,
        theme="Double Check + Smothered Mate",
        hint_text="Unleash a double check with the knight, then sacrifice the queen!",
    ),
    Puzzle(
        puzzle_id="comb_exchange_fork",
        category="combination",
        title="Royal Fork Wins the Exchange",
        fen="4r1k1/5ppp/8/3N4/8/8/5PPP/4R1K1 w - - 0 1",
        solution_uci=("d5e7", "g8f8", "e7c8"),
        rating=1150,
        theme="Knight Fork / Winning the Exchange",
        hint_text="Check the king and attack the rook at the same time.",
    ),
    Puzzle(
        puzzle_id="end_rook_skewer",
        category="endgame",
        title="Endgame Rook Skewer",
        fen="4k3/4P3/8/8/8/8/r7/3R2K1 w - - 0 1",
        solution_uci=("d1d8", "e8f7", "e7e8q"),
        rating=1250,
        theme="Deflection & Promotion",
        hint_text="Force the black king off the promotion square with a rook check.",
    ),
)


def _classify_lichess_themes(themes: set[str]) -> str | None:
    if "mateIn1" in themes:
        return "mate1"
    if "mateIn2" in themes:
        return "mate2"
    if "mateIn3" in themes:
        return "mate3"
    if "endgame" in themes or any(
        t in themes for t in ("pawnEndgame", "rookEndgame", "bishopEndgame", "knightEndgame", "queenEndgame")
    ):
        return "endgame"
    if any(
        t in themes
        for t in (
            "fork",
            "pin",
            "skewer",
            "discoveredAttack",
            "sacrifice",
            "deflection",
            "attraction",
            "xRayAttack",
            "crushing",
        )
    ):
        return "combination"
    return None


class PuzzleRepository:
    """SQLite-backed puzzle storage with indexed category/rating queries and CC0 CSV import."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or settings.PUZZLE_DB_PATH

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def ensure_schema(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS puzzles (
                puzzle_id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                fen TEXT NOT NULL,
                solution_uci TEXT NOT NULL,
                rating INTEGER NOT NULL DEFAULT 1200,
                theme TEXT NOT NULL DEFAULT '',
                hint_text TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT 'builtin'
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_puzzles_category_rating ON puzzles (category, rating)"
        )

    def upsert_puzzles(self, puzzles: list[Puzzle] | tuple[Puzzle, ...]) -> int:
        if not puzzles:
            return 0
        with contextlib.closing(self._connect()) as conn, conn:
            self.ensure_schema(conn)
            conn.executemany(
                """
                INSERT INTO puzzles (puzzle_id, category, title, fen, solution_uci, rating, theme, hint_text, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(puzzle_id) DO UPDATE SET
                    category=excluded.category,
                    title=excluded.title,
                    fen=excluded.fen,
                    solution_uci=excluded.solution_uci,
                    rating=excluded.rating,
                    theme=excluded.theme,
                    hint_text=excluded.hint_text,
                    source=excluded.source
                """,
                [
                    (
                        p.puzzle_id,
                        p.category,
                        p.title,
                        p.fen,
                        " ".join(p.solution_uci),
                        int(p.rating),
                        p.theme,
                        p.hint_text,
                        p.source,
                    )
                    for p in puzzles
                ],
            )
            return len(puzzles)

    def list_puzzles(
        self,
        category: str = "all",
        *,
        max_rating: int | None = None,
        limit: int | None = None,
    ) -> list[Puzzle]:
        if not self.db_path.exists():
            items = list(BUILTIN_PUZZLES)
            if category and category != "all":
                items = [p for p in items if p.category == category]
            if max_rating is not None:
                items = [p for p in items if p.rating <= max_rating]
            items.sort(key=lambda p: (p.rating, p.puzzle_id))
            return items[:limit] if limit is not None else items

        clauses: list[str] = []
        params: list[object] = []
        if category and category != "all":
            clauses.append("category = ?")
            params.append(category)
        if max_rating is not None:
            clauses.append("rating <= ?")
            params.append(int(max_rating))

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        limit_sql = f"LIMIT {int(limit)}" if limit is not None else ""
        sql = (
            f"SELECT puzzle_id, category, title, fen, solution_uci, rating, theme, hint_text, source "
            f"FROM puzzles {where} ORDER BY rating ASC, puzzle_id ASC {limit_sql}"
        )
        try:
            with contextlib.closing(self._connect()) as conn, conn:
                self.ensure_schema(conn)
                rows = conn.execute(sql, params).fetchall()
        except sqlite3.Error as exc:
            log.warning("Could not read puzzle database %s: %s", self.db_path, exc)
            return list(BUILTIN_PUZZLES)

        if not rows and category == "all" and max_rating is None:
            return list(BUILTIN_PUZZLES)
        return [
            Puzzle(
                puzzle_id=row["puzzle_id"],
                category=row["category"],
                title=row["title"],
                fen=row["fen"],
                solution_uci=tuple(row["solution_uci"].split()),
                rating=int(row["rating"]),
                theme=row["theme"],
                hint_text=row["hint_text"],
                source=row["source"],
            )
            for row in rows
            if row["solution_uci"].strip()
        ]

    def count_by_category(self) -> dict[str, int]:
        counts = {key: 0 for key, _ in PUZZLE_CATEGORIES}
        if not self.db_path.exists():
            for p in BUILTIN_PUZZLES:
                counts[p.category] = counts.get(p.category, 0) + 1
            return counts
        try:
            with contextlib.closing(self._connect()) as conn, conn:
                self.ensure_schema(conn)
                for row in conn.execute("SELECT category, COUNT(*) AS cnt FROM puzzles GROUP BY category"):
                    counts[row["category"]] = int(row["cnt"])
        except sqlite3.Error:
            pass
        return counts

    def _existing_puzzle_ids(self) -> set[str]:
        if not self.db_path.exists():
            return set()
        try:
            with contextlib.closing(self._connect()) as conn, conn:
                self.ensure_schema(conn)
                return {str(row[0]) for row in conn.execute("SELECT puzzle_id FROM puzzles")}
        except sqlite3.Error:
            return set()

    @staticmethod
    def _split_themes(raw_themes: Any) -> list[str]:
        if isinstance(raw_themes, (list, tuple)):
            return [str(t).strip() for t in raw_themes if str(t).strip()]
        return [t for t in str(raw_themes or "").split() if t]

    @classmethod
    def _parse_lichess_row(cls, row: dict[str, Any], category: str) -> Puzzle | None:
        raw_id = str(row.get("PuzzleId") or "").strip()
        moves = str(row.get("Moves") or "").split()
        fen_before = str(row.get("FEN") or "").strip()
        if not raw_id or len(moves) < 2 or not fen_before:
            return None
        if not category.startswith("mate") and len(moves) - 1 > 7:
            return None

        try:
            pos = ChessPosition.from_fen(fen_before)
            for idx, uci in enumerate(moves):
                mv = pos.parse_uci(uci)
                if not pos.is_legal(mv):
                    return None
                pos.apply(mv)
                if idx == 0:
                    puzzle_fen = pos.fen()
            if category.startswith("mate") and not pos.is_checkmate():
                return None
        except Exception:
            return None

        themes_raw = cls._split_themes(row.get("Themes"))
        try:
            rating = int(row.get("Rating") or 1200)
        except (TypeError, ValueError):
            rating = 1200
        theme_label = ", ".join(themes_raw[:4])
        return Puzzle(
            puzzle_id=f"lichess_{raw_id}",
            category=category,
            title=_format_lichess_title(category, themes_raw, raw_id),
            fen=puzzle_fen,
            solution_uci=tuple(moves[1:]),
            rating=rating,
            theme=theme_label,
            hint_text=f"Themes: {theme_label}" if theme_label else "",
            source="lichess-cc0",
        )

    def import_lichess_rows(
        self,
        rows: Iterable[dict[str, Any]],
        *,
        limit_per_category: int | None = 250,
        target_per_category: int | None = None,
        min_popularity: int | None = None,
        spread_ratings: bool = False,
        band_relax_after: int = 4000,
    ) -> dict[str, int]:
        """Import verified CC0 Lichess puzzle rows into the SQLite repository."""
        existing_counts = self.count_by_category() if target_per_category is not None else {}
        existing_ids = self._existing_puzzle_ids() if target_per_category is not None else set()

        quotas: dict[str, int] = {}
        for key, _ in PUZZLE_CATEGORIES:
            if target_per_category is not None:
                quotas[key] = max(0, target_per_category - existing_counts.get(key, 0))
            elif limit_per_category is not None:
                quotas[key] = max(0, limit_per_category)
            else:
                quotas[key] = 250

        imported_counts = {key: 0 for key, _ in PUZZLE_CATEGORIES}
        if all(quotas[k] <= 0 for k in quotas):
            return imported_counts

        band_counts: dict[str, list[int]] = {key: [0, 0, 0, 0] for key, _ in PUZZLE_CATEGORIES}
        batch: list[Puzzle] = []

        for scanned, row in enumerate(rows, start=1):
            raw_id = str(row.get("PuzzleId") or "").strip()
            pid = f"lichess_{raw_id}"
            if not raw_id or pid in existing_ids:
                continue

            if min_popularity is not None:
                try:
                    if int(row.get("Popularity") or 0) < min_popularity:
                        continue
                except (TypeError, ValueError):
                    continue

            themes_raw = self._split_themes(row.get("Themes"))
            category = _classify_lichess_themes(set(themes_raw))
            if category is None or imported_counts[category] >= quotas[category]:
                continue

            if spread_ratings and scanned < band_relax_after:
                try:
                    rating_val = int(row.get("Rating") or 1200)
                except (TypeError, ValueError):
                    rating_val = 1200
                band = 0 if rating_val < 1150 else 1 if rating_val < 1450 else 2 if rating_val < 1800 else 3
                band_cap = max(1, (quotas[category] + 3) // 4 + 4)
                if band_counts[category][band] >= band_cap:
                    continue
            else:
                band = None

            puzzle = self._parse_lichess_row(row, category)
            if puzzle is None:
                continue

            existing_ids.add(puzzle.puzzle_id)
            batch.append(puzzle)
            imported_counts[category] += 1
            if band is not None:
                band_counts[category][band] += 1
            if all(imported_counts[k] >= quotas[k] for k in quotas):
                break

        if batch:
            self.upsert_puzzles(batch)
        return imported_counts

    def import_lichess_csv(
        self,
        csv_path: Path,
        *,
        limit_per_category: int | None = 250,
        target_per_category: int | None = None,
        min_popularity: int | None = None,
        spread_ratings: bool = False,
    ) -> dict[str, int]:
        """Import CC0 puzzles from a Lichess puzzle CSV (PuzzleId,FEN,Moves,Rating,Themes,...)."""
        with open(csv_path, mode="r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            return self.import_lichess_rows(
                reader,
                limit_per_category=limit_per_category,
                target_per_category=target_per_category,
                min_popularity=min_popularity,
                spread_ratings=spread_ratings,
            )

    def import_lichess_zst_stream(
        self,
        url: str = LICHESS_PUZZLE_DB_URL,
        *,
        limit_per_category: int | None = None,
        target_per_category: int | None = 100,
        min_popularity: int = 75,
        spread_ratings: bool = True,
        timeout: int = 30,
    ) -> dict[str, int]:
        """Stream and decompress Lichess's CC0 .csv.zst puzzle DB until quotas are satisfied."""
        try:
            from compression import zstd
        except ImportError as exc:
            raise RuntimeError(
                "Streaming .zst puzzle archives requires Python 3.14+ (compression.zstd)."
            ) from exc

        req = urllib.request.Request(url, headers={"User-Agent": "otb-3d-chess-puzzle-loader/1.0"})

        def _row_iter():
            with (
                urllib.request.urlopen(req, timeout=timeout) as resp,
                zstd.open(resp, mode="rt", encoding="utf-8", errors="replace", newline="") as lines,
            ):
                yield from csv.DictReader(lines)

        with contextlib.closing(_row_iter()) as rows:
            return self.import_lichess_rows(
                rows,
                limit_per_category=limit_per_category,
                target_per_category=target_per_category,
                min_popularity=min_popularity,
                spread_ratings=spread_ratings,
            )

    def import_lichess_hf_api(
        self,
        *,
        limit_per_category: int | None = None,
        target_per_category: int | None = 100,
        min_popularity: int = 75,
        spread_ratings: bool = True,
        max_rows: int = 25000,
        page_size: int = 100,
        timeout: int = 20,
    ) -> dict[str, int]:
        """Stream CC0 Lichess puzzles from the HuggingFace Dataset Viewer JSON API."""
        host = "datasets-server.huggingface.co"

        def _row_iter():
            conn = http.client.HTTPSConnection(host, timeout=timeout)
            try:
                for offset in range(0, max_rows, page_size):
                    path = (
                        f"/rows?dataset=Lichess%2Fchess-puzzles&config=default"
                        f"&split=train&offset={offset}&length={page_size}"
                    )
                    payload = None
                    for attempt in range(3):
                        try:
                            conn.request("GET", path, headers={"User-Agent": "otb-3d-chess-puzzle-loader/1.0"})
                            resp = conn.getresponse()
                            body = resp.read()
                            if resp.status == 429:
                                time.sleep(1.0 + attempt)
                                continue
                            if resp.status != 200:
                                raise RuntimeError(f"HuggingFace API HTTP {resp.status}")
                            payload = json.loads(body)
                            break
                        except (http.client.HTTPException, OSError, ValueError):
                            conn.close()
                            if attempt == 2:
                                raise
                            time.sleep(0.4 * (attempt + 1))
                            conn = http.client.HTTPSConnection(host, timeout=timeout)
                    rows = (payload or {}).get("rows") or []
                    if not rows:
                        break
                    for entry in rows:
                        row = entry.get("row")
                        if isinstance(row, dict):
                            yield row
            finally:
                conn.close()

        with contextlib.closing(_row_iter()) as rows:
            return self.import_lichess_rows(
                rows,
                limit_per_category=limit_per_category,
                target_per_category=target_per_category,
                min_popularity=min_popularity,
                spread_ratings=spread_ratings,
                band_relax_after=3500,
            )


class PuzzleProgressStore:
    """Persist solved puzzle IDs in user config directory."""

    def __init__(self, path: Path | None = None):
        self.path = path or (settings.CONFIG_PATH.parent / "puzzles_progress.json")
        self.solved_ids: set[str] = set()
        self.load()

    def load(self) -> set[str]:
        if not self.path.exists():
            self.solved_ids = set()
            return self.solved_ids
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            raw = data.get("solved_ids", []) if isinstance(data, dict) else []
            self.solved_ids = {str(item) for item in raw if isinstance(item, str) and item.strip()}
        except (OSError, UnicodeDecodeError, ValueError):
            self.solved_ids = set()
        return self.solved_ids

    def save(self) -> bool:
        temporary = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps({"version": 1, "solved_ids": sorted(self.solved_ids)}, indent=2)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=self.path.name + ".",
                suffix=".tmp",
                delete=False,
            ) as stream:
                temporary = Path(stream.name)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            return True
        except (OSError, ValueError, TypeError) as exc:
            log.warning("Could not save puzzle progress: %s", exc)
            return False
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass

    def mark_solved(self, puzzle_id: str) -> None:
        pid = (puzzle_id or "").strip()
        if pid:
            self.solved_ids.add(pid)
            self.save()


class PuzzleSession:
    """Track move-by-move progress for an active puzzle on the board."""

    def __init__(self, puzzle: Puzzle):
        self.puzzle = puzzle
        self.ply_index = 0
        self.attempts = 0
        self.hint_used = False
        self.solved = False

    @property
    def expected_uci(self) -> str | None:
        if 0 <= self.ply_index < len(self.puzzle.solution_uci):
            return self.puzzle.solution_uci[self.ply_index]
        return None

    def evaluate_player_move(self, position_after_move: ChessPosition, uci_move: str) -> tuple[str, str | None]:
        """Evaluate a player's move and return (status, opponent_reply_uci).

        status is one of: 'solved', 'continue', 'wrong'.
        """
        if self.solved:
            return "solved", None
        self.attempts += 1
        expected = self.expected_uci
        normalized = (uci_move or "").strip().lower()

        # Accept any immediate checkmate on mate-in-N puzzles
        if self.puzzle.category in ("mate1", "mate2", "mate3") and position_after_move.is_checkmate():
            self.ply_index = len(self.puzzle.solution_uci)
            self.solved = True
            return "solved", None

        if expected is None or normalized != expected.lower():
            return "wrong", None

        self.ply_index += 1
        if self.ply_index >= len(self.puzzle.solution_uci):
            self.solved = True
            return "solved", None

        reply = self.puzzle.solution_uci[self.ply_index]
        self.ply_index += 1
        return "continue", reply
