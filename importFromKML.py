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

    dlg.transient(parent)
    dlg.grab_set()
    dlg.focus_set()

    selected_file = tk.StringVar()
    import_task_num = tk.IntVar(value=1)

    frame = ttk.Frame(dlg, padding=10)
    frame.grid(row=0, column=0)

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
            result["value"] = "importFromKML: No file selected"
        else:
            result["value"] = "OK"
        dlg.destroy()

    def cancel():
        result["value"] = "importFromKML cancelled by user"
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

    kml_path = selected_file.get()
    import_task = import_task_num.get()

    log(f"importFromKML: File selected = {kml_path}, Import as Task = {import_task}")

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

        # NEW: append dist = 0
        rows.append((name, lat, lon, "0", "0"))

    if not rows:
        msg = "importFromKML: No valid coordinates found"
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
        msg = f"importFromKML: Error writing CSV: {e}"
        log(msg)
        return msg

    msg = f"importFromKML: Added {added} rows to TaskPoints.csv"
    log(msg)
    return msg

