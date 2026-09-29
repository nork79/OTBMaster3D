# Microsoft runtime: external prerequisite

Current packaging requires Microsoft Visual C++ x64 Redistributable 14.44.35211.0
or newer to be installed separately. Setup neither bundles nor downloads it.
Standalone runtime DLLs are excluded. Existing installers predate this policy.
If the runtime is missing or too old, interactive and silent Setup stop before
changing application files and provide Microsoft's download-page address:
https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist
Users obtain and install the x64 runtime directly from Microsoft under its terms.
Uninstalling OTBMaster3D does not remove the shared runtime.

The maintainer confirms an individual developing their own application using
Visual Studio Community 2022. The retained Community terms are supplied as
distribution evidence, not as an application EULA. Microsoft-specific terms do
not restrict copying, modification or redistribution of GPL-covered source.

This removes direct redistribution of the standalone runtime from the planned
package. It does not establish rights for any Microsoft code statically embedded
in upstream libraries. That narrowly scoped review remains open, especially for
the software OpenGL binary. See docs/licensing/MICROSOFT_RUNTIME_REMEDIATION.md
in the source archive. No Microsoft-specific condition is added to the GPL source.

Authoritative sources:
- https://visualstudio.microsoft.com/license-terms/vs2022-ga-community/
- https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution
- https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files
