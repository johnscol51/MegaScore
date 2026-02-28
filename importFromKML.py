#importFromKML.py
# Imports placemarks from .kml files into TaskPoints.csv
# Expected Placemark structure: <name> + <coordinates> (lon,lat,...)

import os
import tkinter as tk
from tkinter import filedialog, ttk
from xml.etree import ElementTree as ET
from utils import log

def run(DataDir):
    if not DataDir:
        msg = "importFromKML aborted: DataDir not set"
        log(msg)
        return msg

    imports_dir = os.path.join(DataDir, "imports")
    if not os.path.isdir(imports_dir):
        msg = f"importFromKML aborted: Missing directory {imports_dir}"
        log(msg)
        return msg

    # ---------------------------------------------------------
    # GUI dialog
    # ---------------------------------------------------------
    parent = tk._default_root
    dlg = tk.Toplevel(parent)
    dlg.title("Import from KML")
    dlg.geometry("900x350")          # Wider and taller — fits main + Advanced nicely
    dlg.transient(parent)
    dlg.grab_set()
    dlg.focus_set()

    # Make column 1 (main content) expand
    dlg.grid_columnconfigure(0, weight=1)
    dlg.grid_rowconfigure(0, weight=1)

    selected_file = tk.StringVar()
    import_task_num = tk.IntVar(value=1)
    debug_var = tk.StringVar(value="N")

    # Main frame (left side)
    frame = ttk.Frame(dlg, padding=20)
    frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    ttk.Label(frame, text="Select KML file:").grid(row=0, column=0, sticky="w")
    
    def choose_file():
        f = filedialog.askopenfilename(
            title="Select KML File",
            initialdir=imports_dir,
            filetypes=[("KML Files", "*.kml"), ("All Files", "*.*")]
        )
        if f:
            selected_file.set(f)
        dlg.after(50, dlg.focus_force)

    ttk.Button(frame, text="Browse", command=choose_file).grid(row=0, column=1, padx=10, pady=5, sticky="w")
    
    # File path label expands horizontally
    ttk.Label(frame, textvariable=selected_file, width=80, wraplength=600).grid(
        row=1, column=0, columnspan=2, sticky="ew", pady=5
    )

    ttk.Label(frame, text="Import INTO MegaScore as task number:").grid(
        row=2, column=0, sticky="w", pady=(15, 5)
    )
    ttk.Combobox(
        frame, textvariable=import_task_num, values=list(range(1, 11)), width=5
    ).grid(row=2, column=1, sticky="w")

    # Advanced section (right side)
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
            result["value"] = "importFromKML: No file selected"
        else:
            result["value"] = "OK"
        dlg.destroy()

    def cancel():
        result["value"] = "importFromKML cancelled by user"
        dlg.destroy()

    dlg.protocol("WM_DELETE_WINDOW", cancel)

    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=3, column=0, columnspan=2, pady=20, sticky="ew")
    
    # OK button blue
    style = ttk.Style()
    style.configure("Blue.TButton", background="#0066cc", foreground="white", font=("Helvetica", 10, "bold"))
    ttk.Button(btn_frame, text="OK", width=10, command=confirm,
               style="Blue.TButton").pack(side="left", padx=10)
    
    ttk.Button(btn_frame, text="close", width=10, command=cancel).pack(side="left", padx=10)

    parent.wait_window(dlg)

    if result["value"] != "OK":
        log(result["value"])
        return result["value"]

    kml_path = selected_file.get()
    import_task = import_task_num.get()
    debug_mode = (debug_var.get().upper() == "Y")

    log(f"importFromKML: File selected = {kml_path}, Import as Task = {import_task}, Debug = {debug_mode}")

    # ---------------------------------------------------------
    # Parse KML
    # ---------------------------------------------------------
    try:
        tree = ET.parse(kml_path)
        root_xml = tree.getroot()
    except Exception as e:
        msg = f"importFromKML: Error parsing KML file: {e}"
        log(msg)
        return msg

    # KML namespace handling
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    placemarks = root_xml.findall(".//kml:Placemark", ns)
    if not placemarks:
        msg = "importFromKML: No Placemark elements found"
        log(msg)
        return msg

    rows = []
    imported_names = []  # for debug

    for pm in placemarks:
        name_el = pm.find("kml:name", ns)
        coord_el = pm.find(".//kml:coordinates", ns)
        if name_el is None or coord_el is None:
            continue
        name = name_el.text.strip()
        coords = coord_el.text.strip().split(",")
        if len(coords) < 2:
            continue
        lon = coords[0].strip()
        lat = coords[1].strip()
        rows.append((name, lat, lon, "0", "0"))
        imported_names.append(name)

    if not rows:
        msg = "importFromKML: No valid coordinates found"
        log(msg)
        return msg

    # Debug logging
    if debug_mode:
        log(f"Debug: Parsed {len(rows)} placemarks:")
        for name in imported_names:
            log(f"  - {name}")

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
        msg = f"importFromKML: Error writing CSV: {e}"
        log(msg)
        return msg

    msg = f"importFromKML: Added {added} rows to TaskPoints.csv"
    if debug_mode:
        msg += f" (from {len(rows)} parsed placemarks)"
    log(msg)
    return msg
