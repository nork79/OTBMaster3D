"""Lichess authentication, login parameters, OAuth2 PKCE flow and token storage."""

import argparse
import base64
from dataclasses import dataclass, field
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import logging
import os
from pathlib import Path
import secrets
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

from otb_chess.services import settings
from otb_chess.version import __version__

log = logging.getLogger(__name__)

LICHESS_SCOPES = "board:play challenge:read challenge:write"

# Common time controls from settings.TIME_CONTROLS.
# Direct challenges (/api/challenge/*) accept Hyperbullet, Bullet, Blitz, Rapid, and Classical.
# Lobby seeks (/api/board/seek) on the Lichess Board API only accept Rapid and Classical (>= 480s estimated).
LICHESS_CHALLENGE_PRESETS = (
    "Hyperbullet 15+0",
    "Hyperbullet 20+0",
    "Hyperbullet 30+0",
    "Hyperbullet 30+1",
    "Bullet 1+0",
    "Bullet 1+1",
    "Bullet 2+0",
    "Bullet 2+1",
    "Blitz 3+0",
    "Blitz 3+2",
    "Blitz 5+0",
    "Blitz 5+3",
    "Rapid 10+0",
    "Rapid 10+5",
    "Rapid 15+10",
    "Rapid 20+0",
    "Classical 30+0",
    "Classical 30+20",
    "Classical 45+15",
    "Classical 60+0",
    "Classical 60+30",
    "Classical 90+30",
)

LICHESS_SEEK_PRESETS = (
    "Rapid 10+0",
    "Rapid 10+5",
    "Rapid 15+10",
    "Rapid 20+0",
    "Classical 30+0",
    "Classical 30+20",
    "Classical 45+15",
    "Classical 60+0",
    "Classical 60+30",
    "Classical 90+30",
)


@dataclass(frozen=True)
class LichessChallengeOptions:
    mode: str = "ai"  # "ai", "player", or "seek"
    preset: str = "Rapid 10+0"  # Preset name from TIME_CONTROLS or "Custom"
    custom_minutes: int = 10
    custom_increment: int = 0
    color: str = "random"  # "random", "white", "black"
    rated: bool = False
    opponent_username: str = ""
    ai_level: int = 3  # 1..8

    def resolve_clock(self) -> tuple[int, int]:
        """Return (limit_seconds, increment_seconds) and validate against Lichess API rules."""
        if self.preset != "Custom":
            tc = settings.TIME_CONTROLS.get(self.preset)
            if tc is None or tc.initial_seconds <= 0:
                raise ValueError(f"Unsupported time control preset: {self.preset}")
            limit_sec = int(round(tc.initial_seconds))
            inc_sec = int(round(tc.increment_seconds))
        else:
            if self.custom_minutes < 1 or self.custom_minutes > 180:
                raise ValueError("Custom initial time must be between 1 and 180 minutes.")
            if self.custom_increment < 0 or self.custom_increment > 180:
                raise ValueError("Custom increment must be between 0 and 180 seconds.")
            limit_sec = int(self.custom_minutes) * 60
            inc_sec = int(self.custom_increment)

        estimated = limit_sec + 40 * inc_sec
        if self.mode == "seek" and (estimated < 480 or limit_sec < 60):
            raise ValueError(
                "Lichess Quick Pairing (Lobby Seek) only accepts Rapid or Classical time controls "
                "(at least 8 minutes estimated duration, e.g. Rapid 10+0 or slower)."
            )
        return limit_sec, inc_sec

    def normalized_color(self) -> str:
        c = (self.color or "random").strip().lower()
        if c not in ("random", "white", "black"):
            raise ValueError("Color must be random, white, or black.")
        return c

    def to_challenge_payload(self) -> dict[str, str]:
        limit_sec, inc_sec = self.resolve_clock()
        color = self.normalized_color()
        if self.mode == "ai":
            if not (1 <= int(self.ai_level) <= 8):
                raise ValueError("Lichess AI level must be between 1 and 8.")
            return {
                "level": str(int(self.ai_level)),
                "clock.limit": str(limit_sec),
                "clock.increment": str(inc_sec),
                "color": color,
                "variant": "standard",
            }
        if self.mode == "player":
            opponent = (self.opponent_username or "").strip()
            if not opponent:
                raise ValueError("Enter a Lichess username to challenge.")
            return {
                "rated": "true" if self.rated else "false",
                "clock.limit": str(limit_sec),
                "clock.increment": str(inc_sec),
                "color": color,
                "variant": "standard",
            }
        if self.mode == "seek":
            minutes_str = str(limit_sec // 60) if limit_sec % 60 == 0 else f"{limit_sec / 60:g}"
            return {
                "rated": "true" if self.rated else "false",
                "time": minutes_str,
                "increment": str(inc_sec),
                "color": color,
                "variant": "standard",
            }
        raise ValueError(f"Unknown challenge mode: {self.mode}")


def _format_player_info(side_data: dict) -> tuple[str, str, int | None]:
    """Return (user_id, display_name, rating) from Lichess gameFull white/black object."""
    if not isinstance(side_data, dict):
        return "", "Anonymous", None
    if side_data.get("aiLevel"):
        level = int(side_data["aiLevel"])
        return f"ai_{level}", f"Stockfish Level {level}", None
    user_id = str(side_data.get("id") or side_data.get("name") or "").strip().lower()
    name = str(side_data.get("name") or side_data.get("id") or "Anonymous").strip()
    title = str(side_data.get("title") or "").strip()
    display = f"{title} {name}".strip() if title else name
    rating = side_data.get("rating")
    return user_id, display, int(rating) if isinstance(rating, int) else None


@dataclass
class LichessGameSession:
    game_id: str
    my_color: bool | None  # True = White, False = Black, None = Spectator
    white_id: str = ""
    black_id: str = ""
    white_name: str = "White"
    black_name: str = "Black"
    white_rating: int | None = None
    black_rating: int | None = None
    white_rating_diff: int | None = None
    black_rating_diff: int | None = None
    rated: bool = False
    initial_fen: str = "startpos"
    speed: str = "rapid"
    status: str = "started"
    winner: str | None = None
    wdraw: bool = False
    bdraw: bool = False
    wtakeback: bool = False
    btakeback: bool = False
    move_in_flight: bool = False
    ratings_refreshed: bool = False

    @property
    def active(self) -> bool:
        return self.status in ("created", "started")

    @property
    def opponent_offered_draw(self) -> bool:
        if self.my_color is None:
            return False
        return self.bdraw if self.my_color else self.wdraw

    @property
    def opponent_proposed_takeback(self) -> bool:
        if self.my_color is None:
            return False
        return self.btakeback if self.my_color else self.wtakeback

    def clock_label(self, color: bool) -> str:
        name = self.white_name if color else self.black_name
        rating = self.white_rating if color else self.black_rating
        diff = self.white_rating_diff if color else self.black_rating_diff
        if rating is not None:
            diff_text = f" {diff:+d}" if isinstance(diff, int) and diff != 0 else ""
            tag = f"{name} ({rating}{diff_text})"
        else:
            tag = name
        return f"Lichess · {tag}"

    @classmethod
    def from_game_full(cls, event: dict, my_username: str = "") -> "LichessGameSession":
        game_id = str(event.get("id") or "").strip()
        white_id, white_name, white_rating = _format_player_info(event.get("white") or {})
        black_id, black_name, black_rating = _format_player_info(event.get("black") or {})
        me = (my_username or "").strip().lower()
        my_color: bool | None = None
        if me and white_id == me:
            my_color = True
        elif me and black_id == me:
            my_color = False
        elif white_id.startswith("ai_"):
            my_color = False
        elif black_id.startswith("ai_"):
            my_color = True
        else:
            my_color = True
        state = event.get("state") if isinstance(event.get("state"), dict) else event
        return cls(
            game_id=game_id,
            my_color=my_color,
            white_id=white_id,
            black_id=black_id,
            white_name=white_name,
            black_name=black_name,
            white_rating=white_rating,
            black_rating=black_rating,
            rated=bool(event.get("rated", False)),
            initial_fen=str(event.get("initialFen") or "startpos"),
            speed=str(event.get("speed") or "rapid"),
            status=str(state.get("status") or "started"),
            winner=state.get("winner"),
            wdraw=bool(state.get("wdraw", False)),
            bdraw=bool(state.get("bdraw", False)),
            wtakeback=bool(state.get("wtakeback", False)),
            btakeback=bool(state.get("btakeback", False)),
        )


def format_lichess_termination(status: str, winner: str | None) -> tuple[str, str]:
    """Map Lichess gameState status and winner to (result_text, pgn_result)."""
    win_color = "White" if winner == "white" else "Black" if winner == "black" else None
    lose_color = "Black" if winner == "white" else "White" if winner == "black" else None
    pgn = "1-0" if winner == "white" else "0-1" if winner == "black" else "1/2-1/2"
    if status == "mate" and win_color:
        return f"Checkmate - {win_color} wins", pgn
    if status == "resign" and lose_color and win_color:
        return f"{lose_color} resigned - {win_color} wins", pgn
    if status in ("outoftime", "timeout") and win_color:
        return f"{win_color} wins on time", pgn
    if status == "stalemate":
        return "Stalemate", "1/2-1/2"
    if status == "draw":
        return "Draw - agreement or repetition", "1/2-1/2"
    if status in ("aborted", "noStart"):
        return "Game aborted on Lichess", "*"
    if status == "cheat" and win_color:
        return f"{win_color} wins (fair play violation)", pgn
    if win_color:
        return f"{win_color} wins ({status})", pgn
    return f"Draw - {status}", "1/2-1/2"


@dataclass
class LichessAccount:
    user_id: str
    username: str
    title: str = ""
    perfs: dict[str, int] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        return f"{self.title} {self.username}".strip() if self.title else self.username

    @classmethod
    def from_api(cls, payload: dict) -> "LichessAccount":
        if not isinstance(payload, dict) or not payload.get("username"):
            raise ValueError("Invalid Lichess account response.")
        username = str(payload["username"])
        user_id = str(payload.get("id") or username.lower())
        title = str(payload.get("title") or "")
        perfs = {}
        raw_perfs = payload.get("perfs")
        if isinstance(raw_perfs, dict):
            for key, info in raw_perfs.items():
                if isinstance(info, dict) and isinstance(info.get("rating"), int):
                    perfs[str(key)] = int(info["rating"])
        return cls(user_id=user_id, username=username, title=title, perfs=perfs)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "title": self.title,
            "perfs": dict(self.perfs),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LichessAccount":
        return cls(
            user_id=str(data.get("user_id") or data.get("username", "").lower()),
            username=str(data["username"]),
            title=str(data.get("title") or ""),
            perfs={str(k): int(v) for k, v in (data.get("perfs") or {}).items() if isinstance(v, int)},
        )


@dataclass
class LichessLoginParameters:
    server_url: str = settings.DEFAULT_LICHESS_URL
    client_id: str = settings.DEFAULT_LICHESS_CLIENT_ID
    token: str = ""
    username: str = ""

    def normalized_url(self) -> str:
        url = (self.server_url or settings.DEFAULT_LICHESS_URL).strip().rstrip("/")
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("https", "http") or not parsed.netloc:
            raise ValueError("Lichess server URL must start with https:// or http://.")
        return url

    def normalized_client_id(self) -> str:
        cid = (self.client_id or settings.DEFAULT_LICHESS_CLIENT_ID).strip()
        if not cid:
            raise ValueError("Client ID cannot be empty.")
        return cid

    def normalized_token(self) -> str:
        return (self.token or "").strip()


def parse_cli_login_args(argv=None) -> tuple[LichessLoginParameters | None, list[str]]:
    """Extract optional Lichess CLI login parameters while preserving remaining args."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--lichess-token", default=None)
    parser.add_argument("--lichess-url", default=None)
    parser.add_argument("--lichess-client-id", default=None)
    parser.add_argument("--lichess-username", default=None)
    known, remaining = parser.parse_known_args(argv)
    env_token = os.environ.get("LICHESS_TOKEN") or os.environ.get("OTB_LICHESS_TOKEN")
    env_url = os.environ.get("LICHESS_URL")
    env_client_id = os.environ.get("LICHESS_CLIENT_ID")
    token = known.lichess_token if known.lichess_token is not None else env_token
    url = known.lichess_url if known.lichess_url is not None else env_url
    client_id = known.lichess_client_id if known.lichess_client_id is not None else env_client_id
    username = known.lichess_username
    if any(v is not None for v in (token, url, client_id, username)):
        return LichessLoginParameters(
            server_url=url or settings.DEFAULT_LICHESS_URL,
            client_id=client_id or settings.DEFAULT_LICHESS_CLIENT_ID,
            token=token or "",
            username=username or "",
        ), remaining
    return None, remaining


def generate_pkce_pair() -> tuple[str, str]:
    """Return (code_verifier, code_challenge) for OAuth2 S256 PKCE."""
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def load_stored_auth(path: Path | None = None) -> dict | None:
    auth_path = path or settings.LICHESS_AUTH_PATH
    if not auth_path.exists():
        return None
    try:
        data = json.loads(auth_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("token"), str) or not data["token"].strip():
            return None
        return data
    except Exception:
        return None


def save_stored_auth(token: str, account: LichessAccount | None = None,
                     server_url: str = settings.DEFAULT_LICHESS_URL,
                     client_id: str = settings.DEFAULT_LICHESS_CLIENT_ID,
                     path: Path | None = None) -> bool:
    auth_path = path or settings.LICHESS_AUTH_PATH
    temporary = None
    try:
        payload = json.dumps({
            "version": 1,
            "token": token.strip(),
            "server_url": server_url.rstrip("/"),
            "client_id": client_id.strip(),
            "account": account.to_dict() if account is not None else None,
        }, indent=2)
        auth_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=auth_path.parent,
                                         prefix=auth_path.name + ".", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, auth_path)
        return True
    except (OSError, ValueError, TypeError) as exc:
        log.warning("Lichess credentials could not be saved: %s", exc)
        return False
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def clear_stored_auth(path: Path | None = None) -> bool:
    auth_path = path or settings.LICHESS_AUTH_PATH
    try:
        auth_path.unlink(missing_ok=True)
        return True
    except OSError as exc:
        log.warning("Could not remove Lichess credentials file %s: %s", auth_path, exc)
        return False


class _OAuthCallbackServer(HTTPServer):
    allow_reuse_address = True

    def __init__(self, server_address, RequestHandlerClass):
        super().__init__(server_address, RequestHandlerClass)
        self.oauth_result: dict[str, str] = {}
        self.received_event = threading.Event()

    def record_callback(self, code: str = "", state: str = "", error: str = "", error_description: str = ""):
        self.oauth_result = {
            "code": code,
            "state": state,
            "error": error,
            "error_description": error_description,
        }
        self.received_event.set()


class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return
        params = urllib.parse.parse_qs(parsed.query)
        self.server.record_callback(
            code=params.get("code", [""])[0],
            state=params.get("state", [""])[0],
            error=params.get("error", [""])[0],
            error_description=params.get("error_description", [""])[0],
        )
        success = bool(self.server.oauth_result.get("code") and not self.server.oauth_result.get("error"))
        title = "Login Successful" if success else "Login Cancelled"
        error_desc = self.server.oauth_result.get("error_description") or self.server.oauth_result.get("error")
        message = (
            "You are now signed in to Lichess in OTBMaster3D. You can close this browser tab."
            if success else f"Lichess authorization did not complete ({error_desc or 'cancelled'})."
        )
        body = (
            "<!DOCTYPE html><html><head><meta charset='utf-8'>"
            f"<title>OTBMaster3D - {title}</title>"
            "<style>body{background:#171b22;color:#e8eaf0;font-family:'Segoe UI',sans-serif;"
            "display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}"
            ".card{background:#1e242e;border:1px solid #414b5b;border-radius:8px;padding:28px 36px;"
            "max-width:440px;text-align:center;}h2{color:#d5944a;margin-top:0;}</style></head>"
            f"<body><div class='card'><h2>{title}</h2><p>{message}</p></div></body></html>"
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


class LichessClient:
    """Manage Lichess authentication, account verification and API requests."""

    def __init__(self, server_url: str = settings.DEFAULT_LICHESS_URL,
                 client_id: str = settings.DEFAULT_LICHESS_CLIENT_ID,
                 token: str = "",
                 account: LichessAccount | None = None,
                 opener=None):
        self.server_url = (server_url or settings.DEFAULT_LICHESS_URL).rstrip("/")
        self.client_id = (client_id or settings.DEFAULT_LICHESS_CLIENT_ID).strip()
        self.token = (token or "").strip()
        self.account = account
        self._opener = opener or urllib.request.urlopen
        self._oauth_server: _OAuthCallbackServer | None = None
        self._active_seek_response = None
        self._seek_cancelled = threading.Event()
        self._event_stream_response = None
        self._game_stream_response = None
        self._game_stream_cancelled = threading.Event()
        self._lock = threading.Lock()

    @property
    def is_authenticated(self) -> bool:
        return bool(self.token and self.account is not None)

    @property
    def user_agent(self) -> str:
        return f"OTBMaster3D/{__version__} ({self.client_id})"

    def configure(self, params: LichessLoginParameters):
        self.server_url = params.normalized_url()
        self.client_id = params.normalized_client_id()
        if params.normalized_token():
            self.token = params.normalized_token()

    def _request_json(self, method: str, path: str, *, data: dict | None = None,
                      token: str | None = None, timeout: float = 10.0) -> dict:
        url = f"{self.server_url}{path}"
        headers = {
            "Accept": "application/json",
            "User-Agent": self.user_agent,
        }
        active_token = self.token if token is None else token
        if active_token:
            headers["Authorization"] = f"Bearer {active_token}"
        body = None
        if data is not None:
            body = urllib.parse.urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with self._opener(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw.strip() else {}
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                error_body = exc.read().decode("utf-8")
                parsed = json.loads(error_body)
                detail = parsed.get("error_description") or parsed.get("error") or ""
            except Exception:
                pass
            if exc.code == 401:
                raise ValueError("Invalid or expired Lichess access token.") from None
            raise ValueError(f"Lichess API error ({exc.code})" + (f": {detail}" if detail else ".")) from None
        except urllib.error.URLError as exc:
            raise ValueError(f"Could not connect to Lichess ({exc.reason}).") from None

    def verify_token(self, token: str | None = None) -> LichessAccount:
        candidate = (self.token if token is None else token).strip()
        if not candidate:
            raise ValueError("Enter a Lichess personal access token or sign in with OAuth.")
        payload = self._request_json("GET", "/api/account", token=candidate)
        account = LichessAccount.from_api(payload)
        with self._lock:
            self.token = candidate
            self.account = account
        return account

    def login_with_parameters(self, params: LichessLoginParameters, *, persist: bool = True) -> LichessAccount:
        """Validate login parameters and authenticate against the Lichess account API."""
        self.server_url = params.normalized_url()
        self.client_id = params.normalized_client_id()
        token = params.normalized_token()
        if not token:
            raise ValueError("A personal access token is required for direct token login.")
        account = self.verify_token(token)
        expected_user = (params.username or "").strip()
        if expected_user and expected_user.lower() != account.username.lower():
            with self._lock:
                self.token = ""
                self.account = None
            raise ValueError(
                f"Token belongs to '{account.username}', which does not match expected username '{expected_user}'."
            )
        if persist:
            save_stored_auth(self.token, account, self.server_url, self.client_id)
        return account

    def cancel_oauth(self):
        with self._lock:
            server = self._oauth_server
            self._oauth_server = None
        if server is not None:
            server.received_event.set()
            try:
                server.server_close()
            except OSError:
                pass

    def login_with_oauth_pkce(self, params: LichessLoginParameters | None = None, *,
                              open_browser=webbrowser.open,
                              timeout: float = 120.0,
                              persist: bool = True) -> LichessAccount:
        """Run the OAuth2 Authorization Code + PKCE flow via a loopback HTTP callback."""
        if params is not None:
            self.server_url = params.normalized_url()
            self.client_id = params.normalized_client_id()
        verifier, challenge = generate_pkce_pair()
        state = secrets.token_urlsafe(24)
        self.cancel_oauth()
        server = _OAuthCallbackServer(("127.0.0.1", 0), _OAuthCallbackHandler)
        with self._lock:
            self._oauth_server = server
        try:
            port = server.server_address[1]
            redirect_uri = f"http://127.0.0.1:{port}/callback"
            query = urllib.parse.urlencode({
                "response_type": "code",
                "client_id": self.client_id,
                "redirect_uri": redirect_uri,
                "scope": LICHESS_SCOPES,
                "code_challenge_method": "S256",
                "code_challenge": challenge,
                "state": state,
            })
            if params is not None and params.username.strip():
                query += "&" + urllib.parse.urlencode({"username": params.username.strip()})
            auth_url = f"{self.server_url}/oauth?{query}"

            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            open_browser(auth_url)

            if not server.received_event.wait(timeout=timeout):
                raise ValueError("Lichess browser login timed out or was cancelled.")
            result = server.oauth_result
            if not result:
                raise ValueError("Lichess browser login was cancelled.")
            if result.get("error"):
                desc = result.get("error_description") or result["error"]
                raise ValueError(f"Lichess authorization failed: {desc}")
            if result.get("state") != state or not result.get("code"):
                raise ValueError("Invalid OAuth callback state from Lichess.")

            token_response = self._request_json(
                "POST",
                "/api/token",
                data={
                    "grant_type": "authorization_code",
                    "code": result["code"],
                    "code_verifier": verifier,
                    "redirect_uri": redirect_uri,
                    "client_id": self.client_id,
                },
                token="",
            )
            access_token = str(token_response.get("access_token") or "").strip()
            if not access_token:
                raise ValueError("Lichess did not return an access token.")
            account = self.verify_token(access_token)
            if persist:
                save_stored_auth(self.token, account, self.server_url, self.client_id)
            return account
        finally:
            self.cancel_oauth()

    def restore_saved_session(self, path: Path | None = None) -> LichessAccount | None:
        stored = load_stored_auth(path)
        if not stored:
            return None
        self.server_url = str(stored.get("server_url") or self.server_url).rstrip("/")
        self.client_id = str(stored.get("client_id") or self.client_id).strip()
        self.token = str(stored["token"]).strip()
        account_data = stored.get("account")
        if isinstance(account_data, dict) and account_data.get("username"):
            try:
                self.account = LichessAccount.from_dict(account_data)
            except Exception:
                self.account = None
        return self.account

    def logout(self, *, revoke_remote: bool = True, path: Path | None = None):
        self.cancel_oauth()
        self.cancel_seek()
        self.stop_event_stream()
        self.stop_game_stream()
        with self._lock:
            token = self.token
            self.token = ""
            self.account = None
        clear_stored_auth(path)
        if revoke_remote and token:
            try:
                self._request_json("DELETE", "/api/token", token=token, timeout=5.0)
            except Exception:
                pass

    def _require_auth(self):
        if not self.token:
            raise ValueError("Please log in to Lichess first.")

    def create_challenge(self, options: LichessChallengeOptions) -> dict:
        """Issue an AI challenge or direct player challenge using common time controls."""
        self._require_auth()
        payload = options.to_challenge_payload()
        if options.mode == "ai":
            response = self._request_json("POST", "/api/challenge/ai", data=payload)
            game_id = str(response.get("id") or response.get("challenge", {}).get("id") or "").strip()
            return {"kind": "game", "game_id": game_id, "raw": response}
        if options.mode == "player":
            opponent = options.opponent_username.strip()
            if self.account and opponent.lower() == self.account.username.lower():
                raise ValueError("You cannot challenge your own Lichess account.")
            encoded_user = urllib.parse.quote(opponent, safe="")
            response = self._request_json("POST", f"/api/challenge/{encoded_user}", data=payload)
            challenge_obj = response.get("challenge") if isinstance(response.get("challenge"), dict) else response
            challenge_id = str(challenge_obj.get("id") or "").strip()
            return {"kind": "challenge", "challenge_id": challenge_id, "raw": response}
        raise ValueError("Use start_seek() for Quick Pairing lobby seeks.")

    def cancel_challenge(self, challenge_id: str) -> None:
        self._require_auth()
        cid = (challenge_id or "").strip()
        if not cid:
            return
        self._request_json("POST", f"/api/challenge/{urllib.parse.quote(cid, safe='')}/cancel", data={})

    def accept_challenge(self, challenge_id: str) -> None:
        self._require_auth()
        cid = (challenge_id or "").strip()
        if not cid:
            raise ValueError("Challenge ID is required.")
        self._request_json("POST", f"/api/challenge/{urllib.parse.quote(cid, safe='')}/accept", data={})

    def decline_challenge(self, challenge_id: str, reason: str = "generic") -> None:
        self._require_auth()
        cid = (challenge_id or "").strip()
        if not cid:
            return
        self._request_json(
            "POST",
            f"/api/challenge/{urllib.parse.quote(cid, safe='')}/decline",
            data={"reason": reason},
        )

    def cancel_seek(self) -> None:
        self._seek_cancelled.set()
        with self._lock:
            resp = self._active_seek_response
            self._active_seek_response = None
        if resp is not None:
            try:
                resp.close()
            except Exception:
                pass

    def start_seek(self, options: LichessChallengeOptions, *, timeout: float = 300.0) -> str | None:
        """Open a Board API lobby seek (/api/board/seek) and block until matched or cancelled."""
        self._require_auth()
        if options.mode != "seek":
            raise ValueError("LichessChallengeOptions.mode must be 'seek'.")
        payload = options.to_challenge_payload()
        self.cancel_seek()
        self._seek_cancelled.clear()

        url = f"{self.server_url}/api/board/seek"
        headers = {
            "Accept": "application/x-ndjson",
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": self.user_agent,
        }
        body = urllib.parse.urlencode(payload).encode("utf-8")
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with self._opener(request, timeout=timeout) as response:
                with self._lock:
                    self._active_seek_response = response
                for raw_line in response:
                    if self._seek_cancelled.is_set():
                        return None
                    line = raw_line.decode("utf-8", errors="replace").strip() if isinstance(raw_line, bytes) else str(raw_line).strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(event, dict) and event.get("id"):
                        return str(event["id"])
            return None
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                error_body = exc.read().decode("utf-8")
                parsed = json.loads(error_body)
                detail = parsed.get("error_description") or parsed.get("error") or ""
            except Exception:
                pass
            raise ValueError(f"Lichess seek error ({exc.code})" + (f": {detail}" if detail else ".")) from None
        except Exception as exc:
            if self._seek_cancelled.is_set():
                return None
            raise ValueError(f"Seek connection interrupted ({exc}).") from None
        finally:
            with self._lock:
                self._active_seek_response = None

    def stop_event_stream(self) -> None:
        with self._lock:
            resp = self._event_stream_response
            self._event_stream_response = None
        if resp is not None:
            try:
                resp.close()
            except Exception:
                pass

    def iter_incoming_events(self, *, timeout: float = 60.0):
        """Yield parsed JSON events from GET /api/stream/event until closed."""
        self._require_auth()
        self.stop_event_stream()
        url = f"{self.server_url}/api/stream/event"
        headers = {
            "Accept": "application/x-ndjson",
            "Authorization": f"Bearer {self.token}",
            "User-Agent": self.user_agent,
        }
        request = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with self._opener(request, timeout=timeout) as response:
                with self._lock:
                    self._event_stream_response = response
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="replace").strip() if isinstance(raw_line, bytes) else str(raw_line).strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(event, dict):
                        yield event
        finally:
            with self._lock:
                self._event_stream_response = None

    def stop_game_stream(self) -> None:
        self._game_stream_cancelled.set()
        with self._lock:
            resp = self._game_stream_response
            self._game_stream_response = None
        if resp is not None:
            try:
                resp.close()
            except Exception:
                pass

    def iter_game_stream(self, game_id: str, *, timeout: float = 90.0):
        """Yield parsed NDJSON events (gameFull, gameState, chatLine, opponentGone) for a Lichess board game."""
        self._require_auth()
        gid = (game_id or "").strip()
        if not gid:
            raise ValueError("Game ID is required to stream a Lichess game.")
        self.stop_game_stream()
        self._game_stream_cancelled.clear()
        url = f"{self.server_url}/api/board/game/stream/{urllib.parse.quote(gid, safe='')}"
        headers = {
            "Accept": "application/x-ndjson",
            "Authorization": f"Bearer {self.token}",
            "User-Agent": self.user_agent,
        }
        request = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with self._opener(request, timeout=timeout) as response:
                with self._lock:
                    self._game_stream_response = response
                for raw_line in response:
                    if self._game_stream_cancelled.is_set():
                        return
                    line = raw_line.decode("utf-8", errors="replace").strip() if isinstance(raw_line, bytes) else str(raw_line).strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(event, dict):
                        yield event
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                error_body = exc.read().decode("utf-8")
                parsed = json.loads(error_body)
                detail = parsed.get("error_description") or parsed.get("error") or ""
            except Exception:
                pass
            raise ValueError(f"Lichess game stream error ({exc.code})" + (f": {detail}" if detail else ".")) from None
        except Exception as exc:
            if self._game_stream_cancelled.is_set():
                return
            raise ValueError(f"Lichess game stream disconnected ({exc}).") from None
        finally:
            with self._lock:
                self._game_stream_response = None

    def send_move(self, game_id: str, uci_move: str, *, offering_draw: bool = False) -> dict:
        self._require_auth()
        gid = urllib.parse.quote((game_id or "").strip(), safe="")
        mv = urllib.parse.quote((uci_move or "").strip(), safe="")
        query = "?offeringDraw=true" if offering_draw else ""
        return self._request_json("POST", f"/api/board/game/{gid}/move/{mv}{query}", data={})

    def resign_game(self, game_id: str) -> dict:
        self._require_auth()
        gid = urllib.parse.quote((game_id or "").strip(), safe="")
        return self._request_json("POST", f"/api/board/game/{gid}/resign", data={})

    def abort_game(self, game_id: str) -> dict:
        self._require_auth()
        gid = urllib.parse.quote((game_id or "").strip(), safe="")
        return self._request_json("POST", f"/api/board/game/{gid}/abort", data={})

    def handle_draw_offer(self, game_id: str, accept: bool = True) -> dict:
        self._require_auth()
        gid = urllib.parse.quote((game_id or "").strip(), safe="")
        flag = "yes" if accept else "no"
        return self._request_json("POST", f"/api/board/game/{gid}/draw/{flag}", data={})

    def handle_takeback_offer(self, game_id: str, accept: bool = True) -> dict:
        self._require_auth()
        gid = urllib.parse.quote((game_id or "").strip(), safe="")
        flag = "yes" if accept else "no"
        return self._request_json("POST", f"/api/board/game/{gid}/takeback/{flag}", data={})

    def fetch_post_game_ratings(self, game_id: str, session: LichessGameSession | None = None) -> dict:
        """Fetch updated player and account ratings immediately after a rated Lichess game finishes."""
        self._require_auth()
        gid = urllib.parse.quote((game_id or "").strip(), safe="")
        white_new: int | None = None
        white_diff: int | None = None
        black_new: int | None = None
        black_diff: int | None = None

        # 1. Query exported game JSON for pre-game rating + ratingDiff on both sides
        if gid:
            try:
                export_data = self._request_json(
                    "GET",
                    f"/game/export/{gid}?moves=false&clocks=false&evals=false&opening=false",
                )
                players = export_data.get("players") or {}
                w_info = players.get("white") or {}
                b_info = players.get("black") or {}
                w_base = w_info.get("rating")
                w_delta = w_info.get("ratingDiff")
                if isinstance(w_base, int) and isinstance(w_delta, int):
                    white_new = w_base + w_delta
                    white_diff = w_delta
                b_base = b_info.get("rating")
                b_delta = b_info.get("ratingDiff")
                if isinstance(b_base, int) and isinstance(b_delta, int):
                    black_new = b_base + b_delta
                    black_diff = b_delta
            except Exception:
                pass

        # 2. Refresh our own Lichess account profile (for LichessMenu and fallback clock rating)
        account: LichessAccount | None = None
        try:
            account = self.verify_token(self.token)
        except Exception:
            account = self.account

        if session is not None and account is not None:
            speed_key = (session.speed or "").strip().lower()
            my_perf_rating = account.perfs.get(speed_key)
            if isinstance(my_perf_rating, int):
                if session.my_color is True and white_new is None:
                    white_new = my_perf_rating
                    if isinstance(session.white_rating, int):
                        white_diff = white_new - session.white_rating
                elif session.my_color is False and black_new is None:
                    black_new = my_perf_rating
                    if isinstance(session.black_rating, int):
                        black_diff = black_new - session.black_rating
            # Ensure account.perfs[speed_key] also reflects the new rating from the game export
            if speed_key:
                if session.my_color is True and isinstance(white_new, int):
                    account.perfs[speed_key] = white_new
                elif session.my_color is False and isinstance(black_new, int):
                    account.perfs[speed_key] = black_new
            save_stored_auth(self.token, account, self.server_url, self.client_id)

        # 3. If opponent's updated rating is still unknown, query /api/user/{opponent_id}
        if session is not None:
            speed_key = (session.speed or "").strip().lower()
            for is_white, opp_id, old_rating, known_new in (
                (True, session.white_id, session.white_rating, white_new),
                (False, session.black_id, session.black_rating, black_new),
            ):
                if known_new is not None or not opp_id or opp_id.startswith("ai_"):
                    continue
                if account is not None and opp_id == account.user_id.lower():
                    continue
                try:
                    user_payload = self._request_json(
                        "GET", f"/api/user/{urllib.parse.quote(opp_id, safe='')}"
                    )
                    opp_account = LichessAccount.from_api(user_payload)
                    opp_perf = opp_account.perfs.get(speed_key)
                    if isinstance(opp_perf, int):
                        if is_white:
                            white_new = opp_perf
                            if isinstance(old_rating, int):
                                white_diff = white_new - old_rating
                        else:
                            black_new = opp_perf
                            if isinstance(old_rating, int):
                                black_diff = black_new - old_rating
                except Exception:
                    pass

        return {
            "account": account,
            "white_rating": white_new,
            "white_diff": white_diff,
            "black_rating": black_new,
            "black_diff": black_diff,
        }
