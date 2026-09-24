"""Board gestures, camera controls and legacy GLFW event adapters."""

import glfw
import math
import time
from otb_chess.graphics.gl_primitives import setup_gl


class BoardInput:
    """Translate pointer gestures into camera changes and game moves."""

    @property
    def board_facing(self):
        """Semantic side selected by Flip/Reset, independent of camera orbit."""
        if self.board_mode == "2D":
            return "black" if self.two_d_flipped else "white"
        return getattr(self, "_three_d_facing", "white")

    def set_board_facing(self, facing):
        if facing not in ("white", "black"):
            raise ValueError("Facing must be white or black")
        if self.board_facing != facing:
            self.flip_board()

    @staticmethod
    def _s(w):
        return glfw.get_window_user_pointer(w)

    @staticmethod
    def _resize(w, x, y):
        s = BoardInput._s(w)
        s.width, s.height = max(1, x), max(1, y)
        setup_gl(s.width, s.height)

    @staticmethod
    def _scroll(w, dx, dy):
        s = BoardInput._s(w)
        if s.board_mode == "2D":
            s.two_d_scale = max(0.4, min(2.5, s.two_d_scale * math.exp(-max(-10, min(10, dy)) * 0.1)))
        else:
            s.distance = max(7, min(22, s.distance - dy * 0.7))
        s.mark_camera_dirty()

    @staticmethod
    def _mouse(w, b, a, m):
        s = BoardInput._s(w)
        p = glfw.get_cursor_pos(w)
        if b == glfw.MOUSE_BUTTON_RIGHT and a == glfw.PRESS and s.selected is not None:
            s.cancel_selection()
            return
        if a == glfw.PRESS and s.clock_mode == "OTB":
            binding_map = {
                "Right Mouse": glfw.MOUSE_BUTTON_RIGHT,
                "Middle Mouse": glfw.MOUSE_BUTTON_MIDDLE,
                "Mouse Button 4": glfw.MOUSE_BUTTON_4,
                "Mouse Button 5": glfw.MOUSE_BUTTON_5,
            }
            if s.clock_binding in binding_map and b == binding_map[s.clock_binding]:
                s.hit_clock()
                return
        if b == glfw.MOUSE_BUTTON_LEFT:
            if a == glfw.PRESS and (m & glfw.MOD_CONTROL):
                s.ctrl_left_rotate = True
                s.last_mouse = p
                s.board_pan_drag = False
                s.drag_piece = None
                return
            elif a == glfw.RELEASE and s.ctrl_left_rotate:
                s.ctrl_left_rotate = False
                s.mark_camera_dirty()
                return
            elif a == glfw.PRESS:
                s.left_press(p)
            elif a == glfw.RELEASE:
                s.left_release(p)
        elif b == glfw.MOUSE_BUTTON_RIGHT:
            if a == glfw.PRESS:
                s.right_drag = True
                s.last_mouse = p
            elif a == glfw.RELEASE:
                s.right_drag = False
                s.mark_camera_dirty()

    @staticmethod
    def _cursor(w, x, y):
        s = BoardInput._s(w)
        s.hover_square = s.square_at_mouse((x, y))
        if s.right_drag or s.ctrl_left_rotate:
            if s.board_mode == "2D":
                return
            dx = x - s.last_mouse[0]
            dy = y - s.last_mouse[1]
            s.yaw += dx * 0.009
            s.pitch = max(math.radians(14), min(math.radians(72), s.pitch + dy * 0.007))
            s.last_mouse = (x, y)
            s.mark_camera_dirty()
        elif glfw.get_mouse_button(w, glfw.MOUSE_BUTTON_LEFT) == glfw.PRESS:
            s.left_motion((x, y))

    @staticmethod
    def _key(w, key, sc, action, mods):
        if action != glfw.PRESS:
            return
        s = BoardInput._s(w)
        if key == glfw.KEY_ESCAPE:
            glfw.set_window_should_close(w, True)
        elif (
            key == glfw.KEY_SPACE
            and s.clock_mode == "OTB"
            and s.clock_binding == "Spacebar"
        ):
            s.hit_clock()
        elif key == glfw.KEY_F and mods & glfw.MOD_CONTROL:
            s.flip_board()
        elif key == glfw.KEY_U:
            s.takeback()

    def mark_camera_dirty(self):
        self.camera_dirty = True
        self.last_camera_change = time.perf_counter()

    def maybe_persist_camera(self):
        if self.camera_dirty and time.perf_counter() - self.last_camera_change > 0.35:
            self.camera_dirty = False
            self.persist()

    def cancel_selection(self):
        self.selected = self.drag_piece = self.drag_world = self.left_down_pos = None
        self.board_pan_drag = self.right_drag = self.ctrl_left_rotate = self.was_drag = False
        self.pan_start_world = None

    def left_press(self, pos):
        sq = self.square_at_mouse(pos)
        self.hover_square = sq
        self.left_down_pos = pos
        self.was_drag = False
        if (
            self.human_can_move()
            and self.selected is not None
            and sq in self.legal_targets()
        ):
            if self.try_move(self.selected, sq):
                self.selected = None
                return
        p = self.board.piece_at(sq) if sq is not None else None
        if self.human_can_move() and p and p.color == self.board.turn:
            self.selected = sq
            self.drag_piece = sq
            self.drag_world = self.ray_to_board(*pos)
            self.board_pan_drag = False
        else:
            self.board_pan_drag = True
            self.pan_start_world = self.ray_to_board(*pos)
            self.pan_start_offset = self.view_pan()

    def left_motion(self, pos):
        if self.left_down_pos:
            dx = pos[0] - self.left_down_pos[0]
            dy = pos[1] - self.left_down_pos[1]
            if dx * dx + dy * dy > 16:
                self.was_drag = True
        if self.drag_piece is not None:
            self.drag_world = self.ray_to_board(*pos)
        elif self.board_pan_drag and self.was_drag:
            cur = self.ray_to_board(*pos)
            if cur:
                if self.pan_start_world is None:
                    self.pan_start_world = cur
                    self.pan_start_offset = self.view_pan()
                else:
                    pan_x = self.pan_start_offset[0] + (
                        cur[0] - self.pan_start_world[0]
                    )
                    pan_z = self.pan_start_offset[1] + (
                        cur[2] - self.pan_start_world[2]
                    )
                    if self.board_mode == "2D":
                        self.two_d_pan_x, self.two_d_pan_z = pan_x, pan_z
                    else:
                        self.pan_x, self.pan_z = pan_x, pan_z
                    self.mark_camera_dirty()

    def left_release(self, pos):
        if self.drag_piece is not None:
            src = self.drag_piece
            dst = self.square_at_mouse(pos)
            if self.was_drag:
                moved = self.try_move(src, dst)
                self.selected = None if moved else src
        elif self.board_pan_drag and self.was_drag:
            self.mark_camera_dirty()
        self.drag_piece = self.drag_world = self.left_down_pos = None
        self.board_pan_drag = False
        self.pan_start_world = None
        self.was_drag = False

    def reset_view(self):
        if self.board_mode == "2D":
            self.two_d_flipped = False
            self.two_d_scale = 1.0
            self.two_d_pan_x = self.two_d_pan_z = 0.0
            self.persist()
            self.result_text = "View reset"
            return
        self.yaw = 0.0
        self._three_d_facing = "white"
        self.pitch = math.radians(40)
        self.pan_x = 0.0
        self.fit_board_view()
        self.mark_camera_dirty()
        self.persist()
        self.result_text = "View reset"

    def fit_board_view(self):
        """Fit and visually center the board and piece envelope at reset yaw."""
        aspect = self.width / max(1, self.height)
        tangent = math.tan(math.radians(20))
        cp, sp = math.cos(self.pitch), math.sin(self.pitch)
        # Include the frame underside and space for tall pieces on any square.
        points = [(x,y,z) for half,heights in ((4.36,(-.46,.025)),(3.92,(0,1.65)))
                  for x in (-half,half) for y in heights for z in (-half,half)]

        def bounds(distance, pan):
            projected = []
            for x,y,z in points:
                y -= self.target_y
                z += pan
                depth = distance - sp*y + cp*z
                projected.append((x/(depth*tangent*aspect),(cp*y+sp*z)/(depth*tangent)))
            return (max(abs(x) for x,y in projected),
                    min(y for x,y in projected),max(y for x,y in projected))

        def centered(distance):
            low,high = -3.0,3.0
            for _ in range(40):
                pan = (low+high)/2
                _,bottom,top = bounds(distance,pan)
                if bottom+top < 0:
                    low = pan
                else:
                    high = pan
            return (low+high)/2

        low,high = 7.0,100.0
        for _ in range(40):
            distance = (low+high)/2
            pan = centered(distance)
            width,bottom,top = bounds(distance,pan)
            if max(width,abs(bottom),abs(top)) > .93:
                low = distance
            else:
                high = distance
        self.pan_z = centered(high)
        # camera() applies this aspect correction when rendering.
        self.distance = high / max(1,1.48/aspect)

    def flip_board(self):
        if self.board_mode == "2D":
            self.two_d_flipped = not self.two_d_flipped
            self.two_d_pan_x = -self.two_d_pan_x
            self.two_d_pan_z = -self.two_d_pan_z
            self.persist()
            return
        self._three_d_facing = "black" if self.board_facing == "white" else "white"
        self.yaw = (self.yaw + math.pi) % math.tau
        self.pan_x = -self.pan_x
        self.pan_z = -self.pan_z
        self.mark_camera_dirty()
        self.persist()

