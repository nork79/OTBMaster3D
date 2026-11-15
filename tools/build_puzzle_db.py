"""Build and verify the local SQLite puzzle database (assets/puzzles/puzzles.db).

Usage:
    python tools/build_puzzle_db.py
    python tools/build_puzzle_db.py --fetch-lichess --target-per-category 100
    python tools/build_puzzle_db.py --lichess-csv path/to/lichess_db_puzzle.csv --target-per-category 100
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from otb_chess.chess_backend.position import ChessPosition
from otb_chess.services.puzzles import Puzzle, PuzzleRepository
from otb_chess.services import settings


CURATED_PUZZLES: tuple[Puzzle, ...] = (
    # ======================== MATE IN 1 (12) ========================
    Puzzle("m1_back_rank", "mate1", "Back-Rank Rook Mate",
           "6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1", ("d1d8",), 800,
           "Back-Rank Mate", "The black king has no escape square on the back rank."),
    Puzzle("m1_smothered", "mate1", "Smothered Knight",
           "6rk/6pp/7N/8/8/8/8/6K1 w - - 0 1", ("h6f7",), 850,
           "Smothered Mate", "Black's own rook and pawns box in the king."),
    Puzzle("m1_scholars", "mate1", "Scholar's Mate",
           "r1bqk2r/pppp1ppp/2n2n2/2b1p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4", ("h5f7",), 750,
           "f7 Battery Mate", "Attack f7 with support from your bishop on c4."),
    Puzzle("m1_arabian", "mate1", "Arabian Mate",
           "7k/8/5N2/8/8/8/6R1/6K1 w - - 0 1", ("g2g8",), 900,
           "Arabian Mate", "Knight and rook team up on the corner."),
    Puzzle("m1_black_kiss", "mate1", "Supported Queen Mate",
           "6k1/8/8/8/8/5q2/4b1PP/6K1 b - - 0 1", ("f3f1",), 850,
           "Back-Rank Queen Mate", "Deliver check on the first rank with your bishop's support."),
    Puzzle("m1_anastasia_battery", "mate1", "Bishop-Supported Corner Mate",
           "5r1k/4N1pp/8/8/8/3B4/7Q/6K1 w - - 0 1", ("h2h7",), 900,
           "Corner Battery Mate", "Your bishop on d3 eyes h7 while the knight seals g8 and g6."),
    Puzzle("m1_fools_mate_pattern", "mate1", "Diagonal Queen Mate",
           "rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR b KQkq - 0 2", ("d8h4",), 700,
           "Fool's Mate Pattern", "Target the weakened e1-h4 diagonal."),
    Puzzle("m1_epaulette", "mate1", "Epaulette Mate",
           "3rkr2/3p1p2/8/8/2Q5/8/8/6K1 w - - 0 1", ("c4e4",), 950,
           "Epaulette Mate", "Black's own rooks and pawns box the king in."),
    Puzzle("m1_swallow_tail", "mate1", "Pawn-Supported Back Rank",
           "4k3/4P3/4K3/8/8/8/8/3Q4 w - - 0 1", ("d1d8",), 900,
           "Back-Rank Mate", "Your king and pawn control the escape squares."),

    # ======================== MATE IN 2 (12) ========================
    Puzzle("m2_back_rank_double", "mate2", "Back-Rank Double Rook",
           "2rr2k1/5ppp/8/8/8/8/3R1PPP/3R2K1 w - - 0 1", ("d2d8", "c8d8", "d1d8"), 1050,
           "Back-Rank Clearance", "Trade rooks on d8 to clear the way for the second rook."),
    Puzzle("m2_smothered_sac", "mate2", "Philidor's Smothered Mate",
           "5r1k/6pp/7N/8/8/1Q6/8/6K1 w - - 0 1", ("b3g8", "f8g8", "h6f7"), 1200,
           "Queen Sacrifice + Smothered Mate", "Force the rook to block its own king's escape square."),
    Puzzle("m2_boden", "mate2", "Boden's Mate",
           "2kr4/pp1n4/2p5/8/5B2/2QB4/PPP5/2K5 w - - 0 1", ("c3c6", "b7c6", "d3a6"), 1300,
           "Crisscrossing Bishops", "Sacrifice the queen on c6 to open the diagonal for your d3 bishop."),
    Puzzle("m2_anastasia", "mate2", "Anastasia's Mate",
           "5r1k/4N1pp/8/8/8/7Q/8/2K1R3 w - - 0 1", ("h3h7", "h8h7", "e1h1"), 1250,
           "Queen Sacrifice + Rook Mate", "Sacrifice the queen on h7 to open the h-file for the rook."),
    Puzzle("m2_queen_e8_sac", "mate2", "Queen Sacrifice on e8",
           "4rrk1/5ppp/8/8/8/4Q3/5PPP/4R1K1 w - - 0 1", ("e3e8", "f8e8", "e1e8"), 1100,
           "Back-Rank Deflection", "Sacrifice the queen on e8 to clear the file for your rook."),
    Puzzle("m2_morphy_opera", "mate2", "Opera House Finale",
           "4kb1r/p2n1ppp/4q3/4p1B1/4P3/1Q6/PPP2PPP/2KR4 w - - 0 1", ("b3b8", "d7b8", "d1d8"), 1350,
           "Queen Sacrifice + Rook Mate", "Sacrifice the queen on b8 to deflect the knight."),
    Puzzle("m2_black_queen_sac", "mate2", "Black Queen Corner Sac",
           "6k1/8/8/8/8/5q2/4rPPP/4R1K1 b - - 0 1", ("f3f2", "g1h1", "e2e1"), 1100,
           "Mate in 2", "Capture f2 with the queen to force the king into the corner."),

    # ======================== MATE IN 3 (4) ========================
    Puzzle("m3_smothered_full", "mate3", "Classic Smothered Mate in 3",
           "r4rk1/5Npp/8/8/8/1Q6/8/6K1 w - - 0 1", ("f7h6", "g8h8", "b3g8", "f8g8", "h6f7"), 1450,
           "Double Check + Smothered Mate", "Unleash a double check with the knight, then sacrifice the queen!"),
    Puzzle("m3_overloaded_backrank", "mate3", "Overloaded Back Rank in 3",
           "3rr1k1/2q2ppp/8/3Q4/8/8/3R1PPP/3R2K1 w - - 0 1", ("d5d8", "e8d8", "d2d8", "c7d8", "d1d8"), 1500,
           "Overloaded Back Rank", "Sacrifice the queen on d8 to overload Black's defenders."),
    Puzzle("m3_anastasia_full", "mate3", "Anastasia's Mate in 3",
           "5rk1/6pp/8/3N4/8/7Q/8/2K1R3 w - - 0 1", ("d5e7", "g8h8", "h3h7", "h8h7", "e1h1"), 1550,
           "Knight Check + Queen Sacrifice", "Check on e7 first to force the king into the corner."),
    Puzzle("m3_e8_battery", "mate3", "e-File Triple Battery Mate",
           "3rr1k1/4qppp/8/8/8/4Q3/4RPPP/4R1K1 w - - 0 1", ("e3e8", "d8e8", "e2e8", "e7e8", "e1e8"), 1450,
           "Back-Rank Battery", "Break through on e8 with your queen and two rooks."),

    # ======================== COMBINATIONS & EXCHANGES (12) ========================
    Puzzle("comb_exchange_fork", "combination", "Royal Fork Wins the Exchange",
           "4r1k1/5ppp/8/3N4/8/8/5PPP/4R1K1 w - - 0 1", ("d5e7", "g8f8", "e7c8"), 1150,
           "Knight Fork / Winning the Exchange", "Check the king and attack the rook at the same time."),
    Puzzle("comb_skewer_exchange", "combination", "Bishop Captures Pinned Rook",
           "6k1/8/4r3/8/8/1B6/6PP/6K1 w - - 0 1", ("b3e6",), 900,
           "Pin / Winning the Exchange", "The rook is pinned to the king on the a2-g8 diagonal."),
    Puzzle("comb_discovered_exchange", "combination", "Deflection Wins the Rook",
           "3r2k1/5ppp/8/3B4/8/8/5PPP/3R2K1 w - - 0 1", ("d5f7", "g8f7", "d1d8"), 1200,
           "Deflection / Winning the Exchange", "Pull the black king away from defending the d8 rook."),
    Puzzle("comb_knight_family_fork", "combination", "Knight Fork on c7",
           "r3k3/8/8/3N4/8/8/8/4K3 w - - 0 1", ("d5c7", "e8d7", "c7a8"), 950,
           "Knight Fork", "Jump to c7 to fork the king and rook."),
    Puzzle("comb_skewer_rook_queen", "combination", "Rook Skewer on the Back Rank",
           "4k3/8/8/8/8/8/3q4/R5K1 w - - 0 1", ("a1a8", "e8d7", "a8d8"), 1100,
           "Skewer", "Check along the 8th rank to skewer the king and queen."),
    Puzzle("comb_attraction_fork", "combination", "Knight Check Wins the Exchange",
           "4q1k1/4pppp/8/3N4/8/8/5PPP/4Q1K1 w - - 0 1", ("d5e7", "g8f8", "e7c8"), 1300,
           "Knight Fork / Exchange", "Check on e7 to win material."),
    Puzzle("comb_bishop_skewer_rooks", "combination", "Bishop Pin Wins the Knight",
           "6k1/8/4r3/3n4/8/1B6/8/6K1 w - - 0 1", ("b3d5",), 1100,
           "Pin & Win", "Capture the knight to pin the rook behind it."),
    Puzzle("comb_double_attack_rook", "combination", "Queen Back-Rank Trade",
           "r5k1/5ppp/8/8/8/2Q5/5PPP/6K1 w - - 0 1", ("c3c8", "a8c8", "g1f1"), 1100,
           "Back-Rank Combination", "Exploit the weak back rank."),
    Puzzle("comb_knight_exchange_win", "combination", "Knight Fork on d6",
           "4k3/5r2/8/8/4N3/8/8/6K1 w - - 0 1", ("e4d6", "e8f8", "d6f7"), 1150,
           "Knight Fork Winning Rook", "Fork the king and rook from d6."),

    # ======================== ENDGAME STUDIES (12) ========================
    Puzzle("end_lucena_bridge", "endgame", "Lucena Bridge Setup",
           "3K4/3P1k2/8/8/8/8/4R3/2r5 w - - 0 1", ("e2f2", "f7g7", "f2f4"), 1400,
           "Lucena Position (Building the Bridge)", "Drive the black king away, then prepare to shield your king."),
    Puzzle("end_rook_skewer", "endgame", "Endgame Rook Skewer",
           "4k3/4P3/8/8/8/8/r7/3R2K1 w - - 0 1", ("d1d8", "e8f7", "e7e8q"), 1250,
           "Deflection & Promotion", "Force the black king off the promotion square with a rook check."),
    Puzzle("end_opposition_break", "endgame", "Opposition Outflanking",
           "8/8/3k4/3P4/3K4/8/8/8 w - - 0 1", ("d4c4",), 1100,
           "King Outflanking", "Keep the opposition or outflank around the pawn."),
    Puzzle("end_pawn_breakthrough", "endgame", "Three-Pawn Breakthrough",
           "8/ppp5/8/PPP5/8/8/6k1/4K3 w - - 0 1", ("b5b6", "c7b6", "a5a6"), 1300,
           "Pawn Breakthrough", "Push the central candidate pawn to force a passed pawn."),
    Puzzle("end_knight_fork_promo", "endgame", "Knight Fork Stops Promotion",
           "8/8/8/8/8/4N3/5p1k/5K2 w - - 0 1", ("e3g4", "h2g3", "g4f2"), 1200,
           "Knight Fork in Pawn Endgame", "Fork the king and the promoting pawn."),
    Puzzle("end_rook_behind_pawn", "endgame", "Rook Captures Checking Rook",
           "8/P7/8/8/8/8/1k4K1/R6r w - - 0 1", ("a1h1",), 1000,
           "Rook Endgame Tactic", "Capture the undefended rook on h1."),
    Puzzle("end_king_square_rule", "endgame", "Catching the Outside Pawn",
           "8/8/8/pk6/8/8/6K1/8 w - - 0 1", ("g2f3",), 1050,
           "Rule of the Square", "Step inside the square of the passed pawn."),
    Puzzle("end_underpromotion_stalemate_avoid", "endgame", "Rook Underpromotion Avoids Stalemate",
           "7k/5K2/6P1/8/8/8/8/8 w - - 0 1", ("g6g7", "h8h7", "g7g8q"), 1150,
           "Pawn Promotion", "Advance the g-pawn and promote."),
)


def verify_puzzle(puzzle: Puzzle) -> str | None:
    try:
        pos = ChessPosition.from_fen(puzzle.fen)
        for uci in puzzle.solution_uci:
            mv = pos.parse_uci(uci)
            if not pos.is_legal(mv):
                return f"illegal move {uci}"
            pos.apply(mv)
        if puzzle.category.startswith("mate") and not pos.is_checkmate():
            return "does not end in checkmate"
    except Exception as exc:
        return str(exc)
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build and verify assets/puzzles/puzzles.db")
    parser.add_argument("--db", type=Path, default=settings.PUZZLE_DB_PATH, help="Output SQLite database path")
    parser.add_argument("--lichess-csv", type=Path, default=None, help="Optional Lichess CC0 lichess_db_puzzle.csv")
    parser.add_argument("--fetch-lichess", action="store_true", help="Fetch CC0 puzzles from Lichess / HuggingFace mirror")
    parser.add_argument("--fetch-source", choices=("hf", "zst"), default="hf", help="Remote puzzle source")
    parser.add_argument("--target-per-category", type=int, default=100, help="Target total puzzles per category")
    parser.add_argument("--limit-per-category", type=int, default=None, help="Optional max imported CSV rows per category")
    parser.add_argument("--min-popularity", type=int, default=75, help="Minimum Lichess puzzle popularity score")
    args = parser.parse_args(argv)

    valid: list[Puzzle] = []
    for p in CURATED_PUZZLES:
        err = verify_puzzle(p)
        if err:
            print(f"SKIP {p.puzzle_id}: {err}")
        else:
            valid.append(p)

    repo = PuzzleRepository(args.db)
    count = repo.upsert_puzzles(valid)
    print(f"Seeded {count} verified curated puzzles into {args.db}")
    if args.lichess_csv and args.lichess_csv.exists():
        imported = repo.import_lichess_csv(
            args.lichess_csv,
            limit_per_category=args.limit_per_category,
            target_per_category=None if args.limit_per_category is not None else args.target_per_category,
            min_popularity=args.min_popularity,
            spread_ratings=True,
        )
        print(f"Imported Lichess CC0 puzzles from CSV: {imported}")
    if args.fetch_lichess:
        target = None if args.limit_per_category is not None else args.target_per_category
        if args.fetch_source == "zst":
            imported = repo.import_lichess_zst_stream(
                limit_per_category=args.limit_per_category,
                target_per_category=target,
                min_popularity=args.min_popularity,
                spread_ratings=True,
            )
        else:
            imported = repo.import_lichess_hf_api(
                limit_per_category=args.limit_per_category,
                target_per_category=target,
                min_popularity=args.min_popularity,
                spread_ratings=True,
            )
        print(f"Fetched Lichess CC0 puzzles: {imported}")
    print("Category totals:", repo.count_by_category())


if __name__ == "__main__":
    main()
