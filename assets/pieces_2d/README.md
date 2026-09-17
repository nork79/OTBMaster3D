# Additional 2D sets

Textbook (Cburnett) provides traditional black-and-white diagram pieces by
Colin M. L. Burnett (BSD-3-Clause). Chessnut is by Alexis Luengas (Apache-2.0),
and Firi is by James Faure (CC-BY-4.0). Their folders include source credits,
licences, SVGs and rasterised PNGs. Rebuild with tools/import_diagram_pieces.py.

Fantasy, Celtic, Spatial, Skulls and Eyes are by Maurizio Monge, MIT licensed.
Source: https://github.com/maurimo/chess-art
Retrieved: 2026-09-17. Each set includes the full upstream LICENSE.

Fantasy, Celtic and Spatial were configured with ivory/charcoal gradients and
contrasting outlines. Skulls and Eyes retain the original colours. Bundled SVGs
were rasterised to transparent 256x256 PNGs using tools/import_chess_art.py.
QtSvg is required only to rebuild assets, not to run the game.

View → 2D piece set selects these independently of the 3D pieces. Classic keeps
the original procedural symbols and matches the selected 3D set's colours.
