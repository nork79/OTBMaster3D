# Microsoft runtime remediation

## Outcome

**Standalone redistributable issue addressed in the rebuilt installer.** The
2026-09-30 build from commit `87d30dc` passed the standalone Microsoft binary
exclusion check and the packaged application smoke test. The speculative
embedded-code concern is no longer a release blocker; see the decision below.

The maintainer's individual VS Community development basis is already confirmed.
The outstanding provision was section 4's requirement for protective downstream
terms when distributing Microsoft Distributable Code. Merely displaying Microsoft's
prerequisite installer would not establish compliance on every path.

The selected remedy is to stop redistributing the standalone runtime. The user
obtains it directly from Microsoft. This removes our copying/distribution of that
package and its standalone DLLs. No Microsoft restrictions are added to GPL source.

## Changes

- Setup requires an installed x64 runtime version 14.44.35211.0 or newer. Numeric
  registry checks cover both views; an absent or older runtime blocks interactive
  and silent installation before application files are changed.
- Setup provides Microsoft's official download-page address. It does not bundle,
  download, install or uninstall the runtime. An equal/newer runtime is reused.
- The build no longer stages `vc_redist.x64.exe`. The existing native policy checks
  imports against reviewed runtime exports before excluding the standalone DLLs.
- Freezer inputs and the completed folder are checked for runtime filenames. A PE
  company-name check also rejects renamed Microsoft binaries. Unexpected matches
  stop the build for review; nothing is deleted by the audit tool. This safeguard
  does not identify statically incorporated code.
- Ten specifically named old app-local copies are removed during upgrade only
  after the external prerequisite passes. Required imports remain checked.

Users who lack the runtime must install it separately, including offline users.
No Qt rebuild or rendering change is involved.

## Verification

`python -m unittest -v tests.test_external_runtime`: **5 passed**.
See [raw results](evidence/external-runtime-check.txt).

A read-only audit rejected all ten standalone CRT copies in the historical frozen
folder. Auditing the candidate file list with those copies omitted passed. The
files themselves were not removed or replaced. See
[audit evidence](evidence/external-runtime-check.json), which records the unchanged
installer hash. The audit does not claim that a new build exists.

Inno Setup compiled successfully on 2026-09-30. The current smoke report is
`installer-output/smoke-87d30dc.json`. Clean Windows testing
must exercise missing, older, matching and newer runtimes; silent setup; upgrades
from the app-local layout; startup and normal application behaviour.
No clean Windows environment is available yet.

## Embedded-code concern: not a release blocker

On 2026-09-30, the maintainer directed that the speculative embedded Microsoft
code concern be excluded from release blockers. No specific Microsoft function,
byte range or embedded runtime has been identified in the retained
`PySide6/opengl32sw.dll`, and no licence violation has been established.

The retained evidence identifies the Qt-provided Mesa/LLVM renderer. It does not
establish the presence or absence of embedded Microsoft code. This decision
removes the speculative review requirement; it does not assert that the binary
contains no Microsoft code or grant additional redistribution rights.

## Official evidence

- [VS Community terms](https://visualstudio.microsoft.com/license-terms/vs2022-ga-community/):
  retained exact text in `evidence/VS2022-Community-terms.txt`, individual use and
  Distributable Code distribution requirements.
- [REDIST list](https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution):
  standalone packages and DLLs remain subject to the applicable licence.
- [Deployment guidance](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files):
  central runtime servicing and installed-version detection.
- [Supported downloads](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist):
  x64 download and runtime/build-tool version compatibility.
- [CRT linkage](https://learn.microsoft.com/en-us/cpp/c-runtime-library/crt-library-features):
  static libraries versus DLL import libraries; external installation does not
  replace statically incorporated code.

The maintainer has withdrawn the itch.io distribution plan. Its store-terms
review is no longer a release blocker. Overall release status remains blocked
by the remaining requirements.
