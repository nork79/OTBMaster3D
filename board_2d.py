"""Flat, antialiased chess symbols drawn from local vector shapes."""

import math
import chess
from PIL import Image, ImageDraw
from OpenGL import GL as gl


def piece_image(piece_type, fill, white):
    """Draw at 4x resolution; the symbols use the selected set's materials."""
    scale = 4
    image = Image.new("RGBA", (100*scale, 100*scale))
    draw = ImageDraw.Draw(image)
    ink = (38, 34, 30, 255) if white else (221, 216, 203, 255)
    fill = tuple(round(c*255) for c in fill) + (255,)

    def line(points, width=1.6):
        draw.line([(round(x*scale), round(y*scale)) for x,y in points],
                  fill=ink, width=round(width*scale), joint="curve")

    def polygon(points):
        draw.polygon([(round(x*scale),round(y*scale)) for x,y in points], fill=fill)
        line(points+[points[0]])

    def ellipse(bounds):
        draw.ellipse(tuple(round(v*scale) for v in bounds),fill=fill,outline=ink,width=6)

    def stem(top, bottom=72, upper=12, lower=22):
        # Cubic curves form the concave sides of a traditional turned stem.
        left = []
        for i in range(25):
            t=i/24
            x=(1-t)**3*(50-upper)+3*(1-t)**2*t*43+3*(1-t)*t*t*43+t**3*(50-lower)
            y=(1-t)**3*top+3*(1-t)**2*t*(top+8)+3*(1-t)*t*t*(bottom-8)+t**3*bottom
            left.append((x,y))
        polygon(left+[(100-x,y) for x,y in reversed(left)])

    if piece_type == chess.PAWN:
        stem(48,73,9,18)
        ellipse((39,24,61,46))
        polygon([(37,45),(63,45),(66,51),(34,51)])
    elif piece_type == chess.ROOK:
        polygon([(30,30),(30,17),(40,17),(40,26),(46,26),(46,17),
                 (54,17),(54,26),(60,26),(60,17),(70,17),(70,36),
                 (63,42),(63,66),(70,73),(30,73),(37,66),(37,42),(30,36)])
        line([(31,35),(69,35)])
        line([(38,44),(62,44)])
        line([(37,65),(63,65)])
    elif piece_type == chess.KNIGHT:
        polygon([(27,73),(30,61),(40,50),(41,42),(31,48),(22,44),
                 (24,35),(35,24),(40,15),(48,20),(55,16),(66,28),
                 (72,43),(73,58),(70,73)])
        line([(54,27),(62,38),(65,53),(60,66)])
        line([(31,40),(38,38)])
        draw.ellipse((43*scale,30*scale,47*scale,34*scale),fill=ink)
    elif piece_type == chess.BISHOP:
        stem(51,73,12,23)
        # Pointed mitre with a diagonal cut, rather than a religious figurine.
        points=[(50,17)]
        for i in range(33):
            a=math.pi + math.pi*i/32
            points.append((50+17*math.cos(a),36-17*math.sin(a)))
        polygon(points)
        line([(56,26),(44,40)],2.5)
        ellipse((46,11,54,19))
        polygon([(34,51),(66,51),(68,56),(32,56)])
    elif piece_type == chess.QUEEN:
        stem(49,73,14,24)
        polygon([(29,28),(38,40),(41,22),(46,38),(50,18),(54,38),
                 (59,22),(62,40),(71,28),(64,51),(36,51)])
        for x,y in ((28,25),(41,19),(59,19),(72,25)):
            ellipse((x-3,y-3,x+3,y+3))
        ellipse((47,12,53,18))
        line([(36,47),(64,47)])
        polygon([(34,51),(66,51),(68,56),(32,56)])
    elif piece_type == chess.KING:
        stem(47,73,14,24)
        polygon([(46,11),(54,11),(54,18),(61,18),(61,25),(54,25),
                 (54,34),(46,34),(46,25),(39,25),(39,18),(46,18)])
        polygon([(32,34),(40,30),(50,35),(60,30),(68,34),(63,49),(37,49)])
        polygon([(34,49),(66,49),(68,55),(32,55)])

    width = 22 if piece_type == chess.PAWN else 27
    polygon([(50-width+4,72),(50+width-4,72),(50+width,79),
             (50+width,85),(50-width,85),(50-width,79)])
    line([(50-width+1,79),(50+width-1,79)])
    return image.resize((256,256),Image.Resampling.LANCZOS)


def flat_square(x, z, size_x, size_z, color, y=0.02):
    gl.glPushAttrib(gl.GL_ENABLE_BIT | gl.GL_CURRENT_BIT)
    gl.glDisable(gl.GL_LIGHTING)
    gl.glDisable(gl.GL_CULL_FACE)
    gl.glColor3f(*color)
    gl.glBegin(gl.GL_QUADS)
    for a,b in ((-1,-1),(1,-1),(1,1),(-1,1)):
        gl.glVertex3f(x+a*size_x/2,y,z+b*size_z/2)
    gl.glEnd()
    gl.glPopAttrib()


class FlatPieceRenderer:
    def __init__(self):
        self.textures = {}

    def draw(self, spec, piece, x, z, yaw, lifted=False):
        color = spec.white if piece.color else spec.black
        key = (color,piece.color,piece.piece_type)
        if key not in self.textures:
            image = piece_image(piece.piece_type,color,piece.color)
            texture = gl.glGenTextures(1)
            gl.glBindTexture(gl.GL_TEXTURE_2D,texture)
            gl.glTexParameteri(gl.GL_TEXTURE_2D,gl.GL_TEXTURE_MIN_FILTER,gl.GL_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_2D,gl.GL_TEXTURE_MAG_FILTER,gl.GL_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_2D,gl.GL_TEXTURE_WRAP_S,gl.GL_CLAMP_TO_EDGE)
            gl.glTexParameteri(gl.GL_TEXTURE_2D,gl.GL_TEXTURE_WRAP_T,gl.GL_CLAMP_TO_EDGE)
            gl.glTexImage2D(gl.GL_TEXTURE_2D,0,gl.GL_RGBA,256,256,0,
                            gl.GL_RGBA,gl.GL_UNSIGNED_BYTE,image.tobytes())
            self.textures[key] = texture
        gl.glPushAttrib(gl.GL_ENABLE_BIT | gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT |
                        gl.GL_TEXTURE_BIT | gl.GL_CURRENT_BIT)
        gl.glDisable(gl.GL_LIGHTING)
        gl.glDisable(gl.GL_CULL_FACE)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA,gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glBindTexture(gl.GL_TEXTURE_2D,self.textures[key])
        gl.glDepthMask(gl.GL_FALSE)
        gl.glColor4f(1,1,1,1)
        gl.glPushMatrix()
        gl.glTranslatef(x,.06,z)
        gl.glRotatef(-math.degrees(yaw),0,1,0)
        radius = .53 if lifted else .50
        gl.glBegin(gl.GL_QUADS)
        for u,v,a,b in ((0,0,1,1),(1,0,-1,1),(1,1,-1,-1),(0,1,1,-1)):
            gl.glTexCoord2f(u,v)
            gl.glVertex3f(a*radius,0,b*radius)
        gl.glEnd()
        gl.glPopMatrix()
        gl.glPopAttrib()

    def close(self):
        if self.textures:
            gl.glDeleteTextures(list(self.textures.values()))
        self.textures.clear()
