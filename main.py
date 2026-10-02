# Copyright (C) 2026 nork79
# SPDX-License-Identifier: GPL-3.0-only
"""OTBMaster3D application entry point."""


def main():
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == "--smoke-test":
        from otb_chess.packaging_smoke import run
        return run(sys.argv[2])
    from otb_chess.ui.desktop_ui import run
    run()


if __name__ == "__main__":
    main()
