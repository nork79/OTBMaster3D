"""Opt-in installed-build verification; writes a report and uses temporary state."""
import json
from pathlib import Path
import sys
import tempfile
import time
import traceback


def run(report_path):
    from otb_chess.services import settings
    with tempfile.TemporaryDirectory(prefix="otb-smoke-") as temporary:
        settings.USER_DATA_DIR = Path(temporary)
        settings.CONFIG_PATH = Path(temporary) / "config.json"
        settings.SOUND_DIR = Path(temporary) / "sounds"
        from PySide6.QtCore import Qt, QTimer, qVersion
        from PySide6.QtGui import QIcon
        from PySide6.QtWidgets import QApplication
        from OpenGL.GL import glGetError, GL_NO_ERROR
        from otb_chess.ui.desktop_ui import MainWindow, configure_graphics
        from otb_chess.chess_backend import books
        from otb_chess.version import __version__

        configure_graphics()
        app = QApplication([])
        app.setWindowIcon(QIcon(str(settings.APP_DIR / "assets" / "app-icon.ico")))
        window = MainWindow()
        # Analysis is an opt-in preference; request it explicitly for verification.
        window.game.analysis_enabled = True
        window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        window.show()
        started = time.monotonic()
        report = {"version": __version__, "python": sys.version, "qt": qVersion(), "ok": False}

        def verify():
            game = window.game
            if game.engine_loading or game.engine_output is None:
                if time.monotonic() - started < 25:
                    QTimer.singleShot(150, verify)
                    return
            try:
                assert window.board_widget.isValid(), "OpenGL context unavailable"
                frame = window.board_widget.grabFramebuffer()
                assert not frame.isNull(), "Empty framebuffer"
                window.board_widget.makeCurrent()
                assert glGetError() == GL_NO_ERROR, "OpenGL error"
                menus = [action.text() for action in window.menuBar().actions()]
                assert menus[:2] == ["Game", "File"], menus
                assert not app.windowIcon().isNull(), "Application icon missing"
                assert game.engine_manager.engine is not None, "Bundled Stockfish did not load"
                assert game.engine_output and game.engine_output[1].score is not None, "Evaluation missing"
                book_counts = {}
                for path in settings.BOOK_DIR.glob("lichess-*.bin"):
                    with books.open_reader(path) as book:
                        book_counts[path.name] = len(list(book.find_all(game.board)))
                assert len(book_counts) == 3 and all(book_counts.values()), "Opening books missing"
                report.update(ok=True, menus=menus, engine=game.engine_manager.path,
                              evaluation=window.engine_metrics.text(), books=book_counts,
                              framebuffer=[frame.width(), frame.height()])
            except Exception:
                report["error"] = traceback.format_exc()
            finally:
                Path(report_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
                window.close()
                app.exit(0 if report["ok"] else 1)

        QTimer.singleShot(1000, verify)
        result = app.exec()
    raise SystemExit(result)
