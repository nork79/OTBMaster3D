# Licence evidence and release gaps

This directory contains evidence for third-party components, not a licence grant
for OTBMaster3D. No application source licence is changed by this work.

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

The inventory is not a final binary SBOM. Wheel-bundled libraries, transitive Qt
plugins, CPython/Tcl/Tk and VC runtimes must be checked against the actual build.
Do not ship unresolved placeholders as if they satisfy licence obligations.

See ../THIRD_PARTY_NOTICES.md and ../docs/windows-commercial-distribution.md.
