"""File and clipboard actions for chess notation."""

from pathlib import Path
from PySide6.QtWidgets import QApplication, QFileDialog, QInputDialog, QMessageBox
from otb_chess.core.documents import read_pgn, read_fen


class DocumentActions:
    def edit_game_details(self):
        from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox
        from otb_chess.services.pgn_details import FIELDS
        dialog = QDialog(self)
        dialog.setWindowTitle('Edit Game Details')
        dialog.setObjectName('gameDetailsDialog')
        layout = QFormLayout(dialog)
        fields = {}
        original = self.game.game_details()
        for key, value in original.items():
            field = QLineEdit(value)
            field.setObjectName('pgn' + key)
            field.setAccessibleName(key)
            layout.addRow(key, field)
            fields[key] = field
        fields['Date'].setToolTip('YYYY.MM.DD; use ???? or ?? for unknown parts')
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        layout.addRow(buttons)

        def save():
            try:
                self.game.set_game_details({key: fields[key].text() for key in FIELDS})
            except ValueError as exc:
                QMessageBox.warning(dialog, 'Invalid game details', str(exc))
                return
            g = self.game
            if g.engine_enabled and g.engine_side is not None and g.engine_manager.engine is not None:
                key = 'Black' if g.engine_side else 'White'
            else:
                key = 'Black' if g.cfg.get('player_name') == original['Black'] else 'White'
            name = g.game_details()[key]
            if name != original[key] or not g.cfg.get('player_name'):
                self.game.cfg['player_name'] = '' if name == '?' else name
                self.game.persist()
            self.session.save(self.game, force=True)
            dialog.accept()

        buttons.accepted.connect(save)
        buttons.rejected.connect(dialog.reject)
        dialog.exec()

    def build_file_menu(self):
        menu = self.menuBar().addMenu("File")
        self.action(menu,"Open PGN / FEN…",self.open_notation,"Ctrl+O")
        self.action(menu,"Save PGN…",lambda:self.save_notation("pgn"),"Ctrl+S")
        self.action(menu,"Save FEN…",lambda:self.save_notation("fen"))
        menu.addSeparator()
        self.action(menu,"Copy PGN",lambda:QApplication.clipboard().setText(self.game.export_pgn()))
        self.action(menu,"Copy FEN",lambda:QApplication.clipboard().setText(self.game.board.fen()))
        self.action(menu,"Paste FEN…",self.paste_fen)

    def import_notation(self, text, kind):
        try:
            document = None
            if kind == "fen":
                board = read_fen(text)
            else:
                games = read_pgn(text)
                index = 0
                if len(games) > 1:
                    labels = [f"{i+1}. {g.headers.get('White','?')} — {g.headers.get('Black','?')} ({g.headers.get('Event','?')})"
                              for i,g in enumerate(games)]
                    choice,ok = QInputDialog.getItem(self,"Open PGN","Choose game",labels,0,False)
                    if not ok:
                        return False
                    index = labels.index(choice)
                document = games[index]
                board = document.history
            if self.game.engine_manager.thinking or self.game.engine_loading or self.game.analysis_busy:
                QMessageBox.information(self,"Engine busy","Wait for the current engine operation to finish before opening a game.")
                return False
            if self.game.history_board().move_stack or self.game.game_started:
                if not self.confirm("Open game/position","Replace the current game? Save it first if you want to keep it."):
                    return False
            self.game.load_document(board,document)
            self.board_widget.update()
            return True
        except (ValueError,IndexError) as exc:
            QMessageBox.warning(self,"Invalid notation",str(exc))
            return False

    def open_notation(self):
        path,_ = QFileDialog.getOpenFileName(self,"Open game or position","","Chess notation (*.pgn *.fen);;PGN (*.pgn);;FEN (*.fen)")
        if path:
            try:
                self.import_notation(Path(path).read_text(encoding="utf-8-sig"),Path(path).suffix.lower().lstrip('.'))
            except (OSError,UnicodeError) as exc:
                QMessageBox.warning(self,"Could not open file",str(exc))

    def save_notation(self, kind):
        path,_ = QFileDialog.getSaveFileName(self,f"Save {kind.upper()}",f"game.{kind}",f"{kind.upper()} (*.{kind})")
        if path:
            target = Path(path)
            if not target.suffix:
                target = target.with_suffix('.'+kind)
                if target.exists() and not self.confirm("Replace file",f"Replace {target.name}?"):
                    return
            try:
                text = self.game.export_pgn() if kind == "pgn" else self.game.board.fen()+'\n'
                target.write_text(text,encoding="utf-8")
                self.game.result_text = f"Saved {target.name}"
            except OSError as exc:
                QMessageBox.warning(self,"Could not save file",str(exc))

    def paste_fen(self):
        text,ok = QInputDialog.getText(self,"Paste FEN","Position (FEN)",text=QApplication.clipboard().text().strip())
        if ok:
            self.import_notation(text,"fen")

    def navigate_move(self, row, column):
        item = self.moves.item(row,column)
        ply = item.data(256) if item else None
        if ply is not None:
            self.game.navigate_to_ply(ply)
            self.board_widget.update()
