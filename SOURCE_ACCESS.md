# Corresponding source and your rights

OTBMaster3D source is public under GPL-3.0-only. You may copy, modify and
redistribute it under the licence, including without charge. The application has
no licence key, activation or purchase verification.

## Release 1.6.5

The [GitHub release](https://github.com/nork79/OTBMaster3D/releases/tag/v1.6.5)
provides the installer and the following free downloads together:

- [Exact application source](https://github.com/nork79/OTBMaster3D/releases/download/v1.6.5/OTBMaster3D-1.6.5-application-source.zip)
- [Dependency sources](https://github.com/nork79/OTBMaster3D/releases/download/v1.6.5/OTBMaster3D-1.6.5-dependency-sources.zip)
- [Checksums](https://github.com/nork79/OTBMaster3D/releases/download/v1.6.5/SHA256SUMS.txt)
- [Pairing manifest](https://github.com/nork79/OTBMaster3D/releases/download/v1.6.5/source-release-manifest.json)

See [version-specific build and validation notes](docs/releases/1.6.5-source.md).
The application archive alone does not contain all dependency source. Use both
archives; the dependency bundle includes the retained engine, runtime, library
and artwork inputs, plus Rodent IV source and its build recipe.

## Find the source for an installed version

Open Help > About for the version and Help > Open Source Licences for offline
notices and build metadata. The installed `source/OTBMaster3D-source.zip`
contains the application snapshot, assets, tests and build scripts. Its hash and
base commit are recorded in `build-info.json`; per-file hashes are stored in
`source/application-files.sha256.json`. Current `main` may contain later changes.

The unchanged 1.6.5 snapshot contains historical private-repository and blocked
publication notices. Those describe preparation status before publication; use
the version-specific release notes and release manifest for current download
locations. Historical reports remain evidence for their named builds only.

For dependency build and compatible shared-library replacement instructions,
see [BUILD_AND_REPLACE.md](docs/licensing/BUILD_AND_REPLACE.md). Third-party
components retain their own terms; see [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).
The Microsoft Visual C++ runtime is a separately installed prerequisite.

Public installers are distributed with matching source downloads at no additional
charge. Retain those sources while offering the binary and meet continuing source
retention obligations. This document adds no restrictions to GPL rights and is
not a written source offer under section 6(b).
