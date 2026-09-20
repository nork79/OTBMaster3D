"""OpenGL setup, materials, geometry and coordinate glyphs."""

import math
from otb_chess.services.settings import COORD
from OpenGL.GL import GL_AMBIENT, GL_AMBIENT_AND_DIFFUSE, GL_BACK, GL_CULL_FACE, GL_DEPTH_TEST, GL_DIFFUSE, GL_FRONT, GL_LIGHT0, GL_LIGHT1, GL_LIGHTING, GL_LINES, GL_MODELVIEW, GL_MULTISAMPLE, GL_NORMALIZE, GL_PROJECTION, GL_QUADS, GL_SHININESS, GL_SPECULAR, GL_TRIANGLE_FAN, glBegin, glClearColor, glColor3f, glCullFace, glDisable, glEnable, glEnd, glLightfv, glLineWidth, glLoadIdentity, glMaterialf, glMaterialfv, glMatrixMode, glNormal3f, glPopMatrix, glPushMatrix, glRotatef, glScalef, glTranslatef, glVertex3f, glViewport
from OpenGL.GLU import gluPerspective


GLYPHS = {
    "1": [((0.5, 0.05), (0.5, 0.95)), ((0.35, 0.8), (0.5, 0.95))],
    "2": [
        ((0.15, 0.8), (0.3, 0.95)),
        ((0.3, 0.95), (0.7, 0.95)),
        ((0.7, 0.95), (0.85, 0.8)),
        ((0.85, 0.8), (0.15, 0.05)),
        ((0.15, 0.05), (0.85, 0.05)),
    ],
    "3": [
        ((0.15, 0.95), (0.75, 0.95)),
        ((0.75, 0.95), (0.85, 0.82)),
        ((0.85, 0.82), (0.55, 0.53)),
        ((0.55, 0.53), (0.85, 0.22)),
        ((0.85, 0.22), (0.75, 0.05)),
        ((0.75, 0.05), (0.15, 0.05)),
    ],
    "4": [
        ((0.75, 0.05), (0.75, 0.95)),
        ((0.75, 0.95), (0.15, 0.35)),
        ((0.15, 0.35), (0.9, 0.35)),
    ],
    "5": [
        ((0.85, 0.95), (0.2, 0.95)),
        ((0.2, 0.95), (0.2, 0.55)),
        ((0.2, 0.55), (0.72, 0.55)),
        ((0.72, 0.55), (0.85, 0.42)),
        ((0.85, 0.42), (0.85, 0.18)),
        ((0.85, 0.18), (0.72, 0.05)),
        ((0.72, 0.05), (0.15, 0.05)),
    ],
    "6": [
        ((0.8, 0.88), (0.68, 0.95)),
        ((0.68, 0.95), (0.3, 0.95)),
        ((0.3, 0.95), (0.15, 0.72)),
        ((0.15, 0.72), (0.15, 0.18)),
        ((0.15, 0.18), (0.3, 0.05)),
        ((0.3, 0.05), (0.7, 0.05)),
        ((0.7, 0.05), (0.85, 0.18)),
        ((0.85, 0.18), (0.85, 0.45)),
        ((0.85, 0.45), (0.7, 0.58)),
        ((0.7, 0.58), (0.15, 0.58)),
    ],
    "7": [((0.15, 0.95), (0.85, 0.95)), ((0.85, 0.95), (0.38, 0.05))],
    "8": [
        ((0.3, 0.5), (0.15, 0.65)),
        ((0.15, 0.65), (0.15, 0.82)),
        ((0.15, 0.82), (0.3, 0.95)),
        ((0.3, 0.95), (0.7, 0.95)),
        ((0.7, 0.95), (0.85, 0.82)),
        ((0.85, 0.82), (0.85, 0.65)),
        ((0.85, 0.65), (0.7, 0.5)),
        ((0.7, 0.5), (0.3, 0.5)),
        ((0.3, 0.5), (0.15, 0.35)),
        ((0.15, 0.35), (0.15, 0.18)),
        ((0.15, 0.18), (0.3, 0.05)),
        ((0.3, 0.05), (0.7, 0.05)),
        ((0.7, 0.05), (0.85, 0.18)),
        ((0.85, 0.18), (0.85, 0.35)),
        ((0.85, 0.35), (0.7, 0.5)),
    ],
    "A": [
        ((0.1, 0.05), (0.5, 0.95)),
        ((0.5, 0.95), (0.9, 0.05)),
        ((0.25, 0.45), (0.75, 0.45)),
    ],
    "B": [
        ((0.15, 0.05), (0.15, 0.95)),
        ((0.15, 0.95), (0.62, 0.95)),
        ((0.62, 0.95), (0.82, 0.8)),
        ((0.82, 0.8), (0.82, 0.62)),
        ((0.82, 0.62), (0.62, 0.5)),
        ((0.62, 0.5), (0.15, 0.5)),
        ((0.62, 0.5), (0.84, 0.37)),
        ((0.84, 0.37), (0.84, 0.18)),
        ((0.84, 0.18), (0.62, 0.05)),
        ((0.62, 0.05), (0.15, 0.05)),
    ],
    "C": [
        ((0.85, 0.82), (0.7, 0.95)),
        ((0.7, 0.95), (0.28, 0.95)),
        ((0.28, 0.95), (0.12, 0.78)),
        ((0.12, 0.78), (0.12, 0.22)),
        ((0.12, 0.22), (0.28, 0.05)),
        ((0.28, 0.05), (0.7, 0.05)),
        ((0.7, 0.05), (0.85, 0.18)),
    ],
    "D": [
        ((0.15, 0.05), (0.15, 0.95)),
        ((0.15, 0.95), (0.58, 0.95)),
        ((0.58, 0.95), (0.85, 0.7)),
        ((0.85, 0.7), (0.85, 0.3)),
        ((0.85, 0.3), (0.58, 0.05)),
        ((0.58, 0.05), (0.15, 0.05)),
    ],
    "E": [
        ((0.85, 0.95), (0.15, 0.95)),
        ((0.15, 0.95), (0.15, 0.05)),
        ((0.15, 0.5), (0.72, 0.5)),
        ((0.15, 0.05), (0.85, 0.05)),
    ],
    "F": [
        ((0.15, 0.05), (0.15, 0.95)),
        ((0.15, 0.95), (0.85, 0.95)),
        ((0.15, 0.5), (0.72, 0.5)),
    ],
    "G": [
        ((0.85, 0.8), (0.7, 0.95)),
        ((0.7, 0.95), (0.28, 0.95)),
        ((0.28, 0.95), (0.12, 0.78)),
        ((0.12, 0.78), (0.12, 0.22)),
        ((0.12, 0.22), (0.28, 0.05)),
        ((0.28, 0.05), (0.72, 0.05)),
        ((0.72, 0.05), (0.85, 0.2)),
        ((0.85, 0.2), (0.85, 0.48)),
        ((0.85, 0.48), (0.55, 0.48)),
    ],
    "H": [
        ((0.15, 0.05), (0.15, 0.95)),
        ((0.85, 0.05), (0.85, 0.95)),
        ((0.15, 0.5), (0.85, 0.5)),
    ],
}


def setup_gl(w, h):
    glViewport(0, 0, max(1, w), max(1, h))
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(40, w / max(1, float(h)), 0.1, 80)
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_CULL_FACE)
    glCullFace(GL_BACK)
    glEnable(GL_NORMALIZE)
    glEnable(GL_MULTISAMPLE)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_LIGHT1)
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.28, 0.28, 0.28, 1))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.92, 0.92, 0.92, 1))
    glLightfv(GL_LIGHT1, GL_AMBIENT, (0, 0, 0, 1))
    glLightfv(GL_LIGHT1, GL_DIFFUSE, (0.22, 0.25, 0.30, 1))
    glClearColor(0.055, 0.055, 0.065, 1)


def material(rgb, shininess=35):
    glMaterialfv(GL_FRONT, GL_AMBIENT_AND_DIFFUSE, (*rgb, 1))
    glMaterialfv(GL_FRONT, GL_SPECULAR, (0.32, 0.32, 0.32, 1))
    glMaterialf(GL_FRONT, GL_SHININESS, shininess)


def draw_box(cx, cy, cz, sx, sy, sz, color):
    material(color, 18)
    x0, x1 = cx - sx / 2, cx + sx / 2
    y0, y1 = cy - sy / 2, cy + sy / 2
    z0, z1 = cz - sz / 2, cz + sz / 2
    faces = [
        ((0, 1, 0), [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)]),
        ((0, -1, 0), [(x0, y0, z1), (x1, y0, z1), (x1, y0, z0), (x0, y0, z0)]),
        ((0, 0, -1), [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)]),
        ((0, 0, 1), [(x1, y0, z1), (x0, y0, z1), (x0, y1, z1), (x1, y1, z1)]),
        ((-1, 0, 0), [(x0, y0, z1), (x0, y0, z0), (x0, y1, z0), (x0, y1, z1)]),
        ((1, 0, 0), [(x1, y0, z0), (x1, y0, z1), (x1, y1, z1), (x1, y1, z0)]),
    ]
    glBegin(GL_QUADS)
    for n, vs in faces:
        glNormal3f(*n)
        for v in vs:
            glVertex3f(*v)
    glEnd()


def draw_disc(x, y, z, radius, color, segments=32):
    """Draw a small upward-facing disc on the board plane."""
    glDisable(GL_LIGHTING)
    glColor3f(*color)
    glBegin(GL_TRIANGLE_FAN)
    glVertex3f(x, y, z)
    for step in range(segments + 1):
        angle = 2 * math.pi * step / segments
        glVertex3f(x + radius * math.cos(angle), y, z - radius * math.sin(angle))
    glEnd()
    glEnable(GL_LIGHTING)


def draw_check_halo(x, z):
    """Soft red ring around the king's base, shared by both board modes."""
    from OpenGL import GL as gl
    gl.glPushAttrib(gl.GL_ENABLE_BIT | gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT | gl.GL_CURRENT_BIT)
    gl.glDisable(gl.GL_LIGHTING)
    gl.glDisable(gl.GL_TEXTURE_2D)
    gl.glDisable(gl.GL_CULL_FACE)
    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
    gl.glDepthMask(gl.GL_FALSE)
    for inner, outer, alpha in ((.32, .40, .32), (.40, .45, .88), (.45, .49, .28)):
        gl.glColor4f(1.0, .06, .05, alpha)
        gl.glBegin(gl.GL_QUAD_STRIP)
        for step in range(65):
            angle = math.tau * step / 64
            for radius in (inner, outer):
                gl.glVertex3f(x + radius * math.cos(angle), .045, z + radius * math.sin(angle))
        gl.glEnd()
    gl.glPopAttrib()


def draw_glyph(ch, x, y, z, view_yaw, scale=0.18):
    """Draw a board label flat on the board and readable from the current view."""
    segs = GLYPHS.get(ch.upper())
    if not segs:
        return
    glDisable(GL_LIGHTING)
    glColor3f(*COORD)
    glLineWidth(1.5)
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(-math.degrees(view_yaw), 0, 1, 0)
    glRotatef(90, 1, 0, 0)
    glScalef(-scale, scale, scale)
    glBegin(GL_LINES)
    for a, b in segs:
        glVertex3f(a[0] - 0.5, a[1] - 0.5, 0)
        glVertex3f(b[0] - 0.5, b[1] - 0.5, 0)
    glEnd()
    glPopMatrix()
    glEnable(GL_LIGHTING)

