#importFromPesto.py
# Imports task features from .boris (Pesto) files into TaskPoints.csv
# Supported: Turnpoints, HiddenGates, PointsOfInterest, FinishPointOrGate

import os
import tkinter as tk
from tkinter import filedialog, ttk
from xml.etree import ElementTree as ET
from utils import log

def run(DataDir):
    if not DataDir:
        msg = "importFromPesto aborted: DataDir not set"
        log(msg)
        return msg

    imports_dir = os.path.join(DataDir, "imports")
    if not os.path.isdir(imports_dir):
        msg = f"importFromPesto aborted: Missing directory {imports_dir}"
        log(msg)
        return msg

    # ---------------------------------------------------------
    # GUI dialog
    # ---------------------------------------------------------
    parent = tk._default_root
    dlg = tk.Toplevel(parent)
    dlg.title("Import from Pesto")
    dlg.geometry("950x370")          # Fits main fields + Advanced section
    dlg.transient(parent)
    dlg.grab_set()
    dlg.focus_set()

    selected_file = tk.StringVar()
    pesto_task_num = tk.IntVar(value=1)
    import_task_num = tk.IntVar(value=1)
    debug_var = tk.StringVar(value="N")

    frame = ttk.Frame(dlg, padding=10)
    frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    ttk.Label(frame, text="Select Pesto (.boris) file:").grid(row=0, column=0, sticky="w")
    
    def choose_file():
        f = filedialog.askopenfilename(
            title="Select Pesto File",
            initialdir=imports_dir,
            filetypes=[("Boris/Pesto Files", "*.boris"), ("All Files", "*.*")]
        )
        if f:
            selected_file.set(f)
        dlg.after(50, dlg.focus_force)

    ttk.Button(frame, text="Browse", command=choose_file).grid(row=0, column=1, padx=5)

    ttk.Label(frame, textvariable=selected_file, width=70, wraplength=500).grid(
        row=1, column=0, columnspan=2, sticky="ew", pady=5
    )

    ttk.Label(frame, text="Task number IN Pesto file:").grid(
        row=2, column=0, sticky="w", pady=(10, 0)
    )
    ttk.Combobox(
        frame, textvariable=pesto_task_num, values=list(range(1, 11)), width=5
    ).grid(row=2, column=1, sticky="w")

    ttk.Label(frame, text="Import INTO MegaScore as task number:").grid(
        row=3, column=0, sticky="w", pady=(10, 0)
    )
    ttk.Combobox(
        frame, textvariable=import_task_num, values=list(range(1, 11)), width=5
    ).grid(row=3, column=1, sticky="w")

    # Advanced section
    adv_frame = tk.LabelFrame(dlg, text="Advanced — do not change unless required", padx=10, pady=10)
    adv_frame.grid(row=0, column=1, sticky="ns", padx=20, pady=20)

    tk.Label(adv_frame, text="Debug mode:").pack(anchor="w", pady=5)
    ttk.Combobox(
        adv_frame, textvariable=debug_var,
        values=["Y", "N"], width=5, state="readonly"
    ).pack(anchor="w", pady=5)

    result = {"value": None}

    def confirm():
        if not selected_file.get():
            result["value"] = "importFromPesto: No file selected"
        else:
            result["value"] = "OK"
        dlg.destroy()

    def cancel():
        result["value"] = "importFromPesto cancelled by user"
        dlg.destroy()

    dlg.protocol("WM_DELETE_WINDOW", cancel)

    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=4, column=0, columnspan=2, pady=20, sticky="ew")

    # Blue OK button
    style = ttk.Style()
    style.configure("Blue.TButton", background="#0066cc", foreground="white", font=("Helvetica", 10, "bold"))

    tk.Button(btn_frame, text="OK", width=10,  background="#0066cc", foreground="white", font=("Helvetica", 10, "bold"),command=confirm).pack(side="left", padx=10)
  #  ttk.Button(btn_frame, text="OK", width=10, command=confirm,
  #             style="Blue.TButton").pack(side="left", padx=10)

    ttk.Button(btn_frame, text="Close", width=10, command=cancel).pack(side="left", padx=10)

    parent.wait_window(dlg)

    if result["value"] != "OK":
        log(result["value"])
        return result["value"]

    pesto_path = selected_file.get()
    pesto_task = pesto_task_num.get()
    import_task = import_task_num.get()
    debug_mode = (debug_var.get().upper() == "Y")

    log(f"importFromPesto: File = {pesto_path}, Pesto Task = {pesto_task}, Import as Task = {import_task}, Debug = {debug_mode}")

    # ---------------------------------------------------------
    # Parse Pesto XML
    # ---------------------------------------------------------
    try:
        tree = ET.parse(pesto_path)
        root_xml = tree.getroot()
    except Exception as e:
        msg = f"importFromPesto: Error parsing Pesto file: {e}"
        log(msg)
        return msg

    comp = root_xml.find("Competition")
    if comp is None:
        msg = "importFromPesto: <Competition> element not found"
        log(msg)
        return msg

    features = comp.find("Features")
    tasks = comp.find("Tasks")
    if features is None:
        msg = "importFromPesto: <Features> element not found"
        log(msg)
        return msg
    if tasks is None:
        msg = "importFromPesto: <Tasks> element not found"
        log(msg)
        return msg

    # ---------------------------------------------------------
    # Build feature lookup: name → (lat, lon)
    # ---------------------------------------------------------
    feature_coords = {}
    for pt in features.findall("Point"):
        name_el = pt.find("Name")
        circle = pt.find("Circle")
        if name_el is None or circle is None:
            continue
        lat_el = circle.find("Latitude")
        lon_el = circle.find("Longitude")
        if lat_el is None or lon_el is None:
            continue
        feature_coords[name_el.text.strip()] = (lat_el.text.strip(), lon_el.text.strip())

    for gt in features.findall("Gate"):
        name_el = gt.find("Name")
        line = gt.find("Line")
        if name_el is None or line is None:
            continue
        lat_el = line.find("Latitude")
        lon_el = line.find("Longitude")
        if lat_el is None or lon_el is None:
            continue
        feature_coords[name_el.text.strip()] = (lat_el.text.strip(), lon_el.text.strip())

    for poi in features.findall("PointOfInterest"):
        name_el = poi.find("Name")
        point_el = poi.find("Point")
        if name_el is None or point_el is None:
            continue
        lat_el = point_el.find("Latitude")
        lon_el = point_el.find("Longitude")
        if lat_el is None or lon_el is None:
            continue
        feature_coords[name_el.text.strip()] = (lat_el.text.strip(), lon_el.text.strip())

    # ---------------------------------------------------------
    # Find requested Task
    # ---------------------------------------------------------
    task_elem = None
    for t in tasks.findall("Task"):
        num_el = t.find("Number")
        if num_el is not None:
            try:
                if int(num_el.text.strip()) == pesto_task:
                    task_elem = t
                    break
            except ValueError:
                pass

    if task_elem is None:
        msg = f"importFromPesto: Task with Number={pesto_task} not found"
        log(msg)
        return msg

    # ---------------------------------------------------------
    # Collect all referenced features
    # ---------------------------------------------------------
    names_in_task = []
    type_counts = {
        "Turnpoints": 0,
        "HiddenGates": 0,
        "PointsOfInterest": 0,
        "FinishPointOrGate": 0
    }

    # Turnpoints
    turnpoints = task_elem.find("Turnpoints")
    if turnpoints is not None:
        for pt in turnpoints.findall("Point"):
            name_el = pt.find("Name")
            if name_el is not None:
                names_in_task.append(name_el.text.strip())
                type_counts["Turnpoints"] += 1

    # HiddenGates
    hidden_gates = task_elem.find("HiddenGates")
    if hidden_gates is not None:
        for gt in hidden_gates.findall("Gate"):
            name_el = gt.find("Name")
            if name_el is not None:
                names_in_task.append(name_el.text.strip())
                type_counts["HiddenGates"] += 1

    # PointsOfInterest
    points_of_interest = task_elem.find("PointsOfInterest")
    if points_of_interest is not None:
        for poi in points_of_interest.findall("PointOfInterest"):
            name_el = poi.find("Name")
            if name_el is not None:
                names_in_task.append(name_el.text.strip())
                type_counts["PointsOfInterest"] += 1

    # FinishPointOrGate
    finish_points = task_elem.find("FinishPointOrGate")
    if finish_points is not None:
        for fp in finish_points.findall("Point"):
            name_el = fp.find("Name")
            if name_el is not None:
                names_in_task.append(name_el.text.strip())
                type_counts["FinishPointOrGate"] += 1

    if not names_in_task:
        msg = f"importFromPesto: No features found for Task {pesto_task}"
        log(msg)
        return msg

    # ---------------------------------------------------------
    # Resolve names to coordinates
    # ---------------------------------------------------------
    rows = []
    missing = []
    for name in names_in_task:
        coords = feature_coords.get(name)
        if not coords:
            missing.append(name)
            continue
        lat, lon = coords
        rows.append((name, lat, lon, "0", "0"))

    # Debug / verbose logging
    if debug_mode:
        log(f"Debug: Imported {len(rows)} features for Task {pesto_task} → {import_task}:")
        for typ, count in type_counts.items():
            if count > 0:
                log(f"  {count} {typ}")
        if rows:
            log("Imported names:")
            for name, _, _, _, _ in rows:
                log(f"  - {name}")
        if missing:
            log(f"Missing in <Features>: {', '.join(missing)}")

    if not rows:
        msg = f"importFromPesto: No valid coordinates resolved for Task {pesto_task}"
        log(msg)
        return msg

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
        msg = f"importFromPesto: Error writing CSV: {e}"
        log(msg)
        return msg

    # Summary log
    msg = f"importFromPesto: Added {added} rows (Task {pesto_task} → {import_task})"
    msg += f" — {type_counts['Turnpoints']} Turnpoints, {type_counts['HiddenGates']} HiddenGates, "
    msg += f"{type_counts['PointsOfInterest']} PointsOfInterest, {type_counts['FinishPointOrGate']} Finish points"
    if missing:
        msg += f" — Warning: {len(missing)} features not found in <Features>"
    log(msg)

    return msg
