#!/usr/bin/env python3

# launcher.py
# Standalone launcher for the Map Point Editor.
# Can be run directly: python launcher.py [optional_data_dir]
# Or imported and called: from launcher import launch; launch(data_dir)

import sys
import tkinter as tk
from taskCreator import run as editor_run

def launch(data_dir=None):
    editor_run(data_dir)

if __name__ == "__main__":
    data_dir = None
    if len(sys.argv) > 1:
        data_dir = sys.argv[1]
        if not os.path.isdir(data_dir):
            print(f"Warning: {data_dir} is not a valid directory. Launching without pre-set DataDir.")
            data_dir = None

    launch(data_dir)
