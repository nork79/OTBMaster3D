# Release blocker recheck

Superseded for native-runtime status by the
[2026-09-29 remediation](NATIVE_RUNTIME_REMEDIATION.md). This file retains the
earlier baseline; consult the new inventory and verification results.

## Resolved: missing libyuv source

The archive endpoint still failed, but the official Git server worked. The exact
revision is `644251f252a84bf8ce91ff0aca86a9b16b069ab8`. A source archive was created
using `git archive`, with SHA-256
`b2d5ad4d8ecc0a713f0f7cc7ea0bd99c04efdfdc01da7f2280b62505856fed90`.
LICENSE, PATENTS and AUTHORS are retained in licenses/libyuv. The source inventory
records the Git origin and reproduction command. No substitute revision was used.

## Verified: installed Microsoft tools; entitlement narrowed

Inspection found Visual Studio Community 2022 **17.14.37516.0**, MSVC toolset
**14.44.35207**, and x64 CRT redistributables **14.44.35112**. The compiler exists
outside the normal PATH; the earlier PATH-only check did not establish its absence.

The [Community terms](https://visualstudio.microsoft.com/license-terms/vs2022-ga-community/)
permit individual development of applications for sale and organizational work on
OSI-licensed applications. Redistribution is conditional on the licence and
[REDIST list](https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution).
The official terms document and extracted text are retained under evidence/.

**BLOCKED for the exact current DLL set:** the packaged CRT hashes do not match
this installed redistributable set. MSVCR120, used by GLFW, is not established as
covered by the discovered VS2022 files. The installation supplies useful evidence,
but does not prove entitlement for every copied runtime. See
[the baseline comparison](microsoft-runtime-check.json).

Possible next remediation is to rebuild GLFW with the available compiler and use
an identified supported CRT set, then verify all imports and test on a clean
Windows installation. Do not substitute CRT files blindly or delete required DLLs.
Review the Microsoft-specific distribution conditions separately from the GPL;
do not apply Microsoft restrictions to the application's GPL-covered source.

## Build and native verification

The new frozen app passed a smoke test with byte-distinct LGPL replacements.
This verifies library loading without content locks, not a source-built Qt.
The first installer attempt failed on very long source-notice filenames. Notice
staging now uses content hashes as short installed filenames, with an index mapping
them to original paths. Upstream notice bytes and source-tree paths are retained.

Exact native provenance/build inputs still need review, including the software
OpenGL DLL and static codecs. Bit-identical reproduction is not itself a blanket
GPL requirement; the unresolved issue is establishing the required preferred
source and build/install materials for the actual redistributed components.

## Public source URLs: publication prerequisite

The source archives can be prepared locally, but real public download URLs cannot
be verified without publication. No tag, upload, repository visibility change or
store mutation is authorized in this task. This remains a publication prerequisite,
not evidence that a local source archive is missing. Link the exact free archives
beside the paid installer and check signed-out access before release.

**Overall status remains BLOCKED.** This report supersedes the earlier libyuv
download failure and compiler-discovery findings, not the unresolved native terms.
