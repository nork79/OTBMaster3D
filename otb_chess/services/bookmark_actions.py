"""Transactional bookmark editing and UI-independent live-game restoration."""
import time

from otb_chess.bookmarks import (BookmarkCollection, capture_position,
                                capture_facing, capture_time_control, restore_position)


class BookmarkActions:
    def __init__(self, store):
        self.store = store
        self.collection = store.load()
        self.load_error = store.error

    def destination(self, selected=None):
        if selected is None:
            return self.collection.root_id
        node = self.collection.get(selected)
        if node["type"] == "folder":
            return selected
        return self.parent(selected)

    def parent(self, node_id):
        for node in self.collection.to_dict()["nodes"]:
            if node_id in node.get("children", []):
                return node["id"]
        return self.collection.root_id

    def _commit(self, operation):
        if self.load_error:
            raise ValueError(self.load_error + ". Repair or restore the bookmark file before editing it.")
        candidate = BookmarkCollection.from_dict(self.collection.to_dict())
        result = operation(candidate)
        if not self.store.save(candidate):
            raise OSError(self.store.error or "Could not save bookmarks")
        self.collection = candidate
        return result

    def create_folder(self, selected=None):
        parent = self.destination(selected)
        return self._commit(lambda tree: tree.create_folder(parent, "New folder"))

    def create_bookmark(self, game, selected=None):
        control = game.selected_time_control()
        if control is None:
            raise ValueError("Choose a valid time control first.")
        snapshot = dict(position=capture_position(game.board), facing=capture_facing(game),
                        time_control=capture_time_control(control, game.clock_mode_var.get()))
        parent = self.destination(selected)
        return self._commit(lambda tree: tree.create_bookmark(parent, "New bookmark", **snapshot))

    def rename(self, node_id, name):
        name = name.strip()
        if not name:
            raise ValueError("Enter a name containing at least one non-space character.")
        self._commit(lambda tree: tree.rename(node_id, name))

    def delete(self, node_id):
        parent = self.parent(node_id)
        self._commit(lambda tree: tree.delete(node_id))
        return parent

    def move(self, node_id, parent_id, index=None):
        self._commit(lambda tree: tree.move(node_id, parent_id, index=index))


def validate_restore(node):
    if node["type"] != "bookmark":
        raise ValueError("Select a bookmark to open.")
    board = restore_position(node["position"])
    if node.get("facing", "white") not in ("white", "black"):
        raise ValueError("Invalid bookmark facing")
    return board


def restore_bookmark(game, node):
    """Apply after searches/loading drain, preserving current engine and clock settings."""
    board = validate_restore(node)
    game.clock_paused = True
    game.load_document(board)
    game.game_started = True  # Resume continues this board, including its history.
    game.move_animation = None
    game.pending_engine_error = None
    game.engine_output = None
    game.last_engine_search = None
    game.set_board_facing(node.get("facing", "white"))
    game.clock_paused = True
    game.last_clock_tick = time.perf_counter()
    game.result_text = "Opened " + node["name"] + " — clocks paused"
    game.persist()
    return []
