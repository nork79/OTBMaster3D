"""Transactional bookmark editing and UI-independent live-game restoration."""
import time
import math

from otb_chess.bookmarks import (BookmarkCollection, capture_position, capture_engine,
                                capture_facing, capture_time_control, restore_position)
from otb_chess.services.settings import TIME_CONTROLS


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
        if getattr(game, "engine_loading", False):
            raise ValueError("Wait for the engine to finish loading before saving a bookmark.")
        control = game.selected_time_control()
        if control is None:
            raise ValueError("Choose a valid time control first.")
        engine = capture_engine(game.engine_manager)
        if engine is not None:
            engine["side"] = game.engine_side_var.get()
        snapshot = dict(position=capture_position(game.board), facing=capture_facing(game),
                        engine=engine, time_control=capture_time_control(control, game.clock_mode_var.get()))
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
    control = node.get("time_control")
    if control is not None:
        for key in ("base_seconds", "increment_seconds", "delay_seconds"):
            value = control.get(key, 0)
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError("Invalid saved time control")
        if "base_seconds" not in control or control.get("clock_mode", "Online") not in ("Online", "OTB"):
            raise ValueError("Unsupported saved time control")
    return board


def restore_bookmark(game, node, engine_result):
    """Apply on the UI thread, after searches/loading have drained.

    engine_result is (success, diagnostic) from restore_configuration, performed
    by the UI's background worker. Failed engine restoration leaves its current
    engine/configuration intact; position and time control still restore.
    """
    board = validate_restore(node)
    game.clock_paused = True
    game.load_document(board)
    game.game_started = True  # Resume continues this board, including its history.
    game.move_animation = None
    game.pending_engine_error = None
    game.engine_output = None
    game.last_engine_search = None
    game.set_board_facing(node.get("facing", "white"))
    warnings = []
    control = node.get("time_control")
    if control is not None:
        base, increment = control["base_seconds"], control.get("increment_seconds", 0)
        name = control.get("preset_name", "Custom")
        preset = TIME_CONTROLS.get(name)
        if preset is None or (preset.initial_seconds, preset.increment_seconds) != (base, increment):
            name = "Custom"
        game.time_control_var.set(name)
        game.custom_initial_var.set(base)
        game.custom_increment_var.set(increment)
        game.clock_mode = control.get("clock_mode", "Online")
        game.clock_mode_var.set(game.clock_mode)
        game.white_time = game.black_time = base
        game.increment = increment
        if control.get("delay_seconds", 0):
            warnings.append("Saved delay is not supported by the current clock.")
    success, diagnostic = engine_result
    engine = node.get("engine")
    if success and engine is not None:
        game.cfg.update(engine_elo=engine.get("elo"), engine_rating=engine.get("rating") or 1500,
                        engine_style=engine.get("style", "Balanced"),
                        engine_difficulty=engine.get("profile", "custom"))
        side = engine.get("side", "Black")
        game.engine_side_var.set(side)
        game.engine_side = {"White": True, "Black": False}.get(side)
        game.engine_var.set(game.engine_manager.path)
    elif success and engine is None:
        game.engine_var.set("")
        game.engine_side_var.set("None")
        game.engine_side = None
    elif not success:
        if game.engine_manager.engine is not None:
            game.engine_var.set(game.engine_manager.path)
        warnings.append("Saved engine configuration could not be restored. " + diagnostic)
    game.clock_paused = True
    game.last_clock_tick = time.perf_counter()
    game.result_text = "Opened " + node["name"] + " — clocks paused"
    if warnings:
        game.result_text += ". " + " ".join(warnings)
    game.persist()
    return warnings
