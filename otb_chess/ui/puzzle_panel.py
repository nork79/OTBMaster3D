"""Modeless Puzzle Trainer window and Puzzles menu for Mate 1-3, Combinations, and Endgames."""

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QVBoxLayout,
)

from otb_chess.services.puzzles import (
    PUZZLE_CATEGORIES,
    Puzzle,
    PuzzleProgressStore,
    PuzzleRepository,
)

log = logging.getLogger(__name__)


class PuzzleMenu(QMenu):
    """Puzzles menu providing access to the Puzzle Trainer window."""

    def __init__(self, owner):
        super().__init__("Puzzles", owner)
        self.owner = owner
        owner.menuBar().addMenu(self)
        owner.puzzles_action = owner.action(
            self,
            "Puzzle Trainer…",
            lambda checked: owner.toggle_puzzles(checked),
            "Ctrl+Shift+P",
            True,
        )
        owner.puzzles_action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)


class PuzzlePanel(QDialog):
    """Compact modeless panel for stepping through tactical, mating, and endgame puzzles."""

    def __init__(self, owner, progress: PuzzleProgressStore | None = None,
                 repository: PuzzleRepository | None = None):
        super().__init__(owner, Qt.WindowType.Tool)
        self.owner = owner
        self.progress = progress or PuzzleProgressStore()
        self.repository = repository or PuzzleRepository()
        self._puzzles: list[Puzzle] = []
        self._current_index: int = 0
        self.setObjectName("puzzlePanel")
        self.setWindowTitle("Puzzle Trainer")
        self.setMinimumWidth(340)

        layout = QVBoxLayout(self)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.setObjectName("puzzleCategoryCombo")
        self.category_combo.addItem("All Categories", "all")
        for key, label in PUZZLE_CATEGORIES:
            self.category_combo.addItem(label, key)
        self.category_combo.currentIndexChanged.connect(self._on_category_changed)
        top_row.addWidget(self.category_combo, 1)

        self.progress_label = QLabel("")
        self.progress_label.setObjectName("puzzleProgressLabel")
        top_row.addWidget(self.progress_label)
        layout.addLayout(top_row)

        puzzle_row = QHBoxLayout()
        puzzle_row.addWidget(QLabel("Puzzle:"))
        self.puzzle_combo = QComboBox()
        self.puzzle_combo.setObjectName("puzzleSelectorCombo")
        self.puzzle_combo.currentIndexChanged.connect(self._on_puzzle_selected)
        puzzle_row.addWidget(self.puzzle_combo, 1)
        layout.addLayout(puzzle_row)

        self.title_label = QLabel("")
        self.title_label.setObjectName("puzzleTitleLabel")
        self.title_label.setStyleSheet("font-weight: 700; font-size: 14px;")
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        self.prompt_label = QLabel("")
        self.prompt_label.setObjectName("puzzlePromptLabel")
        self.prompt_label.setWordWrap(True)
        layout.addWidget(self.prompt_label)

        self.theme_label = QLabel("")
        self.theme_label.setObjectName("puzzleThemeLabel")
        self.theme_label.setStyleSheet("color: #9ba8b8;")
        self.theme_label.setWordWrap(True)
        layout.addWidget(self.theme_label)

        self.status_label = QLabel("Make the winning move on the board.")
        self.status_label.setObjectName("puzzleStatusLabel")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        btn_row_1 = QHBoxLayout()
        self.hint_button = QPushButton("Hint")
        self.hint_button.setObjectName("puzzleHintButton")
        self.hint_button.clicked.connect(self.show_hint)
        self.retry_button = QPushButton("Retry")
        self.retry_button.setObjectName("puzzleRetryButton")
        self.retry_button.clicked.connect(self.retry_current)
        self.solution_button = QPushButton("Solution")
        self.solution_button.setObjectName("puzzleSolutionButton")
        self.solution_button.clicked.connect(self.show_solution)
        btn_row_1.addWidget(self.hint_button)
        btn_row_1.addWidget(self.retry_button)
        btn_row_1.addWidget(self.solution_button)
        layout.addLayout(btn_row_1)

        btn_row_2 = QHBoxLayout()
        self.prev_button = QPushButton("Previous")
        self.prev_button.setObjectName("puzzlePrevButton")
        self.prev_button.clicked.connect(self.prev_puzzle)
        self.next_button = QPushButton("Next Puzzle")
        self.next_button.setObjectName("primary")
        self.next_button.clicked.connect(self.next_puzzle)
        btn_row_2.addWidget(self.prev_button)
        btn_row_2.addWidget(self.next_button, 1)
        layout.addLayout(btn_row_2)

        self._refresh_filtered_list(select_unsolved=True)

    def set_category(self, category: str):
        idx = self.category_combo.findData(category or "all")
        if idx >= 0:
            if idx != self.category_combo.currentIndex():
                self.category_combo.setCurrentIndex(idx)
            else:
                self._refresh_filtered_list(select_unsolved=True)
                self.load_current()

    def _on_category_changed(self):
        self._refresh_filtered_list(select_unsolved=True)
        self.load_current()

    def _on_puzzle_selected(self, index: int):
        if 0 <= index < len(self._puzzles) and index != self._current_index:
            self._current_index = index
            self.load_current()

    def _sync_puzzle_combo(self):
        self.puzzle_combo.blockSignals(True)
        try:
            self.puzzle_combo.clear()
            for p in self._puzzles:
                prefix = "✓ " if p.puzzle_id in self.progress.solved_ids else ""
                self.puzzle_combo.addItem(f"{prefix}{p.title} ({p.rating})", p.puzzle_id)
            if 0 <= self._current_index < self.puzzle_combo.count():
                self.puzzle_combo.setCurrentIndex(self._current_index)
        finally:
            self.puzzle_combo.blockSignals(False)

    def _refresh_filtered_list(self, *, select_unsolved: bool = False):
        cat = str(self.category_combo.currentData() or "all")
        self._puzzles = self.repository.list_puzzles(cat)
        self._current_index = 0
        if select_unsolved and self._puzzles:
            for i, p in enumerate(self._puzzles):
                if p.puzzle_id not in self.progress.solved_ids:
                    self._current_index = i
                    break
        self._sync_puzzle_combo()
        self._update_progress_label()

    def _update_progress_label(self):
        total = len(self._puzzles)
        solved = sum(1 for p in self._puzzles if p.puzzle_id in self.progress.solved_ids)
        self.progress_label.setText(f"Solved: {solved}/{total}")

    def current_puzzle(self) -> Puzzle | None:
        if 0 <= self._current_index < len(self._puzzles):
            return self._puzzles[self._current_index]
        return None

    def load_current(self) -> bool:
        puzzle = self.current_puzzle()
        if puzzle is None:
            return False
        if not self.owner.load_puzzle(puzzle):
            return False
        solved_mark = " ✓" if puzzle.puzzle_id in self.progress.solved_ids else ""
        self.title_label.setText(f"{puzzle.title}{solved_mark} ({self._current_index + 1}/{len(self._puzzles)})")
        self.prompt_label.setText(puzzle.prompt_text)
        theme_parts = []
        if puzzle.theme:
            theme_parts.append(f"Theme: {puzzle.theme}")
        if puzzle.rating:
            theme_parts.append(f"Rating: {puzzle.rating}")
        self.theme_label.setText("  |  ".join(theme_parts))
        self.set_status("Make the winning move on the board.", color="#9ba8b8")
        if self.puzzle_combo.currentIndex() != self._current_index:
            self.puzzle_combo.blockSignals(True)
            self.puzzle_combo.setCurrentIndex(self._current_index)
            self.puzzle_combo.blockSignals(False)
        self._update_progress_label()
        return True

    def set_status(self, text: str, *, color: str = "#9ba8b8"):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-weight: 600;")

    def show_hint(self):
        self.owner.show_puzzle_hint()

    def retry_current(self):
        self.load_current()

    def show_solution(self):
        if self.owner.play_puzzle_solution():
            self.set_status("Playing solution on the board…", color="#d5944a")

    def next_puzzle(self):
        if not self._puzzles:
            return
        self._current_index = (self._current_index + 1) % len(self._puzzles)
        self.load_current()

    def prev_puzzle(self):
        if not self._puzzles:
            return
        self._current_index = (self._current_index - 1) % len(self._puzzles)
        self.load_current()

    def notify_solved(self, puzzle: Puzzle):
        self.progress.mark_solved(puzzle.puzzle_id)
        self._sync_puzzle_combo()
        self._update_progress_label()
        self.title_label.setText(f"{puzzle.title} ✓ ({self._current_index + 1}/{len(self._puzzles)})")
        self.set_status("Puzzle solved! Click Next Puzzle to continue.", color="#80bfab")

    def show_panel(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        self.owner.on_puzzle_panel_closed()
        super().closeEvent(event)
