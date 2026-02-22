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

    dlg.transient(parent)
    dlg.grab_set()
    dlg.focus_set()

    selected_file = tk.StringVar()
    import_task_num = tk.IntVar(value=1)

    frame = ttk.Frame(dlg, padding=10)
    frame.grid(row=0, column=0)

    ttk.Label(frame, text="Select CSV file:").grid(row=0, column=0, sticky="w")

    def choose_file():
        f = filedialog.askopenfilename(
            title="Select CSV File",
            initialdir=imports_dir,
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if f:
            selected_file.set(f)
        dlg.after(50, dlg.focus_force)

    ttk.Button(frame, text="Browse", command=choose_file).grid(row=0, column=1, padx=5)
    ttk.Label(frame, textvariable=selected_file, width=65).grid(
        row=1, column=0, columnspan=2, sticky="w"
    )

    ttk.Label(frame, text="Import INTO MegaScore as task number:").grid(
        row=2, column=0, sticky="w", pady=(10, 0)
    )
    ttk.Combobox(
        frame, textvariable=import_task_num, values=list(range(1, 11)), width=5
    ).grid(row=2, column=1, sticky="w")

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
    btn_frame.grid(row=3, column=0, columnspan=2, pady=10)

    ttk.Button(btn_frame, text="OK", width=10, command=confirm).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Cancel", width=10, command=cancel).pack(side="left", padx=5)

    parent.wait_window(dlg)

    if result["value"] != "OK":
        log(result["value"])
        return result["value"]

    csv_path = selected_file.get()
    import_task = import_task_num.get()

    log(f"importFromCSV: File selected = {csv_path}, Import as Task = {import_task}")

    # ---------------------------------------------------------
    # Read CSV
    # ---------------------------------------------------------
    rows = []
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for line in reader:
                if len(line) < 4:
                    continue

                # 4-column format: task,name,lat,lon
                if len(line) == 4:
                    _, name, lat, lon = line
                    dist = "0"
                    pt = "0"

                # 5-column format: task,name,lat,lon,dist
                elif len(line) >= 5:
                    _, name, lat, lon, dist = line[:5]
                    pt = "0"
                elif len(line) >= 6:
                    _, name, lat, lon, dist, pt = line[:6]
                else:
                    continue
                rows.append((name.strip(), lat.strip(), lon.strip(), dist.strip(), pt.strip()))

    except Exception as e:
        msg = f"importFromCSV: Error reading CSV: {e}"
        log(msg)
        return msg

    if not rows:
        msg = "importFromCSV: No valid rows found in CSV"
        log(msg)
        return msg

    # ---------------------------------------------------------
    # Append to TaskPoints.csv
    # ---------------------------------------------------------
    output_file = os.path.join(DataDir, "TaskPoints.csv")
    added = 0

    try:
        with open(output_file, "a", encoding="utf-8") as f:
            for name, lat, lon, dist, pt  in rows:
                f.write(f"{import_task},{name},{lat},{lon},{dist},{pt}\n")
                added += 1
    except Exception as e:
        msg = f"importFromCSV: Error writing CSV: {e}"
        log(msg)
        return msg

    msg = f"importFromCSV: Added {added} rows to TaskPoints.csv"
    log(msg)
    return msg

