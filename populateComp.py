import os
import csv
import tkinter as tk
from tkinter import filedialog, ttk
from utils import log


def run(DataDir):
    if not DataDir:
        msg = "populateComp aborted: DataDir not set"
        log(msg)
        return msg

    comp_file = os.path.join(DataDir, "CompDetails.csv")

    # ---------------------------------------------------------
    # Load existing values if file exists
    # ---------------------------------------------------------
    defaults = {
        "name": "",
        "date": "",
        "HG-score": "",
        "TP-score": "",
        "photo-Score": "",
        "time-Score": "",
        "igcFileLocation": "",
        "pilotFile": "",
        "tba1": "",
        "tba2": ""
    }

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
    parent = tk._default_root
    dlg = tk.Toplevel(parent)
    dlg.title("Competition Details")

    dlg.transient(parent)
    dlg.grab_set()
    dlg.focus_set()

    entries = {}

    frame = ttk.Frame(dlg, padding=10)
    frame.grid(row=0, column=0)

    # Helper to add a labeled entry
    def add_field(label, key, row):
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=3)
        var = tk.StringVar(value=defaults[key])
        ent = ttk.Entry(frame, textvariable=var, width=50)
        ent.grid(row=row, column=1, sticky="w")
        entries[key] = var

    # Basic fields
    add_field("Competition Name:", "name", 0)
    add_field("Date:", "date", 1)
    add_field("HG Score:", "HG-score", 2)
    add_field("TP Score:", "TP-score", 3)
    add_field("Photo Score:", "photo-Score", 4)
    add_field("Time Score:", "time-Score", 5)

    # ---------------------------------------------------------
    # igcFileLocation (folder picker)
    # ---------------------------------------------------------
    ttk.Label(frame, text="IGC File Location:").grid(row=6, column=0, sticky="w", pady=3)

    igc_var = tk.StringVar(value=defaults["igcFileLocation"])
    entries["igcFileLocation"] = igc_var

    def choose_folder():
        folder = filedialog.askdirectory(
            title="Select IGC File Location",
            initialdir=defaults["igcFileLocation"] or DataDir
        )
        if folder:
            igc_var.set(folder)
        dlg.after(50, dlg.focus_force)

    folder_frame = ttk.Frame(frame)
    folder_frame.grid(row=6, column=1, sticky="w")

    ttk.Entry(folder_frame, textvariable=igc_var, width=50).pack(side="left")
    ttk.Button(folder_frame, text="Browse", command=choose_folder).pack(side="left", padx=5)

    # ---------------------------------------------------------
    # pilotFile (CSV file picker)
    # ---------------------------------------------------------
    ttk.Label(frame, text="Pilot File (CSV):").grid(row=7, column=0, sticky="w", pady=3)

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
        dlg.after(50, dlg.focus_force)

    pilot_frame = ttk.Frame(frame)
    pilot_frame.grid(row=7, column=1, sticky="w")

    ttk.Entry(pilot_frame, textvariable=pilot_var, width=50).pack(side="left")
    ttk.Button(pilot_frame, text="Browse", command=choose_pilot_file).pack(side="left", padx=5)

    # Extra fields
    add_field("TBA1:", "tba1", 8)
    add_field("TBA2:", "tba2", 9)

    # ---------------------------------------------------------
    # OK / Cancel
    # ---------------------------------------------------------
    result = {"value": None}

    def confirm():
        result["value"] = "OK"
        dlg.destroy()

    def cancel():
        result["value"] = "populateComp cancelled by user"
        dlg.destroy()

    dlg.protocol("WM_DELETE_WINDOW", cancel)

    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=10, column=0, columnspan=2, pady=10)

    ttk.Button(btn_frame, text="OK", width=10, command=confirm).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Cancel", width=10, command=cancel).pack(side="left", padx=5)

    parent.wait_window(dlg)

    # ---------------------------------------------------------
    # Handle result
    # ---------------------------------------------------------
    if result["value"] != "OK":
        log(result["value"])
        return result["value"]

    # ---------------------------------------------------------
    # Write updated CSV
    # ---------------------------------------------------------
    try:
        with open(comp_file, "w", encoding="utf-8") as f:
            writer = csv.writer(f)
            for key in defaults.keys():
                writer.writerow([key, entries[key].get()])
    except Exception as e:
        msg = f"populateComp: Error writing CompDetails.csv: {e}"
        log(msg)
        return msg

    msg = "populateComp: Competition details saved"
    log(msg)
    return msg

