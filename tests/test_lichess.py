"""Unit and UI integration tests for Phase 1 Lichess login parameters and Lichess menu."""

import io
import json
import logging
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.parse
import urllib.request

from PySide6.QtCore import Qt, QTimer, QCoreApplication, QEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QComboBox, QDoubleSpinBox, QLineEdit, QMessageBox, QPushButton, QSpinBox, QDialogButtonBox, QTableWidget
import shiboken6

from otb_chess.services import settings
from otb_chess.services.lichess import (
    CredentialProtectionError,
    CredentialProtector,
    LICHESS_CHALLENGE_PRESETS,
    LICHESS_SEEK_PRESETS,
    LichessAccount,
    LichessChallengeOptions,
    LichessClient,
    LichessGameSession,
    LichessGameSummary,
    LichessLoginParameters,
    WindowsDPAPIProtector,
    clear_stored_auth,
    format_bot_summary,
    format_lichess_termination,
    generate_pkce_pair,
    load_stored_auth,
    parse_cli_login_args,
    save_stored_auth,
)
from otb_chess.ui.desktop_ui import MainWindow, configure_graphics
from otb_chess.ui.lichess_dialog import LichessChallengeDialog, LichessHistoryDialog, LichessLoginDialog


class _FakeHTTPResponse:
    def __init__(self, payload: dict):
        self._bytes = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._bytes

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class LichessServiceTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.auth_path = Path(self.folder.name) / "lichess_auth.json"
        self.auth_patch = patch.object(settings, "LICHESS_AUTH_PATH", self.auth_path)
        self.auth_patch.start()
        self.addCleanup(self.auth_patch.stop)

    def test_pkce_pair_generation_is_valid_s256(self):
        verifier, challenge = generate_pkce_pair()
        self.assertGreaterEqual(len(verifier), 43)
        self.assertNotIn("=", challenge)
        self.assertNotEqual(verifier, challenge)

    def test_cli_login_parameter_parsing_and_env_fallback(self):
        with patch.dict("os.environ", {}, clear=True):
            params, remaining = parse_cli_login_args([
                "--lichess-token", "lip_abc123",
                "--lichess-url", "https://lichess.org/",
                "--lichess-client-id", "custom-client",
                "--lichess-username", "GrandmasterFlash",
                "--extra-arg",
            ])
            self.assertIsNotNone(params)
            self.assertEqual(params.normalized_token(), "lip_abc123")
            self.assertEqual(params.normalized_url(), "https://lichess.org")
            self.assertEqual(params.normalized_client_id(), "custom-client")
            self.assertEqual(params.username, "GrandmasterFlash")
            self.assertEqual(remaining, ["--extra-arg"])

            none_params, rem = parse_cli_login_args(["--other"])
            self.assertIsNone(none_params)
            self.assertEqual(rem, ["--other"])

        with patch.dict("os.environ", {"LICHESS_TOKEN": "lip_from_env"}, clear=True):
            env_params, _ = parse_cli_login_args([])
            self.assertIsNotNone(env_params)
            self.assertEqual(env_params.normalized_token(), "lip_from_env")

    def test_login_with_parameters_verifies_account_and_persists(self):
        captured_requests = []

        def fake_opener(request, timeout=10.0):
            captured_requests.append(request)
            return _FakeHTTPResponse({
                "id": "nork79",
                "username": "Nork79",
                "title": "FM",
                "perfs": {"rapid": {"rating": 2105}, "blitz": {"rating": 1980}},
            })

        client = LichessClient(opener=fake_opener)
        params = LichessLoginParameters(
            server_url="https://lichess.org/",
            client_id="my-app-id",
            token="lip_test_token_999",
            username="nork79",
        )
        account = client.login_with_parameters(params)
        self.assertTrue(client.is_authenticated)
        self.assertEqual(account.username, "Nork79")
        self.assertEqual(account.display_name, "FM Nork79")
        self.assertEqual(account.perfs["rapid"], 2105)
        self.assertEqual(len(captured_requests), 1)
        self.assertEqual(captured_requests[0].get_header("Authorization"), "Bearer lip_test_token_999")

        # Verify persistence round-trip
        restored_client = LichessClient()
        restored_account = restored_client.restore_saved_session()
        self.assertIsNotNone(restored_account)
        self.assertEqual(restored_account.username, "Nork79")
        self.assertEqual(restored_client.token, "lip_test_token_999")
        self.assertEqual(restored_client.client_id, "my-app-id")

    def test_login_rejects_mismatched_username_or_invalid_url(self):
        def fake_opener(request, timeout=10.0):
            return _FakeHTTPResponse({"id": "someone_else", "username": "SomeoneElse"})

        client = LichessClient(opener=fake_opener)
        with self.assertRaisesRegex(ValueError, "does not match expected username"):
            client.login_with_parameters(LichessLoginParameters(
                token="lip_valid",
                username="ExpectedUser",
            ))
        self.assertFalse(client.is_authenticated)

        with self.assertRaisesRegex(ValueError, "must start with https://"):
            LichessLoginParameters(server_url="ftp://lichess.org").normalized_url()

    def test_oauth_pkce_loopback_flow_exchanges_code_for_token(self):
        requests_made = []

        def fake_opener(request, timeout=10.0):
            requests_made.append(request)
            if request.full_url.endswith("/api/token"):
                return _FakeHTTPResponse({"access_token": "lip_oauth_pkce_token"})
            if request.full_url.endswith("/api/account"):
                return _FakeHTTPResponse({
                    "id": "oauth_player",
                    "username": "OAuthPlayer",
                    "perfs": {"classical": {"rating": 1850}},
                })
            raise AssertionError(f"Unexpected URL: {request.full_url}")

        def simulate_browser(auth_url):
            parsed = urllib.parse.urlparse(auth_url)
            query = urllib.parse.parse_qs(parsed.query)
            self.assertEqual(query["client_id"][0], "otb-pkce-test")
            self.assertEqual(query["code_challenge_method"][0], "S256")
            state = query["state"][0]
            client._oauth_server.record_callback(code="test_auth_code", state=state)

        client = LichessClient(opener=fake_opener)
        account = client.login_with_oauth_pkce(
            LichessLoginParameters(client_id="otb-pkce-test", username="OAuthPlayer"),
            open_browser=simulate_browser,
            timeout=5.0,
        )
        self.assertTrue(client.is_authenticated)
        self.assertEqual(account.username, "OAuthPlayer")
        self.assertEqual(client.token, "lip_oauth_pkce_token")
        self.assertEqual(len(requests_made), 2)

        # Logout revokes and clears stored auth
        client.logout(revoke_remote=False)
        self.assertFalse(client.is_authenticated)
        self.assertIsNone(load_stored_auth())

    def test_time_control_mapping_and_board_api_validation(self):
        # Bullet presets (1+0, 1+1, 2+0, 2+1) and Hyperbullet presets are in LICHESS_CHALLENGE_PRESETS,
        # but excluded from LICHESS_SEEK_PRESETS (since /api/board/seek only accepts Rapid & Classical).
        for fast_preset in ("Bullet 1+0", "Bullet 1+1", "Bullet 2+0", "Bullet 2+1", "Hyperbullet 30+0", "Blitz 3+0"):
            self.assertIn(fast_preset, LICHESS_CHALLENGE_PRESETS)
            self.assertNotIn(fast_preset, LICHESS_SEEK_PRESETS)

        # All challenge presets map cleanly
        for preset in LICHESS_CHALLENGE_PRESETS:
            opts = LichessChallengeOptions(mode="player", preset=preset, opponent_username="maia1", color="white")
            payload = opts.to_challenge_payload()
            tc = settings.TIME_CONTROLS[preset]
            self.assertEqual(payload["clock.limit"], str(int(tc.initial_seconds)))
            self.assertEqual(payload["clock.increment"], str(int(tc.increment_seconds)))
            self.assertEqual(payload["color"], "white")

        # Lichess AI mode has been removed
        with self.assertRaisesRegex(ValueError, "Unknown challenge mode: ai"):
            LichessChallengeOptions(mode="ai", preset="Rapid 10+0").to_challenge_payload()

        # All seek presets map minutes + increment cleanly
        for preset in LICHESS_SEEK_PRESETS:
            opts = LichessChallengeOptions(mode="seek", preset=preset, rated=True, color="random")
            payload = opts.to_challenge_payload()
            tc = settings.TIME_CONTROLS[preset]
            limit_sec = int(tc.initial_seconds)
            expected_time = str(limit_sec // 60) if limit_sec % 60 == 0 else f"{limit_sec / 60:g}"
            self.assertEqual(payload["time"], expected_time)
            self.assertEqual(payload["increment"], str(int(tc.increment_seconds)))
            self.assertEqual(payload["rated"], "true")

        # Bullet and Blitz are rejected for Quick Pairing (seek) per Lichess Board API rules
        for invalid_seek in ("Bullet 1+0", "Bullet 2+1", "Blitz 3+0", "Blitz 5+3"):
            with self.assertRaisesRegex(ValueError, "Quick Pairing.*only accepts Rapid or Classical"):
                LichessChallengeOptions(mode="seek", preset=invalid_seek).to_challenge_payload()

        # Specific check for Bullet 1+0, 1+1, 2+0, 2+1 on direct challenges
        self.assertEqual(
            LichessChallengeOptions(mode="player", preset="Bullet 1+0", opponent_username="Friend").to_challenge_payload()["clock.limit"],
            "60",
        )
        self.assertEqual(
            LichessChallengeOptions(mode="player", preset="Bullet 1+1", opponent_username="Friend").to_challenge_payload(),
            {"rated": "false", "clock.limit": "60", "clock.increment": "1", "color": "random", "variant": "standard"},
        )
        self.assertEqual(
            LichessChallengeOptions(mode="player", preset="Bullet 2+1", opponent_username="Friend").to_challenge_payload(),
            {"rated": "false", "clock.limit": "120", "clock.increment": "1", "color": "random", "variant": "standard"},
        )
        self.assertEqual(
            LichessChallengeOptions(mode="player", preset="Bullet 2+0", opponent_username="Friend").to_challenge_payload(),
            {"rated": "false", "clock.limit": "120", "clock.increment": "0", "color": "random", "variant": "standard"},
        )

        # Infinite time control is rejected
        with self.assertRaisesRegex(ValueError, "Unsupported time control"):
            LichessChallengeOptions(mode="player", preset="Infinite (clocks disabled)", opponent_username="maia1").to_challenge_payload()

        # Player challenge requires opponent username
        with self.assertRaisesRegex(ValueError, "Enter a Lichess username"):
            LichessChallengeOptions(mode="player", preset="Rapid 10+0", opponent_username="").to_challenge_payload()

    def test_create_ai_and_player_challenge_and_seek_stream(self):
        requests_log = []

        class _FakeStreamResponse:
            def __init__(self, lines):
                self._lines = [line.encode("utf-8") for line in lines]
                self.closed = False

            def __iter__(self):
                return iter(self._lines)

            def close(self):
                self.closed = True

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        def fake_opener(request, timeout=10.0):
            body = request.data.decode("utf-8") if request.data else ""
            requests_log.append((request.get_method(), request.full_url, body, request.get_header("Accept") or ""))
            if request.full_url.endswith("/api/challenge/TestFriend"):
                return _FakeHTTPResponse({"challenge": {"id": "chal987", "status": "created"}})
            if request.full_url.endswith("/api/board/seek"):
                accept_hdr = request.get_header("Accept") or ""
                self.assertIn("text/plain", accept_hdr)
                self.assertIn("*/*", accept_hdr)
                return _FakeStreamResponse(["\n", json.dumps({"id": "seekMatch456"}) + "\n"])
            if request.full_url.endswith("/api/stream/event"):
                return _FakeStreamResponse([])
            raise AssertionError(f"Unexpected URL: {request.full_url}")

        client = LichessClient(
            token="lip_mock_token",
            account=LichessAccount(user_id="nork79", username="nork79"),
            opener=fake_opener,
        )

        # 1. Player Challenge (also rejects self-challenge)
        with self.assertRaisesRegex(ValueError, "cannot challenge your own"):
            client.create_challenge(
                LichessChallengeOptions(mode="player", preset="Rapid 10+0", opponent_username="Nork79")
            )

        player_res = client.create_challenge(
            LichessChallengeOptions(mode="player", preset="Rapid 10+5", opponent_username="TestFriend", rated=True)
        )
        self.assertEqual(player_res["challenge_id"], "chal987")
        self.assertIn("rated=true", requests_log[-1][2])

        # 2. Quick Pairing Seek (direct JSON response)
        seek_game_id = client.start_seek(
            LichessChallengeOptions(mode="seek", preset="Rapid 15+10", rated=False, color="random")
        )
        self.assertEqual(seek_game_id, "seekMatch456")
        seek_reqs = [r for r in requests_log if r[1].endswith("/api/board/seek")]
        self.assertTrue(seek_reqs)
        self.assertIn("time=15", seek_reqs[-1][2])
        self.assertIn("increment=10", seek_reqs[-1][2])

        # 3. Quick Pairing Seek (real Lichess flow: empty keepalive on /api/board/seek + gameStart on /api/stream/event)
        def fake_realtime_seek_opener(request, timeout=10.0):
            if request.full_url.endswith("/api/board/seek"):
                return _FakeStreamResponse(["\n", "\n"])
            if request.full_url.endswith("/api/stream/event"):
                return _FakeStreamResponse([
                    json.dumps({"type": "gameStart", "game": {"id": "liveSeekGame789", "gameId": "liveSeekGame789"}}) + "\n"
                ])
            raise AssertionError(f"Unexpected URL: {request.full_url}")

        client._opener = fake_realtime_seek_opener
        realtime_game_id = client.start_seek(
            LichessChallengeOptions(mode="seek", preset="Rapid 10+0", rated=True, color="random")
        )
        self.assertEqual(realtime_game_id, "liveSeekGame789")

    def test_game_session_parsing_and_board_api_actions(self):
        game_full = {
            "id": "liveGame001",
            "type": "gameFull",
            "rated": True,
            "speed": "rapid",
            "initialFen": "startpos",
            "white": {"id": "alice", "name": "Alice", "rating": 1820},
            "black": {"id": "nork79", "name": "nork79", "rating": 1795},
            "state": {
                "type": "gameState",
                "moves": "e2e4 e7e5",
                "wtime": 598000,
                "btime": 597000,
                "winc": 5000,
                "binc": 5000,
                "status": "started",
                "wdraw": True,
            },
        }
        session = LichessGameSession.from_game_full(game_full, my_username="Nork79")
        self.assertEqual(session.game_id, "liveGame001")
        self.assertEqual(session.my_color, False)
        self.assertTrue(session.active)
        self.assertTrue(session.opponent_offered_draw)
        self.assertFalse(session.opponent_proposed_takeback)
        self.assertEqual(session.clock_label(True), "Lichess · Alice (1820)")
        self.assertEqual(session.clock_label(False), "Lichess · nork79 (1795)")

        self.assertEqual(format_lichess_termination("mate", "white"), ("Checkmate - White wins", "1-0"))
        self.assertEqual(format_lichess_termination("resign", "black"), ("White resigned - Black wins", "0-1"))
        self.assertEqual(format_lichess_termination("outoftime", "white"), ("White wins on time", "1-0"))
        self.assertEqual(format_lichess_termination("draw", None), ("Draw - agreement or repetition", "1/2-1/2"))
        self.assertEqual(format_lichess_termination("aborted", None), ("Game aborted on Lichess", "*"))

        calls = []

        def fake_opener(request, timeout=10.0):
            calls.append((request.get_method(), request.full_url))
            return _FakeHTTPResponse({"ok": True})

        client = LichessClient(
            token="lip_action_token",
            account=LichessAccount(user_id="nork79", username="nork79"),
            opener=fake_opener,
        )
        client.send_move("liveGame001", "g1f3")
        client.resign_game("liveGame001")
        client.abort_game("liveGame001")
        client.handle_draw_offer("liveGame001", True)
        client.handle_takeback_offer("liveGame001", False)
        self.assertEqual(
            [url.split("lichess.org")[-1] for _, url in calls],
            [
                "/api/board/game/liveGame001/move/g1f3",
                "/api/board/game/liveGame001/resign",
                "/api/board/game/liveGame001/abort",
                "/api/board/game/liveGame001/draw/yes",
                "/api/board/game/liveGame001/takeback/no",
            ],
        )

    def _make_seek_client(self, opener):
        return LichessClient(
            token="lip_seek_test",
            account=LichessAccount(user_id="nork79", username="nork79"),
            opener=opener,
        )

    def test_quick_pairing_stream_established_before_seek_and_delayed_open(self):
        events_order = []
        allow_stream_open = threading.Event()
        stream_attempt_started = threading.Event()
        seek_called = threading.Event()

        class _BlockingEventStream:
            def __init__(self):
                self._queue = threading.Event()
                self._closed = False
                self._emitted = False

            def __iter__(self):
                return self

            def __next__(self):
                if self._closed or self._emitted:
                    raise StopIteration
                self._queue.wait(timeout=5.0)
                if self._closed:
                    raise StopIteration
                self._emitted = True
                return (json.dumps({"type": "gameStart", "game": {"id": "delayedMatch1", "source": "lobby"}}) + "\n").encode("utf-8")

            def close(self):
                self._closed = True
                self._queue.set()

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                self.close()
                return False

        class _BlockingSeekStream:
            def __init__(self, event_stream):
                self._event_stream = event_stream
                self._closed = False

            def __iter__(self):
                # Trigger gameStart once seek is actually submitted
                self._event_stream._queue.set()
                return iter([])

            def close(self):
                self._closed = True

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        stream_obj = _BlockingEventStream()

        def fake_opener(request, timeout=10.0):
            if request.full_url.endswith("/api/stream/event"):
                events_order.append("stream_open_start")
                stream_attempt_started.set()
                allow_stream_open.wait(timeout=5.0)
                events_order.append("stream_open_ready")
                return stream_obj
            if request.full_url.endswith("/api/board/seek"):
                events_order.append("seek_submitted")
                seek_called.set()
                return _BlockingSeekStream(stream_obj)
            raise AssertionError(f"Unexpected URL: {request.full_url}")

        client = self._make_seek_client(fake_opener)
        result = {}

        def run_seek():
            result["game_id"] = client.start_seek(
                LichessChallengeOptions(mode="seek", preset="Rapid 10+0", rated=False, color="random"),
                timeout=5.0,
            )

        t = threading.Thread(target=run_seek, daemon=True)
        t.start()
        self.assertTrue(stream_attempt_started.wait(timeout=2.0))
        # Seek must NOT be submitted while event stream establishment is delayed
        self.assertFalse(seek_called.is_set())
        allow_stream_open.set()
        t.join(timeout=5.0)
        self.assertFalse(t.is_alive())
        self.assertEqual(result.get("game_id"), "delayedMatch1")
        self.assertEqual(events_order, ["stream_open_start", "stream_open_ready", "seek_submitted"])

    def test_quick_pairing_direct_response_and_immediate_game_start(self):
        class _Stream:
            def __init__(self, lines):
                self._lines = [line.encode("utf-8") for line in lines]

            def __iter__(self):
                return iter(self._lines)

            def close(self):
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        # Case A: direct JSON id from /api/board/seek
        def direct_opener(request, timeout=10.0):
            if request.full_url.endswith("/api/stream/event"):
                return _Stream([])
            if request.full_url.endswith("/api/board/seek"):
                return _Stream([json.dumps({"id": "directSeek99"}) + "\n"])
            raise AssertionError(request.full_url)

        client = self._make_seek_client(direct_opener)
        self.assertEqual(
            client.start_seek(LichessChallengeOptions(mode="seek", preset="Rapid 10+0")),
            "directSeek99",
        )

        # Case B: gameStart arrives immediately upon stream connection
        def immediate_opener(request, timeout=10.0):
            if request.full_url.endswith("/api/stream/event"):
                return _Stream([
                    json.dumps({"type": "gameStart", "game": {"gameId": "immediateGame77", "source": "lobby"}}) + "\n"
                ])
            if request.full_url.endswith("/api/board/seek"):
                return _Stream(["\n"])
            raise AssertionError(request.full_url)

        client._opener = immediate_opener
        self.assertEqual(
            client.start_seek(LichessChallengeOptions(mode="seek", preset="Rapid 10+0")),
            "immediateGame77",
        )

    def test_quick_pairing_event_stream_connection_failure_propagates(self):
        seek_submitted = False

        def failing_stream_opener(request, timeout=10.0):
            nonlocal seek_submitted
            if request.full_url.endswith("/api/stream/event"):
                raise urllib.error.URLError("event stream unreachable")
            if request.full_url.endswith("/api/board/seek"):
                seek_submitted = True
                raise AssertionError("Seek should not be submitted when event stream fails to connect.")
            raise AssertionError(request.full_url)

        client = self._make_seek_client(failing_stream_opener)
        with self.assertRaisesRegex(ValueError, "event stream"):
            client.start_seek(LichessChallengeOptions(mode="seek", preset="Rapid 10+0"), timeout=5.0)
        self.assertFalse(seek_submitted)

    def test_quick_pairing_cancellation_closes_responses_and_stops_worker(self):
        seek_opened = threading.Event()
        stream_closed = threading.Event()
        seek_closed = threading.Event()

        class _CancellableStream:
            def __init__(self, closed_event):
                self._gate = threading.Event()
                self._closed_event = closed_event

            def __iter__(self):
                return self

            def __next__(self):
                self._gate.wait(timeout=5.0)
                raise StopIteration

            def close(self):
                self._closed_event.set()
                self._gate.set()

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                self.close()
                return False

        def cancelling_opener(request, timeout=10.0):
            if request.full_url.endswith("/api/stream/event"):
                return _CancellableStream(stream_closed)
            if request.full_url.endswith("/api/board/seek"):
                seek_opened.set()
                return _CancellableStream(seek_closed)
            raise AssertionError(request.full_url)

        client = self._make_seek_client(cancelling_opener)
        result = {}

        def run_seek():
            result["value"] = client.start_seek(
                LichessChallengeOptions(mode="seek", preset="Rapid 10+0"),
                timeout=5.0,
            )

        t = threading.Thread(target=run_seek, daemon=True)
        t.start()
        self.assertTrue(seek_opened.wait(timeout=2.0))
        client.cancel_seek()
        t.join(timeout=3.0)
        self.assertFalse(t.is_alive())
        self.assertIsNone(result.get("value"))
        self.assertTrue(stream_closed.is_set())
        self.assertTrue(seek_closed.is_set())

    def test_quick_pairing_timeout_and_unexpected_stream_termination(self):
        class _IdleStream:
            def __init__(self):
                self._gate = threading.Event()

            def __iter__(self):
                return self

            def __next__(self):
                self._gate.wait(timeout=5.0)
                raise StopIteration

            def close(self):
                self._gate.set()

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                self.close()
                return False

        # Case A: Timeout without matched opponent
        def timeout_opener(request, timeout=10.0):
            if request.full_url.endswith("/api/stream/event"):
                return _IdleStream()
            if request.full_url.endswith("/api/board/seek"):
                raise TimeoutError("timed out")
            raise AssertionError(request.full_url)

        client = self._make_seek_client(timeout_opener)
        with self.assertRaisesRegex(ValueError, "timed out"):
            client.start_seek(LichessChallengeOptions(mode="seek", preset="Rapid 10+0"), timeout=5.0)

        # Case B: Event stream terminates unexpectedly mid-seek with an error
        seek_entered = threading.Event()
        seek_closed = threading.Event()

        class _FailingMidStream:
            def __iter__(self):
                return self

            def __next__(self):
                seek_entered.wait(timeout=5.0)
                raise urllib.error.URLError("stream dropped mid-seek")

            def close(self):
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        class _WaitingSeekStream(_IdleStream):
            def close(self):
                seek_closed.set()
                super().close()

        def midstream_fail_opener(request, timeout=10.0):
            if request.full_url.endswith("/api/stream/event"):
                return _FailingMidStream()
            if request.full_url.endswith("/api/board/seek"):
                seek_entered.set()
                return _WaitingSeekStream()
            raise AssertionError(request.full_url)

        client._opener = midstream_fail_opener
        with self.assertRaisesRegex(ValueError, "event stream interrupted"):
            client.start_seek(LichessChallengeOptions(mode="seek", preset="Rapid 10+0"), timeout=5.0)
        self.assertTrue(seek_closed.is_set())

    def test_quick_pairing_repeated_attempts_no_stale_state_and_unrelated_events_ignored(self):
        attempt = 0

        class _LineStream:
            def __init__(self, lines):
                self._lines = [l.encode("utf-8") for l in lines]

            def __iter__(self):
                return iter(self._lines)

            def close(self):
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        def repeated_opener(request, timeout=10.0):
            if request.full_url.endswith("/api/stream/event"):
                if attempt == 1:
                    return _LineStream([
                        # Unrelated friend challenge + mismatched variant must be ignored
                        json.dumps({"type": "gameStart", "game": {"id": "friendGame0", "source": "friend"}}) + "\n",
                        json.dumps({"type": "gameStart", "game": {"id": "variantGame0", "source": "lobby", "variant": {"key": "crazyhouse"}}}) + "\n",
                        json.dumps({"type": "gameStart", "game": {"id": "validMatch1", "source": "lobby", "variant": {"key": "standard"}, "rated": False}}) + "\n",
                    ])
                return _LineStream([
                    json.dumps({"type": "gameStart", "game": {"id": "validMatch2", "source": "lobby", "rated": True}}) + "\n",
                ])
            if request.full_url.endswith("/api/board/seek"):
                return _LineStream(["\n"])
            raise AssertionError(request.full_url)

        client = self._make_seek_client(repeated_opener)
        attempt = 1
        g1 = client.start_seek(LichessChallengeOptions(mode="seek", preset="Rapid 10+0", rated=False))
        self.assertEqual(g1, "validMatch1")

        attempt = 2
        g2 = client.start_seek(LichessChallengeOptions(mode="seek", preset="Rapid 10+0", rated=True))
        self.assertEqual(g2, "validMatch2")

    def test_quick_pairing_http_406_and_accept_header(self):
        captured_headers = {}

        def opener_406(request, timeout=10.0):
            if request.full_url.endswith("/api/stream/event"):
                class _Empty:
                    def __iter__(self):
                        return iter([])
                    def close(self):
                        pass
                    def __enter__(self):
                        return self
                    def __exit__(self, *args):
                        return False
                return _Empty()
            if request.full_url.endswith("/api/board/seek"):
                captured_headers["Accept"] = request.get_header("Accept") or ""
                raise urllib.error.HTTPError(
                    request.full_url,
                    406,
                    "Not Acceptable",
                    {},
                    io.BytesIO(json.dumps({"error": "Not Acceptable"}).encode("utf-8")),
                )
            raise AssertionError(request.full_url)

        client = self._make_seek_client(opener_406)
        with self.assertRaisesRegex(ValueError, r"Lichess seek error \(406\)"):
            client.start_seek(LichessChallengeOptions(mode="seek", preset="Rapid 10+0"))
        self.assertIn("text/plain", captured_headers["Accept"])
        self.assertIn("application/json", captured_headers["Accept"])
        self.assertIn("application/x-ndjson", captured_headers["Accept"])
        self.assertIn("*/*", captured_headers["Accept"])

    def test_secure_credential_storage_migration_failure_and_logout(self):
        class _FakeProtector(CredentialProtector):
            scheme = "fake-enc"

            def __init__(self, fail_encrypt=False, fail_decrypt=False):
                self.fail_encrypt = fail_encrypt
                self.fail_decrypt = fail_decrypt

            def protect(self, plaintext: str) -> str:
                if self.fail_encrypt:
                    raise CredentialProtectionError("simulated encryption failure")
                return "ENC:" + plaintext[::-1]

            def unprotect(self, protected: str) -> str:
                if self.fail_decrypt or not protected.startswith("ENC:"):
                    raise CredentialProtectionError("simulated decryption failure")
                return protected[4:][::-1]

        with tempfile.TemporaryDirectory() as tmp:
            auth_path = Path(tmp) / "lichess_auth.json"
            secret = "lip_super_secret_token_xyz"
            acct = LichessAccount(user_id="nork79", username="Nork79", perfs={"rapid": 1800})
            ok_protector = _FakeProtector()

            # 1. Encrypted save must not store plaintext token on disk
            self.assertTrue(save_stored_auth(secret, account=acct, path=auth_path, protector=ok_protector))
            raw_on_disk = auth_path.read_text(encoding="utf-8")
            self.assertNotIn(secret, raw_on_disk)
            parsed = json.loads(raw_on_disk)
            self.assertEqual(parsed["version"], 2)
            self.assertEqual(parsed["token_scheme"], "fake-enc")

            loaded = load_stored_auth(auth_path, protector=ok_protector)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["token"], secret)
            self.assertEqual(loaded["account"]["username"], "Nork79")

            # 2. Failed encryption must NOT overwrite or delete existing valid credentials
            failing_protector = _FakeProtector(fail_encrypt=True)
            self.assertFalse(save_stored_auth("lip_new_token", account=acct, path=auth_path, protector=failing_protector))
            self.assertEqual(auth_path.read_text(encoding="utf-8"), raw_on_disk)

            # 3. Migration from legacy v1 plaintext file
            legacy_payload = {
                "version": 1,
                "token": secret,
                "server_url": "https://lichess.org",
                "client_id": "otbmaster3d",
                "account": acct.to_dict(),
            }
            auth_path.write_text(json.dumps(legacy_payload), encoding="utf-8")
            # Migration failure preserves original file
            loaded_no_mig = load_stored_auth(auth_path, protector=failing_protector)
            self.assertEqual(loaded_no_mig["token"], secret)
            self.assertIn(secret, auth_path.read_text(encoding="utf-8"))
            # Successful migration rewrites to v2 encrypted format
            loaded_mig = load_stored_auth(auth_path, protector=ok_protector)
            self.assertEqual(loaded_mig["token"], secret)
            self.assertNotIn(secret, auth_path.read_text(encoding="utf-8"))
            self.assertEqual(json.loads(auth_path.read_text(encoding="utf-8"))["version"], 2)

            # 4. Corrupted storage & decryption errors never log secrets and return None
            log_stream = io.StringIO()
            handler = logging.StreamHandler(log_stream)
            lichess_logger = logging.getLogger("otb_chess.services.lichess")
            lichess_logger.addHandler(handler)
            try:
                self.assertIsNone(load_stored_auth(auth_path, protector=_FakeProtector(fail_decrypt=True)))
                auth_path.write_text("{corrupt json", encoding="utf-8")
                self.assertIsNone(load_stored_auth(auth_path, protector=ok_protector))
            finally:
                lichess_logger.removeHandler(handler)
            self.assertNotIn(secret, log_stream.getvalue())

            # 5. Logout removes stored credentials
            self.assertTrue(save_stored_auth(secret, account=acct, path=auth_path, protector=ok_protector))
            client = LichessClient(token=secret, account=acct)
            client.logout(revoke_remote=False, path=auth_path)
            self.assertFalse(auth_path.exists())
            self.assertFalse(client.is_authenticated)

    @unittest.skipUnless(sys.platform == "win32", "Windows DPAPI test requires Windows")
    def test_windows_dpapi_protector_round_trip(self):
        protector = WindowsDPAPIProtector()
        secret = "lip_dpapi_roundtrip_12345"
        protected = protector.protect(secret)
        self.assertNotIn(secret, protected)
        self.assertEqual(protector.unprotect(protected), secret)
        with self.assertRaises(CredentialProtectionError):
            protector.unprotect("not-valid-dpapi!!!")

    def test_game_history_service_edge_cases(self):
        class _Resp:
            def __init__(self, text: str):
                self._bytes = text.encode("utf-8")
            def read(self):
                return self._bytes
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False

        # 1. Empty history
        client = LichessClient(opener=lambda req, timeout=10.0: _Resp(""))
        self.assertEqual(client.fetch_user_games("nork79"), [])

        # 2. Empty username
        with self.assertRaisesRegex(ValueError, "Enter a Lichess username"):
            client.fetch_user_games("")

        # 3. Invalid username (404)
        def opener_404(req, timeout=10.0):
            raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)

        client._opener = opener_404
        with self.assertRaisesRegex(ValueError, "was not found"):
            client.fetch_user_games("nonexistent_user_xyz")

        # 4. API connection failure
        def opener_conn_err(req, timeout=10.0):
            raise urllib.error.URLError("network down")

        client._opener = opener_conn_err
        with self.assertRaisesRegex(ValueError, "Could not connect"):
            client.fetch_user_games("nork79")

        # 5. Missing metadata, variant identification, and move counts (moves vs PGN fallback)
        ndjson = "\n".join([
            json.dumps({"id": "gMissingMeta"}),
            json.dumps({
                "id": "gVariant960",
                "variant": {"key": "chess960"},
                "moves": "e4 e5 Nf3 Nc6 Bb5",
                "players": {"white": {"user": {"name": "Alice"}}, "black": {"user": {"name": "Bob"}}},
            }),
            json.dumps({
                "id": "gPgnOnly",
                "variant": "crazyhouse",
                "pgn": '[Event "Test"]\n\n1. e4 e5 2. Nf3 Nc6 1-0\n',
            }),
        ])
        client._opener = lambda req, timeout=10.0: _Resp(ndjson)
        games = client.fetch_user_games("nork79")
        self.assertEqual(len(games), 3)
        self.assertEqual(games[0].date_label, "Unknown")
        self.assertEqual(games[0].white_name, "White")
        self.assertEqual(games[0].opening_label, "—")
        self.assertEqual(games[0].move_count, 0)
        self.assertTrue(games[0].is_supported_variant)

        self.assertEqual(games[1].variant, "chess960")
        self.assertFalse(games[1].is_supported_variant)
        self.assertEqual(games[1].ply_count, 5)
        self.assertEqual(games[1].move_count, 3)

        self.assertEqual(games[2].variant, "crazyhouse")
        self.assertFalse(games[2].is_supported_variant)
        self.assertEqual(games[2].move_count, 2)



class LichessUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configure_graphics()
        cls.qt = QApplication.instance() or QApplication([])

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        for attr, filename in (("CONFIG_PATH", "config.json"), ("LICHESS_AUTH_PATH", "lichess_auth.json")):
            p = patch.object(settings, attr, Path(self.folder.name) / filename)
            p.start()
            self.addCleanup(p.stop)
        for name in ("ENGINE_DIR", "BOOK_DIR"):
            p = patch.object(settings, name, Path(self.folder.name))
            p.start()
            self.addCleanup(p.stop)
            p_ui = patch(f"otb_chess.ui.desktop_ui.{name}", Path(self.folder.name))
            p_ui.start()
            self.addCleanup(p_ui.stop)
        evaluator = patch("otb_chess.ui.desktop_ui.PositionEvaluator")
        evaluator.start().return_value.poll.return_value = None
        self.addCleanup(evaluator.stop)
        self.window = MainWindow()
        self.window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        self.window.show()
        for _ in range(3):
            self.qt.processEvents()
        self.window.timer.stop()

    def tearDown(self):
        if shiboken6.isValid(self.window):
            self.window.close()
            self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.qt.processEvents()

    def test_lichess_menu_exists_and_updates_with_account_state(self):
        w = self.window
        menu_titles = [action.text() for action in w.menuBar().actions()]
        self.assertIn("Lichess", menu_titles)
        self.assertEqual(w.lichess_menu.status_action.text(), "Status: Not logged in")
        self.assertFalse(w.lichess_menu.logout_action.isEnabled())

        # Simulate login parameters applied to window
        w.lichess._opener = lambda req, timeout=10.0: _FakeHTTPResponse({
            "id": "testplayer",
            "username": "TestPlayer",
            "perfs": {"rapid": {"rating": 1750}, "blitz": {"rating": 1620}},
        })
        w.apply_lichess_login_parameters(LichessLoginParameters(
            server_url="https://lichess.org",
            client_id="otbmaster3d-test",
            token="lip_ui_test",
            username="TestPlayer",
        ))
        deadline = 200
        while w.lichess_verifying and deadline > 0:
            QTest.qWait(10)
            deadline -= 1
        w.tick()

        self.assertTrue(w.lichess.is_authenticated)
        self.assertIn("Signed in as TestPlayer", w.lichess_menu.status_action.text())
        self.assertIn("Rapid 1750", w.lichess_menu.status_action.text())
        self.assertTrue(w.lichess_menu.logout_action.isEnabled())
        self.assertEqual(w.game.cfg["lichess_username"], "TestPlayer")

        # Logout via menu action
        w.logout_lichess()
        self.assertFalse(w.lichess.is_authenticated)
        self.assertEqual(w.lichess_menu.status_action.text(), "Status: Not logged in")

    def test_lichess_login_dialog_accepts_parameters_and_authenticates(self):
        w = self.window
        w.lichess._opener = lambda req, timeout=10.0: _FakeHTTPResponse({
            "id": "dialoguser",
            "username": "DialogUser",
            "perfs": {"rapid": {"rating": 1900}},
        })
        dialog = LichessLoginDialog(w)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        dialog.show()
        self.qt.processEvents()

        dialog.findChild(QLineEdit, "lichessServerUrl").setText("https://lichess.org")
        dialog.findChild(QLineEdit, "lichessClientId").setText("custom-client-id")
        dialog.findChild(QLineEdit, "lichessUsername").setText("DialogUser")
        dialog.findChild(QLineEdit, "lichessToken").setText("lip_dialog_token")

        QTest.mouseClick(dialog.findChild(QPushButton, "lichessTokenLogin"), Qt.MouseButton.LeftButton)
        deadline = 200
        while dialog._busy and deadline > 0:
            QTest.qWait(10)
            self.qt.processEvents()
            deadline -= 1
        self.qt.processEvents()

        self.assertTrue(w.lichess.is_authenticated)
        self.assertEqual(w.lichess.account.username, "DialogUser")
        self.assertIn("Connected to Lichess as DialogUser", dialog.status_label.text())
        self.assertEqual(w.game.cfg["lichess_client_id"], "custom-client-id")
        dialog.close()
        dialog.deleteLater()

    def test_lichess_challenge_dialog_issues_player_challenge_and_has_no_ai_option(self):
        w = self.window
        w.lichess.token = "lip_mock_ui_token"
        w.lichess.account = LichessAccount(user_id="nork79", username="nork79")
        w.lichess_menu.refresh()
        self.assertTrue(w.lichess_menu.challenge_action.isEnabled())

        captured = []

        class _FakeEventStreamResponse:
            def __iter__(self):
                return iter([
                    (json.dumps({"type": "gameStart", "game": {"id": "gameFromDialog777"}}) + "\n").encode("utf-8")
                ])

            def close(self):
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        def fake_opener(req, timeout=10.0):
            if "/api/challenge/maia1" in req.full_url:
                captured.append((req.full_url, req.data.decode("utf-8") if req.data else ""))
                return _FakeHTTPResponse({"challenge": {"id": "gameFromDialog777", "status": "created"}})
            if "/api/stream/event" in req.full_url:
                return _FakeEventStreamResponse()
            return _FakeHTTPResponse({})

        w.lichess._opener = fake_opener

        dialog = LichessChallengeDialog(w)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        dialog.show()
        self.qt.processEvents()

        mode_combo = dialog.findChild(QComboBox, "lichessChallengeMode")
        preset_combo = dialog.findChild(QComboBox, "lichessTimeControlPreset")
        opponent_edit = dialog.findChild(QLineEdit, "lichessOpponentEdit")
        color_combo = dialog.findChild(QComboBox, "lichessColorCombo")

        # Verify Play vs Lichess AI (Stockfish) has been completely removed
        self.assertEqual(mode_combo.findData("ai"), -1)
        self.assertIsNone(dialog.findChild(QSpinBox, "lichessAiLevel"))

        mode_combo.setCurrentIndex(mode_combo.findData("player"))
        opponent_edit.setText("maia1")
        preset_combo.setCurrentText("Rapid 10+5")
        color_combo.setCurrentIndex(color_combo.findData("white"))
        self.qt.processEvents()

        QTest.mouseClick(dialog.submit_button, Qt.MouseButton.LeftButton)
        deadline = 200
        while dialog._busy and deadline > 0:
            QTest.qWait(10)
            self.qt.processEvents()
            deadline -= 1
        self.qt.processEvents()

        self.assertEqual(dialog.started_game_id, "gameFromDialog777")
        self.assertEqual(w.lichess_active_game_id, "gameFromDialog777")
        self.assertEqual(w.game.time_control_var.get(), "Rapid 10+5")
        self.assertEqual(w.game.cfg["lichess_time_control"], "Rapid 10+5")
        self.assertEqual(len(captured), 1)
        self.assertIn("/api/challenge/maia1", captured[0][0])
        self.assertIn("clock.limit=600", captured[0][1])
        self.assertIn("clock.increment=5", captured[0][1])
        dialog.close()
        dialog.deleteLater()

    def test_live_lichess_game_playback_clock_sync_and_fair_play_lock(self):
        import chess
        w = self.window
        g = w.game
        w.lichess.token = "lip_live_play_token"
        w.lichess.account = LichessAccount(user_id="nork79", username="nork79")
        w.lichess_active_game_id = "gamePlay999"

        # Enable analysis before online game starts to verify Fair Play lock & restore
        w.toggle_analysis(True)
        self.assertTrue(g.analysis_enabled)
        self.assertTrue(g.engine_enabled)

        sent_urls = []

        def fake_opener(req, timeout=10.0):
            sent_urls.append(req.full_url)
            return _FakeHTTPResponse({"ok": True})

        w.lichess._opener = fake_opener

        # 1. Receive gameFull where nork79 plays Black
        w.lichess_events.put((
            "stream_event",
            "gamePlay999",
            {
                "id": "gamePlay999",
                "type": "gameFull",
                "rated": False,
                "speed": "rapid",
                "initialFen": "startpos",
                "clock": {"initial": 600000, "increment": 5000},
                "white": {"id": "opponent1", "name": "OpponentOne", "rating": 1650},
                "black": {"id": "nork79", "name": "nork79", "rating": 1700},
                "state": {
                    "type": "gameState",
                    "moves": "e2e4",
                    "wtime": 600000,
                    "btime": 600000,
                    "winc": 5000,
                    "binc": 5000,
                    "status": "started",
                },
            },
        ))
        w.tick()

        # Verify orientation, PGN headers, clock labels, and Fair Play lock
        self.assertIsNotNone(g.online_session)
        self.assertTrue(g.online_session.active)
        self.assertEqual(g.board_facing, "black")
        self.assertEqual(len(g.board.move_stack), 1)
        self.assertEqual(g.board.turn, chess.BLACK)
        self.assertFalse(g.engine_enabled)
        self.assertFalse(g.analysis_enabled)
        self.assertFalse(w.analysis_button.isEnabled())
        self.assertFalse(w.analysis_action.isEnabled())
        self.assertFalse(w.play_button.isEnabled())
        self.assertEqual(w.play_button.text(), "Online game active")
        self.assertEqual(w.white_clock.engine_label.toolTip(), "Lichess · OpponentOne (1650)")
        self.assertEqual(w.black_clock.engine_label.toolTip(), "Lichess · nork79 (1700)")
        self.assertEqual(g._pgn_document.headers.get("White"), "OpponentOne")
        self.assertEqual(g._pgn_document.headers.get("Black"), "nork79")
        self.assertEqual(g._pgn_document.headers.get("WhiteElo"), "1650")
        self.assertEqual(g._pgn_document.headers.get("BlackElo"), "1700")

        # Attempting to enable analysis during active online play is blocked
        w.toggle_analysis(True)
        self.assertFalse(g.analysis_enabled)

        # 2. Local player (Black) makes a move: e7e5
        self.assertTrue(g.human_can_move())
        moved = g.try_move(chess.E7, chess.E5)
        self.assertTrue(moved)
        self.assertEqual(g.last_local_uci_move, "e7e5")

        deadline = 100
        while not any("/move/e7e5" in u for u in sent_urls) and deadline > 0:
            QTest.qWait(10)
            deadline -= 1
        w.tick()
        self.assertTrue(any("/api/board/game/gamePlay999/move/e7e5" in u for u in sent_urls))
        # Now it's White's turn, so local player (Black) cannot move White's pieces
        self.assertFalse(g.human_can_move())

        # 3. Opponent replies g1f3 and offers a draw via gameState
        w.lichess_events.put((
            "stream_event",
            "gamePlay999",
            {
                "type": "gameState",
                "moves": "e2e4 e7e5 g1f3",
                "wtime": 585000,
                "btime": 592000,
                "winc": 5000,
                "binc": 5000,
                "status": "started",
                "wdraw": True,
            },
        ))
        w.tick()
        self.assertEqual(len(g.board.move_stack), 3)
        self.assertAlmostEqual(g.white_time, 585.0, delta=1.0)
        self.assertAlmostEqual(g.black_time, 592.0, delta=1.0)
        self.assertTrue(g.online_session.opponent_offered_draw)
        self.assertEqual(w.game_status.text(), "Opponent Offered Draw")

        # 4. Accept draw via clock_actions["draw"]
        w.human_game_action("draw")
        deadline = 100
        while not any("/draw/yes" in u for u in sent_urls) and deadline > 0:
            QTest.qWait(10)
            deadline -= 1
        self.assertTrue(any("/api/board/game/gamePlay999/draw/yes" in u for u in sent_urls))

        # 5. Game ends on server -> Fair Play lock is released and analysis is restored
        w.lichess_events.put((
            "stream_event",
            "gamePlay999",
            {
                "type": "gameState",
                "moves": "e2e4 e7e5 g1f3",
                "wtime": 585000,
                "btime": 592000,
                "status": "draw",
            },
        ))
        w.tick()
        self.assertTrue(g.game_over)
        self.assertEqual(g._declared_result, "1/2-1/2")
        self.assertTrue(w.analysis_button.isEnabled())
        self.assertTrue(w.analysis_action.isEnabled())
        self.assertTrue(g.engine_enabled)
        self.assertTrue(g.analysis_enabled)

    def test_rated_game_end_immediately_updates_clock_and_menu_ratings(self):
        w = self.window
        g = w.game
        w.lichess.token = "lip_rated_token"
        w.lichess.account = LichessAccount(
            user_id="nork79",
            username="nork79",
            perfs={"rapid": 1700, "blitz": 1600},
        )
        w.lichess_menu.refresh()
        self.assertIn("Rapid 1700", w.lichess_menu.status_action.text())

        def fake_opener(req, timeout=10.0):
            if "/game/export/ratedGame888" in req.full_url:
                return _FakeHTTPResponse({
                    "id": "ratedGame888",
                    "rated": True,
                    "speed": "rapid",
                    "players": {
                        "white": {"rating": 1650, "ratingDiff": -7},
                        "black": {"rating": 1700, "ratingDiff": 8},
                    },
                })
            if req.full_url.endswith("/api/account"):
                return _FakeHTTPResponse({
                    "id": "nork79",
                    "username": "nork79",
                    "perfs": {
                        "rapid": {"rating": 1708},
                        "blitz": {"rating": 1600},
                        "bullet": {"rating": 1550},
                    },
                })
            return _FakeHTTPResponse({"ok": True})

        w.lichess._opener = fake_opener
        w.lichess_active_game_id = "ratedGame888"

        # 1. Start rated rapid game
        w.lichess_events.put((
            "stream_event",
            "ratedGame888",
            {
                "id": "ratedGame888",
                "type": "gameFull",
                "rated": True,
                "speed": "rapid",
                "initialFen": "startpos",
                "clock": {"initial": 600000, "increment": 0},
                "white": {"id": "opp1", "name": "OpponentOne", "rating": 1650},
                "black": {"id": "nork79", "name": "nork79", "rating": 1700},
                "state": {
                    "type": "gameState",
                    "moves": "f2f3 e7e5 g2g4",
                    "wtime": 595000,
                    "btime": 596000,
                    "status": "started",
                },
            },
        ))
        w.tick()
        self.assertEqual(w.white_clock.engine_label.toolTip(), "Lichess · OpponentOne (1650)")
        self.assertEqual(w.black_clock.engine_label.toolTip(), "Lichess · nork79 (1700)")

        # 2. Confirmed rated win for Black (mate)
        w.lichess_events.put((
            "stream_event",
            "ratedGame888",
            {
                "type": "gameState",
                "moves": "f2f3 e7e5 g2g4 d8h4",
                "wtime": 595000,
                "btime": 594000,
                "status": "mate",
                "winner": "black",
            },
        ))
        w.tick()

        # Wait for background rating refresh to complete and process_lichess_events to apply it
        deadline = 100
        while g.online_session.black_rating_diff is None and deadline > 0:
            QTest.qWait(10)
            w.tick()
            deadline -= 1

        self.assertEqual(g.online_session.white_rating, 1643)
        self.assertEqual(g.online_session.white_rating_diff, -7)
        self.assertEqual(g.online_session.black_rating, 1708)
        self.assertEqual(g.online_session.black_rating_diff, 8)
        self.assertEqual(w.white_clock.engine_label.toolTip(), "Lichess · OpponentOne (1643 -7)")
        self.assertEqual(w.black_clock.engine_label.toolTip(), "Lichess · nork79 (1708 +8)")
        self.assertEqual(g._pgn_document.headers.get("WhiteElo"), "1643")
        self.assertEqual(g._pgn_document.headers.get("BlackElo"), "1708")
        self.assertIn("Rapid 1708", w.lichess_menu.status_action.text())
        self.assertIn("Bullet 1550", w.lichess_menu.status_action.text())

    def test_premove_one_move_right_click_abort_and_auto_execution(self):
        import chess
        w = self.window
        g = w.game
        w.lichess.token = "lip_premove_token"
        w.lichess.account = LichessAccount(user_id="nork79", username="nork79")
        w.lichess_active_game_id = "premoveGame555"

        sent_urls = []

        def fake_opener(req, timeout=10.0):
            sent_urls.append(req.full_url)
            return _FakeHTTPResponse({"ok": True})

        w.lichess._opener = fake_opener

        # Start online game where nork79 plays Black and it is White's turn (before move 1)
        w.lichess_events.put((
            "stream_event",
            "premoveGame555",
            {
                "id": "premoveGame555",
                "type": "gameFull",
                "rated": False,
                "speed": "bullet",
                "initialFen": "startpos",
                "clock": {"initial": 60000, "increment": 0},
                "white": {"id": "opp1", "name": "OpponentOne", "rating": 1600},
                "black": {"id": "nork79", "name": "nork79", "rating": 1620},
                "state": {
                    "type": "gameState",
                    "moves": "",
                    "wtime": 60000,
                    "btime": 60000,
                    "status": "started",
                },
            },
        ))
        w.tick()

        # It is White's turn, so Black (nork79) cannot move yet, but CAN premove
        self.assertFalse(g.human_can_move())
        self.assertTrue(g.human_can_premove())
        self.assertEqual(g.human_premove_color(), chess.BLACK)

        # Illegal premove geometry (e.g. Knight b8 to b5) is rejected
        self.assertFalse(g.set_premove(chess.B8, chess.B5))
        self.assertIsNone(g.premove)

        # Valid premove (e7 -> e5) is stored and visually moves the piece to e5 in rendered_piece_map()
        self.assertTrue(g.set_premove(chess.E7, chess.E5))
        self.assertEqual(g.premove, (chess.E7, chess.E5, None))
        rendered = g.rendered_piece_map()
        self.assertNotIn(chess.E7, rendered)
        self.assertIn(chess.E5, rendered)
        self.assertEqual(rendered[chess.E5].piece_type, chess.PAWN)
        self.assertEqual(rendered[chess.E5].color, chess.BLACK)

        # Setting a second premove replaces the first (1-move premove limit) and updates rendered outcome
        self.assertTrue(g.set_premove(chess.B8, chess.C6))
        self.assertEqual(g.premove, (chess.B8, chess.C6, None))
        rendered = g.rendered_piece_map()
        self.assertIn(chess.E7, rendered)
        self.assertNotIn(chess.B8, rendered)
        self.assertEqual(rendered[chess.C6].piece_type, chess.KNIGHT)

        # Right-clicking on the board aborts the premove and restores the original piece positions
        QTest.mouseClick(w.board_widget, Qt.MouseButton.RightButton)
        self.assertIsNone(g.premove)
        rendered = g.rendered_piece_map()
        self.assertIn(chess.B8, rendered)
        self.assertNotIn(chess.C6, rendered)

        # Queue premove e7 -> e5 again before White moves
        self.assertTrue(g.set_premove(chess.E7, chess.E5))
        self.assertEqual(g.premove, (chess.E7, chess.E5, None))

        # White plays e2e4 -> Black's premove e7e5 executes immediately and is sent to Lichess
        w.lichess_events.put((
            "stream_event",
            "premoveGame555",
            {
                "type": "gameState",
                "moves": "e2e4",
                "wtime": 59500,
                "btime": 60000,
                "status": "started",
            },
        ))
        w.tick()

        self.assertIsNone(g.premove)
        self.assertEqual([g.position.uci(m) for m in g.position.moves], ["e2e4", "e7e5"])
        deadline = 100
        while not any("/move/e7e5" in u for u in sent_urls) and deadline > 0:
            QTest.qWait(10)
            deadline -= 1
        self.assertTrue(any("/api/board/game/premoveGame555/move/e7e5" in u for u in sent_urls))

    def test_engine_minimum_thinking_time_setting_and_move_delay(self):
        import chess
        import time
        from otb_chess_core import Move
        from otb_chess.engine_state import EngineResult
        w = self.window
        g = w.game

        def interact():
            dialog = self.qt.activeModalWidget()
            self.assertIsNotNone(dialog)
            spin = dialog.findChild(QDoubleSpinBox, "engineMinThinkingTime")
            self.assertIsNotNone(spin)
            # Ensure right-side arrow subcontrols are not covered by internal lineEdit
            self.assertGreaterEqual(spin.width() - spin.lineEdit().geometry().right(), 45)
            spin.setFocus()
            QTest.keyClick(spin, Qt.Key.Key_Up)
            self.assertAlmostEqual(spin.value(), 0.5)
            QTest.keyClick(spin, Qt.Key.Key_Down)
            self.assertAlmostEqual(spin.value(), 0.0)
            spin.setValue(0.3)
            dialog.accept()

        QTimer.singleShot(0, interact)
        w.engine_settings()
        self.assertAlmostEqual(g.cfg["engine_min_thinking_seconds"], 0.3)

        # Verify EngineManager passes seconds=max(0.12, min_think) and apply_pending_engine_move waits
        recorded_seconds = []

        class _FakeEngine:
            def configure_strength(self, elo=None):
                pass

            def play(self, position, seconds=0.12, style="Balanced"):
                recorded_seconds.append(seconds)
                return EngineResult(Move(chess.E7, chess.E5), None, None)

        g.start_game()
        g.engine_enabled = True
        g.engine_side = chess.BLACK
        g.engine_manager.engine = _FakeEngine()
        g.engine_manager.loaded_configuration = {"engine_id": "stockfish"}

        # White plays e2e4 -> triggers maybe_request_engine_move()
        self.assertTrue(g.try_move(chess.E2, chess.E4))
        deadline = 100
        while g.pending_engine_move is None and deadline > 0:
            QTest.qWait(10)
            deadline -= 1
        self.assertEqual(recorded_seconds, [0.3])
        self.assertIsNotNone(g.pending_engine_move)

        # Calling apply_pending_engine_move before 0.3s has elapsed must wait (not apply yet)
        g.pending_engine_ready_at = time.perf_counter() + 1.0
        g.apply_pending_engine_move()
        self.assertEqual(len(g.board.move_stack), 1)
        self.assertIsNotNone(g.pending_engine_move)

        # Once the minimum thinking time has elapsed, apply_pending_engine_move plays the move
        g.pending_engine_ready_at = time.perf_counter() - 0.01
        g.apply_pending_engine_move()
        self.assertEqual(len(g.board.move_stack), 2)
        self.assertIsNone(g.pending_engine_move)
        g.engine_manager.engine = None

    def test_fetch_online_bots_and_challenge_dialog_bot_dropdown(self):
        from PySide6.QtCore import QBuffer, QIODevice
        from PySide6.QtGui import QPixmap, QColor
        from PySide6.QtWidgets import QFrame, QLabel, QTextBrowser

        w = self.window
        w.lichess.token = "lip_bot_list_token"
        w.lichess.account = LichessAccount(user_id="nork79", username="nork79")

        # Create a valid 16x16 PNG in memory to simulate Lichess flair/flag/avatar assets
        sample_pm = QPixmap(16, 16)
        sample_pm.fill(QColor("#80bfab"))
        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        sample_pm.save(buf, "PNG")
        sample_png_bytes = bytes(buf.data())

        ndjson_bots = "\n".join([
            json.dumps({
                "id": "maia1",
                "username": "maia1",
                "title": "BOT",
                "patron": True,
                "flair": "smileys.robot",
                "profile": {
                    "bio": "Maia 1 is a human-like neural network chess engine trained on 1100-rated Lichess games.",
                    "realName": "CSSLab / University of Toronto",
                    "location": "Toronto",
                    "flag": "CA",
                    "links": "https://maiachess.com\nhttps://github.com/CSSLab/maia-chess",
                },
                "count": {"all": 500000, "win": 250000, "loss": 220000, "draw": 30000},
                "perfs": {
                    "bullet": {"rating": 1520, "games": 120000},
                    "blitz": {"rating": 1480, "games": 210000},
                    "rapid": {"rating": 1440, "games": 170000},
                },
            }),
            json.dumps({
                "id": "leelachess",
                "username": "LeelaChess",
                "title": "BOT",
                "flair": "activity.chess-pawn",
                "profile": {
                    "bio": "LCZero neural network bot.",
                    "realName": "LCZero Team",
                    "country": "US",
                },
                "perfs": {
                    "bullet": {"rating": 2650},
                    "blitz": {"rating": 2590},
                    "rapid": {"rating": 2510},
                    "classical": {"rating": 2430},
                },
            }),
        ])

        class _FakeRawBytesResponse:
            def __init__(self, data: bytes):
                self._data = data

            def read(self):
                return self._data

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        asset_requests = []

        def fake_opener(req, timeout=10.0):
            if "/api/bot/online" in req.full_url:
                return _FakeRawBytesResponse(ndjson_bots.encode("utf-8"))
            if any(ext in req.full_url for ext in (".webp", ".png")):
                asset_requests.append(req.full_url)
                return _FakeRawBytesResponse(sample_png_bytes)
            return _FakeHTTPResponse({})

        w.lichess._opener = fake_opener

        # 1. Verify LichessClient.fetch_online_bots, rich profile parsing, and format_bot_summary
        bots = w.lichess.fetch_online_bots()
        self.assertEqual(len(bots), 2)
        self.assertEqual(bots[0].bio, "Maia 1 is a human-like neural network chess engine trained on 1100-rated Lichess games.")
        self.assertEqual(bots[0].flair, "smileys.robot")
        self.assertEqual(bots[0].country, "CA")
        self.assertIn("flair", bots[0].asset_urls())
        self.assertIn("flag", bots[0].asset_urls())
        self.assertIn("avatar", bots[0].asset_urls())
        self.assertEqual(format_bot_summary(bots[0]), "maia1")
        self.assertEqual(format_bot_summary(bots[1]), "LeelaChess")

        # 2. Verify LichessChallengeDialog populates Online Bots dropdown and opens the Bot Profile & Assets pane
        dialog = LichessChallengeDialog(w)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        dialog.show()
        self.qt.processEvents()

        mode_combo = dialog.findChild(QComboBox, "lichessChallengeMode")
        bot_combo = dialog.findChild(QComboBox, "lichessOnlineBotCombo")
        opponent_edit = dialog.findChild(QLineEdit, "lichessOpponentEdit")
        bot_pane = dialog.findChild(QFrame, "lichessBotDetailsPane")
        bot_title = dialog.findChild(QLabel, "lichessBotTitle")
        bot_desc = dialog.findChild(QTextBrowser, "lichessBotDescription")
        bot_avatar = dialog.findChild(QLabel, "lichessBotAvatar")
        bot_flair = dialog.findChild(QLabel, "lichessBotFlairAsset")
        bot_flag = dialog.findChild(QLabel, "lichessBotFlagAsset")
        self.assertIsNotNone(bot_combo)
        self.assertIsNotNone(bot_pane)
        self.assertTrue(bot_pane.isVisible())

        deadline = 100
        while (dialog._loading_bots or bot_combo.count() < 3) and deadline > 0:
            QTest.qWait(10)
            self.qt.processEvents()
            deadline -= 1

        self.assertEqual(bot_combo.count(), 3)
        self.assertEqual(bot_combo.itemText(1), "maia1")
        self.assertEqual(bot_combo.itemData(1), "maia1")
        self.assertEqual(bot_combo.itemText(2), "LeelaChess")
        self.assertEqual(bot_combo.itemData(2), "LeelaChess")

        # 3. Selecting a bot populates Opponent Username and displays its description & Lichess assets in the pane
        bot_combo.setCurrentIndex(1)
        deadline = 100
        while "maia1" not in dialog._bot_assets_cache and deadline > 0:
            QTest.qWait(10)
            self.qt.processEvents()
            deadline -= 1
        self.qt.processEvents()

        self.assertEqual(opponent_edit.text(), "maia1")
        self.assertEqual(dialog.current_options().opponent_username, "maia1")
        self.assertTrue(bot_pane.isVisible())
        self.assertIn("BOT maia1", bot_title.text())
        self.assertIn("Patron", bot_title.text())
        self.assertIn("human-like neural network chess engine", bot_desc.toPlainText())
        self.assertIn("maiachess.com", bot_desc.toPlainText())
        self.assertFalse(bot_avatar.pixmap().isNull())
        self.assertTrue(bot_flair.isVisible())
        self.assertFalse(bot_flair.pixmap().isNull())
        self.assertTrue(bot_flag.isVisible())
        self.assertFalse(bot_flag.pixmap().isNull())
        self.assertTrue(any("smileys.robot.webp" in u for u in asset_requests))
        self.assertTrue(any("CA.png" in u for u in asset_requests))

        dialog.close()
        dialog.deleteLater()

    def test_lichess_game_history_fetch_and_load_into_board(self):
        from PySide6.QtWidgets import QTableWidget
        from otb_chess.ui.lichess_dialog import LichessHistoryDialog

        w = self.window
        w.lichess.token = "lip_history_token"
        w.lichess.account = LichessAccount(user_id="nork79", username="nork79")

        sample_pgn = (
            '[Event "Rated Rapid game"]\n'
            '[Site "https://lichess.org/histGame01"]\n'
            '[White "nork79"]\n'
            '[Black "OpponentTwo"]\n'
            '[Result "1-0"]\n'
            '[WhiteElo "1750"]\n'
            '[BlackElo "1720"]\n\n'
            '1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0\n'
        )
        ndjson_games = "\n".join([
            json.dumps({
                "id": "histGame01",
                "rated": True,
                "variant": "standard",
                "speed": "rapid",
                "perf": "rapid",
                "createdAt": 1700000000000,
                "status": "resign",
                "winner": "white",
                "players": {
                    "white": {"user": {"id": "nork79", "name": "nork79"}, "rating": 1750},
                    "black": {"user": {"id": "opponenttwo", "name": "OpponentTwo"}, "rating": 1720},
                },
                "opening": {"eco": "C70", "name": "Ruy Lopez: Morphy Defense"},
                "moves": "e4 e5 Nf3 Nc6 Bb5 a6",
                "pgn": sample_pgn,
            }),
            json.dumps({
                "id": "histGame02",
                "rated": False,
                "variant": "standard",
                "speed": "blitz",
                "perf": "blitz",
                "createdAt": 1699990000000,
                "status": "draw",
                "players": {
                    "white": {"user": {"id": "alice", "name": "Alice"}, "rating": 1610},
                    "black": {"user": {"id": "nork79", "name": "nork79"}, "rating": 1640},
                },
                "opening": {"eco": "B20", "name": "Sicilian Defense"},
                "moves": "e4 c5",
                "pgn": '[White "Alice"]\n[Black "nork79"]\n[Result "1/2-1/2"]\n\n1. e4 c5 1/2-1/2\n',
            }),
        ])

        class _FakeHistoryResponse:
            def read(self):
                return ndjson_games.encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        requested_urls = []

        def fake_opener(req, timeout=10.0):
            requested_urls.append(req.full_url)
            if "/api/games/user/nork79" in req.full_url:
                return _FakeHistoryResponse()
            return _FakeHTTPResponse({})

        w.lichess._opener = fake_opener

        # 1. Verify LichessClient.fetch_user_games
        games = w.lichess.fetch_user_games("nork79", max_games=15, perf_type="rapid", rated=True)
        self.assertEqual(len(games), 2)
        self.assertEqual(games[0].game_id, "histGame01")
        self.assertEqual(games[0].result_label, "1-0")
        self.assertEqual(games[0].opening_label, "C70 Ruy Lopez: Morphy Defense")
        self.assertEqual(games[0].side_label(True), "nork79 (1750)")
        self.assertIn("perfType=rapid", requested_urls[-1])
        self.assertIn("rated=true", requested_urls[-1])
        self.assertIn("pgnInJson=true", requested_urls[-1])

        # 2. Verify LichessHistoryDialog populates table and loads selected game onto the board
        self.assertTrue(w.lichess_menu.history_action.isEnabled())
        dialog = LichessHistoryDialog(w)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        dialog.show()
        self.qt.processEvents()

        table = dialog.findChild(QTableWidget, "lichessHistoryTable")
        self.assertIsNotNone(table)
        deadline = 100
        while (dialog._busy or table.rowCount() < 2) and deadline > 0:
            QTest.qWait(10)
            self.qt.processEvents()
            deadline -= 1

        self.assertEqual(table.rowCount(), 2)
        self.assertEqual(table.item(0, 1).text(), "Rapid")
        self.assertEqual(table.item(0, 2).text(), "nork79 (1750)")
        self.assertEqual(table.item(0, 3).text(), "OpponentTwo (1720)")
        self.assertEqual(table.item(0, 4).text(), "1-0")
        self.assertEqual(table.item(0, 5).text(), "3")
        self.assertEqual(table.item(0, 6).text(), "C70 Ruy Lopez: Morphy Defense")

        table.selectRow(0)
        QTest.mouseClick(dialog.load_button, Qt.MouseButton.LeftButton)
        self.qt.processEvents()

        self.assertEqual(dialog.loaded_game_id, "histGame01")
        self.assertEqual([w.game.position.uci(m) for m in w.game.position.moves], ["e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6"])
        self.assertEqual(w.game._pgn_document.headers.get("White"), "nork79")
        self.assertEqual(w.game._pgn_document.headers.get("Black"), "OpponentTwo")
        dialog.deleteLater()

    def test_lichess_game_history_pgn_fallback_error_handling_and_variant_rejection(self):
        w = self.window
        w.lichess = LichessClient(
            token="lip_hist_ui",
            account=LichessAccount(user_id="nork79", username="nork79"),
        )
        exported_pgn = '[Event "Exported"]\n[White "nork79"]\n[Black "BotFriend"]\n\n1. d4 d5 2. c4 *\n'

        class _TextResponse:
            def __init__(self, text: str):
                self._bytes = text.encode("utf-8")

            def read(self):
                return self._bytes

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        mode = "ok"

        def fake_opener(req, timeout=10.0):
            if mode == "fail_list":
                raise urllib.error.URLError("list failed")
            if "/api/games/user/" in req.full_url:
                return _TextResponse("\n".join([
                    json.dumps({
                        "id": "noPgnFallback",
                        "variant": "standard",
                        "moves": "d4 d5 c4",
                        "players": {"white": {"user": {"name": "nork79"}}, "black": {"user": {"name": "BotFriend"}}},
                    }),
                    json.dumps({
                        "id": "crazyVariantGame",
                        "variant": "crazyhouse",
                        "moves": "e4 e5",
                        "pgn": '[Event "Crazy"]\n\n1. e4 e5 *\n',
                        "players": {"white": {"user": {"name": "nork79"}}, "black": {"user": {"name": "VariantBot"}}},
                    }),
                    json.dumps({
                        "id": "emptyPgnGame",
                        "variant": "standard",
                        "players": {"white": {"user": {"name": "nork79"}}, "black": {"user": {"name": "EmptyBot"}}},
                    }),
                ]))
            if "/game/export/noPgnFallback" in req.full_url:
                if mode == "fail_pgn":
                    raise urllib.error.URLError("export failed")
                return _TextResponse(exported_pgn)
            if "/game/export/emptyPgnGame" in req.full_url:
                return _TextResponse("")
            raise AssertionError(req.full_url)

        w.lichess._opener = fake_opener

        # 1. API failure on initial fetch updates status label and keeps controls enabled
        mode = "fail_list"
        dialog = LichessHistoryDialog(w)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        dialog.show()
        deadline = 100
        while dialog._busy and deadline > 0:
            QTest.qWait(10)
            self.qt.processEvents()
            deadline -= 1
        self.assertIn("Could not connect", dialog.status_label.text())
        self.assertTrue(dialog.fetch_button.isEnabled())

        # 2. Successful fetch populates table
        mode = "ok"
        dialog.fetch_games()
        table = dialog.findChild(QTableWidget, "lichessHistoryTable")
        deadline = 100
        while (dialog._busy or table.rowCount() < 3) and deadline > 0:
            QTest.qWait(10)
            self.qt.processEvents()
            deadline -= 1
        self.assertEqual(table.rowCount(), 3)

        # 3. Unsupported variant is rejected with warning and does not replace board
        table.selectRow(1)
        with patch.object(QMessageBox, "warning") as warn_mock:
            dialog.load_selected_game()
            warn_mock.assert_called_once()
            self.assertIn("Unsupported Variant", warn_mock.call_args.args[1])

        # 4. Missing/empty PGN shows warning
        table.selectRow(2)
        with patch.object(QMessageBox, "warning") as warn_mock:
            dialog.load_selected_game()
            deadline = 100
            while dialog._busy and deadline > 0:
                QTest.qWait(10)
                self.qt.processEvents()
                deadline -= 1
            warn_mock.assert_called_once()

        # 5. PGN export failure shows status error
        mode = "fail_pgn"
        table.selectRow(0)
        dialog.load_selected_game()
        deadline = 100
        while dialog._busy and deadline > 0:
            QTest.qWait(10)
            self.qt.processEvents()
            deadline -= 1
        self.assertIn("Could not connect", dialog.status_label.text())

        # 6. PGN fallback succeeds when export returns valid PGN
        mode = "ok"
        dialog.load_selected_game()
        deadline = 100
        while dialog._busy and deadline > 0:
            QTest.qWait(10)
            self.qt.processEvents()
            deadline -= 1
        self.assertEqual(dialog.loaded_game_id, "noPgnFallback")
        self.assertEqual([w.game.position.uci(m) for m in w.game.position.moves], ["d2d4", "d7d5", "c2c4"])
        dialog.deleteLater()


if __name__ == "__main__":
    unittest.main()
