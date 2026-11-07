"""Board feedback without a native OpenGL window."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import chess
from otb_chess.chess_backend.rules import Board
from otb_chess.graphics import rendering
from otb_chess.services.settings import SELECT


class BoardHighlightTests(unittest.TestCase):
    def state(self):
        return SimpleNamespace(
            board=Board(), board_mode="2D", board_type="classic",
            view_yaw=lambda: 0, frame_color=(0, 0, 0),
            dark_square=(0.2, 0.2, 0.2), light_square=(0.8, 0.8, 0.8),
            selected=None, hover_square=None, move_animation=None,
            show_move_indicator=False, show_coordinates=False,
        )

    def colors(self, state):
        with patch.object(rendering, "flat_square") as draw:
            rendering.BoardRendering.draw_board(state)
        return {chess.square(round(3.5-call.args[0]), round(call.args[1]+3.5)):
                call.args[4] for call in draw.call_args_list[1:]}

    def test_selection_and_hover_include_occupied_squares(self):
        state = self.state()
        baseline = self.colors(state)
        state.selected, state.hover_square = chess.E2, chess.D2
        colors = self.colors(state)
        self.assertEqual(colors[chess.E2], SELECT)
        self.assertNotEqual(colors[chess.D2], baseline[chess.D2])
        state.selected = None
        self.assertEqual(self.colors(state), baseline)

    def test_last_move_highlights_after_animation_and_clears_on_undo(self):
        state = self.state()
        baseline = self.colors(state)
        state.board.push_uci("e2e4")
        state.move_animation = object()
        self.assertEqual(self.colors(state), baseline)
        state.move_animation = None
        colors = self.colors(state)
        self.assertEqual({sq for sq in colors if colors[sq] != baseline[sq]},
                         {chess.E2, chess.E4})
        state.board.pop()
        self.assertEqual(self.colors(state), baseline)

    def test_markers_skip_occupied_capture_targets(self):
        state = self.state()
        state.show_move_indicator = True
        state.legal_targets = lambda: {chess.E3, chess.E4, chess.D7}
        with patch.object(rendering, "draw_disc") as draw, \
                patch.object(rendering, "glDisable"), \
                patch.object(rendering, "glEnable"), \
                patch.object(rendering, "glDepthMask"):
            rendering.BoardRendering.draw_legal_markers(state)
        self.assertEqual({(call.args[0], call.args[2]) for call in draw.call_args_list},
                         {(-0.5, -1.5), (-0.5, -0.5)})

    def test_energetic_overlay_uses_displayed_position_and_overrides_square_highlights(self):
        state = self.state()
        state.show_energetic_overlay = True
        state.display_board = Board('7r/8/8/8/8/8/P7/R7 w - - 0 1')
        state.selected = chess.A3
        colors = self.colors(state)
        self.assertEqual(colors[chess.A3], (1, 1, 0))
        self.assertEqual(colors[chess.H7], (0, 1, 0))
        self.assertEqual(colors[chess.A8], (1, 0, 0))
        self.assertEqual(colors[chess.A1], state.dark_square)
        state.show_energetic_overlay = False
        self.assertEqual(self.colors(state)[chess.A3], SELECT)

    def test_reported_h2_draws_stronger_translucent_red(self):
        state = self.state()
        state.show_energetic_overlay = True
        state.board = Board('r1b1kb1r/ppp1pppp/3q1n2/8/3n4/2NP1N2/PPPBBPPP/R2QK2R w KQkq - 5 8')
        with patch.object(rendering, 'flat_square') as draw:
            rendering.BoardRendering.draw_board(state)
        overlay = [call for call in draw.call_args_list if call.kwargs.get('y') == .025
                   and call.args[:2] == (-3.5, -2.5)]
        self.assertEqual(len(overlay), 1)
        self.assertEqual(overlay[0].args[4], (1, 0, 0))
        self.assertEqual(overlay[0].kwargs['opacity'], .60)


if __name__ == "__main__":
    unittest.main()
