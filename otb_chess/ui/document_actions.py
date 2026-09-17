"""File and clipboard actions for chess notation."""

from pathlib import Path
from PySide6.QtWidgets import QApplication, QFileDialog, QInputDialog, QMessageBox
from otb_chess.core.documents import read_pgn, read_fen


class DocumentActions:
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
