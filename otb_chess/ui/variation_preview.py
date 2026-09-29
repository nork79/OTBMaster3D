"""Display-only PV navigation. The live board is never replaced or pushed."""
import time


class VariationPreview:
    variation_preview = None

    def analysis_position_token(self):
        position = (id(self.board), self.position.history(),
                    id(self.history_board()), self.game_started, self.game_over)
        if position != getattr(self, '_analysis_position', None):
            self._analysis_position = position
            self._analysis_revision = getattr(self, '_analysis_revision', 0) + 1
        return position + (self._analysis_revision,)

    def begin_variation(self, source, moves, token, number=1):
        self.validate_variation()
        if self.game_over or token != self.analysis_position_token() or source != self.board.fen():
            return False
        try:
            positions = [position.legacy_board for position in self.position.variation_positions(moves)]
        except ValueError:
            return False
        if len(positions) == 1:
            return False
        if self.variation_preview is None:
            clocks = {key: getattr(self, key) for key in
                      ('white_time', 'black_time', 'active_clock_color', 'clock_paused')}
        else:
            clocks = self.variation_preview['clocks']
        self.variation_preview = dict(token=token, clocks=clocks, positions=positions,
                                      index=0, number=number)
        self.clock_paused = True
        self.selected = self.drag_piece = self.drag_world = None
        self.was_drag = False
        self.move_animation = None
        return True

    @property
    def preview_board(self):
        if self.variation_preview is not None:
            return self.variation_preview['positions'][self.variation_preview['index']]
        return None

    @property
    def preview_description(self):
        state = self.variation_preview
        return (f"Variation Preview · Variation {state['number']} — Move "
                f"{state['index']}/{len(state['positions'])-1}" if state else '')

    def step_variation(self, delta):
        self.validate_variation()
        if self.variation_preview is not None:
            state = self.variation_preview
            state['index'] = max(0, min(len(state['positions'])-1, state['index']+delta))

    def end_variation(self, resume=True):
        state = self.variation_preview
        if state is None:
            return
        self.variation_preview = None
        # Never restore any board or old clocks over a replacement game.
        if state['token'] == self.analysis_position_token():
            for key, value in state['clocks'].items():
                setattr(self, key, value)
        elif state['token'][0] == id(self.board):
            # External mutation of this board: release only our temporary pause.
            self.clock_paused = state['clocks']['clock_paused']
        self.last_clock_tick = time.perf_counter()
        if resume:
            self.maybe_request_engine_move()

    def validate_variation(self):
        if self.variation_preview is not None and self.variation_preview['token'] != self.analysis_position_token():
            self.end_variation(resume=False)

    def human_can_move(self):
        return self.variation_preview is None and super().human_can_move()

    def try_move(self, *args, **kwargs):
        if self.variation_preview is not None:
            return False
        moved = super().try_move(*args, **kwargs)
        if moved:
            self.analysis_position_token()
        return moved

    def legal_targets(self):
        return set() if self.variation_preview is not None else super().legal_targets()

    def update_clock(self):
        self.validate_variation()
        if self.variation_preview is None:
            super().update_clock()

    def apply_pending_engine_move(self):
        if self.variation_preview is None:
            super().apply_pending_engine_move()

    def maybe_request_engine_move(self):
        if self.variation_preview is None:
            super().maybe_request_engine_move()

    def hit_clock(self):
        if self.variation_preview is None:
            super().hit_clock()

    def stop_clock(self):
        if self.variation_preview is None:
            super().stop_clock()

    def clocks_editable(self):
        return self.variation_preview is None and super().clocks_editable()

    def reset_clock(self):
        self.end_variation(resume=False)
        return super().reset_clock()

    def set_engine_enabled(self, enabled):
        self.end_variation(resume=False)
        return super().set_engine_enabled(enabled)

    def offer_draw(self):
        self.end_variation(resume=False)
        return super().offer_draw()

    def load_document(self, *args, **kwargs):
        self.end_variation(resume=False)
        return super().load_document(*args, **kwargs)

    def start_game(self, *args, **kwargs):
        self.end_variation(resume=False)
        return super().start_game(*args, **kwargs)

    def reset_board(self):
        self.end_variation(resume=False)
        return super().reset_board()

    def takeback(self):
        self.end_variation(resume=False)
        return super().takeback()

    def resign(self, *args, **kwargs):
        self.end_variation(resume=False)
        return super().resign(*args, **kwargs)


    def navigate_to_ply(self, ply):
        self.end_variation(resume=False)
        return super().navigate_to_ply(ply)

    def return_to_live(self):
        self.end_variation(resume=False)
        return super().return_to_live()
