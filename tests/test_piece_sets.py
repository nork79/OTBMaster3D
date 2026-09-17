"""Run with: python -m unittest discover -s tests -v

Rendering tests use hidden OpenGL/Tk windows and never change user config.
"""

import gzip
import json
import math
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

import chess
import glfw
from otb_chess.core import game
from otb_chess.services import settings
import time
import tkinter as tk
from tkinter import messagebox
from OpenGL.GL import glFinish, glGetError, GL_NO_ERROR
from OpenGL.GLU import gluProject
from otb_chess.graphics.piece_sets import ASSET_DIR, PIECE_NAMES, discover_sets, load_obj


class AssetTests(unittest.TestCase):
    def test_sourced_set_is_complete_and_fits_board(self):
        heights = []
        for name in PIECE_NAMES:
            raw = gzip.decompress((ASSET_DIR / f"{name}.mesh.gz").read_bytes())
            self.assertEqual(len(raw) % 72, 0)
            rows = list(struct.iter_unpack("<6f", raw))
            self.assertGreater(len(rows), 0)
            for nx, ny, nz, x, y, z in rows:
                self.assertTrue(all(math.isfinite(v) for v in (nx,ny,nz,x,y,z)))
                self.assertAlmostEqual(nx*nx+ny*ny+nz*nz, 1, places=5)
                self.assertLessEqual(max(abs(x),abs(z)), .42)
                self.assertGreaterEqual(y, 0)
            heights.append(max(row[4] for row in rows))
        self.assertLess(heights[0], heights[3])  # pawn < rook
        self.assertLess(heights[4], heights[5])  # queen < king
        self.assertAlmostEqual(heights[5], 1.55, places=5)

    def test_discovery_requires_all_six_pieces(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            custom = root / "custom"
            custom.mkdir()
            (custom / "set.json").write_text(json.dumps({"name": "Test set"}))
            for name in PIECE_NAMES[:-1]:
                (custom / f"{name}.obj").write_text("v 0 0 0\n")
            self.assertNotIn("external:custom", discover_sets(root))
            (custom / "king.obj").write_text("v 0 0 0\n")
            self.assertIn("external:custom", discover_sets(root))
            (custom / "set.json").write_text("not json")
            self.assertNotIn("external:custom", discover_sets(root))

    def test_obj_negative_indices_and_invalid_mesh(self):
        with tempfile.TemporaryDirectory() as folder:
            obj = Path(folder) / "piece.obj"
            obj.write_text("v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nf -4 -3 -2 -1\n")
            mesh = load_obj(obj)
            self.assertEqual(len(mesh), 6)
            self.assertEqual(mesh[0][0], (0,0,1))
            obj.write_text("v 0 0 0\n")
            with self.assertRaises(ValueError):
                load_obj(obj)


class LiveSwitchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        create_window = glfw.create_window
        create_tk = tk.Tk

        def hidden_window(*args, **kwargs):
            glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
            return create_window(*args, **kwargs)

        def hidden_tk(*args, **kwargs):
            try:
                root = create_tk(*args, **kwargs)
            except tk.TclError as exc:
                # Some Windows Python installs package Tcl as zip libraries
                # that the sandbox cannot auto-mount. Unpack only for this test.
                if "init.tcl" not in str(exc):
                    raise
                libraries = Path(sys.base_prefix) / "tcl"
                cls.tcl_temp = tempfile.TemporaryDirectory()
                cls.addClassCleanup(cls.tcl_temp.cleanup)
                environment = {}
                for library, variable in (("tcl", "TCL_LIBRARY"), ("tk", "TK_LIBRARY")):
                    archive = next(libraries.glob(f"lib{library}*.zip"))
                    with zipfile.ZipFile(archive) as zipped:
                        zipped.extractall(cls.tcl_temp.name)
                    environment[variable] = str(Path(cls.tcl_temp.name) / f"{library}_library")
                env_patch = patch.dict(os.environ, environment)
                env_patch.start()
                cls.addClassCleanup(env_patch.stop)
                root = create_tk(*args, **kwargs)
            root.withdraw()
            return root

        with patch.object(glfw, "create_window", hidden_window), \
             patch.object(game, "load_config", settings.default_config), \
             patch.object(tk, "Tk", hidden_tk):
            cls.app = game.Chess3D()
            cls.app.build_ui()

    @classmethod
    def tearDownClass(cls):
        cls.app.ui.destroy()
        cls.app.piece_renderer.close()
        cls.app.flat_piece_renderer.close()
        glfw.destroy_window(cls.app.window)
        glfw.terminate()

    def test_switching_renders_and_preserves_game_and_persists(self):
        app = self.app
        app.board = chess.Board()
        app.board.push_uci("e2e4")
        app.board.push_uci("e7e5")
        app.selected = chess.G1
        app.white_time, app.black_time = 42.25, 37.75
        app.clock_mode = "OTB"
        app.awaiting_clock_press = True
        before = (app.board.fen(), tuple(app.board.move_stack), app.selected,
                  app.white_time, app.black_time, app.awaiting_clock_press)
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(settings, "CONFIG_PATH", Path(folder) / "config.json"):
            for key in app.piece_set_keys:
                app.piece_combo.current(app.piece_set_keys.index(key))
                app.piece_combo.event_generate("<<ComboboxSelected>>")
                app.ui.update()
                self.assertEqual(app.piece_set, key)
                self.assertEqual(settings.load_config()["piece_set"], key)
                app.draw()
                # Both colours, all six types, including the lifted drag path.
                for color in chess.COLORS:
                    for pt in chess.PIECE_TYPES:
                        app.draw_game_piece(chess.Piece(pt,color), 0,0,True)
                glFinish()
                self.assertEqual(glGetError(), GL_NO_ERROR)
                self.assertEqual(before, (app.board.fen(),tuple(app.board.move_stack),
                    app.selected,app.white_time,app.black_time,app.awaiting_clock_press))
        # Staunton finishes share one allocation; Club and Sci-fi each add one.
        self.assertEqual(len(app.piece_renderer.cache), 3)

    def test_load_error_keeps_previous_selection(self):
        app = self.app
        previous = app.piece_set
        app.piece_combo.current(app.piece_set_keys.index("club"))
        with patch.object(app.piece_renderer, "prepare", side_effect=ValueError("Invalid model")), \
             patch.object(messagebox, "showerror") as error, \
             patch.object(app, "persist") as persist:
            app.change_piece_set()
        self.assertEqual(app.piece_set, previous)
        self.assertEqual(app.piece_combo.current(), app.piece_set_keys.index(previous))
        error.assert_called_once()
        persist.assert_not_called()

    def test_2d_switch_preserves_colours_game_camera_and_picking(self):
        app = self.app
        self.assertNotIn("original", app.piece_set_keys)
        app.board = chess.Board()
        app.board.push_uci("e2e4")
        app.selected = chess.G8
        app.yaw, app.pitch, app.distance = .42, .73, 13.5
        app.pan_x, app.pan_z = 1.2, -.4
        before = (app.board.fen(), tuple(app.board.move_stack), app.white_time, app.black_time,
                  app.selected, app.light_square, app.dark_square, app.frame_color,
                  app.background_color, app.background_image_path,
                  app.yaw, app.pitch, app.distance, app.pan_x, app.pan_z)
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(settings, "CONFIG_PATH", Path(folder) / "config.json"):
            app.board_mode_var.set("2D")
            app.change_board_mode()
            self.assertEqual(settings.load_config()["board_mode"], "2D")
            for width,height in ((1180,800),(600,900)):
                glfw.set_window_size(app.window,width,height)
                glfw.poll_events()
                game.Chess3D._resize(app.window,*glfw.get_framebuffer_size(app.window))
                for flipped in (False,True):
                    app.two_d_flipped = flipped
                    app.draw()
                    for square in chess.SQUARES:
                        pos = self.screen_square(square)
                        self.assertEqual(app.square_at_mouse(pos), square)
                    self.assertEqual(glGetError(), GL_NO_ERROR)
            app.board_mode_var.set("3D")
            app.change_board_mode()
            app.draw()
            self.assertEqual(before, (app.board.fen(),tuple(app.board.move_stack),app.white_time,
                app.black_time,app.selected,app.light_square,app.dark_square,app.frame_color,
                app.background_color,app.background_image_path,app.yaw,app.pitch,app.distance,
                app.pan_x,app.pan_z))
            self.assertEqual(settings.load_config()["board_mode"], "3D")

    def screen_square(self, square):
        app = self.app
        app.camera()
        px,pz = app.view_pan()
        x,y,_ = gluProject(3.5-chess.square_file(square)+px,0,
                               chess.square_rank(square)-3.5+pz)
        width,height = glfw.get_window_size(app.window)
        return x*width/app.width, (app.height-y)*height/app.height

    def test_2d_click_and_drag_moves(self):
        app = self.app
        with patch.object(app, "persist"), patch.object(app, "play_game_sound"):
            app.board = chess.Board()
            app.game_over = app.game_started = app.awaiting_clock_press = False
            app.selected = None
            app.board_mode_var.set("2D")
            app.change_board_mode()
            app.draw()
            start,end = self.screen_square(chess.E2), self.screen_square(chess.E4)
            app.left_press(start)
            app.left_motion(end)
            app.draw()  # includes the flat dragging sprite
            app.left_release(end)
            self.assertEqual(app.board.peek(), chess.Move.from_uci("e2e4"))
            start,end = self.screen_square(chess.E7), self.screen_square(chess.E5)
            app.left_press(start)
            app.left_release(start)
            app.left_press(end)
            app.left_release(end)
            self.assertEqual(app.board.peek(), chess.Move.from_uci("e7e5"))
            app.board_mode_var.set("3D")
            app.change_board_mode()

    def test_zoom_and_2d_pan_follow_pointer_and_preserve_3d_camera(self):
        app = self.app
        camera = (app.yaw, app.pitch, app.distance, app.pan_x, app.pan_z)
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(settings, "CONFIG_PATH", Path(folder) / "config.json"):
            app.board = chess.Board()
            app.selected = None
            app.board_mode_var.set("2D")
            app.change_board_mode()
            app.reset_view()
            game.Chess3D._scroll(app.window, 0, 1)
            self.assertLess(app.two_d_scale, 1)
            game.Chess3D._scroll(app.window, 0, -1)
            self.assertAlmostEqual(app.two_d_scale, 1)
            for flipped in (False, True):
                app.two_d_flipped = flipped
                game.Chess3D._scroll(app.window, 0, 2)
                start = self.screen_square(chess.D4)
                before = app.view_pan()
                app.left_press(start)
                app.left_motion((start[0]+1,start[1]+1))
                self.assertEqual(app.view_pan(), before)
                end = (start[0]+60,start[1]+35)
                app.left_motion(end)
                app.left_release(end)
                actual = self.screen_square(chess.D4)
                self.assertAlmostEqual(actual[0],end[0],places=4)
                self.assertAlmostEqual(actual[1],end[1],places=4)
                app.draw()
                for square in chess.SQUARES:
                    self.assertEqual(app.square_at_mouse(self.screen_square(square)),square)
                self.assertEqual(app.board.fen(),chess.STARTING_FEN)
            app.persist()
            saved = settings.load_config()
            self.assertEqual(saved["two_d_scale"],app.two_d_scale)
            self.assertEqual(saved["two_d_pan_x"],app.two_d_pan_x)
            self.assertEqual(saved["two_d_pan_z"],app.two_d_pan_z)
            app.reset_view()
            self.assertEqual(app.view_pan(),(0,0))
            self.assertEqual(app.two_d_scale,1)
            app.board_mode_var.set("3D")
            app.change_board_mode()
            self.assertEqual(camera,(app.yaw,app.pitch,app.distance,app.pan_x,app.pan_z))
            app.distance = 12.4
            game.Chess3D._scroll(app.window,0,1)
            self.assertLess(app.distance,12.4)
            game.Chess3D._scroll(app.window,0,-1)
            self.assertAlmostEqual(app.distance,12.4)


if __name__ == "__main__":
    unittest.main()
