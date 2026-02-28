#!/usr/bin/env python3
##  MegaScore.py
import tkinter as tk
from tkinter import ttk
import subprocess
import sys,os
from pathlib import Path
from collections import deque
from datetime import datetime
from utils import init_logger



def app_dir():
    """Return the directory where the MegaScore app is running from."""
    if getattr(sys, 'frozen', False):
        # Running as a packaged executable
        return os.path.dirname(sys.executable)
    else:
        # Running from source
        return os.path.dirname(os.path.abspath(__file__))



class MegaScoreApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.DataDir = None # <— THIS is the correct place

        self.title("MegaScore")
        self.geometry("1000x650")   # Larger default window

        log_path = os.path.join(app_dir(), "debug.log")
        init_logger(log_path)

        # store last 5 status messages
        self.status_messages = deque(maxlen=5)

        # ---------------------------------------------------------
        # Exit button (top-right)
        # ---------------------------------------------------------
        exit_btn = tk.Button(self, text="Exit", command=self.quit, bg="#cc0000", fg="white")
        exit_btn.pack(side="top", anchor="ne", padx=10, pady=5)

        # ---------------------------------------------------------
        # Main notebook (tabs)
        # ---------------------------------------------------------
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        # create tabs
        self.admin_tab = self.create_tab("Admin")
        self.task_tab = self.create_tab("Task Importer")
        self.scorer_tab = self.create_tab("Scorer")
        self.results_tab = self.create_tab("Results")

        # populate tabs
        self.build_admin_tab()
        self.build_task_importer_tab()
        self.build_scorer_tab()
        self.build_results_tab()
        #self.build_placeholder_tab(self.results_tab, "Results")

        # ---------------------------------------------------------
        # Bottom container (branding + status bar)
        # ---------------------------------------------------------
        bottom_container = tk.Frame(self)
        bottom_container.pack(side="bottom", fill="x")

        # Branding area (left side)
        branding_frame = tk.Frame(bottom_container)
        branding_frame.pack(side="left", padx=10, pady=5)

        # Blue box
        tk.Frame(branding_frame, width=20, height=20, bg="blue").pack(side="left", padx=5)

        # Yellow box
        tk.Frame(branding_frame, width=20, height=20, bg="yellow").pack(side="left", padx=5)

        # ---------------------------------------------------------
        # Status bar (right side)
        # ---------------------------------------------------------
        status_frame = tk.Frame(bottom_container, relief="sunken", bd=1)
        status_frame.pack(side="right", fill="x", expand=True)

        self.status_label = tk.Label(
            status_frame,
            anchor="w",
            justify="left",
            bg="#e6e6e6"   # lighter grey background
        )
        self.status_label.pack(fill="x")

        self.update_status("MegaScore started")

    # ---------------------------------------------------------
    # Helper: create a tab frame
    # ---------------------------------------------------------
    def create_tab(self, name):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=name)
        return frame

    # ---------------------------------------------------------
    # Helper: run external script
    # ---------------------------------------------------------
    def run_script(self, script_name):
        try:
            module = __import__(script_name)

            # Special case: dataDir returns a directory
            if script_name == "dataDir":
                selected = module.run()
                if selected:
                    self.DataDir = selected
                    self.update_status(f"DataDir set to: {self.DataDir}")
                else:
                    self.update_status("DataDir not changed")
                return

            # Prevent running other modules if DataDir is not set
            if not self.DataDir:
                self.update_status("Cannot run this option: DataDir has not been set")
                return

            # All other modules receive DataDir
            if hasattr(module, "run"):
                result = module.run(self.DataDir)
                if isinstance(result, str):
                    self.update_status(result)
                else:
                    self.update_status(f"{script_name} executed")
            else:
                self.update_status(f"{script_name} has no run() function")

        except Exception as e:
            self.update_status(f"Error running {script_name}: {e}")

    # ---------------------------------------------------------
    # Admin tab
    # ---------------------------------------------------------
    def build_admin_tab(self):
        options = [
            "dataDir",
            "populateComp",
            "readme",
            "readDebug"
        ]
        self.build_button_list(self.admin_tab, options)

    # ---------------------------------------------------------
    # Task Importer tab
    # ---------------------------------------------------------
    def build_task_importer_tab(self):
        options = [
            "taskCreator",
            "importFromKML",
            "importFromPesto",
            "importFromCSV",
            "TaskPointsReview"
        ]
        self.build_button_list(self.task_tab, options)

    # ---------------------------------------------------------
    # Scorer tab
    # ---------------------------------------------------------
    def build_scorer_tab(self):
        options = [
            "ScoreNavTask",
            "SpotLanding",
            "ScoreCircle",
            "NavKMLgen",
        ]
        self.build_button_list(self.scorer_tab, options)

    # ---------------------------------------------------------
    # results tab
    # ---------------------------------------------------------
    def build_results_tab(self):
        options = [
            "NavResults",
            "SpotResults",
            "CircleResults",
            "OverallResults",
        ]
        self.build_button_list(self.results_tab, options)

    # ---------------------------------------------------------
    # Placeholder tabs for Scorer + Results
    # ---------------------------------------------------------
    def build_placeholder_tab(self, tab, name):
        label = tk.Label(tab, text=f"{name} options will be added later.", font=("Arial", 14))
        label.pack(pady=20)

    # ---------------------------------------------------------
    # Helper: build a vertical list of buttons
    # ---------------------------------------------------------
    def build_button_list(self, parent, options):
        frame = tk.Frame(parent)
        frame.pack(pady=20)

        for opt in options:
            btn = tk.Button(
                frame,
                text=opt,
                width=25,
                command=lambda o=opt: self.run_script(o)
            )
            btn.pack(pady=5)

    # ---------------------------------------------------------
    # Status bar update
    # ---------------------------------------------------------
    def update_status(self, message):
        # Update GUI status messages
        self.status_messages.appendleft(message)
        text = "\n".join(self.status_messages)
        self.status_label.config(text=text)

        # Write to debug.log via utils
        from utils import log
        log(message)

    def write_log(self, message):
        """Append a timestamped message to debug.log in the app directory."""
        log_path = os.path.join(app_dir(), "debug.log")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            # If logging fails, at least show it in the GUI
            self.status_messages.appendleft(f"Logging error: {e}")




if __name__ == "__main__":
    app = MegaScoreApp()
    app.mainloop()

