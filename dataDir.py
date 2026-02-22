import tkinter as tk
from tkinter import filedialog
from utils import log
########  called by the megaScore menu to set the inital dataDir

def run():
    """Open a directory picker and return the selected path."""
    root = tk.Tk()
    root.withdraw()

    directory = filedialog.askdirectory(title="Select Competition Data Directory")

    if directory:
        log(f"DataDir selected: {directory}")
        return directory

    log("DataDir selection cancelled")
    return None

