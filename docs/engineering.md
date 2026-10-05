# Engineering overview

OTBMaster3D is an independent desktop engineering portfolio project by nork79.
It brings together a Python/Qt interface, OpenGL rendering, external chess engines,
persistent study data and a Windows distribution pipeline. The public repository
and matching release sources make those implementation choices inspectable.

## Guided code tour

| Area | Start here | What to inspect |
| --- | --- | --- |
| Desktop interface | [desktop_ui.py](../otb_chess/ui/desktop_ui.py) | Qt actions, clocks, bookmark restoration and coordination with the board |
| Graphics | [graphics](../otb_chess/graphics) | Board and piece rendering, resources and visual configuration |
| Application services | [services](../otb_chess/services) | Engine difficulty, bookmark actions and document workflows |
| Production rules boundary | [chess_backend](../otb_chess/chess_backend) | Encapsulation of the existing python-chess rules provider |
| Candidate rules core | [core README](../otb_chess_core/README.md) | Owned immutable moves, provider isolation and explicit legality/history policies |
| Regression coverage | [tests](../tests) | Chess rules, notation, persistence, UI contracts and live engine behavior |
| Distribution | [packaging](../packaging), [tools](../tools) | Frozen payload preparation, native runtime checks and source pairing |

## Design decisions and tradeoffs

The Qt desktop interface and OpenGL board need coordinated lifecycle and input
handling. Engine searches and bookmark restoration also interact with live game
state: restoring a position preserves engine preferences and pauses clocks;
resetting a study position explicitly resets both clocks. Regression tests cover
these user-visible contracts.

Persistent settings and session recovery use atomic writes. Bookmarks organize
positions into nested folders, while PGN/FEN support provides standard interchange.
The [notation boundary](pgn-history-boundary.md) documents how transfer objects
separate notation/history work from provider-owned state.

Production uses python-chess. The separate `otb_chess_core` package evaluates a
cozy-chess-backed rules adapter with owned data and a narrow provider boundary.
It is not the production rules engine. See the [architecture notes](chess_core_architecture.md)
and [migration assessment](production-rules-switch-readiness.md) for the scope and
remaining work. This distinction keeps experimental architecture claims separate
from behavior shipped to users.

The application integrates existing UCI engines; it does not implement Stockfish,
Fairy-Stockfish or Rodent's search algorithms. Third-party engines, libraries and
artwork are attributed in [the notices](../THIRD_PARTY_LICENSES.md).

## Verification and delivery

[Windows CI](../.github/workflows) separates tests requiring only Python
dependencies from integration tests that install and run chess engines. Native
rendering needs a desktop/OpenGL context. [CONTRIBUTING.md](../CONTRIBUTING.md)
describes the environments and commands.

The 1.6.5 build record reports 268 passing tests, followed by all eight piece-set
tests passing with desktop access after a sandbox Tcl setup error. Its packaged
smoke test passed. These are recorded build results, not a claim of universal
hardware compatibility. Clean Windows install, upgrade and uninstall testing
remain pending; the installer is unsigned.

Release engineering retains the exact application source archive, file hashes,
dependency sources and build metadata alongside each binary. That supports source
inspection and modification; it does not establish bit-for-bit reproducibility.
See [release 1.6.5](releases/1.6.5-source.md) and [Windows packaging](windows-installer.md).

## Try it or contribute

Use the [installer](https://github.com/nork79/OTBMaster3D/releases/tag/v1.6.5)
for a quick demonstration, or follow [source setup](../README.md#run-and-build-from-source).
Useful contribution areas include clean-machine validation, focused regression
fixes and documentation improvements. Maintenance is [best effort](MAINTENANCE.md).
