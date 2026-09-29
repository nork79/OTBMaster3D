"""Verify the pinned practice engine, PE imports, UCI settings and legal play."""
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import zipfile

import pefile

from install_fairy_stockfish import ROOT, EXE_NAME, SOURCE_NAME, EXE_SHA256, SOURCE_SHA256, EXE_URL, SOURCE_URL, SOURCE_PREFIX
sys.path.insert(0, str(ROOT))
from otb_chess.chess_backend import rules
from otb_chess.services.engine import EngineManager
from otb_chess.services.difficulty import DIFFICULTIES, engine_path
from otb_chess.bookmarks import capture_engine


def verify():
    folder = ROOT / 'engines/fairy-stockfish-14'
    executable, source = folder / EXE_NAME, folder / SOURCE_NAME
    assert hashlib.sha256(executable.read_bytes()).hexdigest() == EXE_SHA256
    assert hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_SHA256
    pe = pefile.PE(str(executable))
    assert pe.FILE_HEADER.Machine == 0x8664
    imports = sorted({dep.dll.decode().lower() for attr in ('DIRECTORY_ENTRY_IMPORT', 'DIRECTORY_ENTRY_DELAY_IMPORT')
                      for dep in getattr(pe, attr, [])})
    assert set(imports) <= {'advapi32.dll', 'kernel32.dll', 'msvcrt.dll'}, imports
    with zipfile.ZipFile(source) as archive:
        assert archive.testzip() is None
        assert 'either version 3' in archive.read(SOURCE_PREFIX + 'src/ucioption.cpp').decode()
        assert 'nnue = no' in archive.read(SOURCE_PREFIX + 'src/Makefile').decode()
        materials = {name: hashlib.sha256(archive.read(SOURCE_PREFIX + name)).hexdigest()
                     for name in ('Copying.txt', 'AUTHORS', 'src/Makefile', '.github/workflows/build.yml', 'src/search.cpp')}
    results = []
    for key, preset in DIFFICULTIES.items():
        if preset.engine != 'fairy-stockfish':
            continue
        app = SimpleNamespace(cfg={'engine_difficulty': key, 'engine_elo': preset.rating})
        manager = EngineManager(app)
        try:
            ok, message = manager.load(str(engine_path(key)))
            assert ok, message
            engine = manager.engine
            assert engine.strength_range() == (500, 2850)
            saved = capture_engine(manager)
            assert saved['engine_id'] == 'fairy-stockfish'
            assert saved['settings']['uci_options']['Use NNUE'] is False
            assert saved['settings']['uci_options']['UCI_LimitStrength'] is True
            assert saved['settings']['uci_options']['UCI_Elo'] == preset.rating
            positions = [rules.Board(), rules.Board('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1'),
                         rules.Board('7k/P7/8/8/8/8/8/7K w - - 0 1'),
                         rules.Board('4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1')]
            moves = []
            for board in positions:
                for _ in range(2):
                    move = rules.provider_move(engine.play(rules.snapshot_history(board), seconds=.05).move)
                    assert move in board.legal_moves
                    moves.append(move.uci())
                    board.push(move)
            assert manager.restore_configuration(saved) == (True, '')
            assert capture_engine(manager)['profile_id'] == saved['profile_id']
            results.append({'preset': key, 'target': preset.rating, 'moves': moves,
                            'options': saved['settings']['uci_options'], 'bookmark_roundtrip': True})
        finally:
            manager.unload()
    report = {'version': '14', 'source_tag': 'fairy_sf_14', 'exe_url': EXE_URL, 'exe_sha256': EXE_SHA256,
              'source_url': SOURCE_URL, 'source_sha256': SOURCE_SHA256, 'publisher_checksum': None,
              'hash_meaning': 'Locally pinned bytes fetched from official release/tag over HTTPS; not a signature claim',
              'architecture': 'x64', 'imports': imports, 'source_materials_sha256': materials,
              'licence': 'GPL-3.0-or-later', 'nnue': 'Disabled; no external or embedded network is distributed in this non-NNUE release',
              'tests': results, 'passed': True,
              'limits': 'Development-host UCI tests; not human-Elo calibration, clean Windows testing or rebuilt-installer verification'}
    output = ROOT / 'docs/licensing/evidence/fairy-stockfish-verification.json'
    output.write_text(json.dumps(report, indent=2))
    print(f'PASS: {len(results)} practice settings, legal moves for both sides, exact bookmark roundtrips; {output}')


if __name__ == '__main__':
    verify()
