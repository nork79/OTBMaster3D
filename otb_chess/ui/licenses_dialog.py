# Copyright (C) 2026 norKI79
# SPDX-License-Identifier: GPL-3.0-only
"""Offline application licence, source information and third-party notices."""
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPlainTextEdit, QDialogButtonBox, QComboBox
from otb_chess.services.settings import APP_DIR
from otb_chess.version import __version__

REPOSITORY_URL = 'https://github.com/norKI79/OTBMaster3D'


def licence_documents(root=APP_DIR):
    """Include notices stored beside bundled assets and engines."""
    paths = [root / name for name in (
        'LICENSE', 'COPYRIGHT.md', 'THIRD_PARTY_LICENSES.md',
        'THIRD_PARTY_NOTICES.md', 'SOURCE_ACCESS.md',
    )]
    if (root / 'build-info.json').is_file():
        paths.append(root / 'build-info.json')
    for folder in ('licenses', 'assets', 'books', 'engines'):
        for path in sorted((root / folder).rglob('*')):
            if path.is_file() and (
                folder == 'licenses'
                or any(word in path.name.lower() for word in ('license', 'licence', 'copying', 'copyright', 'notice'))
                or path.name == 'AUTHORS'
            ):
                paths.append(path)
    return paths


def show_licenses(parent, initial='THIRD_PARTY_LICENSES.md'):
    dialog = QDialog(parent)
    dialog.setObjectName('openSourceLicencesDialog')
    dialog.setWindowTitle('Open Source Licences')
    dialog.resize(740, 540)
    layout = QVBoxLayout(dialog)
    layout.addWidget(QLabel('Complete licence texts and notices stored with this installation.'))
    selector = QComboBox()
    selector.setAccessibleName('Licence document')
    text = QPlainTextEdit()
    text.setReadOnly(True)
    text.setAccessibleName('Licence text')
    for path in licence_documents():
        selector.addItem(path.relative_to(APP_DIR).as_posix(), path)

    def display(index):
        path = selector.itemData(index)
        try:
            content = path.read_bytes()
            try:
                document = content.decode('utf-8-sig')
            except UnicodeDecodeError:
                # Retained OpenJPEG notice uses Latin-1; preserve original bytes.
                document = content.decode('latin-1')
            text.setPlainText(document)
        except (OSError, UnicodeError) as exc:
            text.setPlainText(f'Document unavailable: {path.name}\n{exc}')

    selector.currentIndexChanged.connect(display)
    selector.setCurrentIndex(max(0, selector.findText(initial)))
    display(selector.currentIndex())
    layout.addWidget(selector)
    layout.addWidget(text)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    dialog.exec()
    dialog.deleteLater()


def show_about(parent):
    dialog = QDialog(parent)
    dialog.setWindowTitle('About OTBMaster3D')
    layout = QVBoxLayout(dialog)
    layout.addWidget(QLabel(
        f'OTBMaster3D\nVersion {__version__}\n\nCopyright (C) 2026 norKI79\n\n'
        'Licensed under GNU GPL version 3.\nFree and open-source software.\n\n'
        'Uses Qt, PySide6 and Shiboken under LGPL version 3.\n'
        'Copyright The Qt Company Ltd. and contributors.\n'
        'Licence texts and notices: Help > Open Source Licences.'
    ))
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    for title, action in (
        ('GNU GPL version 3', lambda: show_licenses(dialog, 'LICENSE')),
        ('Open Source Licences', lambda: show_licenses(dialog, 'THIRD_PARTY_LICENSES.md')),
        ('Corresponding source', lambda: show_licenses(dialog, 'SOURCE_ACCESS.md')),
        ('GitHub repository', lambda: QDesktopServices.openUrl(QUrl(REPOSITORY_URL))),
    ):
        buttons.addButton(title, QDialogButtonBox.ButtonRole.ActionRole).clicked.connect(action)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    dialog.exec()
    dialog.deleteLater()
