"""Distinct board profiles with bundled CC0 surface materials."""

from dataclasses import dataclass
import math
from PIL import Image, ImageOps
from OpenGL import GL as gl
from otb_chess.services.settings import APP_DIR
from otb_chess.graphics.gl_primitives import material


@dataclass(frozen=True)
class BoardType:
    name: str
    texture: str | None
    depth: float
    radius: float
    gloss: int
    trim: bool = False


BOARD_TYPES = {
    "classic": BoardType("Classic",None,.28,.02,18),
    "marble": BoardType("Polished Marble","Marble012",.38,.16,100),
    "rounded_wood": BoardType("Rounded Oak","Wood049",.30,.32,45),
    "tournament": BoardType("Tournament Wood","Wood049",.18,.07,18,True),
    "canvas": BoardType("Canvas Roll-up","Fabric030",.055,.18,2),
    "luxury": BoardType("Marble & Brass","Marble012",.46,.22,100,True),
}


def outline(half, radius):
    """Clockwise in X/Z, hence upward-facing in OpenGL coordinates."""
    points = []
    for x,z,start in ((half-radius,half-radius,0),(-half+radius,half-radius,90),
                      (-half+radius,-half+radius,180),(half-radius,-half+radius,270)):
        for step in range(9):
            angle = math.radians(start+step*90/8)
            points.append((x+radius*math.cos(angle),z+radius*math.sin(angle)))
    return list(reversed(points))


class BoardSurfaceRenderer:
    def __init__(self):
        self.textures = {}
        self.failed = set()

    def texture(self, name):
        if name is None or name in self.failed:
            return None
        if name not in self.textures:
            try:
                with Image.open(APP_DIR/'assets'/'boards'/f'{name}.jpg') as source:
                    # Neutral luminance modulation preserves the user's colour theme.
                    image = ImageOps.autocontrast(source.convert('L')).point(
                        [int(140+i*115/255) for i in range(256)]).convert('RGB')
                    image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
                texture = gl.glGenTextures(1)
                gl.glBindTexture(gl.GL_TEXTURE_2D,texture)
                for parameter,value in ((gl.GL_TEXTURE_MIN_FILTER,gl.GL_LINEAR),
                                        (gl.GL_TEXTURE_MAG_FILTER,gl.GL_LINEAR),
                                        (gl.GL_TEXTURE_WRAP_S,gl.GL_REPEAT),
                                        (gl.GL_TEXTURE_WRAP_T,gl.GL_REPEAT)):
                    gl.glTexParameteri(gl.GL_TEXTURE_2D,parameter,value)
                gl.glTexImage2D(gl.GL_TEXTURE_2D,0,gl.GL_RGB,*image.size,0,
                                gl.GL_RGB,gl.GL_UNSIGNED_BYTE,image.tobytes())
                self.textures[name] = texture
            except (OSError,ValueError):
                self.failed.add(name)
                return None
        return self.textures[name]

    def slab(self, half, radius, top, bottom, color, texture, gloss):
        points = outline(half,radius)
        material(color,gloss)
        if texture:
            gl.glEnable(gl.GL_TEXTURE_2D)
            gl.glBindTexture(gl.GL_TEXTURE_2D,texture)
        else:
            gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glBegin(gl.GL_TRIANGLE_FAN)
        gl.glNormal3f(0,1,0)
        gl.glTexCoord2f(.5,.5)
        gl.glVertex3f(0,top,0)
        for x,z in points+[points[0]]:
            gl.glTexCoord2f((x+half)/(2*half),(z+half)/(2*half))
            gl.glVertex3f(x,top,z)
        gl.glEnd()
        gl.glDisable(gl.GL_TEXTURE_2D)
        material(tuple(c*.72 for c in color),gloss)
        gl.glBegin(gl.GL_QUADS)
        for (x,z),(xx,zz) in zip(points,points[1:]+points[:1]):
            length = math.hypot(xx-x,zz-z)
            if length < 1e-8:
                continue
            gl.glNormal3f(-(zz-z)/length,0,(xx-x)/length)
            for vertex in ((x,top,z),(x,bottom,z),(xx,bottom,zz),(xx,top,zz)):
                gl.glVertex3f(*vertex)
        gl.glEnd()

    def frame(self, key, color, flat=False):
        spec = BOARD_TYPES[key]
        gl.glPushAttrib(gl.GL_ENABLE_BIT|gl.GL_LIGHTING_BIT|gl.GL_TEXTURE_BIT|gl.GL_CURRENT_BIT)
        try:
            texture = self.texture(spec.texture)
            self.slab(4.36,spec.radius,0,-spec.depth,color,texture,spec.gloss)
            if spec.trim and not flat:
                trim = (.66,.47,.20) if key == 'luxury' else tuple(min(1,c*1.6) for c in color)
                self.slab(4.35,spec.radius,.004,-.105,trim,None,90)
                self.slab(4.28,max(.02,spec.radius-.04),.008,-.06,color,texture,spec.gloss)
            if key == 'canvas':
                gl.glDisable(gl.GL_LIGHTING)
                gl.glColor3f(.65,.61,.51)
                gl.glBegin(gl.GL_LINES)
                for axis in (-1,1):
                    for step in range(64):
                        p = -4.12+step*.13
                        gl.glVertex3f(p,.012,axis*4.25)
                        gl.glVertex3f(p+.065,.012,axis*4.25)
                        gl.glVertex3f(axis*4.25,.012,p)
                        gl.glVertex3f(axis*4.25,.012,p+.065)
                gl.glEnd()
        finally:
            gl.glPopAttrib()

    def square(self, key, x, z, color):
        spec = BOARD_TYPES[key]
        texture = self.texture(spec.texture)
        gl.glPushAttrib(gl.GL_ENABLE_BIT|gl.GL_LIGHTING_BIT|gl.GL_TEXTURE_BIT|gl.GL_CURRENT_BIT)
        try:
            material(color,spec.gloss)
            if texture:
                gl.glEnable(gl.GL_TEXTURE_2D)
                gl.glBindTexture(gl.GL_TEXTURE_2D,texture)
            else:
                gl.glDisable(gl.GL_TEXTURE_2D)
            scale = 2 if key == 'canvas' else .3
            gl.glBegin(gl.GL_QUADS)
            gl.glNormal3f(0,1,0)
            for dx,dz in ((-.5,-.5),(-.5,.5),(.5,.5),(.5,-.5)):
                gl.glTexCoord2f((x+dx+4)*scale,(z+dz+4)*scale)
                gl.glVertex3f(x+dx,.019,z+dz)
            gl.glEnd()
        finally:
            gl.glPopAttrib()

    def close(self):
        if self.textures:
            gl.glDeleteTextures(list(self.textures.values()))
        self.textures.clear()
        self.failed.clear()
