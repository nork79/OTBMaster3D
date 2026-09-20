"""Compact modeless bookmark tool window; UUID-backed, single-selection tree."""
import logging

from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QToolButton,
                              QTreeWidget, QTreeWidgetItem, QAbstractItemView, QHeaderView,
                              QMenu, QMessageBox, QStyle, QStyledItemDelegate)

from otb_chess.services.bookmarks import BookmarkStore
from otb_chess.services.bookmark_actions import BookmarkActions

log = logging.getLogger(__name__)


class BookmarkNameDelegate(QStyledItemDelegate):
    """Keep inline editors compact instead of inheriting dialog input padding."""
    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(max(size.height(), option.fontMetrics.height() + 8))
        return size

    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        editor.setObjectName("bookmarkNameEditor")
        editor.setStyleSheet("QLineEdit#bookmarkNameEditor { padding: 0px 3px; margin: 0px; min-height: 0px; border-radius: 2px; }")
        editor.setTextMargins(0, 0, 0, 0)
        editor.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return editor

    def updateEditorGeometry(self, editor, option, index):
        super().updateEditorGeometry(editor, option, index)
        rect = editor.geometry()  # Retain the style's icon/text indentation.
        rect.setTop(option.rect.top() + 1)
        rect.setBottom(option.rect.bottom() - 1)
        editor.setGeometry(rect)


class BookmarkMenu(QMenu):
    """Rebuild disposable menu actions from the shared authoritative collection."""
    def __init__(self, owner):
        super().__init__("Bookmarks", owner)
        self.owner = owner
        owner.bookmarks_action = owner.action(self, "Manage Bookmarks", owner.toggle_bookmarks,
                                              "Ctrl+Shift+B", True)
        owner.bookmarks_action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        self.add_bookmark_action = owner.action(self, "Add Bookmark", lambda: self.create("add_bookmark"))
        self.new_folder_action = owner.action(self, "New Folder", lambda: self.create("add_folder"))
        self.addSeparator()
        self.aboutToShow.connect(self.rebuild)

    def create(self, method):
        self.owner.bookmarks_action.setChecked(True)
        self.owner.toggle_bookmarks(True)
        getattr(self.owner.get_bookmark_panel(), method)()

    def open_bookmark(self, node_id):
        panel = self.owner.get_bookmark_panel()
        try:
            node = panel.actions.collection.get(node_id)
        except KeyError:
            panel.error(ValueError("This bookmark no longer exists."))
            return
        self.owner.open_bookmark(node)

    def rebuild(self):
        for action in self.actions()[4:]:
            submenu = action.menu()
            self.removeAction(action)
            if submenu is not None:
                submenu.deleteLater()
            else:
                action.deleteLater()
        collection = self.owner.get_bookmark_panel().actions.collection
        nodes = {node["id"]: node for node in collection.to_dict()["nodes"]}
        pending = [(self, collection.root_id)]
        while pending:
            menu, folder_id = pending.pop()
            for node_id in nodes[folder_id]["children"]:
                node = nodes[node_id]
                name = node["name"].replace("&", "&&")
                if node["type"] == "folder":
                    submenu = menu.addMenu(name)
                    submenu.menuAction().setData(node_id)
                    pending.append((submenu, node_id))
                else:
                    action = menu.addAction(name)
                    action.setData(node_id)
                    action.triggered.connect(lambda checked=False, key=node_id: self.open_bookmark(key))


class BookmarkTree(QTreeWidget):
    open_requested = Signal()
    delete_requested = Signal()
    rename_requested = Signal()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self.itemAt(event.position().toPoint()) is None:
            self.clearSelection()
            self.setCurrentItem(None)

    def startDrag(self, supported_actions):
        if not self.selectedItems():
            return
        drag = QDrag(self)
        drag.setMimeData(self.mimeData(self.selectedItems()))
        # The service owns movement; Qt must not remove source rows afterward.
        drag.exec(Qt.DropAction.MoveAction)

    def dropEvent(self, event):
        if event.source() is not self:
            event.ignore()
            return
        target = self.itemAt(event.position().toPoint())
        if self.move_item(self.currentItem(), target, self.dropIndicatorPosition()):
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self, event):
        if self.state() != QAbstractItemView.State.EditingState:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.open_requested.emit()
                return
            if event.key() == Qt.Key.Key_Delete:
                self.delete_requested.emit()
                return
            if event.key() == Qt.Key.Key_F2:
                self.rename_requested.emit()
                return
        super().keyPressEvent(event)


class BookmarkPanel(QDialog):
    def __init__(self, owner):
        super().__init__(owner, Qt.WindowType.Tool)
        self.owner = owner
        self.setObjectName("bookmarkPanel")
        self.setWindowTitle("Bookmarks")
        self.setModal(False)
        self.actions = BookmarkActions(BookmarkStore())
        self.items = {}
        self.positioned = False
        self.setMinimumSize(205, 220)
        self.resize(205, 380)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        header = QHBoxLayout()
        header.addWidget(QLabel("Bookmarks"))
        header.addStretch()
        for text, tip, callback in (("+", "Add Bookmark", self.add_bookmark),
                                    ("Folder", "New Folder", self.add_folder)):
            button = QToolButton()
            button.setText(text)
            button.setToolTip(tip)
            button.setAccessibleName(tip)
            button.clicked.connect(callback)
            header.addWidget(button)
        layout.addLayout(header)
        self.tree = BookmarkTree()
        self.tree.setObjectName("bookmarkTree")
        self.tree.setColumnCount(1)
        self.tree.setHeaderHidden(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setItemDelegate(BookmarkNameDelegate(self.tree))
        self.tree.setIndentation(16)
        self.tree.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.tree.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.tree.setDropIndicatorShown(True)
        self.tree.move_item = self.move_item
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.context_menu)
        self.tree.itemChanged.connect(self.rename_committed)
        self.tree.itemDoubleClicked.connect(lambda item, column: self.open_selected())
        self.tree.open_requested.connect(self.open_selected)
        self.tree.delete_requested.connect(self.delete_selected)
        self.tree.rename_requested.connect(self.rename_selected)
        layout.addWidget(self.tree)
        self.rebuild()

    def selected_id(self):
        item = self.tree.currentItem()
        return item.data(0, Qt.ItemDataRole.UserRole) if item else None

    def show_panel(self):
        self.setStyleSheet(self.owner.styleSheet())
        self.rebuild(self.selected_id())
        screen = self.owner.screen().availableGeometry()
        if not self.positioned:
            saved = self.owner.game.cfg.get("bookmark_panel_geometry")
            if (isinstance(saved, list) and len(saved) == 4
                    and all(type(value) is int for value in saved)
                    and saved[2] >= self.minimumWidth() and saved[3] >= self.minimumHeight()):
                self.resize(min(saved[2], screen.width()), min(saved[3], screen.height() - 48))
                self.move(saved[0], saved[1])
                self.positioned = True
        if not self.positioned:
            self.resize(self.width(), min(round(self.owner.height() * 0.8), screen.height() - 48))
            anchor = self.owner.sidebar.mapToGlobal(QPoint(0, 0))
            self.move(anchor.x() - self.width() - 12, anchor.y())
            self.positioned = True
        self.move(max(screen.left(), min(self.x(), screen.right() - self.width())),
                  max(screen.top(), min(self.y(), screen.bottom() - self.height() - 32)))
        self.show()
        self.raise_()
        self.activateWindow()
        if self.actions.load_error:
            self.error(ValueError(self.actions.load_error))

    def remember_geometry(self):
        if self.positioned:
            self.owner.game.cfg["bookmark_panel_geometry"] = [self.x(), self.y(), self.width(), self.height()]

    def hideEvent(self, event):
        self.remember_geometry()
        self.owner.game.persist()
        super().hideEvent(event)

    def closeEvent(self, event):
        self.owner.bookmarks_action.setChecked(False)
        super().closeEvent(event)

    def reject(self):
        self.owner.bookmarks_action.setChecked(False)
        super().reject()

    def error(self, exc):
        log.warning("Bookmark action failed: %s", exc)
        QMessageBox.warning(self, "Bookmarks", str(exc))

    def rebuild(self, selected=None, edit=False):
        expanded = {key for key, item in self.items.items() if item.isExpanded()}
        self.tree.blockSignals(True)
        try:
            self.tree.clear()
            self.items = {}
            collection = self.actions.collection
            nodes = {node["id"]: node for node in collection.to_dict()["nodes"]}
            pending = [(child, self.tree.invisibleRootItem())
                       for child in reversed(nodes[collection.root_id]["children"])]
            while pending:
                node_id, parent = pending.pop()
                node = nodes[node_id]
                item = QTreeWidgetItem(parent, [node["name"]])
                item.setData(0, Qt.ItemDataRole.UserRole, node_id)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                if node["type"] == "bookmark":
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsDropEnabled)
                icon = QStyle.StandardPixmap.SP_DirIcon if node["type"] == "folder" else QStyle.StandardPixmap.SP_FileIcon
                item.setIcon(0, self.style().standardIcon(icon))
                self.items[node_id] = item
                item.setExpanded(node_id in expanded)
                pending.extend((child, item) for child in reversed(node.get("children", [])))
            if selected in self.items:
                item = self.items[selected]
                parent = item.parent()
                while parent is not None:
                    parent.setExpanded(True)
                    parent = parent.parent()
                self.tree.setCurrentItem(item)
                self.tree.scrollToItem(item)
        finally:
            self.tree.blockSignals(False)
        if edit and selected in self.items:
            self.tree.editItem(self.items[selected], 0)

    def add_bookmark(self):
        try:
            if self.owner.bookmark_pending is not None:
                raise ValueError("Wait for the bookmark to finish opening.")
            node_id = self.actions.create_bookmark(self.owner.game, self.selected_id())
            self.rebuild(node_id, edit=True)
        except Exception as exc:
            self.error(exc)

    def move_item(self, item, target, indicator):
        if item is None:
            return False
        node_id = item.data(0, Qt.ItemDataRole.UserRole)
        collection = self.actions.collection
        positions = QAbstractItemView.DropIndicatorPosition
        try:
            parent_id = collection.root_id
            index = None
            if target is not None and indicator != positions.OnViewport:
                target_id = target.data(0, Qt.ItemDataRole.UserRole)
                if indicator == positions.OnItem:
                    if collection.get(target_id)["type"] != "folder":
                        return False
                    parent_id = target_id
                else:
                    parent_id = self.actions.parent(target_id)
                    children = collection.get(parent_id)["children"]
                    index = children.index(target_id) + (indicator == positions.BelowItem)
                    # Model indices describe the list after removing the source.
                    if node_id in children and children.index(node_id) < index:
                        index -= 1
            self.actions.move(node_id, parent_id, index)
            self.rebuild(node_id)
            return True
        except Exception as exc:
            self.error(exc)
            return False

    def add_folder(self):
        try:
            node_id = self.actions.create_folder(self.selected_id())
            self.rebuild(node_id, edit=True)
        except Exception as exc:
            self.error(exc)

    def rename_selected(self):
        if self.tree.currentItem() is not None:
            self.tree.editItem(self.tree.currentItem(), 0)

    def rename_committed(self, item, column):
        node_id = item.data(0, Qt.ItemDataRole.UserRole)
        try:
            self.actions.rename(node_id, item.text(0))
        except Exception as exc:
            self.error(exc)
        # Keep the delegate/item alive until Qt finishes committing the editor.
        self.tree.blockSignals(True)
        item.setText(0, self.actions.collection.get(node_id)["name"])
        self.tree.blockSignals(False)

    def open_selected(self):
        node_id = self.selected_id()
        if node_id is not None:
            node = self.actions.collection.get(node_id)
            if node["type"] == "bookmark":
                self.owner.open_bookmark(node)

    def delete_selected(self):
        node_id = self.selected_id()
        if node_id is None:
            return
        try:
            node = self.actions.collection.get(node_id)
            if node.get("children"):
                answer = QMessageBox.question(self, "Delete folder", f'Delete “{node["name"]}” and all bookmarks and folders inside it?',
                                              QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                              QMessageBox.StandardButton.No)
                if answer != QMessageBox.StandardButton.Yes:
                    return
            parent = self.actions.delete(node_id)
            self.rebuild(parent)
        except Exception as exc:
            self.error(exc)

    def context_menu(self, point):
        item = self.tree.itemAt(point)
        self.tree.setCurrentItem(item)
        menu = QMenu(self)
        node = self.actions.collection.get(self.selected_id()) if item else None
        if node and node["type"] == "bookmark":
            menu.addAction("Open", self.open_selected)
        else:
            menu.addAction("New Bookmark Here" if node else "Add Bookmark", self.add_bookmark)
            menu.addAction("New Folder", self.add_folder)
        if node:
            menu.addSeparator()
            menu.addAction("Rename", self.rename_selected)
            menu.addAction("Delete", self.delete_selected)
        menu.exec(self.tree.viewport().mapToGlobal(point))
