"""Board rendering and projection, shared by Qt and the legacy host."""

from otb_chess.chess_backend import values as chess

from otb_chess.graphics.board_2d import flat_square
import glfw
import math
from otb_chess.services.settings import BOARD_Y, LEGAL, SELECT, TURN_INDICATOR
from otb_chess.graphics.gl_primitives import draw_box, draw_disc, draw_glyph
from OpenGL.GL import GL_COLOR_BUFFER_BIT, GL_CULL_FACE, GL_DEPTH_BUFFER_BIT, GL_DEPTH_TEST, GL_FALSE, GL_LIGHT0, GL_LIGHT1, GL_LIGHTING, GL_MODELVIEW, GL_MODELVIEW_MATRIX, GL_POSITION, GL_PROJECTION, GL_PROJECTION_MATRIX, GL_QUADS, GL_TEXTURE_2D, GL_TRUE, GL_VIEWPORT, glBegin, glBindTexture, glClear, glClearColor, glColor3f, glDepthMask, glDisable, glEnable, glEnd, glGetDoublev, glGetIntegerv, glLightfv, glLoadIdentity, glMatrixMode, glOrtho, glPopMatrix, glPushMatrix, glTexCoord2f, glTranslatef, glVertex2f
from OpenGL.GLU import gluLookAt, gluPerspective, gluUnProject


class BoardRendering:
    """Render controller state into the current host's OpenGL context."""

    def camera(self):
        aspect = self.width / max(1, self.height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        if self.board_mode == "2D":
            half_x = 4.65 * self.two_d_scale * max(1, aspect)
            half_z = 4.65 * self.two_d_scale * max(1, 1 / aspect)
            glOrtho(-half_x, half_x, -half_z, half_z, 0.1, 80)
        else:
            gluPerspective(40, aspect, 0.1, 80)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        if self.board_mode == "2D":
            gluLookAt(0, 10, 0, 0, 0, 0, 0, 0, -1 if self.two_d_flipped else 1)
            return
        cp = math.cos(self.pitch)
        distance = self.distance * max(1, 1.48 / aspect)
        eye = (
            math.sin(self.yaw) * cp * distance,
            math.sin(self.pitch) * distance + self.target_y,
            -math.cos(self.yaw) * cp * distance,
        )
        gluLookAt(*eye, 0, self.target_y, 0, 0, 1, 0)
        glLightfv(GL_LIGHT0, GL_POSITION, (4, 9, -6, 1))
        glLightfv(GL_LIGHT1, GL_POSITION, (-5, 5, 5, 1))

    def draw_background(self):
        glClearColor(*self.background_color, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        if (getattr(self, "preview_background_color", False)
                or self.background_texture is None or self.background_texture_size is None):
            return

        image_width, image_height = self.background_texture_size
        image_aspect = image_width / image_height
        viewport_aspect = self.width / max(1, self.height)
        u0, u1, v0, v1 = 0.0, 1.0, 0.0, 1.0
        if image_aspect > viewport_aspect:
            visible_width = viewport_aspect / image_aspect
            u0 = (1.0 - visible_width) / 2
            u1 = 1.0 - u0
        else:
            visible_height = image_aspect / viewport_aspect
            v0 = (1.0 - visible_height) / 2
            v1 = 1.0 - v0

        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_CULL_FACE)
        glDepthMask(GL_FALSE)
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(-1, 1, -1, 1, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.background_texture)
        glColor3f(1, 1, 1)
        glBegin(GL_QUADS)
        glTexCoord2f(u0, v0)
        glVertex2f(-1, -1)
        glTexCoord2f(u1, v0)
        glVertex2f(1, -1)
        glTexCoord2f(u1, v1)
        glVertex2f(1, 1)
        glTexCoord2f(u0, v1)
        glVertex2f(-1, 1)
        glEnd()
        glDisable(GL_TEXTURE_2D)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glDepthMask(GL_TRUE)
        glEnable(GL_CULL_FACE)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)

    def draw_board(self):
        flat = self.board_mode == "2D"
        yaw = self.view_yaw()
        if self.board_type != "classic":
            self.board_surface_renderer.frame(self.board_type,self.frame_color,flat)
        elif flat:
            flat_square(0, 0, 8.72, 8.72, self.frame_color, y=0)
        else:
            draw_box(0, -0.14, 0, 8.72, 0.28, 8.72, self.frame_color)
        legal = self.legal_targets()
        for r in range(8):
            for f in range(8):
                sq = chess.square(f, r)
                col = self.dark_square if (f + r) % 2 == 0 else self.light_square
                if sq == self.selected:
                    col = SELECT
                elif sq in legal:
                    col = tuple(0.60 * c + 0.40 * l for c, l in zip(col, LEGAL))
                if self.board_type != "classic":
                    self.board_surface_renderer.square(self.board_type,3.5-f,r-3.5,col)
                elif flat:
                    flat_square(3.5 - f, r - 3.5, 1, 1, col)
                else:
                    draw_box(3.5 - f, 0.005, r - 3.5, 0.995, 0.025, 0.995, col)

        if self.show_move_indicator:
            indicator_x = 4.17 if math.cos(yaw) >= 0 else -4.17
            indicator_z = -4.17 if self.board.turn == chess.WHITE else 4.17
            draw_disc(indicator_x, 0.04, indicator_z, 0.055, TURN_INDICATOR)

        if self.show_coordinates:
            # Screen-left is +X from White's initial view, so files are stored in
            # reverse world-X order. Keep them on the edge nearest the viewer so
            # White sees A..H and Black sees H..A after the board is flipped.
            file_label_z = -4.12 if math.cos(yaw) >= 0 else 4.12
            for f, ch in enumerate("HGFEDCBA"):
                draw_glyph(ch, f - 3.5, 0.035, file_label_z, yaw, 0.18)
            # Rank 1 belongs at the near-left corner and increases away from White.
            for r, ch in enumerate("12345678"):
                rank_label_x = -4.12 if flat and self.two_d_flipped else 4.12
                draw_glyph(ch, rank_label_x, 0.035, r - 3.5, yaw, 0.18)

    def draw(self):
        self.draw_background()
        self.camera()
        glPushMatrix()
        pan_x, pan_z = self.view_pan()
        glTranslatef(pan_x, 0, pan_z)
        self.draw_board()
        for sq, p in self.board.piece_map().items():
            if self.drag_piece == sq and self.was_drag and self.drag_world:
                continue
            self.draw_game_piece(
                p,
                3.5 - chess.square_file(sq),
                chess.square_rank(sq) - 3.5,
                sq == self.selected,
            )
        if self.drag_piece is not None and self.was_drag and self.drag_world:
            p = self.board.piece_at(self.drag_piece)
            if p:
                x, _, z = self.drag_world
                self.draw_game_piece(
                    p,
                    max(-3.85, min(3.85, x - pan_x)),
                    max(-3.85, min(3.85, z - pan_z)),
                    True,
                )
        glPopMatrix()

    def draw_game_piece(self, piece, x, z, lifted=False):
        spec = self.piece_sets[self.piece_set]
        if self.board_mode == "2D":
            self.flat_piece_renderer.draw(spec, piece, x, z, self.view_yaw(), lifted)
        else:
            self.piece_renderer.draw(spec, piece, x, z, lifted)

    def make_context_current(self):
        if self.render_widget is not None:
            self.render_widget.makeCurrent()
        else:
            glfw.make_context_current(self.window)

    def view_pan(self):
        return (self.two_d_pan_x, self.two_d_pan_z) if self.board_mode == "2D" else (self.pan_x, self.pan_z)

    def view_yaw(self):
        if self.board_mode == "2D":
            return math.pi if self.two_d_flipped else 0
        return self.yaw

    def ray_to_board(self, mx, my):
        # Input positions are window coordinates; OpenGL uses framebuffer pixels.
        self.make_context_current()
        if self.render_widget is not None:
            window_width, window_height = self.render_widget.width(), self.render_widget.height()
        else:
            window_width, window_height = glfw.get_window_size(self.window)
        mx *= self.width / max(1, window_width)
        my *= self.height / max(1, window_height)
        self.camera()
        vp = glGetIntegerv(GL_VIEWPORT)
        model = glGetDoublev(GL_MODELVIEW_MATRIX)
        proj = glGetDoublev(GL_PROJECTION_MATRIX)
        near = gluUnProject(mx, vp[3] - my, 0, model, proj, vp)
        far = gluUnProject(mx, vp[3] - my, 1, model, proj, vp)
        dy = far[1] - near[1]
        if abs(dy) < 1e-8:
            return None
        t = (BOARD_Y - near[1]) / dy
        if t < 0:
            return None
        return (
            near[0] + t * (far[0] - near[0]),
            BOARD_Y,
            near[2] + t * (far[2] - near[2]),
        )

    def square_at_mouse(self, pos):
        p = self.ray_to_board(*pos)
        if not p:
            return None
        pan_x, pan_z = self.view_pan()
        f = 7 - int(math.floor((p[0] - pan_x) + 4))
        r = int(math.floor((p[2] - pan_z) + 4))
        return chess.square(f, r) if 0 <= f < 8 and 0 <= r < 8 else None

