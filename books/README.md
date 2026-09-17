# Bundled opening repertoires

Source: https://github.com/lichess-org/chess-openings (downloaded 2026-09-18).
Original TSV files and CC0 dedication are preserved in `sources/`.

- `lichess-all.bin`: 7,991 position/move entries from all 3,810 named lines.
- `lichess-e4.bin`: 4,108 entries from lines beginning 1.e4.
- `lichess-d4.bin`: 2,724 entries from lines beginning 1.d4.

Built with `python tools/build_opening_books.py`. The converter includes up to
24 plies per line, merges transpositions, and writes sorted Polyglot records.
Weights count named lines, not popularity, wins, or engine evaluations. Some
named gambits are intentionally unsound; these books are for opening variety.
The app falls back to its selected engine when a position is outside the book.

The data is public domain / CC0, credited to the Lichess opening-data contributors.
Generated books retain that dedication.
