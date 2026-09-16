"""Complete local chess sets and a cached OpenGL mesh renderer.

Tournament models are by clarkerubber (MIT); the club design is procedural.
Optional external sets use six Wavefront OBJ files plus set.json;
see assets/pieces/README.md.
"""

from dataclasses import dataclass
import json
import gzip
import struct
import math
from pathlib import Path

import chess
from OpenGL import GL as gl


PIECE_NAMES = ("pawn", "knight", "bishop", "rook", "queen", "king")


@dataclass(frozen=True)
class PieceSet:
    key: str
    name: str
    description: str
    style: str
    white: tuple = (0.91, 0.84, 0.69)
    black: tuple = (0.095, 0.075, 0.065)
    accent: tuple = (0.53, 0.36, 0.15)
    directory: Path | None = None


ASSET_DIR = Path(__file__).resolve().parent / "assets" / "pieces" / "tournament"
BUILTIN_SETS = (
    PieceSet("tournament", "Tournament Staunton",
             "Traditional Staunton in satin ivory and black.", "mesh",
             (0.80, 0.78, 0.70), (0.115, 0.12, 0.13), directory=ASSET_DIR),
    PieceSet("wooden", "Wooden Staunton",
             "The same Staunton carving in boxwood and rosewood tones.", "mesh",
             (0.76, 0.54, 0.30), (0.23, 0.095, 0.045), directory=ASSET_DIR),
    PieceSet("club", "Classic Club",
             "Simple turned pieces with carved knights and mitred bishops.", "staunton",
             (0.91, 0.87, 0.75), (0.10, 0.11, 0.12), (0.34, 0.31, 0.25)),
)


def discover_sets(root):
    """Only offer complete sets. Invalid custom manifests cannot break startup."""
    result = {spec.key: spec for spec in BUILTIN_SETS}
    for manifest in sorted(Path(root).glob("*/set.json")):
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            if not all((manifest.parent / f"{name}.obj").is_file()
                       for name in PIECE_NAMES):
                continue
            name = data["name"]
            if not isinstance(name, str) or not name.strip():
                continue
            key = f"external:{manifest.parent.name}"
            result[key] = PieceSet(key, name, str(data.get("description", "Imported 3D set")),
                                   "obj", directory=manifest.parent)
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return result


def normal(a, b, c):
    u = [b[i] - a[i] for i in range(3)]
    v = [c[i] - a[i] for i in range(3)]
    n = (u[1]*v[2] - u[2]*v[1], u[2]*v[0] - u[0]*v[2], u[0]*v[1] - u[1]*v[0])
    length = math.sqrt(sum(x*x for x in n)) or 1
    return tuple(x / length for x in n)


def triangle(mesh, a, b, c):
    n = normal(a, b, c)
    mesh.extend((n, p) for p in (a, b, c))


def lathe(profile, segments=64):
    """Revolve a bottom-to-top (radius, height) profile with outward normals."""
    mesh = []
    for (r0, y0), (r1, y1) in zip(profile, profile[1:]):
        dy, dr = y1-y0, r1-r0
        length = math.hypot(dy, dr) or 1
        for i in range(segments):
            angles = (2*math.pi*i/segments, 2*math.pi*(i+1)/segments)
            normals = [(dy*math.cos(a)/length, -dr/length, dy*math.sin(a)/length) for a in angles]
            points = [(r*math.cos(a), y, r*math.sin(a))
                      for r, y, a in ((r0,y0,angles[0]), (r1,y1,angles[0]),
                                      (r1,y1,angles[1]), (r0,y0,angles[1]))]
            for j in (0, 1, 2, 0, 2, 3):
                mesh.append((normals[0 if j < 2 else 1], points[j]))
    return mesh


def ellipsoid(rx, ry, rz, center, segments=40, rings=20):
    mesh = []
    def vertex(i, j):
        a, b = math.pi*i/rings, math.tau*j/segments
        unit = (math.sin(a)*math.cos(b), -math.cos(a), math.sin(a)*math.sin(b))
        n = (unit[0]/rx, unit[1]/ry, unit[2]/rz)
        length = math.sqrt(sum(v*v for v in n)) or 1
        return (tuple(v/length for v in n),
                tuple(center[k] + unit[k]*r for k, r in enumerate((rx,ry,rz))))
    for i in range(rings):
        for j in range(segments):
            q = (vertex(i,j), vertex(i+1,j), vertex(i+1,j+1), vertex(i,j+1))
            mesh.extend(q[k] for k in (0,1,2,0,2,3))
    return mesh


def box(center, size):
    x,y,z = center
    a,b,c = (v/2 for v in size)
    vertices = [(x+sx*a, y+sy*b, z+sz*c) for sx,sy,sz in
                ((-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                 (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1))]
    mesh = []
    for face in ((0,3,2,1),(4,5,6,7),(0,4,7,3),(1,2,6,5),(3,7,6,2),(0,1,5,4)):
        a,b,c,d = [vertices[i] for i in face]
        triangle(mesh,a,b,c)
        triangle(mesh,a,c,d)
    return mesh


def triangulate(polygon):
    """Ear clipping for a simple 2D silhouette (including concave knights)."""
    def cross(a,b,c):
        return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
    indices = list(range(len(polygon)))
    area = sum(polygon[i][0]*polygon[(i+1)%len(polygon)][1] -
               polygon[(i+1)%len(polygon)][0]*polygon[i][1] for i in indices)
    if area < 0:
        indices.reverse()
    triangles = []
    while len(indices) > 3:
        for k, b in enumerate(indices):
            a, c = indices[k-1], indices[(k+1)%len(indices)]
            if cross(polygon[a],polygon[b],polygon[c]) <= 1e-10:
                continue
            if any(all(cross(polygon[u],polygon[v],polygon[p]) >= -1e-10
                       for u,v in ((a,b),(b,c),(c,a)))
                   for p in indices if p not in (a,b,c)):
                continue
            triangles.append((a,b,c))
            indices.pop(k)
            break
        else:
            raise ValueError("Cannot triangulate polygon")
    triangles.append(tuple(indices))
    return triangles


def knight_head(modern=False):
    # Silhouette coordinates are (forward, height); White faces +Z.
    outline = [(-.23,.42),(.16,.42),(.14,.57),(.06,.74),(.09,.90),
               (.28,.85),(.36,.90),(.34,1.03),(.17,1.16),(.04,1.21),
               (-.03,1.36),(-.10,1.21),(-.18,1.28),(-.23,1.08),
               (-.28,.87),(-.28,.64)]
    if modern:
        outline = [(-.23,.39),(.16,.39),(.02,.84),(.30,.81),(.36,.96),
                   (.08,1.16),(-.04,1.32),(-.13,1.16),(-.23,1.08),(-.28,.77)]
    mesh = []
    # Bevelled sides avoid the block-shaped knight of the original set.
    layers = []
    for x, scale in ((-.145,.79),(-.105,1),(.105,1),(.145,.79)):
        layers.append([(x, .88+(y-.88)*scale, z*scale) for z,y in outline])
    for a,b,c in triangulate(outline):
        triangle(mesh,layers[0][a],layers[0][b],layers[0][c])
        triangle(mesh,layers[-1][c],layers[-1][b],layers[-1][a])
    for left,right in zip(layers,layers[1:]):
        for i in range(len(outline)):
            j = (i+1)%len(outline)
            triangle(mesh,left[i],right[i],right[j])
            triangle(mesh,left[i],right[j],left[j])
    return mesh


def clip_mesh(mesh, axis, limit, keep_less):
    """Clip a closed convex mesh and cap its cut, used for the bishop's slit."""
    result, boundary = [], []
    def distance(p):
        return sum(p[i]*axis[i] for i in range(3))-limit
    for start in range(0,len(mesh),3):
        poly = mesh[start:start+3]
        clipped = []
        for k, (n,p) in enumerate(poly):
            nn,q = poly[(k+1)%3]
            dp,dq = distance(p),distance(q)
            inside = dp <= 0 if keep_less else dp >= 0
            other = dq <= 0 if keep_less else dq >= 0
            if inside:
                clipped.append((n,p))
            if inside != other:
                t = dp/(dp-dq)
                point = tuple(p[i]+t*(q[i]-p[i]) for i in range(3))
                norm = tuple(n[i]+t*(nn[i]-n[i]) for i in range(3))
                clipped.append((norm,point))
                boundary.append(point)
        for k in range(1,len(clipped)-1):
            result.extend((clipped[0],clipped[k],clipped[k+1]))
    if boundary:
        center = tuple(sum(p[i] for p in boundary)/len(boundary) for i in range(3))
        # Here the clipping plane normal lies in XY, so Z is an in-plane axis.
        boundary.sort(key=lambda p: math.atan2((p[0]-center[0])*(-axis[1]) +
                                              (p[1]-center[1])*axis[0], p[2]-center[2]))
        for p,q in zip(boundary,boundary[1:]+boundary[:1]):
            n = normal(center,p,q)
            if (sum(n[i]*axis[i] for i in range(3)) > 0) != keep_less:
                p,q = q,p
            triangle(result,center,p,q)
    return result


def build_piece(style, piece_type):
    modern = style == "modern"
    width = {chess.PAWN:.29, chess.KNIGHT:.34, chess.BISHOP:.33,
             chess.ROOK:.34, chess.QUEEN:.37, chess.KING:.39}[piece_type]
    if modern:
        base = [(0,0),(width*.88,0),(width,.035),(width,.09),
                (width*.88,.14),(width*.70,.17)]
    else:
        base = [(0,0),(width*.88,0),(width,.035),(width,.075),
                (width*.97,.10),(width*.86,.13),(width*.86,.16),
                (width*.95,.18),(width*.91,.21),(width*.72,.24)]
    stem_end = {chess.PAWN:.53,chess.KNIGHT:.39,chess.BISHOP:.77,
                chess.ROOK:.69,chess.QUEEN:.91,chess.KING:1.01}[piece_type]
    stem = [(width*.56,.29),(width*.40,stem_end-.16),(width*.40,stem_end-.04),
            (width*.62,stem_end),(width*.65,stem_end+.035),
            (width*.52,stem_end+.065),(0,stem_end+.065)]
    if modern:
        stem = [(width*.36,stem_end-.07),(width*.58,stem_end),
                (width*.55,stem_end+.04),(0,stem_end+.04)]
    body = lathe(base+stem)
    accents = lathe([(width*.99,.065),(width*1.005,.071),
                     (width*1.005,.084),(width*.99,.091)])
    if piece_type == chess.PAWN:
        body += ellipsoid(.155,.155,.155,(0,.71,0))
    elif piece_type == chess.KNIGHT:
        body += knight_head(modern)
        for x in (-.145,.145):
            accents += ellipsoid(.018,.027,.027,(x,1.075,.105),20,10)
    elif piece_type == chess.BISHOP:
        head = ellipsoid(.175,.265,.175,(0,1.035,0))
        # A real diagonal mitre cut with closed inner faces.
        body += clip_mesh(head,(.8,1,0),1.08,True)
        body += clip_mesh(head,(.8,1,0),1.13,False)
        body += ellipsoid(.048,.055,.048,(0,1.31,0),24,12)
    elif piece_type == chess.ROOK:
        body += lathe([(0,.71),(.235,.71),(.26,.75),(.26,.90),
                       (.18,.90),(.18,.78),(0,.78)])
        for i in range(6 if not modern else 4):
            a = math.tau*i/(6 if not modern else 4)
            tooth = box((0,.94,.215),(.105,.15,.105))
            for n,p in tooth:
                body.append(((n[0]*math.cos(a)+n[2]*math.sin(a), n[1],
                              -n[0]*math.sin(a)+n[2]*math.cos(a)),
                             (p[0]*math.cos(a)+p[2]*math.sin(a), p[1],
                              -p[0]*math.sin(a)+p[2]*math.cos(a))))
    elif piece_type == chess.QUEEN:
        body += lathe([(0,.95),(.17,.95),(.24,1.03),(.27,1.15),
                       (.22,1.15),(.18,1.05),(0,1.05)])
        for i in range(8):
            a = math.tau*i/8
            body += ellipsoid(.045,.075,.045,(.24*math.cos(a),1.16,.24*math.sin(a)),20,10)
        body += ellipsoid(.072,.085,.072,(0,1.18,0),24,12)
    elif piece_type == chess.KING:
        body += ellipsoid(.16,.14,.16,(0,1.14,0))
        body += box((0,1.385,0),(.085,.34,.085))
        body += box((0,1.435,0),(.265,.08,.085))
    return body, accents


def load_obj(path):
    """Read triangle/convex-polygon OBJ geometry, preserving supplied normals."""
    vertices, normals, mesh = [], [], []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split('#',1)[0].split()
        if not parts:
            continue
        if parts[0] in ("v", "vn"):
            values = tuple(float(x) for x in parts[1:4])
            if len(values) != 3 or not all(math.isfinite(x) for x in values):
                raise ValueError(f"Invalid coordinates in {path.name}")
            (vertices if parts[0] == "v" else normals).append(values)
        elif parts[0] == "f":
            corners = []
            for item in parts[1:]:
                refs = item.split('/')
                vi = int(refs[0])
                if vi == 0:
                    raise ValueError("OBJ indices start at 1")
                point = vertices[vi-1 if vi > 0 else vi]
                n = None
                if len(refs) > 2 and refs[2]:
                    ni = int(refs[2])
                    if ni == 0:
                        raise ValueError("OBJ indices start at 1")
                    n = normals[ni-1 if ni > 0 else ni]
                corners.append((n,point))
            for k in range(1,len(corners)-1):
                tri = (corners[0],corners[k],corners[k+1])
                face_normal = normal(*(v[1] for v in tri))
                mesh.extend((n or face_normal,p) for n,p in tri)
    if not mesh:
        raise ValueError(f"No faces in {path.name}")
    return mesh


class PieceRenderer:
    def __init__(self):
        self.cache = {}

    def prepare(self, spec):
        cache_key = self.cache_key(spec)
        if cache_key in self.cache:
            return
        if spec.style == "mesh":
            geometry = []
            for name in PIECE_NAMES:
                with gzip.open(spec.directory / f"{name}.mesh.gz", "rb") as source:
                    raw = source.read()
                rows = struct.iter_unpack("<6f", raw)
                geometry.append(([(row[:3], row[3:]) for row in rows], []))
        elif spec.style == "obj":
            meshes = [load_obj(spec.directory / f"{name}.obj") for name in PIECE_NAMES]
            # One shared scale preserves the artist's relative piece heights.
            height = max(p[1] for _,p in meshes[-1])-min(p[1] for _,p in meshes[-1])
            if height <= 0:
                raise ValueError("The king must have nonzero height (Y-up)")
            scale = 1.55/height
            width = max(max(p[i] for _,p in mesh)-min(p[i] for _,p in mesh)
                        for mesh in meshes for i in (0,2))
            if width > 0:
                scale = min(scale,.82/width)
            geometry = []
            for mesh in meshes:
                low = [min(p[i] for _,p in mesh) for i in range(3)]
                high = [max(p[i] for _,p in mesh) for i in range(3)]
                origin = ((low[0]+high[0])/2,low[1],(low[2]+high[2])/2)
                geometry.append(([(n,tuple((p[i]-origin[i])*scale for i in range(3)))
                                  for n,p in mesh],[]))
        else:
            geometry = [build_piece(spec.style,pt) for pt in chess.PIECE_TYPES]
        lists = []
        try:
            for body,accent in geometry:
                for mesh in (body,accent):
                    display_list = gl.glGenLists(1)
                    if not display_list:
                        raise RuntimeError("Could not allocate piece geometry")
                    lists.append(display_list)
                    gl.glNewList(display_list,gl.GL_COMPILE)
                    gl.glBegin(gl.GL_TRIANGLES)
                    for n,p in mesh:
                        gl.glNormal3f(*n)
                        gl.glVertex3f(*p)
                    gl.glEnd()
                    gl.glEndList()
            self.cache[cache_key] = tuple(lists)
        except Exception:
            for display_list in lists:
                gl.glDeleteLists(display_list,1)
            raise

    def draw(self, spec, piece, x, z, lifted=False):
        self.prepare(spec)
        gl.glPushMatrix()
        gl.glTranslatef(x,.045+(.20 if lifted else 0),z)
        if piece.color == chess.BLACK:
            gl.glRotatef(180,0,1,0)
        color = spec.white if piece.color else spec.black
        gl.glMaterialfv(gl.GL_FRONT_AND_BACK,gl.GL_AMBIENT_AND_DIFFUSE,(*color,1))
        gl.glMaterialfv(gl.GL_FRONT_AND_BACK,gl.GL_SPECULAR,(.23,.23,.23,1))
        gl.glMaterialf(gl.GL_FRONT_AND_BACK,gl.GL_SHININESS,72 if spec.style == "staunton" else 38)
        body,accent = self.cache[self.cache_key(spec)][2*(piece.piece_type-1):2*piece.piece_type]
        gl.glCallList(body)
        gl.glMaterialfv(gl.GL_FRONT_AND_BACK,gl.GL_AMBIENT_AND_DIFFUSE,(*spec.accent,1))
        gl.glMaterialf(gl.GL_FRONT_AND_BACK,gl.GL_SHININESS,85)
        gl.glCallList(accent)
        gl.glPopMatrix()

    @staticmethod
    def cache_key(spec):
        return (spec.style, str(spec.directory) if spec.directory else spec.key)

    def close(self):
        for lists in self.cache.values():
            for display_list in lists:
                gl.glDeleteLists(display_list,1)
        self.cache.clear()
