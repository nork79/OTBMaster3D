"""UI-independent bookmark tree and technical position snapshots.

Nodes returned to callers are owned copies. All tree mutations go through the
collection, so callers cannot accidentally create multiple parents or cycles.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
import logging
import math
from uuid import UUID, uuid4

from otb_chess.chess_backend.position import ChessPosition
from otb_chess.document_state import History
from otb_chess.engine_identity import profile_identifier

log = logging.getLogger(__name__)
SCHEMA_VERSION = 1


def _now():
    return datetime.now(timezone.utc).isoformat()


def _name(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Name must be nonempty text")
    return value


def _uuid(value):
    if not isinstance(value, str) or str(UUID(value)) != value:
        raise ValueError("Expected a canonical UUID")
    return value


def _object(value):
    if not isinstance(value, dict):
        raise ValueError("Expected an object")
    # Reject non-JSON values and nonfinite clock/engine settings at the boundary.
    return json.loads(json.dumps(value, allow_nan=False))


def capture_position(board):
    """Preserve repetition history and raw EP state using the live rules provider."""
    history = ChessPosition.from_board(board).history(raw_ep=True)
    return {"representation": "fen-history", "fen": history.final_fen,
            "root_fen": history.root_fen,
            "moves": [ChessPosition.uci(move) for move in history.moves]}


def restore_position(position):
    """FEN is authoritative; use optional history only when it agrees exactly."""
    if position.get("representation", "fen-history") != "fen-history":
        raise ValueError("Unsupported position representation")
    authoritative = ChessPosition(position["fen"])
    if not authoritative.is_valid():
        raise ValueError("Invalid chess position")
    if "root_fen" not in position and "moves" not in position:
        return authoritative.legacy_board
    try:
        board = ChessPosition(position["root_fen"])
        moves = position["moves"]
        if not isinstance(moves, list) or not board.is_valid():
            raise ValueError("Invalid optional history")
        history = History(board.fen(raw_ep=True), tuple(ChessPosition.parse_uci(move) for move in moves),
                          authoritative.fen(raw_ep=True))
        return ChessPosition.from_history(history, raw_ep=True).legacy_board
    except (ValueError, TypeError, KeyError, AttributeError, IndexError) as exc:
        log.warning("Ignoring optional bookmark history: %s", exc)
        return authoritative.legacy_board


def capture_engine(manager):
    """Capture actual loaded model plus the settings used for subsequent searches."""
    with manager.lock:
        return _capture_engine(manager)


def _capture_engine(manager):
    if manager.engine is None:
        return None
    result = deepcopy(manager.loaded_configuration)
    if result is None:
        raise ValueError("Loaded engine has no configuration snapshot")
    cfg = manager.app.cfg
    result.update(executable=manager.path, elo=cfg.get("engine_elo"),
                  rating=cfg.get("engine_rating"), style=cfg.get("engine_style", "Balanced"),
                  side=cfg.get("engine_side", "Black"))
    configuration = manager.engine.configuration_snapshot()
    result["name"] = configuration["name"] or result["name"]
    result["settings"]["uci_options"] = configuration["uci_options"]
    result["profile_id"] = profile_identifier(result)
    return _object(result)


def capture_time_control(control, clock_mode="Online", **settings):
    return {"preset_name": control.name, "base_seconds": control.initial_seconds,
            "increment_seconds": control.increment_seconds, "delay_seconds": 0,
            "clock_mode": clock_mode, "settings": settings}


def capture_facing(game):
    facing = game.board_facing
    if facing not in ("white", "black"):
        raise ValueError("Invalid semantic board facing")
    return facing


def _bookmark(node):
    restore_position(node["position"])
    node.setdefault("facing", "white")
    if node["facing"] not in ("white", "black"):
        raise ValueError("Invalid board facing")
    node.setdefault("engine", None)
    if node["engine"] is not None:
        engine = node["engine"] = _object(node["engine"])
        _name(engine["engine_id"])
        _name(engine["name"])
        engine.setdefault("settings", {})
        _object(engine["settings"])
        # Older snapshots may lack a registry/profile ID. Preserve provided IDs
        # verbatim, including references unavailable on the current computer.
        if "profile_id" in engine:
            _name(engine["profile_id"])
    node.setdefault("time_control", None)
    if node["time_control"] is not None:
        control = node["time_control"] = _object(node["time_control"])
        control.setdefault("increment_seconds", 0)
        control.setdefault("delay_seconds", 0)
        for field in ("base_seconds", "increment_seconds", "delay_seconds"):
            value = control[field]
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError("Invalid time control")
    node.setdefault("created_at", _now())
    node.setdefault("modified_at", node["created_at"])
    for field in ("created_at", "modified_at"):
        if datetime.fromisoformat(node[field]).tzinfo is None:
            raise ValueError("Timestamp must include timezone")


class BookmarkCollection:
    def __init__(self):
        self._root_id = str(uuid4())
        self._nodes = {self.root_id: {"id": self.root_id, "type": "folder",
                                    "name": "Bookmarks", "children": []}}
        self._parents = {}
        self._extra = {}

    @property
    def root_id(self):
        return self._root_id

    def get(self, node_id):
        return deepcopy(self._nodes[node_id])

    def _folder(self, node_id):
        node = self._nodes[node_id]
        if node["type"] != "folder":
            raise ValueError("Parent must be a folder")
        return node

    @staticmethod
    def _index(index, length):
        if index is None:
            return length
        if type(index) is not int or not 0 <= index <= length:
            raise ValueError("Invalid child index")
        return index

    def _insert(self, parent_id, node, index):
        parent = self._folder(parent_id)
        index = self._index(index, len(parent["children"]))
        _uuid(node["id"])
        _name(node["name"])
        if node["id"] in self._nodes:
            raise ValueError("Duplicate UUID")
        self._nodes[node["id"]] = node
        self._parents[node["id"]] = parent_id
        parent["children"].insert(index, node["id"])
        return node["id"]

    def create_folder(self, parent_id, name, *, index=None, node_id=None):
        return self._insert(parent_id, {"id": node_id or str(uuid4()), "type": "folder",
                                       "name": name, "children": []}, index)

    def create_bookmark(self, parent_id, name, position, *, facing="white", engine=None,
                        time_control=None, index=None, node_id=None):
        node = _object({"id": node_id or str(uuid4()), "type": "bookmark", "name": name,
                        "position": position, "facing": facing, "engine": engine,
                        "time_control": time_control})
        _bookmark(node)
        return self._insert(parent_id, node, index)

    def rename(self, node_id, name):
        node = self._nodes[node_id]
        node["name"] = _name(name)
        if node["type"] == "bookmark":
            node["modified_at"] = _now()

    def delete(self, node_id):
        if node_id == self.root_id:
            raise ValueError("Cannot delete root")
        parent = self._parents[node_id]
        self._nodes[parent]["children"].remove(node_id)
        pending = [node_id]
        while pending:
            current = pending.pop()
            pending.extend(self._nodes[current].get("children", []))
            del self._nodes[current]
            del self._parents[current]

    def move(self, node_id, parent_id, *, index=None):
        """Index is the final index after removing the item from its old parent."""
        if node_id == self.root_id:
            raise ValueError("Cannot move root")
        old = self._parents[node_id]
        parent = self._folder(parent_id)
        ancestor = parent_id
        while ancestor is not None:
            if ancestor == node_id:
                raise ValueError("Cannot move a folder into its subtree")
            ancestor = self._parents.get(ancestor)
        index = self._index(index, len(parent["children"]) - (old == parent_id))
        self._nodes[old]["children"].remove(node_id)
        parent["children"].insert(index, node_id)
        self._parents[node_id] = parent_id

    def reorder(self, parent_id, children):
        parent = self._folder(parent_id)
        children = list(children)
        if len(children) != len(parent["children"]) or set(children) != set(parent["children"]):
            raise ValueError("Order must contain every child exactly once")
        parent["children"] = children

    def to_dict(self):
        return deepcopy({**self._extra, "schema_version": SCHEMA_VERSION,
                         "root_id": self.root_id, "nodes": list(self._nodes.values())})

    @classmethod
    def from_dict(cls, data, *, engine_available=None):
        """Recover valid reachable nodes. First valid parent wins damaged edges.

        An optional resolver checks engine identity/profile/resources without
        launching engines. Unavailable references are retained unchanged.
        """
        if not isinstance(data, dict) or type(data.get("schema_version")) is not int or data["schema_version"] != SCHEMA_VERSION:
            raise ValueError("Unsupported bookmark schema")
        root_id = _uuid(data["root_id"])
        if not isinstance(data["nodes"], list):
            raise ValueError("Expected node list")
        candidates = {}
        for raw in data["nodes"]:
            try:
                node = _object(raw)
                node_id = _uuid(node["id"])
                _name(node["name"])
                if node_id in candidates:
                    raise ValueError("Duplicate UUID")
                if node["type"] == "folder":
                    node.setdefault("children", [])
                    if not isinstance(node["children"], list):
                        raise ValueError("Invalid children")
                elif node["type"] == "bookmark":
                    if "children" in node:
                        raise ValueError("Bookmark cannot contain children")
                    _bookmark(node)
                else:
                    raise ValueError("Unknown node type")
                candidates[node_id] = node
            except (ValueError, TypeError, KeyError, AttributeError, OverflowError) as exc:
                log.warning("Skipping malformed bookmark node: %s", exc)
        if root_id not in candidates or candidates[root_id]["type"] != "folder":
            raise ValueError("Missing valid bookmark root")
        result = cls()
        result._root_id = root_id
        result._nodes = {root_id: candidates[root_id]}
        result._extra = {key: deepcopy(value) for key, value in data.items()
                         if key not in ("schema_version", "root_id", "nodes")}
        pending = [root_id]
        while pending:
            node_id = pending.pop()
            node = result._nodes[node_id]
            if node["type"] == "bookmark":
                if node["engine"] is not None and engine_available is not None:
                    try:
                        available = engine_available(deepcopy(node["engine"]))
                    except Exception as exc:
                        log.warning("Engine resolver failed for %s: %s", node_id, exc)
                        available = False
                    if not available:
                        log.warning("Unavailable engine configuration for bookmark %s; retained", node_id)
                continue
            children = node["children"]
            node["children"] = []
            for child in children:
                if not isinstance(child, str) or child not in candidates or child in result._nodes:
                    log.warning("Ignoring invalid/duplicate/cyclic bookmark edge from %s", node_id)
                    continue
                result._nodes[child] = candidates[child]
                result._parents[child] = node_id
                node["children"].append(child)
                pending.append(child)
        if len(result._nodes) != len(candidates):
            log.warning("Discarding unreachable bookmark nodes")
        return result
