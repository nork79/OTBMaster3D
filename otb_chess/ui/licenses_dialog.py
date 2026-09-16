"""Lightweight, offline third-party licence information."""

import json
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPlainTextEdit, QDialogButtonBox
from otb_chess.services.settings import APP_DIR


def show_licenses(parent):
    dialog = QDialog(parent)
    dialog.setObjectName('openSourceLicencesDialog')
    dialog.setWindowTitle('Open Source Licences')
    dialog.resize(740,540)
    layout = QVBoxLayout(dialog)
    heading = QLabel('OTBMaster3D includes third-party open-source software.\n'
                     f'Full notices: {APP_DIR / "THIRD_PARTY_NOTICES.md"}\n'
                     f'Licence files: {APP_DIR / "licenses"}')
    heading.setWordWrap(True)
    layout.addWidget(heading)
    text = QPlainTextEdit()
    text.setReadOnly(True)
    try:
        data = json.loads((APP_DIR/'third_party_bom.json').read_text(encoding='utf-8'))
        text.setPlainText('\n\n'.join(f"{c['name']} — {c['version']}\n{c['apparent_license']}\n"
                                      f"Category: {c['category']}; redistribution: {c['redistribution']}"
                                      for c in data['components']))
    except (OSError,ValueError,KeyError) as exc:
        text.setPlainText(f'Licence inventory unavailable: {exc}\nSee the notices path above.')
    layout.addWidget(text)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    dialog.exec()
    dialog.deleteLater()
