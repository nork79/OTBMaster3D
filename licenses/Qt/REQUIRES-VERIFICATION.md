# Remediation update — 2026-09-28

Matching QtBase and PySide setup 6.11.2 source archives and full notices are collected. See docs/licensing/BUILD_AND_REPLACE.md for the limited replacement test and remaining build verification.

## Historical finding

# Qt / PySide6 / Shiboken6: requires verification before release

Observed bindings and Qt runtime: 6.11.2. Intended route: LGPLv3, where available
for the exact shipped libraries. No static linking is proposed.

Authoritative sources:
- https://doc.qt.io/qtforpython-6/licenses.html
- https://doc.qt.io/qt-6/licensing.html
- https://www.qt.io/development/open-source-lgpl-obligations
- https://www.gnu.org/licenses/lgpl-3.0.txt
- https://www.gnu.org/licenses/gpl-3.0.txt
- https://download.qt.io/official_releases/QtForPython/
- https://download.qt.io/official_releases/qt/

Before release obtain the exact applicable licence texts and copyright notices
for PySide6, Shiboken6, Qt libraries/plugins and their embedded dependencies from
the matching source release/build. Archive matching corresponding source and
build/patch information, and establish the required source distribution/offer
mechanism with legal review. A general upstream homepage alone is not that mechanism.

Include LGPLv3 and its referenced GPLv3 text. Preserve applicable third-party
notices (including Qt for Python's non-Qt code). Installed Commercial licence
references do not establish satisfaction of these obligations.

Keep covered DLLs, extension modules, plugins and Python support files replaceable.
Do not impose licence terms that prohibit modifications or reverse engineering
for debugging modifications to the LGPL-covered portions. Supply installation
information where required; validate replacement using a compatible rebuilt Qt.
