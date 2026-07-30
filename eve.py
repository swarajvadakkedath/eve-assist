#!/usr/bin/env python3
"""Eve OS — single-click desktop launcher.

Double-click this file to start Eve.
No terminal required.

Uses LauncherService internally — a reusable orchestration engine
that does NOT own the UI. Future Tauri integration will call
LauncherService directly.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from launcher.launcher import main

if __name__ == "__main__":
    main()
