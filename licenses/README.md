# Licence evidence and release gaps

## Remediation update — 2026-09-28

Current evidence: [../docs/licensing/REMEDIATION.md](../docs/licensing/REMEDIATION.md).
Full PyOpenGL 3.1.10 text is now retained in licenses/PyOpenGL/LICENSE.txt;
Qt/PySide and native source notices are inventoried in notice-inventory.json.
Packaging includes only Stockfish and Fairy-Stockfish engine resources. The maintainer confirmed original code/icon/sound/screenshot rights.
Earlier unresolved statements below are historical where superseded by this update.
Existing third-party attribution and licence texts remain applicable.

This directory contains evidence for third-party components. OTBMaster3D application
source is GPL-3.0-only under the root LICENSE; these components retain their own licences.

Files under package-name directories were copied byte-for-byte from installed
distribution metadata by `tools/audit_dependencies.py`. Their original paths and
SHA-256 hashes are in `third_party_bom.json`. `assets/Staunton-MIT.txt` is copied
from the bundled model licence. Files named `REQUIRES-VERIFICATION.md` are notices,
**not substituted or fabricated licence texts**.

The installed PySide6, Essentials, Addons and Shiboken wheels supplied only a
`LicenseRef-Qt-Commercial.txt` in their metadata licence directories. Its inclusion
here is evidence, not a commercial entitlement and not the proposed licence route.
Obtain the matching LGPLv3/GPLv3 texts, component notices and source materials
before release. See Qt/REQUIRES-VERIFICATION.md.

The official GNU LGPLv3 text is now in Qt/LGPL-3.0.txt, alongside the official
root GPLv3 text. The Inno Setup 6.4.3 licence is retained in InnoSetup/LICENSE.txt.
These additions do not resolve the version-specific Qt notices or source gaps.

The inventory is not a final binary SBOM. Wheel-bundled libraries, transitive Qt
plugins, CPython/Tcl/Tk and VC runtimes must be checked against the actual build.
Do not ship unresolved placeholders as if they satisfy licence obligations.

See ../THIRD_PARTY_NOTICES.md and ../docs/windows-commercial-distribution.md.
