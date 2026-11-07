"""Lichess menu and login / account parameters dialog."""

import base64
import html
import threading
import webbrowser
from PySide6.QtCore import QBuffer, QIODevice, QPointF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPalette, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QFrame, QLabel, QLineEdit,
    QPushButton, QDialogButtonBox, QMenu, QMessageBox, QComboBox, QSpinBox,
    QTextBrowser, QWidget,
)

from otb_chess.services import settings
from otb_chess.services.lichess import (
    LichessAccount,
    LichessLoginParameters,
    LichessChallengeOptions,
    LICHESS_SCOPES,
    LICHESS_CHALLENGE_PRESETS,
    LICHESS_SEEK_PRESETS,
    format_bot_summary,
)


class LichessMenu(QMenu):
    """Top-level Lichess menu displaying authentication status, challenge launcher, and live game actions."""

    def __init__(self, owner):
        super().__init__("Lichess", owner)
        self.owner = owner
        self.setObjectName("lichessMenu")
        self.status_action = self.addAction("Status: Not logged in")
        self.status_action.setEnabled(False)
        self.game_status_action = self.addAction("Live Game: None")
        self.game_status_action.setEnabled(False)
        self.addSeparator()
        self.challenge_action = owner.action(
            self, "New Challenge / Seek…", owner.open_lichess_challenge, "Ctrl+Shift+L"
        )
        self.resign_online_action = owner.action(
            self, "Resign / Abort Online Game", lambda: owner.lichess_game_action("resign")
        )
        self.draw_online_action = owner.action(
            self, "Offer / Accept Draw", lambda: owner.lichess_game_action("draw")
        )
        self.takeback_online_action = owner.action(
            self, "Request / Accept Takeback", lambda: owner.lichess_game_action("takeback")
        )
        self.addSeparator()
        self.login_action = owner.action(self, "Login / Account Settings…", owner.open_lichess_login)
        self.verify_action = owner.action(self, "Verify Connection", owner.verify_lichess_session)
        self.logout_action = owner.action(self, "Logout", owner.logout_lichess)
        self.aboutToShow.connect(self.refresh)
        self.refresh()

    def refresh(self):
        client = getattr(self.owner, "lichess", None)
        authenticated = bool(client and client.is_authenticated)
        if authenticated:
            account = client.account
            ratings = []
            for key, label in (
                ("bullet", "Bullet"),
                ("blitz", "Blitz"),
                ("rapid", "Rapid"),
                ("classical", "Classical"),
            ):
                if key in account.perfs:
                    ratings.append(f"{label} {account.perfs[key]}")
            suffix = f" ({', '.join(ratings)})" if ratings else ""
            self.status_action.setText(f"Signed in as {account.display_name}{suffix}")
            self.login_action.setText("Account / Login Parameters…")
        elif client and client.token:
            self.status_action.setText("Status: Token configured (unverified)")
            self.login_action.setText("Login / Account Settings…")
        else:
            self.status_action.setText("Status: Not logged in")
            self.login_action.setText("Login to Lichess…")

        game = getattr(self.owner, "game", None)
        online = getattr(game, "online_session", None) if game is not None else None
        online_active = bool(online is not None and online.active)
        if online is not None:
            state_label = "Active" if online.active else f"Finished ({online.status})"
            self.game_status_action.setText(
                f"Live Game: {online.white_name} vs {online.black_name} — {state_label}"
            )
        else:
            self.game_status_action.setText("Live Game: None")

        self.challenge_action.setEnabled(bool(client and (client.is_authenticated or client.token)))
        self.resign_online_action.setEnabled(online_active)
        self.draw_online_action.setEnabled(online_active)
        self.takeback_online_action.setEnabled(
            online_active and bool(game is not None and game.history_board().move_stack)
        )
        self.verify_action.setEnabled(bool(client and client.token))
        self.logout_action.setEnabled(bool(client and (client.token or client.is_authenticated)))


class LichessLoginDialog(QDialog):
    """Configure Lichess login parameters and authenticate via Token or OAuth2 PKCE."""

    auth_finished = Signal(bool, object, str)

    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.client = owner.lichess
        self.game = owner.game
        self._busy = False
        self.setObjectName("lichessLoginDialog")
        self.setWindowTitle("Lichess Login & Account Parameters")
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        self.status_label = QLabel()
        self.status_label.setObjectName("lichessStatusLabel")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        form = QFormLayout()
        self.server_url_edit = QLineEdit(
            self.game.cfg.get("lichess_url", settings.DEFAULT_LICHESS_URL) or settings.DEFAULT_LICHESS_URL
        )
        self.server_url_edit.setObjectName("lichessServerUrl")
        self.server_url_edit.setPlaceholderText(settings.DEFAULT_LICHESS_URL)

        self.client_id_edit = QLineEdit(
            self.game.cfg.get("lichess_client_id", settings.DEFAULT_LICHESS_CLIENT_ID) or settings.DEFAULT_LICHESS_CLIENT_ID
        )
        self.client_id_edit.setObjectName("lichessClientId")
        self.client_id_edit.setPlaceholderText(settings.DEFAULT_LICHESS_CLIENT_ID)

        default_username = (
            self.client.account.username
            if self.client.account is not None
            else self.game.cfg.get("lichess_username", "")
        )
        self.username_edit = QLineEdit(default_username)
        self.username_edit.setObjectName("lichessUsername")
        self.username_edit.setPlaceholderText("Optional (verified against Lichess account)")

        self.token_edit = QLineEdit(self.client.token)
        self.token_edit.setObjectName("lichessToken")
        self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_edit.setPlaceholderText("lip_... (Personal Access Token with board:play, challenge:write)")

        token_row = QHBoxLayout()
        token_row.addWidget(self.token_edit, 1)
        self.show_token_button = QPushButton("Show")
        self.show_token_button.setObjectName("lichessShowToken")
        self.show_token_button.setCheckable(True)
        self.show_token_button.toggled.connect(
            lambda checked: (
                self.token_edit.setEchoMode(QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password),
                self.show_token_button.setText("Hide" if checked else "Show"),
            )
        )
        token_row.addWidget(self.show_token_button)

        form.addRow("Server URL", self.server_url_edit)
        form.addRow("OAuth Client ID", self.client_id_edit)
        form.addRow("Username", self.username_edit)
        form.addRow("Access Token", token_row)
        layout.addLayout(form)

        scope_hint = QLabel(
            f"Required Lichess scopes: {LICHESS_SCOPES}.\n"
            "Sign in directly through your browser (OAuth2 PKCE) or paste a Personal Access Token."
        )
        scope_hint.setObjectName("hint")
        scope_hint.setWordWrap(True)
        layout.addWidget(scope_hint)

        action_row = QHBoxLayout()
        self.oauth_button = QPushButton("Sign in with Browser (OAuth)…")
        self.oauth_button.setObjectName("primary")
        self.oauth_button.clicked.connect(self.start_oauth_login)

        self.token_login_button = QPushButton("Login with Token")
        self.token_login_button.setObjectName("lichessTokenLogin")
        self.token_login_button.clicked.connect(self.start_token_login)

        self.create_token_button = QPushButton("Create Token on Lichess…")
        self.create_token_button.setObjectName("lichessCreateToken")
        self.create_token_button.clicked.connect(self.open_token_creation_page)

        action_row.addWidget(self.oauth_button)
        action_row.addWidget(self.token_login_button)
        action_row.addWidget(self.create_token_button)
        layout.addLayout(action_row)

        bottom_row = QHBoxLayout()
        self.logout_button = QPushButton("Logout")
        self.logout_button.setObjectName("lichessLogoutButton")
        self.logout_button.clicked.connect(self.handle_logout)
        bottom_row.addWidget(self.logout_button)
        bottom_row.addStretch()

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Close
        )
        self.buttons.accepted.connect(self.save_parameters_only)
        self.buttons.rejected.connect(self.reject)
        bottom_row.addWidget(self.buttons)
        layout.addLayout(bottom_row)

        self.auth_finished.connect(self._on_auth_finished)
        self.refresh_state()

    def current_parameters(self) -> LichessLoginParameters:
        return LichessLoginParameters(
            server_url=self.server_url_edit.text(),
            client_id=self.client_id_edit.text(),
            token=self.token_edit.text(),
            username=self.username_edit.text(),
        )

    def refresh_state(self):
        if self._busy:
            return
        if self.client.is_authenticated and self.client.account is not None:
            acc = self.client.account
            self.status_label.setText(f"Connected to Lichess as {acc.display_name} ({self.client.server_url}).")
            self.status_label.setStyleSheet("font-weight: 600; color: #80bfab;")
        elif self.client.token:
            self.status_label.setText("Token saved. Click 'Login with Token' to verify your Lichess account.")
            self.status_label.setStyleSheet("color: #d5944a;")
        else:
            self.status_label.setText("Not signed in to Lichess.")
            self.status_label.setStyleSheet("")
        self.logout_button.setEnabled(bool(self.client.token or self.client.is_authenticated))

    def _set_busy(self, busy: bool, message: str = ""):
        self._busy = busy
        for widget in (
            self.server_url_edit, self.client_id_edit, self.username_edit,
            self.token_edit, self.oauth_button, self.token_login_button,
            self.create_token_button, self.logout_button,
            self.buttons.button(QDialogButtonBox.StandardButton.Save),
        ):
            if widget is not None:
                widget.setEnabled(not busy)
        if busy and message:
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color: #d5944a;")

    def open_token_creation_page(self):
        try:
            base = self.current_parameters().normalized_url()
        except ValueError as exc:
            QMessageBox.warning(self, "Lichess", str(exc))
            return
        url = (
            f"{base}/account/oauth/token/create?"
            "scopes[]=board:play&scopes[]=challenge:read&scopes[]=challenge:write"
            "&description=OTBMaster3D+Desktop"
        )
        webbrowser.open(url)

    def start_token_login(self):
        try:
            params = self.current_parameters()
            params.normalized_url()
            params.normalized_client_id()
            if not params.normalized_token():
                raise ValueError("Paste a Lichess Personal Access Token first, or use 'Sign in with Browser'.")
        except ValueError as exc:
            QMessageBox.warning(self, "Lichess Login", str(exc))
            return

        self._set_busy(True, "Verifying Lichess access token…")

        def worker():
            try:
                account = self.client.login_with_parameters(params, persist=True)
                self.auth_finished.emit(True, account, f"Signed in to Lichess as {account.display_name}.")
            except Exception as exc:
                self.auth_finished.emit(False, None, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def start_oauth_login(self):
        try:
            params = self.current_parameters()
            params.normalized_url()
            params.normalized_client_id()
        except ValueError as exc:
            QMessageBox.warning(self, "Lichess Login", str(exc))
            return

        self._set_busy(True, "Waiting for Lichess authorization in your browser…")

        def worker():
            try:
                account = self.client.login_with_oauth_pkce(params, persist=True)
                self.auth_finished.emit(True, account, f"Signed in to Lichess as {account.display_name}.")
            except Exception as exc:
                self.auth_finished.emit(False, None, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_auth_finished(self, ok: bool, account, message: str):
        self._set_busy(False)
        if ok and account is not None:
            self.username_edit.setText(account.username)
            self.token_edit.setText(self.client.token)
            self._persist_config_fields(username=account.username)
            self.owner.on_lichess_auth_changed(message)
            self.refresh_state()
        else:
            self.status_label.setText(f"Login failed: {message}")
            self.status_label.setStyleSheet("color: #e36d65;")
            self.logout_button.setEnabled(bool(self.client.token or self.client.is_authenticated))

    def _persist_config_fields(self, username: str | None = None):
        params = self.current_parameters()
        self.game.cfg["lichess_url"] = params.normalized_url()
        self.game.cfg["lichess_client_id"] = params.normalized_client_id()
        resolved_username = username if username is not None else params.username.strip()
        self.game.cfg["lichess_username"] = resolved_username
        if resolved_username and not self.game.cfg.get("player_name"):
            self.game.cfg["player_name"] = resolved_username
        self.game.persist()

    def save_parameters_only(self):
        try:
            params = self.current_parameters()
            url = params.normalized_url()
            cid = params.normalized_client_id()
        except ValueError as exc:
            QMessageBox.warning(self, "Lichess Parameters", str(exc))
            return
        self.client.server_url = url
        self.client.client_id = cid
        token = params.normalized_token()
        if token != self.client.token:
            self.client.token = token
            self.client.account = None
        if token:
            from otb_chess.services.lichess import save_stored_auth
            save_stored_auth(token, self.client.account, url, cid)
        else:
            from otb_chess.services.lichess import clear_stored_auth
            clear_stored_auth()
        self._persist_config_fields()
        self.owner.on_lichess_auth_changed("Lichess parameters saved.")
        self.accept()

    def handle_logout(self):
        self.client.logout()
        self.token_edit.clear()
        self.game.cfg["lichess_username"] = ""
        self.game.persist()
        self.owner.on_lichess_auth_changed("Logged out of Lichess.")
        self.refresh_state()

    def reject(self):
        if self._busy:
            self.client.cancel_oauth()
            self._set_busy(False)
        super().reject()


def _pixmap_to_data_uri(pixmap: QPixmap) -> str:
    """Encode a QPixmap as an inline PNG data URI for rich HTML labels."""
    if pixmap.isNull():
        return ""
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    pixmap.save(buf, "PNG")
    encoded = base64.b64encode(bytes(buf.data())).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _render_speed_icon_pixmap(speed_key: str, size: int = 16) -> QPixmap:
    """Render a crisp icon asset for Bullet, Blitz, Rapid, or Classical ratings."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    if speed_key == "bullet":
        # Sleek gold bullet projectile
        color = QColor("#e5a65c")
        painter.setPen(QPen(color, 1.4))
        painter.setBrush(color)
        poly = QPolygonF([
            QPointF(3.0, size - 4.0),
            QPointF(6.5, size - 4.0),
            QPointF(size - 2.5, 5.0),
            QPointF(size - 2.0, 2.0),
            QPointF(size - 5.0, 2.5),
            QPointF(3.0, size - 7.5),
        ])
        painter.drawPolygon(poly)
    elif speed_key == "blitz":
        # Lightning bolt
        color = QColor("#f4c542")
        painter.setPen(QPen(color, 1.0))
        painter.setBrush(color)
        bolt = QPolygonF([
            QPointF(size * 0.58, 1.5),
            QPointF(size * 0.22, size * 0.56),
            QPointF(size * 0.50, size * 0.56),
            QPointF(size * 0.38, size - 1.5),
            QPointF(size * 0.78, size * 0.44),
            QPointF(size * 0.50, size * 0.44),
        ])
        painter.drawPolygon(bolt)
    elif speed_key == "rapid":
        # Stopwatch / clock icon
        color = QColor("#80bfab")
        painter.setPen(QPen(color, 1.6))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(2, 3, size - 4, size - 4)
        painter.drawLine(int(size * 0.38), 1, int(size * 0.62), 1)
        painter.drawLine(int(size * 0.5), int(size * 0.55), int(size * 0.5), 5)
        painter.drawLine(int(size * 0.5), int(size * 0.55), int(size * 0.72), int(size * 0.55))
    else:
        # Classical hourglass / trophy emblem
        color = QColor("#78b7ec")
        painter.setPen(QPen(color, 1.5))
        painter.setBrush(QColor(120, 183, 236, 70))
        glass = QPolygonF([
            QPointF(3.0, 2.5),
            QPointF(size - 3.0, 2.5),
            QPointF(size * 0.56, size * 0.5),
            QPointF(size - 3.0, size - 2.5),
            QPointF(3.0, size - 2.5),
            QPointF(size * 0.44, size * 0.5),
        ])
        painter.drawPolygon(glass)

    painter.end()
    return pixmap


def _render_bot_emblem_pixmap(bot: LichessAccount | None, size: int = 64) -> QPixmap:
    """Render a stylized bot emblem pixmap as a fallback or base asset for the Bot Details pane."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    bg_color = QColor("#232b38")
    border_color = QColor("#d5944a") if (bot and bot.patron) else QColor("#80bfab")
    painter.setBrush(bg_color)
    painter.setPen(QPen(border_color, 2))
    painter.drawRoundedRect(2, 2, size - 4, size - 4, 10, 10)

    # Top "BOT" pill
    pill_color = QColor("#b65973")
    painter.setBrush(pill_color)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(10, 7, size - 20, 15, 4, 4)

    font_small = QFont("Segoe UI", 7, QFont.Weight.Bold)
    painter.setFont(font_small)
    painter.setPen(QColor("#ffffff"))
    painter.drawText(10, 7, size - 20, 15, int(Qt.AlignmentFlag.AlignCenter), "BOT")

    # Bot initials or chess knight glyph
    initials = (bot.username[:2].upper() if bot and bot.username else "♞")
    font_main = QFont("Segoe UI", 16, QFont.Weight.Bold)
    painter.setFont(font_main)
    painter.setPen(QColor("#e8eaf0"))
    painter.drawText(4, 22, size - 8, size - 26, int(Qt.AlignmentFlag.AlignCenter), initials)
    painter.end()
    return pixmap


class LichessChallengeDialog(QDialog):
    """Issue a Lichess player/bot challenge or Quick Pairing seek using common time controls."""

    operation_finished = Signal(bool, str, str)
    bots_loaded = Signal(bool, object, str)
    bot_assets_loaded = Signal(str, object, object)

    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.client = owner.lichess
        self.game = owner.game
        self._busy = False
        self._loading_bots = False
        self._bots_loaded_once = False
        self._online_bots: list[LichessAccount] = []
        self._bot_by_username: dict[str, LichessAccount] = {}
        self._bot_assets_cache: dict[str, dict[str, bytes]] = {}
        self._selected_bot: LichessAccount | None = None
        self._pending_challenge_id = ""
        self.started_game_id = ""
        self.setObjectName("lichessChallengeDialog")
        self.setWindowTitle("Lichess Challenge & Quick Pairing")
        self.setMinimumWidth(840)

        root_layout = QVBoxLayout(self)
        account_name = self.client.account.display_name if self.client.account else "Lichess"
        self.header_label = QLabel(f"Signed in as {account_name}. Choose opponent and time control:")
        self.header_label.setObjectName("lichessChallengeHeader")
        self.header_label.setWordWrap(True)
        root_layout.addWidget(self.header_label)

        content_row = QHBoxLayout()
        content_row.setSpacing(16)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.form = QFormLayout()

        self.mode_combo = QComboBox()
        self.mode_combo.setObjectName("lichessChallengeMode")
        self.mode_combo.addItem("Challenge a Player by Username", "player")
        self.mode_combo.addItem("Quick Pairing (Lobby Seek)", "seek")
        saved_mode = self.game.cfg.get("lichess_challenge_mode", "player")
        if saved_mode not in ("player", "seek"):
            saved_mode = "player"
        self.mode_combo.setCurrentIndex(max(0, self.mode_combo.findData(saved_mode)))

        self.online_bot_row = QWidget()
        bot_row_layout = QHBoxLayout(self.online_bot_row)
        bot_row_layout.setContentsMargins(0, 0, 0, 0)
        self.online_bot_combo = QComboBox()
        self.online_bot_combo.setObjectName("lichessOnlineBotCombo")
        self.online_bot_combo.addItem("Select an online bot…", "")
        self.refresh_bots_button = QPushButton("Refresh")
        self.refresh_bots_button.setObjectName("lichessRefreshBotsButton")
        self.refresh_bots_button.setToolTip("Fetch online bots and their ratings from Lichess")
        self.refresh_bots_button.clicked.connect(self.refresh_online_bots)
        bot_row_layout.addWidget(self.online_bot_combo, 1)
        bot_row_layout.addWidget(self.refresh_bots_button)

        self.opponent_edit = QLineEdit(self.game.cfg.get("lichess_opponent", ""))
        self.opponent_edit.setObjectName("lichessOpponentEdit")
        self.opponent_edit.setPlaceholderText("Lichess username to challenge (or pick an online bot above)")

        self.preset_combo = QComboBox()
        self.preset_combo.setObjectName("lichessTimeControlPreset")

        self.custom_minutes_spin = QSpinBox()
        self.custom_minutes_spin.setObjectName("lichessCustomMinutes")
        self.custom_minutes_spin.setRange(1, 180)
        self.custom_minutes_spin.setSuffix(" min")
        self.custom_minutes_spin.setValue(int(self.game.cfg.get("lichess_custom_minutes", 10)))

        self.custom_increment_spin = QSpinBox()
        self.custom_increment_spin.setObjectName("lichessCustomIncrement")
        self.custom_increment_spin.setRange(0, 180)
        self.custom_increment_spin.setSuffix(" sec")
        self.custom_increment_spin.setValue(int(self.game.cfg.get("lichess_custom_increment", 0)))

        self.color_combo = QComboBox()
        self.color_combo.setObjectName("lichessColorCombo")
        self.color_combo.addItem("Random", "random")
        self.color_combo.addItem("White", "white")
        self.color_combo.addItem("Black", "black")
        saved_color = self.game.cfg.get("lichess_color", "random")
        self.color_combo.setCurrentIndex(max(0, self.color_combo.findData(saved_color)))

        self.rated_combo = QComboBox()
        self.rated_combo.setObjectName("lichessRatedCombo")
        self.rated_combo.addItem("Casual (Unrated)", False)
        self.rated_combo.addItem("Rated", True)
        self.rated_combo.setCurrentIndex(1 if self.game.cfg.get("lichess_rated", False) else 0)

        self.form.addRow("Game Mode", self.mode_combo)
        self.form.addRow("Online Bots", self.online_bot_row)
        self.form.addRow("Opponent Username", self.opponent_edit)
        self.form.addRow("Time Control", self.preset_combo)
        self.form.addRow("Initial Time", self.custom_minutes_spin)
        self.form.addRow("Increment", self.custom_increment_spin)
        self.form.addRow("Your Side", self.color_combo)
        self.form.addRow("Game Type", self.rated_combo)
        left_layout.addLayout(self.form)

        self.rule_note = QLabel()
        self.rule_note.setObjectName("hint")
        self.rule_note.setWordWrap(True)
        left_layout.addWidget(self.rule_note)

        self.status_label = QLabel("")
        self.status_label.setObjectName("lichessChallengeStatus")
        self.status_label.setWordWrap(True)
        left_layout.addWidget(self.status_label)
        left_layout.addStretch()

        # Separate Bot Profile, Description & Lichess Assets Pane
        self.bot_details_pane = QFrame()
        self.bot_details_pane.setObjectName("lichessBotDetailsPane")
        self.bot_details_pane.setMinimumWidth(340)
        self.bot_details_pane.setStyleSheet(
            "QFrame#lichessBotDetailsPane {"
            "  background-color: #000000;"
            "  border: 1px solid #414b5b;"
            "  border-radius: 8px;"
            "}"
        )
        pane_layout = QVBoxLayout(self.bot_details_pane)
        pane_layout.setContentsMargins(14, 12, 14, 12)
        pane_layout.setSpacing(8)

        pane_header = QLabel("BOT PROFILE & LICHESS ASSETS")
        pane_header.setObjectName("section")
        pane_header.setStyleSheet("font-weight: 700; color: #d5944a; letter-spacing: 0.5px;")
        pane_layout.addWidget(pane_header)

        identity_row = QHBoxLayout()
        identity_row.setSpacing(12)
        self.bot_avatar_label = QLabel()
        self.bot_avatar_label.setObjectName("lichessBotAvatar")
        self.bot_avatar_label.setFixedSize(64, 64)
        self.bot_avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        identity_row.addWidget(self.bot_avatar_label)

        identity_text_col = QVBoxLayout()
        identity_text_col.setSpacing(3)
        self.bot_title_label = QLabel("No Bot Selected")
        self.bot_title_label.setObjectName("lichessBotTitle")
        self.bot_title_label.setWordWrap(True)
        self.bot_title_label.setStyleSheet("font-size: 14px; font-weight: 700;")
        identity_text_col.addWidget(self.bot_title_label)

        self.bot_meta_label = QLabel("")
        self.bot_meta_label.setObjectName("lichessBotMeta")
        self.bot_meta_label.setWordWrap(True)
        self.bot_meta_label.setOpenExternalLinks(True)
        identity_text_col.addWidget(self.bot_meta_label)

        assets_strip = QHBoxLayout()
        assets_strip.setContentsMargins(0, 2, 0, 0)
        assets_strip.setSpacing(8)
        self.bot_flair_label = QLabel()
        self.bot_flair_label.setObjectName("lichessBotFlairAsset")
        self.bot_flair_label.setFixedSize(24, 24)
        self.bot_flair_label.hide()
        self.bot_flag_label = QLabel()
        self.bot_flag_label.setObjectName("lichessBotFlagAsset")
        self.bot_flag_label.setFixedSize(24, 18)
        self.bot_flag_label.hide()
        self.bot_asset_status_label = QLabel("")
        self.bot_asset_status_label.setObjectName("hint")
        assets_strip.addWidget(self.bot_flair_label)
        assets_strip.addWidget(self.bot_flag_label)
        assets_strip.addWidget(self.bot_asset_status_label, 1)
        identity_text_col.addLayout(assets_strip)

        identity_row.addLayout(identity_text_col, 1)
        pane_layout.addLayout(identity_row)

        self.bot_ratings_label = QLabel("")
        self.bot_ratings_label.setObjectName("lichessBotRatings")
        self.bot_ratings_label.setWordWrap(True)
        self.bot_ratings_label.setStyleSheet("color: #80bfab; font-weight: 600;")
        pane_layout.addWidget(self.bot_ratings_label)

        self.bot_description_browser = QTextBrowser()
        self.bot_description_browser.setObjectName("lichessBotDescription")
        self.bot_description_browser.setOpenExternalLinks(True)
        self.bot_description_browser.setMinimumHeight(140)
        desc_palette = self.bot_description_browser.palette()
        desc_palette.setColor(QPalette.ColorRole.Base, QColor("#000000"))
        desc_palette.setColor(QPalette.ColorRole.Window, QColor("#000000"))
        desc_palette.setColor(QPalette.ColorRole.Text, QColor("#e8eaf0"))
        desc_palette.setColor(QPalette.ColorRole.WindowText, QColor("#e8eaf0"))
        self.bot_description_browser.setPalette(desc_palette)
        self.bot_description_browser.viewport().setPalette(desc_palette)
        self.bot_description_browser.setStyleSheet(
            "QTextBrowser#lichessBotDescription, QTextBrowser#lichessBotDescription QWidget {"
            "  background-color: #000000;"
            "  color: #e8eaf0;"
            "  border: 1px solid #414b5b;"
            "  border-radius: 6px;"
            "  padding: 6px;"
            "}"
        )
        self.bot_description_browser.viewport().setStyleSheet(
            "background-color: #000000; color: #e8eaf0; border: none;"
        )
        pane_layout.addWidget(self.bot_description_browser, 1)

        content_row.addWidget(left_panel, 3)
        content_row.addWidget(self.bot_details_pane, 2)
        root_layout.addLayout(content_row, 1)

        button_row = QHBoxLayout()
        self.submit_button = QPushButton("Send Challenge")
        self.submit_button.setObjectName("primary")
        self.submit_button.clicked.connect(self.start_challenge_or_seek)

        self.cancel_button = QPushButton("Close")
        self.cancel_button.setObjectName("lichessChallengeCancel")
        self.cancel_button.clicked.connect(self.reject)

        button_row.addStretch()
        button_row.addWidget(self.submit_button)
        button_row.addWidget(self.cancel_button)
        root_layout.addLayout(button_row)

        self.mode_combo.currentIndexChanged.connect(self._update_mode_fields)
        self.online_bot_combo.currentIndexChanged.connect(self._on_online_bot_selected)
        self.opponent_edit.textEdited.connect(self._on_opponent_text_edited)
        self.preset_combo.currentTextChanged.connect(self._update_custom_clock_visibility)
        self.operation_finished.connect(self._on_operation_finished)
        self.bots_loaded.connect(self._on_bots_loaded)
        self.bot_assets_loaded.connect(self._on_bot_assets_loaded)

        self._render_bot_pane(None)
        self._populate_presets(self.game.cfg.get("lichess_time_control", "Rapid 10+0"))
        self._update_mode_fields()

    def _render_bot_pane(self, bot: LichessAccount | None, assets: dict[str, bytes] | None = None):
        """Update the separate Bot Details pane with the selected bot's description, ratings, and Lichess imagery."""
        self._selected_bot = bot
        if bot is None:
            self.bot_avatar_label.setPixmap(_render_bot_emblem_pixmap(None, 64))
            self.bot_title_label.setText("Select an Online Bot")
            self.bot_meta_label.setText("Choose a bot from the Online Bots dropdown to inspect its Lichess profile.")
            self.bot_flair_label.clear()
            self.bot_flair_label.hide()
            self.bot_flag_label.clear()
            self.bot_flag_label.hide()
            self.bot_asset_status_label.setText("")
            self.bot_ratings_label.setText("")
            self.bot_description_browser.setHtml(
                "<body style='background-color:#000000; color:#e8eaf0; margin:0;'>"
                "<p style='color:#a3afc1; margin-top:0;'>When you select an online bot opponent from the dropdown, "
                "its Lichess description (bio), ratings across Bullet/Blitz/Rapid/Classical, author details, "
                "and Lichess imagery/flair assets are displayed here.</p></body>"
            )
            return

        # 1. Resolve Imagery / Assets (Avatar, Flair, Flag) first so inline HTML can embed them
        resolved_assets = assets if assets is not None else self._bot_assets_cache.get(bot.username.lower(), {})
        avatar_pixmap = None
        for key in ("avatar", "flair"):
            raw_bytes = resolved_assets.get(key)
            if raw_bytes:
                pm = QPixmap()
                if pm.loadFromData(raw_bytes) and not pm.isNull():
                    avatar_pixmap = pm.scaled(
                        64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                    )
                    break
        if avatar_pixmap is None:
            avatar_pixmap = _render_bot_emblem_pixmap(bot, 64)
        self.bot_avatar_label.setPixmap(avatar_pixmap)

        flair_bytes = resolved_assets.get("flair")
        flair_pm = QPixmap()
        has_flair_img = bool(flair_bytes and flair_pm.loadFromData(flair_bytes) and not flair_pm.isNull())
        if has_flair_img:
            scaled_flair = flair_pm.scaled(
                24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            self.bot_flair_label.setPixmap(scaled_flair)
            self.bot_flair_label.setToolTip(f"Lichess Flair: {bot.flair}")
            self.bot_flair_label.show()
        else:
            self.bot_flair_label.clear()
            self.bot_flair_label.hide()

        flag_bytes = resolved_assets.get("flag")
        flag_pm = QPixmap()
        has_flag_img = bool(flag_bytes and flag_pm.loadFromData(flag_bytes) and not flag_pm.isNull())
        if has_flag_img:
            scaled_flag = flag_pm.scaled(
                24, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            self.bot_flag_label.setPixmap(scaled_flag)
            self.bot_flag_label.setToolTip(f"Country / Flag: {bot.country}")
            self.bot_flag_label.show()
        else:
            self.bot_flag_label.clear()
            self.bot_flag_label.hide()

        self.bot_asset_status_label.setText("")

        # 2. Title & Patron badge
        title_tag = bot.title or "BOT"
        patron_badge = " · ★ Patron" if bot.patron else ""
        self.bot_title_label.setText(f"{title_tag} {bot.username}{patron_badge}")

        # 3. Metadata (Maintainer, Location/Flag icon, Profile Link)
        meta_parts = []
        if bot.real_name:
            meta_parts.append(f"<b>Author:</b> {html.escape(bot.real_name)}")
        if bot.location or has_flag_img or bot.country:
            flag_img_tag = ""
            if has_flag_img:
                flag_uri = _pixmap_to_data_uri(
                    flag_pm.scaled(16, 12, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                )
                if flag_uri:
                    flag_img_tag = f"<img src='{flag_uri}' width='16' height='12'> "
            loc_text = html.escape(bot.location) if bot.location else html.escape(bot.country)
            meta_parts.append(f"<b>Location:</b> {flag_img_tag}{loc_text}")
        profile_href = bot.profile_url or f"https://lichess.org/@/{bot.username}"
        meta_parts.append(
            f"<a href='{html.escape(profile_href)}' style='color:#d5944a;'>View on Lichess (@{html.escape(bot.username)})</a>"
        )
        self.bot_meta_label.setText("<br>".join(meta_parts))

        # 4. Ratings with graphical speed icon assets (no "(58,653g)" character strings)
        rating_chunks = []
        for key, label in (
            ("bullet", "Bullet"),
            ("blitz", "Blitz"),
            ("rapid", "Rapid"),
            ("classical", "Classical"),
        ):
            if key in bot.perfs:
                icon_uri = _pixmap_to_data_uri(_render_speed_icon_pixmap(key, 16))
                img_html = f"<img src='{icon_uri}' width='14' height='14'> " if icon_uri else ""
                rating_chunks.append(f"{img_html}<b>{label}</b> {bot.perfs[key]}")
        ratings_html = "&nbsp;&nbsp;·&nbsp;&nbsp;".join(rating_chunks) if rating_chunks else "Unrated"
        if bot.total_games > 0:
            ratings_html += (
                f"<br><span style='color:#a3afc1; font-size:11px; font-weight:normal;'>"
                f"Total Games: {bot.total_games:,} &nbsp;(Wins: {bot.wins:,} · Draws: {bot.draws:,} · Losses: {bot.losses:,})"
                f"</span>"
            )
        self.bot_ratings_label.setText(ratings_html)

        # 5. Description (Bio) & External Links
        html_blocks = ["<body style='background-color:#000000; color:#e8eaf0; margin:0;'>"]
        if bot.bio:
            escaped_bio = html.escape(bot.bio).replace("\n", "<br>")
            html_blocks.append(f"<p style='color:#e8eaf0; margin-top:0; line-height:1.35;'>{escaped_bio}</p>")
        else:
            html_blocks.append("<p style='color:#a3afc1; margin-top:0;'><i>No bio description provided on Lichess.</i></p>")

        if bot.links:
            link_items = []
            for raw_link in bot.links.splitlines():
                link = raw_link.strip()
                if not link:
                    continue
                href = link if link.startswith(("http://", "https://")) else f"https://{link}"
                link_items.append(
                    f"<li><a href='{html.escape(href)}' style='color:#80bfab;'>{html.escape(link)}</a></li>"
                )
            if link_items:
                html_blocks.append(
                    "<p style='color:#e8eaf0; margin-bottom:2px;'><b>Links &amp; Resources:</b></p>"
                    f"<ul style='color:#e8eaf0; margin-top:2px; padding-left:18px;'>{''.join(link_items)}</ul>"
                )
        html_blocks.append("</body>")
        self.bot_description_browser.setHtml("".join(html_blocks))

    def _request_bot_assets(self, bot: LichessAccount):
        key = bot.username.lower()
        if key in self._bot_assets_cache:
            self._render_bot_pane(bot, self._bot_assets_cache[key])
            return

        def worker():
            try:
                enriched_bot, assets = self.client.fetch_bot_details_and_assets(bot)
                self.bot_assets_loaded.emit(bot.username, enriched_bot, assets)
            except Exception:
                self.bot_assets_loaded.emit(bot.username, bot, {})

        threading.Thread(target=worker, daemon=True).start()

    def _on_bot_assets_loaded(self, username: str, enriched_bot, assets):
        key = (username or "").strip().lower()
        if isinstance(assets, dict):
            self._bot_assets_cache[key] = assets
        if isinstance(enriched_bot, LichessAccount):
            self._bot_by_username[key] = enriched_bot
        if self._selected_bot is not None and self._selected_bot.username.lower() == key:
            target_bot = self._bot_by_username.get(key, self._selected_bot)
            self._render_bot_pane(target_bot, self._bot_assets_cache.get(key, {}))
            if not target_bot.asset_urls() and not self._bot_assets_cache.get(key):
                self.bot_asset_status_label.setText("Lichess Bot Emblem")
            elif not self._bot_assets_cache.get(key):
                self.bot_asset_status_label.setText("Lichess Bot Emblem")

    def _on_online_bot_selected(self, _index: int = 0):
        bot_username = str(self.online_bot_combo.currentData() or "").strip()
        if bot_username:
            self.opponent_edit.setText(bot_username)
            bot = self._bot_by_username.get(bot_username.lower())
            self.bot_details_pane.setVisible(self.mode_combo.currentData() == "player")
            self._render_bot_pane(bot)
            if bot is not None:
                self._request_bot_assets(bot)
        else:
            self._render_bot_pane(None)

    def _on_opponent_text_edited(self, text: str):
        typed = (text or "").strip().lower()
        self.online_bot_combo.blockSignals(True)
        matched_index = 0
        if typed:
            for idx in range(1, self.online_bot_combo.count()):
                data = str(self.online_bot_combo.itemData(idx) or "").strip().lower()
                if data == typed:
                    matched_index = idx
                    break
        self.online_bot_combo.setCurrentIndex(matched_index)
        self.online_bot_combo.blockSignals(False)
        bot = self._bot_by_username.get(typed) if matched_index > 0 else None
        self._render_bot_pane(bot)
        if bot is not None:
            self._request_bot_assets(bot)

    def set_online_bots(self, bots: list[LichessAccount]):
        """Populate the online bots dropdown with formatted 'bot: ratings' entries."""
        self._online_bots = list(bots or [])
        self._bot_by_username = {b.username.lower(): b for b in self._online_bots}
        self._bots_loaded_once = True
        current_target = self.opponent_edit.text().strip().lower()
        self.online_bot_combo.blockSignals(True)
        self.online_bot_combo.clear()
        placeholder = (
            f"Select an online bot ({len(self._online_bots)} online)…"
            if self._online_bots
            else "No online bots available"
        )
        self.online_bot_combo.addItem(placeholder, "")
        selected_idx = 0
        for idx, bot in enumerate(self._online_bots, start=1):
            self.online_bot_combo.addItem(format_bot_summary(bot), bot.username)
            if current_target and bot.username.lower() == current_target:
                selected_idx = idx
        self.online_bot_combo.setCurrentIndex(selected_idx)
        self.online_bot_combo.blockSignals(False)
        if selected_idx > 0:
            bot = self._online_bots[selected_idx - 1]
            self._render_bot_pane(bot)
            self._request_bot_assets(bot)
        else:
            self._render_bot_pane(None)

    def refresh_online_bots(self):
        if self._loading_bots:
            return
        self._loading_bots = True
        self._bots_loaded_once = True
        self.refresh_bots_button.setEnabled(False)
        self.online_bot_combo.blockSignals(True)
        if self.online_bot_combo.count() == 0:
            self.online_bot_combo.addItem("Loading online bots…", "")
        else:
            self.online_bot_combo.setItemText(0, "Loading online bots…")
        self.online_bot_combo.blockSignals(False)

        def worker():
            try:
                bots = self.client.fetch_online_bots()
                self.bots_loaded.emit(True, bots, "")
            except Exception as exc:
                self.bots_loaded.emit(False, [], str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_bots_loaded(self, ok: bool, bots, error_message: str):
        self._loading_bots = False
        self.refresh_bots_button.setEnabled(not self._busy)
        if ok:
            self.set_online_bots(bots)
        else:
            self.online_bot_combo.blockSignals(True)
            self.online_bot_combo.clear()
            self.online_bot_combo.addItem("Select an online bot (click Refresh)…", "")
            self.online_bot_combo.blockSignals(False)
            if error_message and not self._busy:
                self.status_label.setText(error_message)
                self.status_label.setStyleSheet("color: #e36d65;")

    def _populate_presets(self, preferred: str):
        mode = self.mode_combo.currentData()
        presets = LICHESS_SEEK_PRESETS if mode == "seek" else LICHESS_CHALLENGE_PRESETS
        current = preferred or self.preset_combo.currentText() or "Rapid 10+0"
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItems([*presets, "Custom"])
        if current in presets or current == "Custom":
            self.preset_combo.setCurrentText(current)
        else:
            self.preset_combo.setCurrentText("Rapid 10+0")
        self.preset_combo.blockSignals(False)
        self._update_custom_clock_visibility()

    def _update_mode_fields(self):
        mode = self.mode_combo.currentData()
        current_preset = self.preset_combo.currentText()
        self._populate_presets(current_preset)
        self.custom_minutes_spin.setRange(8 if mode == "seek" else 1, 180)
        is_player_mode = mode == "player"
        self.form.setRowVisible(self.online_bot_row, is_player_mode)
        self.form.setRowVisible(self.opponent_edit, is_player_mode)
        self.bot_details_pane.setVisible(is_player_mode)
        if is_player_mode:
            self.submit_button.setText("Send Challenge")
            self.rule_note.setText(
                "Send a direct challenge to a Lichess user or select an online bot (Bullet, Blitz, Rapid, or Classical)."
            )
            if not self._bots_loaded_once:
                self.refresh_online_bots()
        else:
            self.submit_button.setText("Find Opponent (Seek)")
            self.rule_note.setText(
                "Lichess Board API Quick Pairing (Lobby Seek) only accepts Rapid and Classical time controls (10+0 or slower)."
            )

    def _update_custom_clock_visibility(self):
        is_custom = self.preset_combo.currentText() == "Custom"
        self.form.setRowVisible(self.custom_minutes_spin, is_custom)
        self.form.setRowVisible(self.custom_increment_spin, is_custom)

    def current_options(self) -> LichessChallengeOptions:
        mode = self.mode_combo.currentData()
        opponent = self.opponent_edit.text().strip() or str(self.online_bot_combo.currentData() or "").strip()
        return LichessChallengeOptions(
            mode=mode,
            preset=self.preset_combo.currentText(),
            custom_minutes=self.custom_minutes_spin.value(),
            custom_increment=self.custom_increment_spin.value(),
            color=self.color_combo.currentData(),
            rated=bool(self.rated_combo.currentData()),
            opponent_username=opponent,
        )

    def _save_preferences(self, options: LichessChallengeOptions):
        self.game.cfg.update(
            lichess_challenge_mode=options.mode,
            lichess_time_control=options.preset,
            lichess_custom_minutes=options.custom_minutes,
            lichess_custom_increment=options.custom_increment,
            lichess_color=options.color,
            lichess_rated=options.rated,
            lichess_opponent=options.opponent_username,
        )
        self.game.persist()

    def _set_busy(self, busy: bool, status_text: str = ""):
        self._busy = busy
        for widget in (
            self.mode_combo, self.online_bot_combo, self.refresh_bots_button,
            self.opponent_edit,
            self.preset_combo, self.custom_minutes_spin, self.custom_increment_spin,
            self.color_combo, self.rated_combo, self.submit_button,
        ):
            widget.setEnabled(not busy)
        self.cancel_button.setText("Cancel" if busy else "Close")
        if status_text:
            self.status_label.setText(status_text)
            self.status_label.setStyleSheet("color: #d5944a; font-weight: 600;")

    def start_challenge_or_seek(self):
        try:
            options = self.current_options()
            options.to_challenge_payload()
        except ValueError as exc:
            QMessageBox.warning(self, "Lichess Challenge", str(exc))
            return

        self._save_preferences(options)
        self._pending_challenge_id = ""
        if options.mode == "player":
            self._set_busy(True, f"Challenging {options.opponent_username} ({options.preset})…")
        else:
            self._set_busy(True, f"Searching Lichess lobby for {options.preset} opponent…")

        def worker():
            try:
                if options.mode == "seek":
                    game_id = self.client.start_seek(options)
                    if not game_id:
                        self.operation_finished.emit(False, "", "Lobby seek cancelled.")
                        return
                    self.operation_finished.emit(
                        True, game_id, f"Matched on Lichess ({options.preset}, ID: {game_id})."
                    )
                    return

                if options.mode == "player":
                    result = self.client.create_challenge(options)
                    cid = result.get("challenge_id", "")
                    self._pending_challenge_id = cid
                    for event in self.client.iter_incoming_events():
                        etype = event.get("type")
                        if etype == "gameStart":
                            game_obj = event.get("game") or {}
                            gid = str(game_obj.get("gameId") or game_obj.get("id") or "").strip()
                            if not cid or gid == cid:
                                self._pending_challenge_id = ""
                                self.operation_finished.emit(
                                    True, gid, f"Challenge accepted by {options.opponent_username} (ID: {gid})."
                                )
                                return
                        elif etype == "challengeDeclined":
                            declined = event.get("challenge") or {}
                            if not cid or str(declined.get("id") or "") == cid:
                                reason = declined.get("declineReason") or "declined"
                                self._pending_challenge_id = ""
                                self.operation_finished.emit(
                                    False, "", f"Challenge to {options.opponent_username} was declined ({reason})."
                                )
                                return
                        elif etype == "challengeCanceled":
                            canceled = event.get("challenge") or {}
                            if not cid or str(canceled.get("id") or "") == cid:
                                self._pending_challenge_id = ""
                                self.operation_finished.emit(False, "", "Challenge cancelled.")
                                return
                    self.operation_finished.emit(False, "", "Challenge cancelled.")
            except Exception as exc:
                self._pending_challenge_id = ""
                self.operation_finished.emit(False, "", str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_operation_finished(self, ok: bool, game_id: str, message: str):
        self._set_busy(False)
        if ok and game_id:
            self.started_game_id = game_id
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color: #80bfab; font-weight: 600;")
            self.owner.on_lichess_game_matched(game_id, self.current_options(), message)
            self.accept()
        else:
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color: #e36d65;")

    def cancel_active_operation(self):
        cid = self._pending_challenge_id
        self._pending_challenge_id = ""
        self.client.cancel_seek()
        self.client.stop_event_stream()
        if cid:
            threading.Thread(
                target=lambda: self._safe_cancel_challenge(cid),
                daemon=True,
            ).start()

    def _safe_cancel_challenge(self, challenge_id: str):
        try:
            self.client.cancel_challenge(challenge_id)
        except Exception:
            pass

    def reject(self):
        if self._busy:
            self.cancel_active_operation()
            self._set_busy(False, "Cancelled.")
            return
        super().reject()
