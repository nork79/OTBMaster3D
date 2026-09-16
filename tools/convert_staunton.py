"""Convert the attributed Staunton STL files to compact, smooth render meshes.

Usage: python tools/convert_staunton.py source_directory output_directory
No network access or third-party conversion dependencies required.
"""

from collections import defaultdict
import gzip
import math
from pathlib import Path
import struct
import sys


def convert(source, target):
    raw = source.read_bytes()
    count = struct.unpack_from("<I", raw, 80)[0]
    if len(raw) != 84 + count * 50:
        raise ValueError("Expected binary STL")
    faces, adjacency = [], defaultdict(list)
    for i in range(count):
        row = struct.unpack_from("<12fH", raw, 84 + i * 50)
        points = [tuple(round(x, 5) for x in row[j:j+3]) for j in (3, 6, 9)]
        a, b, c = points
        u, v = [b[k]-a[k] for k in range(3)], [c[k]-a[k] for k in range(3)]
        n = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
        length = math.sqrt(sum(x*x for x in n))
        if length < 1e-10:
            continue
        n = tuple(x/length for x in n)
        faces.append((n, points))
        for p in points:
            adjacency[p].append(n)
    low = [min(p[k] for p in adjacency) for k in range(3)]
    high = [max(p[k] for p in adjacency) for k in range(3)]
    center = ((low[0]+high[0])/2, low[1], (low[2]+high[2])/2)
    # The source king is 78 units tall. Preserve the entire set's proportions.
    scale = 1.55/78
    out = bytearray()
    for n, points in faces:
        for p in points:
            neighbours = [q for q in adjacency[p] if sum(n[k]*q[k] for k in range(3)) > .75]
            smooth = [sum(q[k] for q in neighbours) for k in range(3)]
            length = math.sqrt(sum(x*x for x in smooth)) or 1
            smooth = [x/length for x in smooth]
            position = [(p[k]-center[k])*scale for k in range(3)]
            out.extend(struct.pack("<6f", *smooth, *position))
    target.write_bytes(gzip.compress(bytes(out), mtime=0))
    print(f"{source.stem}: {len(faces):,} triangles, {target.stat().st_size:,} bytes")


if __name__ == "__main__":
    source, target = map(Path, sys.argv[1:])
    target.mkdir(parents=True, exist_ok=True)
    for name in ("pawn", "knight", "bishop", "rook", "queen", "king"):
        convert(source / f"{name}.stl", target / f"{name}.mesh.gz")
    (target / "LICENSE").write_bytes((source / "LICENSE").read_bytes())
