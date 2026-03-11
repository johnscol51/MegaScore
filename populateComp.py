# populateComp.py
# GUI to edit/save competition details in CompDetails.csv

import os
import csv
import tkinter as tk
from tkinter import ttk , filedialog
from utils import log

def run(DataDir):
    if not DataDir:
        msg = "populateComp aborted: DataDir not set"
        log(msg)
        return msg

    comp_file = os.path.join(DataDir, "CompDetails.csv")

    # ---------------------------------------------------------
    # Default values (with requested defaults for scores)
    # ---------------------------------------------------------
    defaults = {
        "name": "",
        "date": "summer 2026?",
        "HG-score": "100",
        "TP-score": "50",
        "photo-Score": "100",
        "time-Score": "100",
        "igcFileLocation": "",
        "pilotFile": "",
        "tba1": "",
        "tba2": ""
    }

    # Load existing values if file exists
    if os.path.isfile(comp_file):
        try:
            with open(comp_file, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2:
                        key, val = row[0].strip(), row[1].strip()
                        if key in defaults:
                            defaults[key] = val
        except Exception as e:
            msg = f"populateComp: Error reading CompDetails.csv: {e}"
            log(msg)
            return msg

    # ---------------------------------------------------------
    # GUI dialog
    # ---------------------------------------------------------
    dlg = tk.Toplevel()
    dlg.title("Competition Details")
    dlg.geometry("920x420")  # Wider and tall enough for all fields
    dlg.transient(tk._default_root)
    dlg.grab_set()
    dlg.focus_set()

    entries = {}
    frame = tk.Frame(dlg, padx=20, pady=20)
    frame.pack(fill="both", expand=True)

    # Helper to add a labeled entry
    def add_field(label, key, row):
        tk.Label(frame, text=label).grid(row=row, column=0, sticky="e", pady=5, padx=(0, 10))
        var = tk.StringVar(value=defaults[key])
        ent = tk.Entry(frame, textvariable=var, width=60)
        ent.grid(row=row, column=1, sticky="w")
        entries[key] = var

    # Basic fields
    add_field("Competition Name:", "name", 0)
    add_field("Date:", "date", 1)
    add_field("HG Score:", "HG-score", 2)
    add_field("TP Score:", "TP-score", 3)
    add_field("Photo Score:", "photo-Score", 4)
    add_field("Time Score:", "time-Score", 5)

    # IGC File Location (folder picker)
    tk.Label(frame, text="IGC File Location:").grid(row=6, column=0, sticky="e", pady=5, padx=(0, 10))
    igc_var = tk.StringVar(value=defaults["igcFileLocation"])
    entries["igcFileLocation"] = igc_var

    def choose_folder():
        folder = filedialog.askdirectory(
            title="Select IGC File Location",
            initialdir=defaults["igcFileLocation"] or DataDir
        )
        if folder:
            igc_var.set(folder)

    folder_frame = tk.Frame(frame)
    folder_frame.grid(row=6, column=1, sticky="w")
    tk.Entry(folder_frame, textvariable=igc_var, width=75).pack(side="left", padx=(0, 5))
    tk.Button(folder_frame, text="Browse", command=choose_folder).pack(side="left")

    # Pilot File (CSV picker)
    tk.Label(frame, text="Pilot File (CSV):").grid(row=7, column=0, sticky="e", pady=5, padx=(0, 10))
    pilot_var = tk.StringVar(value=defaults["pilotFile"])
    entries["pilotFile"] = pilot_var

    def choose_pilot_file():
        f = filedialog.askopenfilename(
            title="Select Pilot CSV File",
            initialdir=defaults["pilotFile"] or DataDir,
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if f:
            pilot_var.set(f)

    pilot_frame = tk.Frame(frame)
    pilot_frame.grid(row=7, column=1, sticky="w")
    tk.Entry(pilot_frame, textvariable=pilot_var, width=75).pack(side="left", padx=(0, 5))
    tk.Button(pilot_frame, text="Browse", command=choose_pilot_file).pack(side="left")

    # Extra fields
    add_field("TBA1:", "tba1", 8)
    add_field("TBA2:", "tba2", 9)

    # OK / Cancel buttons
    btn_frame = tk.Frame(frame)
    btn_frame.grid(row=10, column=0, columnspan=2, pady=20, sticky="ew")

    tk.Button(btn_frame, text="OK", width=10, foreground="blue", font=("Helvetica", 10, "bold"), command=lambda: dlg.destroy()).pack(side="left", padx=10)
#    ttk.Button(btn_frame, text="OK", width=10, command=lambda: dlg.destroy(),
#               style="Blue.TButton").pack(side="left", padx=10)

    ttk.Button(btn_frame, text="Close", width=10, command=dlg.destroy).pack(side="left", padx=10)

    # Wait for dialog to close
    dlg.wait_window(dlg)

    # ---------------------------------------------------------
    # Save if OK was pressed (dlg.destroy() called from OK)
    # ---------------------------------------------------------
    if dlg.winfo_exists() == 0:  # Dialog closed via OK or Cancel
        # Check if OK was pressed (simple way: check if entries still exist)
        try:
            entries["name"].get()  # If dialog closed via Cancel, this will error
            # Save
            with open(comp_file, "w", encoding="utf-8") as f:
                writer = csv.writer(f)
                for key in defaults:
                    writer.writerow([key, entries[key].get()])
            msg = "populateComp: Competition details saved"
            log(msg)
            return msg
        except:
            msg = "populateComp cancelled by user"
            log(msg)
            return msg
    else:
        msg = "populateComp cancelled by user"
        log(msg)
        return msg
