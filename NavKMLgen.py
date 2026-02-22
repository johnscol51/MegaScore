# NavKMLgen.py
#
# Generates one KML file per IGC flight for the selected task.
# - Reads igcFileLocation from CompDetails.csv
# - Selects only the highest-version IGC per pilot for the task
# - Outputs to DataDir/scores/<taskNo>-KML/
# - Uses simplekml (pip install simplekml)

import os
import csv
import re
import math
from collections import defaultdict

import tkinter as tk
from tkinter import ttk, messagebox
import simplekml

from utils import log


def get_igc_file_location(data_dir):
    """Get igcFileLocation from CompDetails.csv or return None."""
    path = os.path.join(data_dir, "CompDetails.csv")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    key = row[0].strip().lower().replace(" ", "")
                    if "igcfilelocation" in key or "igclocation" in key:
                        return row[1].strip()
    except Exception:
        pass
    return None


def parse_igc_track(igc_path):
    """Extract ground track (lat, lon) from B records in IGC file."""
    track = []
    try:
        with open(igc_path, "r", encoding="latin-1", errors="ignore") as f:
            for line in f:
                if line.startswith("B") and len(line) >= 35:
                    lat_str = line[7:14]
                    lat_hemi = line[14]
                    lon_str = line[15:23]
                    lon_hemi = line[23]

                    lat_deg = int(lat_str[0:2])
                    lat_min = int(lat_str[2:4]) + int(lat_str[4:]) / 1000.0
                    lat = lat_deg + lat_min / 60.0
                    if lat_hemi.upper() == "S":
                        lat = -lat

                    lon_deg = int(lon_str[0:3])
                    lon_min = int(lon_str[3:5]) + int(lon_str[5:]) / 1000.0
                    lon = lon_deg + lon_min / 60.0
                    if lon_hemi.upper() == "W":
                        lon = -lon

                    track.append((lat, lon))
    except Exception:
        pass
    return track


def add_task_circle(kml, name, lat, lon, radius_m, color):
    """Add a ground-clamped circle polygon + central label."""
    n = 36
    coords = []
    for i in range(n + 1):
        ang = 2 * math.pi * i / n
        dlat = (radius_m / 6378137.0) * math.cos(ang) * (180.0 / math.pi)
        dlon = (radius_m / 6378137.0) * math.sin(ang) * (180.0 / math.pi) / math.cos(math.radians(lat))
        coords.append((lon + dlon, lat + dlat))

    poly = kml.newpolygon(name=name, outerboundaryis=coords)
    poly.style.polystyle.color = simplekml.Color.changealphaint(90, color)  # ~35% opacity
    poly.style.polystyle.fill = 1
    poly.style.linestyle.color = simplekml.Color.black
    poly.style.linestyle.width = 2
    poly.altitudemode = simplekml.AltitudeMode.clamptoground

    p = kml.newpoint(name=name, coords=[(lon, lat)])
    p.style.labelstyle.color = simplekml.Color.black
    p.style.labelstyle.scale = 0.8
    p.altitudemode = simplekml.AltitudeMode.clamptoground


def run(DataDir):
    if not DataDir or not os.path.isdir(DataDir):
        msg = "NavKMLgen aborted: Invalid or missing DataDir"
        log(msg)
        return msg

    # ====================== GUI ======================
    parent = tk._default_root
    dlg = tk.Toplevel(parent)
    dlg.title("Generate Navigation KML")
    dlg.transient(parent)
    dlg.grab_set()
    dlg.focus_set()
    dlg.geometry("480x420")

    main_frame = ttk.LabelFrame(dlg, text="Task & Generation", padding=12)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Task selection
    ttk.Label(main_frame, text="Task Number:").grid(row=0, column=0, sticky="w", pady=(4,8))
    task_var = tk.IntVar(value=1)
    ttk.Combobox(
        main_frame,
        textvariable=task_var,
        values=list(range(1, 16)),
        width=6,
        state="readonly"
    ).grid(row=0, column=1, sticky="w", pady=(4,8))

    # Scrollable status
    status_frame = ttk.LabelFrame(main_frame, text="Status", padding=6)
    status_frame.grid(row=1, column=0, columnspan=2, pady=10, sticky="nsew")
    main_frame.rowconfigure(1, weight=1)
    main_frame.columnconfigure(0, weight=1)

    status_text = tk.Text(
        status_frame, height=8, width=60, wrap="word",
        state="disabled", bg="#f8f8f8", font=("TkDefaultFont", 10)
    )
    status_text.pack(fill="both", expand=True)

    scrollbar = ttk.Scrollbar(status_frame, orient="vertical", command=status_text.yview)
    scrollbar.pack(side="right", fill="y")
    status_text.config(yscrollcommand=scrollbar.set)

    def append_status(msg):
        status_text.config(state="normal")
        status_text.insert("end", msg + "\n")
        status_text.see("end")
        status_text.config(state="disabled")
        dlg.update_idletasks()

    # Buttons frame
    btn_frame = ttk.Frame(main_frame)
    btn_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky="e")

    # Blue OK button style
    style = ttk.Style()
    style.configure("Blue.TButton", foreground="white", background="#0066cc")
    style.map("Blue.TButton",
              background=[("active", "#0055aa"), ("pressed", "#004488")])

    # OK left (blue), Cancel right
    ttk.Button(btn_frame, text="OK", width=10,
               command=lambda: confirm(), style="Blue.TButton").pack(side="left", padx=6)
    ttk.Button(btn_frame, text="Cancel", width=10,
               command=lambda: cancel()).pack(side="left", padx=6)

    result = {"value": None, "processed": 0}

    def confirm():
        task_no = task_var.get()
        append_status(f"Starting generation for task {task_no} ...")

        igc_dir = get_igc_file_location(DataDir)
        if not igc_dir or not os.path.isdir(igc_dir):
            append_status("ERROR: igcFileLocation not found or invalid in CompDetails.csv")
            messagebox.showerror("Error", "Cannot find IGC folder.\nCheck CompDetails.csv", parent=dlg)
            return

        igc_regex = re.compile(r"^(\d+)T(\d{2})V(\d+)R1_(.+)\.igc$", re.IGNORECASE)
        per_pilot = defaultdict(list)

        for fname in os.listdir(igc_dir):
            if not fname.lower().endswith(".igc"):
                continue
            m = igc_regex.match(fname)
            if m and int(m.group(2)) == task_no:
                pilot = int(m.group(1))
                version = int(m.group(3))
                per_pilot[pilot].append((version, fname))

        selected_files = []
        for versions in per_pilot.values():
            versions.sort(key=lambda x: x[0], reverse=True)
            selected_files.append(versions[0][1])

        if not selected_files:
            append_status(f"No IGC files found for task {task_no}.")
            return

        append_status(f"Found {len(selected_files)} flight file(s). Starting KML generation...")

        scores_dir = os.path.join(DataDir, "scores")
        kml_dir = os.path.join(scores_dir, f"{task_no}-KML")
        os.makedirs(kml_dir, exist_ok=True)

        task_points = []
        tp_path = os.path.join(DataDir, "TaskPoints.csv")
        try:
            with open(tp_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) < 4 or row[0].strip() != str(task_no):
                        continue
                    name = row[1].strip()
                    try:
                        lat = float(row[2])
                        lon = float(row[3])
                        task_points.append((name, lat, lon))
                    except ValueError:
                        continue
        except Exception as e:
            append_status(f"Warning: Could not load TaskPoints.csv – {e}")

        processed = 0
        total = len(selected_files)
        for i, fname in enumerate(selected_files, 1):
            append_status(f"[{i}/{total}] Processing {fname} ...")
            igc_path = os.path.join(igc_dir, fname)
            track = parse_igc_track(igc_path)
            if len(track) < 2:
                append_status(f"  → Skipped (no valid track data)")
                continue

            kml = simplekml.Kml()

            # Flight track
            coords = [(lon, lat, 0) for lat, lon in track]
            lin = kml.newlinestring(name="Flight Track", coords=coords)
            lin.style.linestyle.color = simplekml.Color.blue
            lin.style.linestyle.width = 2.5
            lin.altitudemode = simplekml.AltitudeMode.clamptoground

            # Task points
            for name, lat, lon in task_points:
                n_lower = name.lower()
                if "hg" in n_lower:
                    radius, color = 250, simplekml.Color.green
                elif "photo" in n_lower:
                    radius, color = 50, simplekml.Color.yellow
                else:
                    radius, color = 250, simplekml.Color.blue
                add_task_circle(kml, name, lat, lon, radius, color)

            out_path = os.path.join(kml_dir, fname.replace(".igc", ".kml", 1))
            try:
                kml.save(out_path)
                processed += 1
                append_status(f"  → Saved {fname.replace('.igc', '.kml')}")
            except Exception as e:
                append_status(f"  → Failed to save: {e}")

        append_status("")
        append_status(f"Completed: {processed} file(s) processed out of {total}")
        append_status(f"KML files saved to: scores/{task_no}-KML/")
        result["value"] = "OK"
        result["processed"] = processed

    def cancel():
        result["value"] = "NavKMLgen cancelled by user"
        dlg.destroy()

    dlg.protocol("WM_DELETE_WINDOW", cancel)
    parent.wait_window(dlg)

    if result["value"] != "OK":
        log(result["value"])
        return result["value"]

    msg = f"NavKMLgen: Generated {result['processed']} KML files for task {task_var.get()}"
    log(msg)
    return msg
