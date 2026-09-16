# Qt module audit

Generated import evidence (including filenames/lines): `third_party_bom.json`.
Audit environment: PySide6/Shiboken6/Qt 6.11.2. Scan covers application, tools and
tests; it does not prove the transitive native dependency closure of a build.

| Imported module | Use | Apparent route / authoritative reference |
| --- | --- | --- |
| PySide6.QtCore | Runtime | LGPLv3 available: https://doc.qt.io/qt-6/qtcore-index.html |
| PySide6.QtGui | Runtime | LGPLv3 available: https://doc.qt.io/qt-6/qtgui-index.html |
| PySide6.QtWidgets | Runtime | LGPLv3 available: https://doc.qt.io/qt-6/qtwidgets-index.html |
| PySide6.QtOpenGLWidgets | Runtime | Qt OpenGL component, LGPLv3 available: https://doc.qt.io/qt-6/qtopengl-index.html |
| PySide6.QtTest | Tests only | LGPLv3 available: https://doc.qt.io/qt-6/qttest-index.html |

QtOpenGL is a transitive native dependency of QtOpenGLWidgets, even though the app
does not import its Python module. QtCore/Gui/Widgets, OpenGL and OpenGLWidgets are
the intended native module allowlist. QtTest is not intended for deployment.

No directly imported module was identified as GPL-only. This is **not** a claim
that the entire Addons wheel or all plugins are LGPL-compatible. Qt Charts, Data
Visualization, Graphs and other modules have different conditions; do not add
them without checking their version-specific licensing. See the authoritative
module list at https://doc.qt.io/qt-6/licensing.html . All unlisted Qt modules
are rejected by the draft packaging check, rather than maintaining a potentially
incomplete GPL-only denylist.

Plugins and embedded codecs have additional notices. Windows platform plugin
qwindows.dll is expected; optional imageformats/platform plugins must be selected
and verified separately. Do not copy QML, multimedia, WebEngine, designer tools,
translations or the entire PySide6 installation as a convenience.
