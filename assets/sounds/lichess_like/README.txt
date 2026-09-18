OTBMaster3D - Lichess-Like Original Sound Pack
==============================================

These sounds are newly synthesized/original and are NOT extracted from Lichess,
Chess.com, or any other chess site.

Design goal:
- very short
- dry / low reverb
- unobtrusive
- clear distinction between move and capture
- suitable for rapid / blitz / bullet play

Files
-----
move.wav        Normal legal move
capture.wav     Piece capture
castle.wav      Castling
check.wav       Checking move
promote.wav     Pawn promotion
illegal.wav     Illegal move / invalid action
game_start.wav  Game start
game_end.wav    Game end

Technical
---------
Format: PCM WAV
Sample rate: 44.1 kHz
Bit depth: 16-bit
Channels: Mono

Suggested Codex integration
---------------------------
1. Put files in:
   assets/sounds/

2. Recommended event mapping:
   legal quiet move -> move.wav
   capture          -> capture.wav
   castle           -> castle.wav
   gives check      -> check.wav
   promotion        -> promote.wav
   illegal input    -> illegal.wav
   game begins      -> game_start.wav
   game finishes    -> game_end.wav

3. Suggested priority when one move triggers multiple events:
   promotion > castle > check > capture > move

   Alternatively:
   - use capture.wav for checking captures
   - reserve check.wav for non-capturing checks

4. Keep sound playback asynchronous/non-blocking so UI and clocks are never delayed.

5. Add a master Sound Effects toggle and a volume slider.
