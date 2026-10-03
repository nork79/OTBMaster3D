"""Bookmark data and storage tests; no graphics, UI, or engine processes."""
from copy import deepcopy
import json
import math
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

from otb_chess.bookmarks import (BookmarkCollection, capture_position, restore_position,
                                 capture_engine, capture_facing, capture_time_control)
from otb_chess.chess_backend import rules, uci
from otb_chess.core.board_input import BoardInput
from otb_chess.engine_identity import identify_engine, profile_identifier
from otb_chess.services.bookmarks import BookmarkStore
from otb_chess.services.engine import EngineManager
from otb_chess.services.settings import TimeControl


class BookmarkTests(unittest.TestCase):
    def setUp(self):
        self.collection = BookmarkCollection()
        self.root = self.collection.root_id
        self.position = capture_position(rules.Board())

    def bookmark(self, parent=None, **kwargs):
        return self.collection.create_bookmark(parent or self.root, "Position", self.position, **kwargs)

    def test_create_nested_folders_and_recursive_delete(self):
        first = self.collection.create_folder(self.root, "Opening")
        second = self.collection.create_folder(first, "Variation")
        item = self.bookmark(second)
        self.assertEqual(self.collection.get(first)["children"], [second])
        self.assertEqual(self.collection.get(second)["children"], [item])
        self.collection.delete(first)
        self.assertEqual(self.collection.get(self.root)["children"], [])
        for node in (first, second, item):
            with self.assertRaises(KeyError):
                self.collection.get(node)

    def test_bookmark_creation_rename_and_delete(self):
        item = self.bookmark(facing="black")
        node = self.collection.get(item)
        self.assertEqual(str(UUID(item)), item)
        self.assertEqual(node["created_at"], node["modified_at"])
        self.assertEqual(node["facing"], "black")
        self.collection.rename(item, "Endgame")
        renamed = self.collection.get(item)
        self.assertEqual(renamed["name"], "Endgame")
        self.assertEqual(renamed["created_at"], node["created_at"])
        self.assertGreaterEqual(renamed["modified_at"], node["modified_at"])
        self.collection.delete(item)
        self.assertEqual(self.collection.get(self.root)["children"], [])

    def test_move_bookmarks_folders_rename_and_order(self):
        folder = self.collection.create_folder(self.root, "A")
        other = self.collection.create_folder(self.root, "B")
        first, second = self.bookmark(folder), self.bookmark(folder)
        self.collection.rename(folder, "C")
        self.assertEqual(self.collection.get(folder)["name"], "C")
        self.collection.move(first, other)
        self.collection.move(folder, other, index=0)
        self.assertEqual(self.collection.get(other)["children"], [folder, first])
        self.assertEqual(self.collection.get(folder)["children"], [second])
        self.collection.reorder(other, [first, folder])
        self.collection.move(folder, other, index=0)
        self.assertEqual(self.collection.get(other)["children"], [folder, first])

    def test_invalid_operations_are_atomic(self):
        folder = self.collection.create_folder(self.root, "A")
        nested = self.collection.create_folder(folder, "B")
        item = self.bookmark()
        operations = [lambda: self.collection.move(self.root, folder),
                      lambda: self.collection.delete(self.root),
                      lambda: self.collection.move(folder, folder),
                      lambda: self.collection.move(folder, nested),
                      lambda: self.collection.move(folder, item),
                      lambda: self.collection.move(item, folder, index=12),
                      lambda: self.collection.reorder(self.root, [folder, folder]),
                      lambda: self.collection.create_folder(self.root, "D", node_id=item),
                      lambda: self.collection.create_folder(item, "D"),
                      lambda: self.collection.rename(item, " ")]
        before = self.collection.to_dict()
        for operation in operations:
            with self.assertRaises(ValueError):
                operation()
            self.assertEqual(self.collection.to_dict(), before)

    def test_snapshots_do_not_alias_model(self):
        item = self.bookmark()
        self.position["fen"] = "bad"
        node = self.collection.get(item)
        node["position"]["fen"] = "bad"
        self.collection.to_dict()["nodes"].clear()
        self.assertEqual(restore_position(self.collection.get(item)["position"]).fen(), rules.Board().fen())

    def test_exact_position_history_ep_castling_and_counters(self):
        board = rules.Board()
        for move in ("g1f3", "g8f6", "f3g1", "f6g8", "e2e4"):
            board.push_uci(move)
        position = capture_position(board)
        self.assertEqual(position["fen"].split()[3], "e3")
        restored = restore_position(position)
        self.assertEqual(restored.fen(en_passant="fen"), board.fen(en_passant="fen"))
        self.assertEqual(restored.move_stack, board.move_stack)
        self.assertEqual(restored.castling_rights, board.castling_rights)
        board = rules.Board("r3k2r/8/8/8/8/8/8/R3K2R b Kq - 123 456")
        self.assertEqual(restore_position(capture_position(board)).fen(), board.fen())
        position["moves"].append("e7e5")
        with self.assertLogs("otb_chess.bookmarks", level="WARNING"):
            restored = restore_position(position)
        self.assertEqual(restored.fen(en_passant="fen"), position["fen"])
        self.assertEqual(restored.move_stack, [])

    def test_repetition_restored(self):
        board = rules.Board()
        for move in ("g1f3", "g8f6", "f3g1", "f6g8") * 2:
            board.push_uci(move)
        self.assertTrue(restore_position(capture_position(board)).is_repetition(3))

    def test_facing_only_and_time_controls(self):
        game = BoardInput()
        game.board_mode, game.yaw, game.two_d_flipped = "3D", math.pi, False
        self.assertEqual(capture_facing(game), "white")
        game.board_mode = "2D"
        self.assertEqual(capture_facing(game), "white")
        for name in ("Custom", "Bullet 2+1"):
            control = capture_time_control(TimeControl(name, 120, 1), "OTB", custom_initial=120)
            item = self.bookmark(time_control=control)
            self.assertEqual(self.collection.get(item)["time_control"], control)
        self.assertNotIn("yaw", json.dumps(self.collection.to_dict()))
        with self.assertRaises(ValueError):
            self.bookmark(time_control={"base_seconds": float("nan")})

    def test_semantic_facing_orbit_flip_reset_and_roundtrip(self):
        game = BoardInput()
        game.board_mode, game.two_d_flipped = "3D", False
        game.pan_x = game.pan_z = game.two_d_pan_x = game.two_d_pan_z = 0
        game.mark_camera_dirty = game.persist = game.fit_board_view = Mock()
        for yaw in (0, math.pi / 2, math.pi, 3 * math.pi / 2, -17):
            game.yaw = yaw
            self.assertEqual(capture_facing(game), "white")
        game.flip_board()
        self.assertEqual(capture_facing(game), "black")
        game.yaw = 0.12  # free camera orbit does not change selected side
        item = self.bookmark(facing=capture_facing(game))
        loaded = BookmarkCollection.from_dict(self.collection.to_dict()).get(item)
        self.assertEqual(loaded["facing"], "black")
        self.assertNotIn("yaw", json.dumps(loaded))
        game.reset_view()
        self.assertEqual(capture_facing(game), "white")
        game.set_board_facing(loaded["facing"])
        self.assertEqual(capture_facing(game), "black")
        yaw = game.yaw
        game.set_board_facing("black")
        self.assertEqual(game.yaw, yaw)
        game.board_mode = "2D"
        game.set_board_facing("black")
        self.assertTrue(game.two_d_flipped)
        game.reset_view()
        self.assertEqual(capture_facing(game), "white")

    def test_fen_authority_with_absent_damaged_or_mismatching_history(self):
        board = rules.Board()
        board.push_uci("e2e4")
        fen = board.fen(en_passant="fen")
        for history in ({}, {"moves": []}, {"root_fen": "bad", "moves": []},
                        {"root_fen": rules.Board().fen(), "moves": ["bad"]},
                        {"root_fen": rules.Board().fen(), "moves": []},
                        {"root_fen": fen.replace(" e3 ", " - "), "moves": []},
                        {"root_fen": fen.rsplit(" ", 1)[0] + " 99", "moves": []},
                        {"root_fen": fen, "moves": "wrong type"}):
            position = {"fen": fen, **history}
            with self.subTest(history=history):
                if history:
                    with self.assertLogs("otb_chess.bookmarks", level="WARNING"):
                        restored = restore_position(position)
                else:
                    restored = restore_position(position)
                self.assertEqual(restored.fen(en_passant="fen"), fen)
                self.assertEqual(restored.move_stack, [])
        with self.assertRaises(ValueError):
            restore_position({"fen": "bad", "root_fen": rules.Board().fen(), "moves": []})
        item = self.bookmark()
        data = self.collection.to_dict()
        data["nodes"][-1]["position"] = {"fen": fen, "moves": ["bad"]}
        with self.assertLogs("otb_chess.bookmarks", level="WARNING"):
            loaded = BookmarkCollection.from_dict(data)
        self.assertEqual(loaded.get(item)["position"]["fen"], fen)

    def test_roundtrip_optional_and_unknown_fields(self):
        item = self.bookmark()
        data = self.collection.to_dict()
        data["future_metadata"] = {"x": 1}
        node = next(n for n in data["nodes"] if n["id"] == item)
        node["future_feature"] = ["opaque"]
        for field in ("time_control", "facing", "created_at", "modified_at"):
            del node[field]
        loaded = BookmarkCollection.from_dict(json.loads(json.dumps(data)))
        self.assertEqual(loaded.get(item)["future_feature"], ["opaque"])
        self.assertEqual(loaded.to_dict()["future_metadata"], {"x": 1})
        self.assertEqual(loaded.get(item)["facing"], "white")
        self.assertEqual(BookmarkCollection.from_dict(loaded.to_dict()).to_dict(), loaded.to_dict())

    def test_damaged_nodes_and_edges_recovered(self):
        folder = self.collection.create_folder(self.root, "Folder")
        item = self.bookmark(folder)
        data = self.collection.to_dict()
        data["nodes"][0]["children"].extend([folder, "missing", {}, self.root])
        data["nodes"][1]["children"].append(self.root)
        data["nodes"].extend([deepcopy(data["nodes"][2]), {"id": "bad"}, None])
        bad = deepcopy(data["nodes"][2])
        bad["id"] = str(uuid4())
        bad["position"]["fen"] = "bad fen"
        data["nodes"].append(bad)
        data["nodes"][0]["children"].append(bad["id"])
        with self.assertLogs("otb_chess.bookmarks", level="WARNING"):
            loaded = BookmarkCollection.from_dict(data)
        self.assertEqual(loaded.get(self.root)["children"], [folder])
        self.assertEqual(loaded.get(folder)["children"], [item])
        self.assertEqual(len(loaded.to_dict()["nodes"]), 3)

    def test_arbitrary_folder_depth_without_recursive_json(self):
        parent = self.root
        for _ in range(1100):
            parent = self.collection.create_folder(parent, "Nested")
        self.bookmark(parent)
        loaded = BookmarkCollection.from_dict(json.loads(json.dumps(self.collection.to_dict())))
        first = loaded.get(self.root)["children"][0]
        loaded.delete(first)
        self.assertEqual(len(loaded.to_dict()["nodes"]), 1)

    def test_legacy_engine_snapshots_are_discarded_without_resolution(self):
        item = self.bookmark()
        data = self.collection.to_dict()
        node = next(node for node in data["nodes"] if node["id"] == item)
        node["engine"] = {"engine_id": "missing", "name": "Old engine"}
        resolver = Mock(side_effect=AssertionError("Must not resolve engine"))
        loaded = BookmarkCollection.from_dict(data, engine_available=resolver)
        self.assertNotIn("engine", loaded.get(item))
        resolver.assert_not_called()

    def test_stable_engine_and_profile_identifiers(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "original.exe"
            moved = Path(directory) / "renamed.exe"
            first.write_bytes(b"test engine binary")
            moved.write_bytes(first.read_bytes())
            self.assertEqual(identify_engine("Custom Engine", first), identify_engine("New label", moved))
            self.assertEqual(identify_engine("Stockfish 19", first), "stockfish")
            self.assertEqual(identify_engine("Stockfish 20", moved), "stockfish")
            self.assertEqual(identify_engine("Rodent IV", moved), "rodent")
            config = {"engine_id": "fairy-stockfish", "name": "Fairy-Stockfish", "profile": "Club",
                      "settings": {"uci_options": {"UCI_Elo": 900}}}
            original = profile_identifier(config)
            config.update(name="Translated", executable="new/path", profile="Renamed label")
            self.assertEqual(profile_identifier(config), original)
            config["settings"]["uci_options"]["UCI_Elo"] = 1100
            self.assertNotEqual(profile_identifier(config), original)
            stockfish = {"engine_id": "stockfish", "settings": {}}
            ids = {profile_identifier({**stockfish, "style": style}) for style in ("Balanced", "Active", "Quiet")}
            self.assertEqual(len(ids), 3)
            self.assertNotEqual(profile_identifier(stockfish), profile_identifier({**stockfish, "elo": 1500}))
            personality = Path(directory) / "Tal.txt"
            personality.write_text("Attack=100")
            rodent = {"engine_id": "rodent", "settings": {"PersonalityFile": str(personality)}}
            original = profile_identifier(rodent)
            personality.rename(Path(directory) / "new-name.txt")
            rodent["settings"]["PersonalityFile"] = str(Path(directory) / "new-name.txt")
            self.assertEqual(profile_identifier(rodent), original)

    def test_custom_engine_personality_and_strength_snapshot(self):
        transport = SimpleNamespace(id={"name": "Rodent"}, protocol=SimpleNamespace(
            target_config={"PersonalityFile": "Tal.txt", "UCI_Elo": 1700}))
        manager = EngineManager(SimpleNamespace(cfg={"engine_elo": 1700, "engine_style": "Quiet"}))
        manager.engine = uci.Engine(transport)
        manager.path = "rodent.exe"
        manager.loaded_configuration = {"engine_id": "rodent", "name": "Rodent",
                                        "profile": "Tal", "settings": {}}
        captured = capture_engine(manager)
        self.assertEqual(captured["elo"], 1700)
        self.assertEqual(captured["style"], "Balanced")  # Rodent uses its native personality.
        self.assertEqual(captured["settings"]["uci_options"]["PersonalityFile"], "Tal.txt")


class BookmarkStoreTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "bookmarks.json"

    def test_persistence_across_restart(self):
        collection = BookmarkStore(self.path).load()
        folder = collection.create_folder(collection.root_id, "Saved")
        collection.create_bookmark(folder, "Start", capture_position(rules.Board()))
        self.assertTrue(BookmarkStore(self.path).save(collection))
        self.assertEqual(BookmarkStore(self.path).load().to_dict(), collection.to_dict())

    def test_malformed_json_and_future_schema_leave_source_untouched(self):
        for source in ('{"nodes":', 'null', '{"schema_version": 999}', '{"schema_version": 1}'):
            self.path.write_text(source, encoding="utf-8")
            store = BookmarkStore(self.path)
            with self.assertLogs("otb_chess.services.bookmarks", level="WARNING"):
                loaded = store.load()
            self.assertEqual(loaded.get(loaded.root_id)["children"], [])
            self.assertIsNotNone(store.error)
            self.assertEqual(self.path.read_text(encoding="utf-8"), source)

    def test_legacy_engine_is_removed_on_next_save(self):
        collection = BookmarkCollection()
        item = collection.create_bookmark(collection.root_id, "Saved", capture_position(rules.Board()))
        data = collection.to_dict()
        next(node for node in data["nodes"] if node["id"] == item)["engine"] = {"name": "Missing"}
        self.path.write_text(json.dumps(data), encoding="utf-8")
        store = BookmarkStore(self.path)
        with patch.object(uci.Engine, "open", side_effect=AssertionError("Must not launch")):
            loaded = store.load()
        self.assertNotIn("engine", loaded.get(item))
        self.assertTrue(store.save(loaded))
        self.assertNotIn('"engine"', self.path.read_text(encoding="utf-8"))

    def test_failed_flush_or_replace_preserves_previous_collection(self):
        collection = BookmarkCollection()
        store = BookmarkStore(self.path)
        self.assertTrue(store.save(collection))
        previous = self.path.read_bytes()
        collection.create_folder(collection.root_id, "New")
        for operation in ("fsync", "replace"):
            with patch("otb_chess.services.bookmarks.os." + operation, side_effect=OSError("failure")), \
                    self.assertLogs("otb_chess.services.bookmarks", level="WARNING"):
                self.assertFalse(store.save(collection))
            self.assertEqual(self.path.read_bytes(), previous)
            self.assertEqual(list(self.path.parent.glob("*.tmp")), [])
        self.assertTrue(store.save(collection))
        self.assertIsNone(store.error)


if __name__ == "__main__":
    unittest.main()
