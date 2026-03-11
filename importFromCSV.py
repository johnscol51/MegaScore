#importFromCSV.py
# Imports task points from CSV into TaskPoints.csv
# Input format: old_task,name,lat,lon[,dist[,pt]]
# Output: new_task,name,lat,lon,dist,pt  (old_task is ignored)

import os
import csv
import tkinter as tk
from tkinter import filedialog, ttk
from utils import log

def run(DataDir):
    if not DataDir:
        msg = "importFromCSV aborted: DataDir not set"
        log(msg)
        return msg

    imports_dir = os.path.join(DataDir, "imports")
    if not os.path.isdir(imports_dir):
        msg = f"importFromCSV aborted: Missing directory {imports_dir}"
        log(msg)
        return msg

    # ---------------------------------------------------------
    # GUI dialog
    # ---------------------------------------------------------
    parent = tk._default_root
    dlg = tk.Toplevel(parent)
    dlg.title("Import from CSV")
    dlg.geometry("900x350")          # Your preferred size
    dlg.transient(parent)
    dlg.grab_set()
    dlg.focus_set()

    # Make column 0 (main) expand horizontally, column 1 (Advanced) fixed width
    dlg.grid_columnconfigure(0, weight=1)
    dlg.grid_columnconfigure(1, weight=0)
    dlg.grid_rowconfigure(0, weight=1)

    selected_file = tk.StringVar()
    import_task_num = tk.IntVar(value=1)
    debug_var = tk.StringVar(value="N")

    # Main frame (left side) - now expands
    frame = ttk.Frame(dlg, padding=15)
    frame.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)

    ttk.Label(frame, text="Select CSV file:").grid(row=0, column=0, sticky="w", pady=8)

    def choose_file():
        f = filedialog.askopenfilename(
            title="Select CSV File",
            initialdir=imports_dir,
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if f:
            selected_file.set(f)
        dlg.after(50, dlg.focus_force)

    ttk.Button(frame, text="Browse", command=choose_file).grid(row=0, column=0, padx=9, pady=8, sticky="e")

    # File path label expands horizontally
    ttk.Label(frame, textvariable=selected_file, width=80, wraplength=650).grid(
        row=1, column=0, columnspan=2, sticky="ew", pady=10
    )

    ttk.Label(frame, text="Import INTO MegaScore as task number:").grid(
        row=2, column=0, sticky="w", pady=(15, 8)
    )
    ttk.Combobox(
        frame, textvariable=import_task_num, values=list(range(1, 11)), width=5
    ).grid(row=2, column=0, sticky="e", pady=8)

    # Advanced section (right side) - fixed width, vertical fill
    adv_frame = tk.LabelFrame(dlg, text="Advanced — do not change unless required", padx=15, pady=15)
    adv_frame.grid(row=0, column=1, sticky="ns", padx=20, pady=20)

    tk.Label(adv_frame, text="Debug mode:").pack(anchor="w", pady=8)
    ttk.Combobox(
        adv_frame, textvariable=debug_var,
        values=["Y", "N"], width=5, state="readonly"
    ).pack(anchor="w", pady=5)

    result = {"value": None}

    def confirm():
        if not selected_file.get():
            result["value"] = "importFromCSV: No file selected"
        else:
            result["value"] = "OK"
        dlg.destroy()

    def cancel():
        result["value"] = "importFromCSV cancelled by user"
        dlg.destroy()

    dlg.protocol("WM_DELETE_WINDOW", cancel)

    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=3, column=0, columnspan=2, pady=20, sticky="ew")

    tk.Button(btn_frame, text="OK", width=10,  foreground="blue", font=("Helvetica", 10, "bold"),command=confirm).pack(side="left", padx=10)

    ttk.Button(btn_frame, text="Close", width=10, command=cancel).pack(side="left", padx=10)
    parent.wait_window(dlg)

    if result["value"] != "OK":
        log(result["value"])
        return result["value"]

    csv_path = selected_file.get()
    import_task = import_task_num.get()
    debug_mode = (debug_var.get().upper() == "Y")

    log(f"importFromCSV: File = {csv_path}, Import as Task = {import_task}, Debug = {debug_mode}")

    # ---------------------------------------------------------
    # Read CSV
    # ---------------------------------------------------------
    rows = []
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for line_num, line in enumerate(reader, start=1):
                if len(line) < 5:  # Minimum: old_task,name,lat,lon[,dist]
                    if debug_mode:
                        log(f"Debug: Skipping invalid row {line_num} (too few columns): {line}")
                    continue

                # Strip whitespace from all fields
                line = [x.strip() for x in line]

                # Ignore first column (old task number)
                # Take: name = line[1], lat = line[2], lon = line[3], dist = line[4] or "0", pt = line[5] or "0"
                name = line[1]
                lat = line[2]
                lon = line[3]
                dist = line[4] if len(line) > 4 else "0"
                pt = line[5] if len(line) > 5 else "0"

                rows.append((name, lat, lon, dist, pt))

    except Exception as e:
        msg = f"importFromCSV: Error reading CSV: {e}"
        log(msg)
        return msg

    if not rows:
        msg = "importFromCSV: No valid rows found in CSV"
        log(msg)
        return msg

    # NEW: Filter out invalid point names (e.g. "01-fred")
    valid_rows = []
    skipped = []
    valid_prefixes = {"SP", "FP", "TP", "HG", "PHOTO", "P"}
    for name, lat, lon, dist, pt in rows:
        upper = name.upper()
        if any(upper.startswith(prefix) for prefix in valid_prefixes):
            valid_rows.append((name, lat, lon, dist, pt))
        else:
            skipped.append(name)

    if skipped and debug_mode:
        log(f"Skipped {len(skipped)} invalid points: {', '.join(skipped)}")

    rows = valid_rows  # Use only valid rows for output

    # Debug logging (now only shows valid rows)
    if debug_mode:
        log(f"Debug: Parsed and kept {len(rows)} valid rows from CSV:")
        for name, lat, lon, dist, pt in rows:
            log(f" - {name}: {lat}, {lon} (dist={dist}, pt={pt})")

    # ---------------------------------------------------------
    # Append to TaskPoints.csv
    # ---------------------------------------------------------
    output_file = os.path.join(DataDir, "TaskPoints.csv")
    added = 0
    try:
        with open(output_file, "a", encoding="utf-8") as f:
            for name, lat, lon, dist, pt in rows:
                f.write(f"{import_task},{name},{lat},{lon},{dist},{pt}\n")
                added += 1
    except Exception as e:
        msg = f"importFromCSV: Error writing CSV: {e}"
        log(msg)
        return msg

    msg = f"importFromCSV: Added {added} rows to TaskPoints.csv"
    if debug_mode:
        msg += f" (from {len(rows)} parsed rows)"
    log(msg)

    return msg
