# Piece sets

The View ? Piece set menu switches immediately, keeps the current game and clocks,
and remembers the selection. Assets are bundled, so no downloads are needed at
runtime.

- **Tournament Staunton**: all six 3D models from
  [clarkerubber/Staunton-Pieces](https://github.com/clarkerubber/Staunton-Pieces),
  `Source/Staunton`, in an ivory/black satin finish.
- **Wooden Staunton**: the same sourced geometry in boxwood/rosewood colours
  (solid material colours, not wood-grain textures).
- **Classic Club**: original procedural models with turned bases, bevelled horse
  heads, bishop slits, crenellated rooks, queen crowns and king crosses.
- **Sci-fi Vehicles**: Drummyfish's CC0 tanks, vehicles and towers, converted from
  Blender to OBJ. See [source and conversion credits](scifi/README.md).

The 2D view has an independent View → 2D piece set menu, with Classic symbols
and five [additional MIT-licensed sets](../pieces_2d/README.md). Classic uses the
selected 3D set's white/black colours. Board colours and backgrounds are shared
between 2D and 3D. The former Original option has been removed; saved selections
of it automatically use Tournament Staunton instead.

The sourced models are copyright (c) 2014 clarkerubber and distributed under the
MIT licence. The full licence is in [tournament/LICENSE](tournament/LICENSE).
Modifications: centring, a uniform scale (king height 1.55 board units),
crease-aware smooth normals, and conversion from binary STL to compressed
triangle meshes. The original model proportions are preserved. Render materials
are supplied by this app. The meshes were retrieved on 2026-09-16 from:

`https://raw.githubusercontent.com/clarkerubber/Staunton-Pieces/master/Source/Staunton/{Piece}/{Piece}.STL`

`{Piece}` is Pawn, Knight, Bishop, Rook, Queen or King. To rebuild the meshes from
those six files (lowercase local filenames) and their upstream LICENSE:

```powershell
.\.venv\Scripts\python.exe tools\convert_staunton.py source_directory assets\pieces\tournament
```

Each `.mesh.gz` contains little-endian float32 records `(nx, ny, nz, x, y, z)`;
every three records form a triangle. No external model library is required.

## Add another complete set

Create a subfolder here containing `pawn.obj`, `knight.obj`, `bishop.obj`,
`rook.obj`, `queen.obj`, `king.obj`, the source licence/credits, and `set.json`:

```json
{
  "name": "My chess set",
  "description": "A short description of the design."
}
```

Restart the app to discover it. Only complete sets appear. Use triangulated OBJ
files with Y up, White's knight facing +Z, outward face winding, and consistent
units across all six pieces. Vertex normals are supported; material libraries
and textures are not. The app centres each piece, preserves relative dimensions,
and scales the whole set to fit the squares. Invalid model data produces an error
when selected and leaves the previous set active.
