"""Lichess menu and login / account parameters dialog."""

import threading
import webbrowser
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QPushButton, QDialogButtonBox, QMenu, QMessageBox, QComboBox, QSpinBox,
)

from otb_chess.services import settings
from otb_chess.services.lichess import (
    LichessLoginParameters,
    LichessChallengeOptions,
    LICHESS_SCOPES,
    LICHESS_CHALLENGE_PRESETS,
    LICHESS_SEEK_PRESETS,
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


class LichessChallengeDialog(QDialog):
    """Issue a Lichess challenge or Quick Pairing seek using common time controls."""

    operation_finished = Signal(bool, str, str)

    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.client = owner.lichess
        self.game = owner.game
        self._busy = False
        self._pending_challenge_id = ""
        self.started_game_id = ""
        self.setObjectName("lichessChallengeDialog")
        self.setWindowTitle("Lichess Challenge & Quick Pairing")
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        account_name = self.client.account.display_name if self.client.account else "Lichess"
        self.header_label = QLabel(f"Signed in as {account_name}. Choose opponent and time control:")
        self.header_label.setObjectName("lichessChallengeHeader")
        self.header_label.setWordWrap(True)
        layout.addWidget(self.header_label)

        self.form = QFormLayout()

        self.mode_combo = QComboBox()
        self.mode_combo.setObjectName("lichessChallengeMode")
        self.mode_combo.addItem("Play vs Lichess AI (Stockfish)", "ai")
        self.mode_combo.addItem("Challenge a Player by Username", "player")
        self.mode_combo.addItem("Quick Pairing (Lobby Seek)", "seek")
        saved_mode = self.game.cfg.get("lichess_challenge_mode", "ai")
        self.mode_combo.setCurrentIndex(max(0, self.mode_combo.findData(saved_mode)))

        self.opponent_edit = QLineEdit(self.game.cfg.get("lichess_opponent", ""))
        self.opponent_edit.setObjectName("lichessOpponentEdit")
        self.opponent_edit.setPlaceholderText("Lichess username to challenge")

        self.ai_level_spin = QSpinBox()
        self.ai_level_spin.setObjectName("lichessAiLevel")
        self.ai_level_spin.setRange(1, 8)
        self.ai_level_spin.setValue(int(self.game.cfg.get("lichess_ai_level", 3)))
        self.ai_level_spin.setPrefix("Level ")

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
        self.form.addRow("Opponent Username", self.opponent_edit)
        self.form.addRow("AI Strength (1–8)", self.ai_level_spin)
        self.form.addRow("Time Control", self.preset_combo)
        self.form.addRow("Initial Time", self.custom_minutes_spin)
        self.form.addRow("Increment", self.custom_increment_spin)
        self.form.addRow("Your Side", self.color_combo)
        self.form.addRow("Game Type", self.rated_combo)
        layout.addLayout(self.form)

        self.rule_note = QLabel()
        self.rule_note.setObjectName("hint")
        self.rule_note.setWordWrap(True)
        layout.addWidget(self.rule_note)

        self.status_label = QLabel("")
        self.status_label.setObjectName("lichessChallengeStatus")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        button_row = QHBoxLayout()
        self.submit_button = QPushButton("Issue Challenge")
        self.submit_button.setObjectName("primary")
        self.submit_button.clicked.connect(self.start_challenge_or_seek)

        self.cancel_button = QPushButton("Close")
        self.cancel_button.setObjectName("lichessChallengeCancel")
        self.cancel_button.clicked.connect(self.reject)

        button_row.addStretch()
        button_row.addWidget(self.submit_button)
        button_row.addWidget(self.cancel_button)
        layout.addLayout(button_row)

        self.mode_combo.currentIndexChanged.connect(self._update_mode_fields)
        self.preset_combo.currentTextChanged.connect(self._update_custom_clock_visibility)
        self.operation_finished.connect(self._on_operation_finished)

        self._populate_presets(self.game.cfg.get("lichess_time_control", "Rapid 10+0"))
        self._update_mode_fields()

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
        self.form.setRowVisible(self.opponent_edit, mode == "player")
        self.form.setRowVisible(self.ai_level_spin, mode == "ai")
        self.form.setRowVisible(self.rated_combo, mode != "ai")
        if mode == "ai":
            self.submit_button.setText("Start AI Game")
            self.rule_note.setText(
                "Challenge Lichess Stockfish (Level 1–8) using Bullet, Blitz, Rapid, or Classical time controls."
            )
        elif mode == "player":
            self.submit_button.setText("Send Challenge")
            self.rule_note.setText(
                "Send a direct challenge to a Lichess user (Bullet, Blitz, Rapid, or Classical)."
            )
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
        return LichessChallengeOptions(
            mode=mode,
            preset=self.preset_combo.currentText(),
            custom_minutes=self.custom_minutes_spin.value(),
            custom_increment=self.custom_increment_spin.value(),
            color=self.color_combo.currentData(),
            rated=False if mode == "ai" else bool(self.rated_combo.currentData()),
            opponent_username=self.opponent_edit.text().strip(),
            ai_level=self.ai_level_spin.value(),
        )

    def _save_preferences(self, options: LichessChallengeOptions):
        self.game.cfg.update(
            lichess_challenge_mode=options.mode,
            lichess_time_control=options.preset,
            lichess_custom_minutes=options.custom_minutes,
            lichess_custom_increment=options.custom_increment,
            lichess_color=options.color,
            lichess_rated=options.rated,
            lichess_ai_level=options.ai_level,
            lichess_opponent=options.opponent_username,
        )
        self.game.persist()

    def _set_busy(self, busy: bool, status_text: str = ""):
        self._busy = busy
        for widget in (
            self.mode_combo, self.opponent_edit, self.ai_level_spin,
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
        if options.mode == "ai":
            self._set_busy(True, f"Starting game vs Lichess AI (Level {options.ai_level})…")
        elif options.mode == "player":
            self._set_busy(True, f"Challenging {options.opponent_username} ({options.preset})…")
        else:
            self._set_busy(True, f"Searching Lichess lobby for {options.preset} opponent…")

        def worker():
            try:
                if options.mode == "ai":
                    result = self.client.create_challenge(options)
                    game_id = result.get("game_id", "")
                    if not game_id:
                        raise ValueError("Lichess did not return a game ID.")
                    self.operation_finished.emit(
                        True, game_id, f"Lichess AI game started ({options.preset}, ID: {game_id})."
                    )
                    return

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
