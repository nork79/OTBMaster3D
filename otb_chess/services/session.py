"""Atomic, local recovery snapshots. Restored games always have paused clocks."""
import json
import math
import os
import time

from otb_chess.services import settings
from otb_chess.core.documents import read_pgn
from otb_chess.chess_backend import rules


FIELDS = ('white_time','black_time','increment','active_clock_color',
          'game_started','game_over','awaiting_clock_press','awaiting_clock_color',
          'clock_mode','clock_binding','clock_history','result_text')


class SessionStore:
    def __init__(self):
        self.path = settings.CONFIG_PATH.with_name('session.json')
        self.backup = self.path.with_suffix('.backup.json')
        self.last_save = 0
        self.last_payload = None
        self.error = None

    def save(self, game, force=False):
        now = time.perf_counter()
        if not force and now-self.last_save < 1:
            return
        self.last_save = now
        try:
            data = {'version':1,'pgn':game.export_pgn(),
                    'review_ply':len(game.board.move_stack),
                    'state':{key:getattr(game,key) for key in FIELDS}}
            payload = json.dumps(data,allow_nan=False)
            if payload == self.last_payload:
                return
            temporary = self.path.with_suffix('.tmp')
            with temporary.open('w',encoding='utf-8') as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            if self.path.exists():
                # Only rotate a valid previous snapshot into the backup.
                try:
                    self.decode(self.path)
                except (ValueError,KeyError,TypeError,AttributeError):
                    pass
                else:
                    os.replace(self.path,self.backup)
            os.replace(temporary,self.path)
            self.last_payload = payload
            self.error = None
        except (OSError,ValueError) as exc:
            self.error = 'Session could not be saved: '+str(exc)

    @staticmethod
    def decode(path):
        data = json.loads(path.read_text(encoding='utf-8'))
        if data['version'] != 1:
            raise ValueError('Unsupported session version')
        document = read_pgn(data['pgn'])[0]
        board = document.history
        state = data['state']
        for key in FIELDS:
            state[key]
        for key in ('white_time','black_time','increment'):
            if not isinstance(state[key],(int,float)) or not math.isfinite(state[key]) or state[key]<0:
                raise ValueError('Invalid clock')
        for key in ('game_started','game_over','awaiting_clock_press','active_clock_color'):
            if type(state[key]) is not bool:
                raise ValueError('Invalid game state')
        if state['awaiting_clock_color'] is not None and type(state['awaiting_clock_color']) is not bool:
            raise ValueError('Invalid clock colour')
        if state['clock_mode'] not in ('Online','OTB') or not isinstance(state['result_text'],str):
            raise ValueError('Invalid clock mode or result')
        if not isinstance(state['clock_binding'],str) or not isinstance(state['clock_history'],list):
            raise ValueError('Invalid clock history')
        for row in state['clock_history']:
            if not isinstance(row,list) or len(row)!=3 or type(row[2]) is not bool:
                raise ValueError('Invalid clock history entry')
            if any(not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in row[:2]):
                raise ValueError('Invalid historical clock')
        if type(data['review_ply']) is not int or not 0<=data['review_ply']<=len(board.moves):
            raise ValueError('Invalid review position')
        return data,document,board

    def restore(self, game):
        damaged = False
        for path in (self.path,self.backup):
            if not path.exists():
                continue
            try:
                data,document,board = self.decode(path)
            except (OSError,ValueError,KeyError,TypeError,AttributeError,IndexError):
                damaged = True
                continue
            game.load_document(board,document)
            for key in FIELDS:
                setattr(game,key,data['state'][key])
            reason = rules.termination_reason(game.board)
            if reason is None and game._declared_result is not None:
                reason = game.result_text if game.game_over else 'Imported result - ' + game._declared_result
            if reason is not None:
                game.game_over = True
                game.game_started = False
                game.awaiting_clock_press = False
                game.awaiting_clock_color = None
                game.result_text = reason
            game.clock_paused = True
            game.last_clock_tick = time.perf_counter()
            game.clock_mode_var.set(game.clock_mode)
            game.clock_binding_var.set(game.clock_binding)
            game.navigate_to_ply(data['review_ply'])
            result = game.result_text if game.game_over else ''
            game.result_text = ('Recovered backup session' if path==self.backup else 'Restored session')+' — clocks paused'+(' · '+result if result else '')
            return True
        if damaged:
            game.result_text = 'Saved session could not be recovered; opened a fresh board.'
        return False
