"""Bookmark controller transactions, restoration and native Qt interactions."""
from copy import deepcopy
from pathlib import Path
import tempfile
import sys
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLineEdit, QMessageBox

from otb_chess.bookmarks import capture_position, capture_engine
from otb_chess.chess_backend import rules, uci
from otb_chess.services.bookmarks import BookmarkStore
from otb_chess.services.bookmark_actions import BookmarkActions, restore_bookmark
from otb_chess.services.engine import EngineManager
from otb_chess.services import settings
from otb_chess.core.documents import GameDocuments
from otb_chess.core.board_input import BoardInput
from otb_chess.ui.desktop_ui import Value
from tests import test_desktop_ui as desktop_fixture


class Host(GameDocuments, BoardInput):
    def __init__(self):
        self.board = rules.Board()
        self.board_mode = "3D"
        self.two_d_flipped = False
        self.yaw = .4
        self.pitch, self.distance, self.piece_set = .8, 14, "tournament"
        self.pan_x = self.pan_z = 0
        self.cfg = {"engine_elo": None, "engine_rating": 1500, "engine_style": "Balanced"}
        self.engine_manager = EngineManager(self)
        self.engine_side_var, self.engine_var = Value("Black"), Value("")
        self.time_control_var, self.clock_mode_var = Value("Bullet 2+1"), Value("Online")
        self.custom_initial_var, self.custom_increment_var = Value(120), Value(1)
        self.clock_mode = "Online"
        self.clock_history = []
        self.clock_paused = False
        self.refresh_move_list = self.persist = self.mark_camera_dirty = Mock()

    def selected_time_control(self):
        return settings.TIME_CONTROLS[self.time_control_var.get()]


class BookmarkIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = BookmarkStore(Path(self.temp.name) / "bookmarks.json")
        self.actions = BookmarkActions(self.store)
        self.game = Host()

    def test_destinations_create_rename_delete_and_restart(self):
        root = self.actions.collection.root_id
        self.assertEqual(self.actions.destination(), root)
        folder = self.actions.create_folder()
        self.assertEqual(self.actions.destination(folder), folder)
        item = self.actions.create_bookmark(self.game, folder)
        self.assertEqual(self.actions.destination(item), folder)
        nested = self.actions.create_folder(item)
        self.assertEqual(self.actions.parent(nested), folder)
        self.actions.rename(item, "  Sicilian  ")
        self.assertEqual(self.actions.collection.get(item)["name"], "Sicilian")
        with self.assertRaises(ValueError):
            self.actions.rename(item, " \n ")
        self.assertEqual(BookmarkActions(self.store).collection.to_dict(), self.actions.collection.to_dict())
        self.actions.delete(folder)
        self.assertEqual(self.actions.collection.get(root)["children"], [])

    def test_saving_bookmark_does_not_capture_engine(self):
        self.game.engine_manager = Mock()
        self.game.engine_loading = True
        item = self.actions.create_bookmark(self.game)
        self.assertNotIn("engine", self.actions.collection.get(item))
        self.assertEqual(self.game.engine_manager.mock_calls, [])

    def test_failed_save_does_not_publish_phantom_edits(self):
        item = self.actions.create_bookmark(self.game)
        before = self.actions.collection.to_dict()
        previous_file = self.store.path.read_bytes()
        with patch.object(self.store, "save", return_value=False):
            for operation in (lambda: self.actions.create_folder(),
                              lambda: self.actions.rename(item, "Changed"),
                              lambda: self.actions.delete(item)):
                with self.assertRaises(OSError):
                    operation()
                self.assertEqual(self.actions.collection.to_dict(), before)
        self.assertEqual(self.store.path.read_bytes(), previous_file)

    def test_damaged_file_not_overwritten_by_ui(self):
        self.store.path.write_text("broken")
        with self.assertLogs("otb_chess.services.bookmarks", level="WARNING"):
            actions = BookmarkActions(self.store)
        with self.assertRaises(ValueError):
            actions.create_folder()
        self.assertEqual(self.store.path.read_text(), "broken")

    def test_restore_position_facing_preserves_engine_and_clock_settings(self):
        self.game.board.push_uci("e2e4")
        item = self.actions.create_bookmark(self.game)
        saved = self.actions.collection.get(item)
        original_cfg = deepcopy(self.game.cfg)
        self.game.white_time, self.game.black_time, self.game.increment = 91, 83, 1
        self.game.engine_side = False
        current_engine = self.game.engine_manager.engine = Mock()
        self.game.engine_var.set("current.exe")
        for facing in ("black", "white"):
            saved["facing"] = facing
            saved["engine"] = {"engine_id": "missing", "name": "Missing"}
            saved["time_control"].update(preset_name="Custom", base_seconds=432, increment_seconds=7, clock_mode="OTB")
            warnings = restore_bookmark(self.game, saved)
            self.assertFalse(warnings)
            self.assertEqual(self.game.board.fen(en_passant="fen"), saved["position"]["fen"])
            self.assertEqual(self.game.board_facing, facing)
            self.assertTrue(self.game.clock_paused)
            self.assertTrue(self.game.game_started)
            self.assertEqual((self.game.white_time, self.game.black_time, self.game.increment), (91, 83, 1))
            self.assertEqual(self.game.time_control_var.get(), "Bullet 2+1")
            self.assertEqual((self.game.pitch, self.game.distance, self.game.piece_set), (.8, 14, "tournament"))
            self.assertEqual(self.game.cfg, original_cfg)
            self.assertEqual(self.game.clock_mode_var.get(), "Online")
            self.assertEqual(self.game.clock_mode, "Online")
            self.assertEqual(self.game.custom_initial_var.get(), 120)
            self.assertEqual(self.game.custom_increment_var.get(), 1)
            self.assertEqual(self.game.engine_side_var.get(), "Black")
            self.assertFalse(self.game.engine_side)
            self.assertEqual(self.game.engine_var.get(), "current.exe")
            self.assertIs(self.game.engine_manager.engine, current_engine)

    def test_candidate_engine_failure_keeps_current_engine(self):
        manager = self.game.engine_manager
        previous = manager.engine = Mock()
        manager.path = "current.exe"
        config = {"engine_id": "missing", "name": "Missing", "executable": "does-not-exist.exe", "settings": {}}
        with self.assertLogs("otb_chess.services.engine", level="WARNING"):
            result = manager.restore_configuration(config)
        self.assertFalse(result[0])
        self.assertIs(manager.engine, previous)
        previous.quit.assert_not_called()

    def test_unsupported_profile_keeps_current_engine(self):
        executable = Path(self.temp.name) / "rodent.exe"
        executable.write_bytes(b"fake executable")
        previous = self.game.engine_manager.engine = Mock()
        snapshot = {"engine_id": "rodent", "settings": {"personality": "missing"}, "executable": str(executable)}
        with self.assertLogs("otb_chess.services.engine", level="WARNING"):
            success, _ = self.game.engine_manager.restore_configuration(snapshot)
        self.assertFalse(success)
        self.assertIs(self.game.engine_manager.engine, previous)
        previous.quit.assert_not_called()

    def test_missing_engine_uses_explicit_default_only_when_none_is_loaded(self):
        root = Path(self.temp.name)
        executable = root / "stockfish-test.exe"
        executable.touch()
        manager = self.game.engine_manager
        def load_default(path):
            manager.engine = Mock()
            manager.path = path
            return True, "Loaded"
        snapshot = {"engine_id": "missing", "name": "Missing", "settings": {}}
        with patch.object(settings, "ENGINE_DIR", root), patch.object(manager, "load", side_effect=load_default), \
                self.assertLogs("otb_chess.services.engine", level="WARNING"):
            success, message = manager.restore_configuration(snapshot)
        self.assertFalse(success)  # A fallback is never reported as the saved profile.
        self.assertIn("Default Stockfish loaded instead", message)
        self.assertIsNotNone(manager.engine)


class BookmarkEngineIntegrationTests(unittest.TestCase):
    """Requires the installed Windows Stockfish executable."""

    def test_legacy_bookmark_preserves_current_stockfish_configuration(self):
        if sys.platform != 'win32':
            self.skipTest('Bundled engines require Windows')
        path = next(settings.ENGINE_DIR.rglob("stockfish*.exe"), None)
        if path is None:
            self.skipTest("Bundled Stockfish not installed")
        self.game = Host()
        manager = self.game.engine_manager
        self.addCleanup(manager.unload)
        self.game.cfg.update(engine_elo=1500, engine_style="Active")
        self.assertTrue(manager.load(str(path))[0])
        saved = capture_engine(manager)
        self.game.cfg.update(engine_elo=None, engine_style="Quiet")
        before = capture_engine(manager)
        node = {"type": "bookmark", "name": "Engine", "position": capture_position(rules.Board()), "engine": saved}
        restore_bookmark(self.game, node)
        actual = capture_engine(manager)
        self.assertEqual(actual["profile_id"], before["profile_id"])
        self.assertEqual(actual["settings"], before["settings"])
        self.assertEqual(self.game.cfg["engine_style"], "Quiet")


class BookmarkUITests(unittest.TestCase):
    setUpClass = classmethod(desktop_fixture.DesktopTests.setUpClass.__func__)
    setUp = desktop_fixture.DesktopTests.setUp
    tearDown = desktop_fixture.DesktopTests.tearDown
    screen = desktop_fixture.DesktopTests.screen

    def panel(self):
        self.window.bookmarks_action.trigger()
        self.qt.processEvents()
        return self.window.bookmark_panel

    def finish_edit(self, panel, text):
        self.qt.processEvents()
        editor = panel.tree.findChild(QLineEdit)
        self.assertIsNotNone(editor)
        editor.selectAll()
        QTest.keyClicks(editor, text)
        QTest.keyClick(editor, Qt.Key.Key_Return)
        self.qt.processEvents()

    def wait_restore(self):
        deadline = time.monotonic() + 10
        while self.window.bookmark_pending is not None and time.monotonic() < deadline:
            self.window.tick()
            self.qt.processEvents()
            time.sleep(.01)
        self.assertIsNone(self.window.bookmark_pending)

    def test_panel_geometry_inline_workflow_hide_reopen_and_delete_confirmation(self):
        width = self.widget.width()
        panel = self.panel()
        self.assertFalse(panel.isModal())
        self.assertEqual(panel.width(), 205)
        self.assertEqual(self.widget.width(), width)
        panel.add_folder()
        folder = panel.selected_id()
        self.finish_edit(panel, "Openings")
        panel.add_folder()
        nested = panel.selected_id()
        self.finish_edit(panel, "Sicilian")
        panel.add_bookmark()
        item = panel.selected_id()
        self.finish_edit(panel, "Starting position")
        self.assertEqual(panel.actions.parent(item), nested)
        self.assertEqual(panel.actions.parent(nested), folder)
        QTest.keyClick(panel.tree, Qt.Key.Key_F2)
        self.finish_edit(panel, "Renamed position")
        panel.tree.setCurrentItem(panel.items[folder])
        panel.rename_selected()
        self.finish_edit(panel, "Renamed folder")
        panel.move(panel.pos() + QPoint(8, 8))
        previous = panel.pos()
        panel.close()
        self.assertFalse(self.window.bookmarks_action.isChecked())
        self.window.bookmarks_action.trigger()
        self.assertEqual(panel.pos(), previous)
        self.assertEqual(self.widget.width(), width)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
            panel.delete_selected()
        self.assertIn(folder, panel.items)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes) as question:
            panel.delete_selected()
            self.assertIn("all bookmarks and folders", question.call_args.args[2])
        self.assertEqual(panel.tree.topLevelItemCount(), 0)

    def test_select_does_not_open_double_click_and_enter_restore_facing(self):
        panel = self.panel()
        self.game.board.push_uci("e2e4")
        self.game.set_board_facing("black")
        item = panel.actions.create_bookmark(self.game)
        panel.rebuild()
        self.game.board.reset()
        self.game.set_board_facing("white")
        rect = panel.tree.visualItemRect(panel.items[item])
        QTest.mouseClick(panel.tree.viewport(), Qt.MouseButton.LeftButton, pos=rect.center())
        self.assertEqual(self.game.board.fen(), rules.Board().fen())
        QTest.mouseDClick(panel.tree.viewport(), Qt.MouseButton.LeftButton, pos=rect.center())
        self.wait_restore()
        self.assertEqual(self.game.board_facing, "black")
        self.assertEqual(self.game.board.peek().uci(), "e2e4")
        self.assertTrue(self.game.clock_paused)
        self.assertEqual(self.game.time_control_var.get(), "Bullet 2+1")
        self.game.set_board_facing("white")
        white = panel.actions.create_bookmark(self.game)
        panel.rebuild(white)
        self.game.set_board_facing("black")
        QTest.keyClick(panel.tree, Qt.Key.Key_Return)
        self.wait_restore()
        self.assertEqual(self.game.board_facing, "white")
        self.assertTrue(self.widget.isEnabled())
        panel.close()
        self.game.stop_clock()
        self.game.engine_side = None
        QTest.mouseClick(self.widget, Qt.MouseButton.LeftButton, pos=self.screen(52))
        QTest.mouseClick(self.widget, Qt.MouseButton.LeftButton, pos=self.screen(36))
        self.assertEqual(self.game.board.peek().uci(), "e7e5")

    def test_blank_rename_rejected_escape_cancels_and_save_failure_has_no_phantom(self):
        panel = self.panel()
        item = panel.actions.create_folder()
        panel.rebuild(item)
        with patch.object(QMessageBox, "warning"):
            panel.rename_selected()
            self.finish_edit(panel, "   ")
        self.assertEqual(panel.items[item].text(0), "New folder")
        panel.rename_selected()
        self.qt.processEvents()
        editor = panel.tree.findChild(QLineEdit)
        QTest.keyClicks(editor, "Discard")
        QTest.keyClick(editor, Qt.Key.Key_Escape)
        self.qt.processEvents()
        self.assertEqual(panel.items[item].text(0), "New folder")
        with patch.object(panel.actions.store, "save", return_value=False), patch.object(QMessageBox, "warning"):
            panel.add_folder()
        self.assertEqual(len(panel.items), 1)

    def test_open_waits_for_search_discards_stale_result_and_restores_missing_engine_position(self):
        panel = self.panel()
        node_id = panel.actions.create_bookmark(self.game)
        node = panel.actions.collection.get(node_id)
        node["engine"] = {"engine_id": "unavailable", "name": "Missing", "settings": {}}
        self.game.engine_manager.thinking = True
        with patch.object(self.game.engine_manager, "stop_search") as stop:
            self.window.open_bookmark(node)
            stop.assert_called()
            self.assertTrue(self.game.clock_paused)
            self.assertFalse(self.widget.isEnabled())
            self.game.pending_engine_move = rules.Move.from_uci("e2e4")
            self.game.engine_manager.thinking = False
            with patch.object(self.game.engine_manager, "restore_configuration") as restore:
                self.wait_restore()
                restore.assert_not_called()
        self.assertIsNone(self.game.pending_engine_move)
        self.assertEqual(self.game.board.fen(), rules.Board().fen())
        self.assertNotIn("could not be restored", self.game.result_text)
        self.assertTrue(self.game.clock_paused)

    def test_context_selection_order_scrolling_and_long_names(self):
        from PySide6.QtWidgets import QMenu, QAbstractItemView
        panel = self.panel()
        first = panel.actions.create_folder()
        second = panel.actions.create_folder()
        panel.actions.rename(second, "A very long folder name " * 15)
        for _ in range(22):
            panel.actions.create_folder()
        panel.rebuild(first)
        self.qt.processEvents()
        width = panel.width()
        labels = []
        def inspect_menu():
            menu = self.qt.activePopupWidget()
            if menu is not None:
                labels.extend(action.text() for action in menu.actions() if not action.isSeparator())
                menu.close()
        QTimer.singleShot(0, inspect_menu)
        panel.context_menu(panel.tree.visualItemRect(panel.items[second]).center())
        self.assertEqual(labels, ["New Bookmark Here", "New Folder", "Rename", "Delete"])
        self.assertEqual(panel.selected_id(), second)
        self.assertEqual(panel.tree.topLevelItem(0).data(0, Qt.ItemDataRole.UserRole), first)
        self.assertEqual(panel.width(), width)
        self.assertGreater(panel.tree.verticalScrollBar().maximum(), 0)
        self.assertEqual(panel.tree.dragDropMode(), QAbstractItemView.DragDropMode.InternalMove)

    def test_empty_area_clears_target_for_multiple_root_folders(self):
        panel = self.panel()
        for name in ("Openings", "Endgames", "Tactical Positions"):
            point = QPoint(20, panel.tree.viewport().height() - 10)
            self.assertIsNone(panel.tree.itemAt(point))
            QTest.mouseClick(panel.tree.viewport(), Qt.MouseButton.LeftButton, pos=point)
            self.assertIsNone(panel.selected_id())
            self.assertEqual(panel.tree.selectedItems(), [])
            self.window.bookmarks_menu.new_folder_action.trigger()
            self.finish_edit(panel, name)
        root = panel.actions.collection.get(panel.actions.collection.root_id)
        self.assertEqual([panel.actions.collection.get(key)["name"] for key in root["children"]],
                         ["Openings", "Endgames", "Tactical Positions"])
        self.assertEqual(panel.tree.topLevelItemCount(), 3)

    def test_drop_movement_order_persistence_and_menu(self):
        from PySide6.QtWidgets import QAbstractItemView
        from PySide6.QtCore import QPointF
        positions = QAbstractItemView.DropIndicatorPosition
        panel = self.panel()
        first = panel.actions.create_folder()
        second = panel.actions.create_folder()
        a, b = [panel.actions.create_bookmark(self.game, first) for _ in range(2)]
        c, d = [panel.actions.create_bookmark(self.game, second) for _ in range(2)]
        panel.rebuild(b)

        def drop(source, target, indicator):
            panel.tree.setCurrentItem(panel.items[source])
            if target:
                panel.tree.scrollToItem(panel.items[target])
                point = panel.tree.visualItemRect(panel.items[target]).center()
            else:
                point = QPoint(20, panel.tree.viewport().height() - 5)
            event = Mock()
            event.source.return_value = panel.tree
            event.position.return_value = QPointF(point)
            with patch.object(panel.tree, "dropIndicatorPosition", return_value=indicator):
                panel.tree.dropEvent(event)
            event.accept.assert_called_once()
            event.setDropAction.assert_called_once_with(Qt.DropAction.MoveAction)

        drop(b, a, positions.AboveItem)
        self.assertEqual(panel.actions.collection.get(first)["children"], [b, a])
        drop(b, a, positions.BelowItem)
        self.assertEqual(panel.actions.collection.get(first)["children"], [a, b])
        panel.items[second].setExpanded(True)
        drop(b, d, positions.AboveItem)
        self.assertEqual(panel.actions.collection.get(second)["children"], [c, b, d])
        drop(a, second, positions.OnItem)
        self.assertEqual(panel.actions.collection.get(second)["children"], [c, b, d, a])
        drop(b, None, positions.OnViewport)
        root = panel.actions.collection.root_id
        self.assertEqual(panel.actions.collection.get(root)["children"], [first, second, b])
        reloaded = BookmarkActions(panel.actions.store).collection
        self.assertEqual(reloaded.root_id, root)
        self.assertEqual({node["id"]: node for node in reloaded.to_dict()["nodes"]},
                         {node["id"]: node for node in panel.actions.collection.to_dict()["nodes"]})
        menu = self.window.bookmarks_menu
        menu.aboutToShow.emit()
        self.assertEqual([action.data() for action in menu.actions()[4:]], [first, second, b])
        self.assertEqual([action.data() for action in menu.actions()[5].menu().actions()], [c, d, a])

    def test_invalid_drop_and_failed_save_preserve_tree(self):
        from PySide6.QtWidgets import QAbstractItemView
        positions = QAbstractItemView.DropIndicatorPosition
        panel = self.panel()
        folder = panel.actions.create_folder()
        nested = panel.actions.create_folder(folder)
        bookmark = panel.actions.create_bookmark(self.game, folder)
        panel.rebuild(bookmark)
        before = panel.actions.collection.to_dict()
        with patch.object(panel, "error"):
            self.assertFalse(panel.move_item(panel.items[folder], panel.items[nested], positions.OnItem))
            self.assertFalse(panel.move_item(panel.items[folder], panel.items[folder], positions.OnItem))
            self.assertFalse(panel.move_item(panel.items[nested], panel.items[bookmark], positions.OnItem))
            with patch.object(panel.actions.store, "save", return_value=False):
                self.assertFalse(panel.move_item(panel.items[bookmark], None, positions.OnViewport))
        self.assertEqual(panel.actions.collection.to_dict(), before)
        self.assertIs(panel.items[bookmark].parent(), panel.items[folder])
        self.assertEqual(BookmarkActions(panel.actions.store).collection.to_dict(), before)

    def test_toggle_shortcut_while_tool_window_has_focus(self):
        panel = self.panel()
        panel.activateWindow()
        panel.tree.setFocus()
        self.qt.processEvents()
        QTest.keyClick(panel.tree, Qt.Key.Key_B, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
        self.qt.processEvents()
        self.assertFalse(panel.isVisible())
        self.assertFalse(self.window.bookmarks_action.isChecked())

    def test_menu_hierarchy_tracks_model_mutations_and_order(self):
        panel = self.panel()
        menu = self.window.bookmarks_menu
        self.assertIs(menu.actions()[0], self.window.bookmarks_action)
        self.assertEqual(menu.actions()[0].shortcut().toString(), "Ctrl+Shift+B")
        folder = panel.actions.create_folder()
        nested = panel.actions.create_folder(folder)
        bookmark = panel.actions.create_bookmark(self.game, nested)
        empty = panel.actions.create_folder()
        panel.actions.rename(folder, "Openings & studies")
        panel.actions.rename(bookmark, "Position C")
        menu.aboutToShow.emit()
        dynamic = menu.actions()[4:]
        self.assertEqual([a.data() for a in dynamic], [folder, empty])
        self.assertEqual(dynamic[0].text(), "Openings && studies")
        self.assertEqual(dynamic[0].menu().actions()[0].menu().actions()[0].data(), bookmark)
        self.assertEqual(dynamic[1].menu().actions(), [])
        with patch.object(self.window, "open_bookmark") as restore:
            dynamic[0].trigger()
            restore.assert_not_called()
        root = panel.actions.collection.root_id
        panel.actions._commit(lambda collection: collection.move(bookmark, root))
        panel.actions._commit(lambda collection: collection.move(nested, empty))
        panel.actions._commit(lambda collection: collection.reorder(root, [bookmark, empty, folder]))
        panel.actions.rename(nested, "Moved folder")
        menu.aboutToShow.emit()
        dynamic = menu.actions()[4:]
        self.assertEqual([a.data() for a in dynamic], [bookmark, empty, folder])
        self.assertEqual(dynamic[1].menu().actions()[0].text(), "Moved folder")
        panel.rebuild()
        self.assertEqual([panel.tree.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole)
                          for i in range(3)], [a.data() for a in dynamic])
        panel.actions.delete(bookmark)
        panel.actions.delete(empty)
        menu.aboutToShow.emit()
        self.assertEqual([a.data() for a in menu.actions()[4:]], [folder])

    def test_menu_creation_and_restore_use_shared_actions(self):
        menu = self.window.bookmarks_menu
        menu.new_folder_action.trigger()
        panel = self.window.bookmark_panel
        self.finish_edit(panel, "Menu folder")
        folder = panel.selected_id()
        self.game.board.push_uci("d2d4")
        self.game.set_board_facing("black")
        menu.add_bookmark_action.trigger()
        self.finish_edit(panel, "Menu position")
        bookmark = panel.selected_id()
        self.assertEqual(panel.actions.parent(bookmark), folder)
        self.game.board.reset()
        self.game.set_board_facing("white")
        menu.aboutToShow.emit()
        action = menu.actions()[4].menu().actions()[0]
        with patch.object(self.window, "open_bookmark", wraps=self.window.open_bookmark) as restore:
            action.trigger()
            restore.assert_called_once()
            self.wait_restore()
        self.assertEqual(self.game.board.peek().uci(), "d2d4")
        self.assertEqual(self.game.board_facing, "black")
        self.assertTrue(self.game.clock_paused)

    def test_inline_editor_has_font_space_for_create_and_rename(self):
        from PySide6.QtWidgets import QStyle, QStyleOptionFrame
        panel = self.panel()
        for create in (panel.add_folder, panel.add_bookmark):
            create()
            for renaming in (False, True):
                if renaming:
                    panel.rename_selected()
                self.qt.processEvents()
                editor = panel.tree.findChild(QLineEdit)
                self.assertIsNotNone(editor)
                option = QStyleOptionFrame()
                editor.initStyleOption(option)
                contents = editor.style().subElementRect(QStyle.SubElement.SE_LineEditContents, option, editor)
                row = panel.tree.visualItemRect(panel.tree.currentItem())
                self.assertGreaterEqual(contents.height(), editor.fontMetrics().height())
                self.assertLessEqual(row.height(), editor.fontMetrics().height() + 14)
                self.assertGreaterEqual(editor.geometry().top(), row.top())
                self.assertLessEqual(editor.geometry().bottom(), row.bottom())
                self.assertTrue(editor.alignment() & Qt.AlignmentFlag.AlignVCenter)
                self.finish_edit(panel, "Agjpqy fully visible")

    def test_panel_geometry_and_tree_restore_after_window_restart(self):
        from otb_chess.ui.desktop_ui import MainWindow
        panel = self.panel()
        first = panel.actions.create_folder()
        second = panel.actions.create_folder(first)
        bookmark = panel.actions.create_bookmark(self.game, second)
        panel.actions.move(bookmark, first, 0)
        expected = panel.actions.collection.to_dict()
        panel.resize(510, 470)
        self.qt.processEvents()
        self.window.close()
        self.qt.processEvents()
        self.assertEqual(settings.load_config()["bookmark_panel_geometry"][2:], [510, 470])
        restored = MainWindow()
        restored.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        try:
            restored.show()
            restored.timer.stop()
            restored.bookmarks_action.trigger()
            self.qt.processEvents()
            reopened = restored.bookmark_panel
            self.assertEqual((reopened.width(), reopened.height()), (510, 470))
            actual = reopened.actions.collection.to_dict()
            self.assertEqual(actual["root_id"], expected["root_id"])
            self.assertEqual({node["id"]: node for node in actual["nodes"]},
                             {node["id"]: node for node in expected["nodes"]})
            restored.bookmarks_menu.rebuild()
            children = restored.bookmarks_menu.actions()[4].menu().actions()
            self.assertEqual([action.data() for action in children], [bookmark, second])
        finally:
            restored.close()
            self.qt.processEvents()

    def test_user_widened_panel_retains_width_on_reopen(self):
        panel = self.panel()
        self.assertEqual(panel.minimumWidth(), 205)
        panel.resize(610, 420)
        self.qt.processEvents()
        panel.close()
        self.window.bookmarks_action.trigger()
        self.qt.processEvents()
        self.assertEqual(panel.width(), 610)


if __name__ == "__main__":
    unittest.main()
