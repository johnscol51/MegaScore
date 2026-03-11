#!/usr/bin/env python3
#ScoreNavTask.py
import tkinter as tk
from tkinter import ttk, messagebox
import os
import csv
import math
from datetime import datetime
import sys
import re

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from time_scoring import compute_timing_scores
from utils import log



def app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


sys.path.append(app_dir())
from flight_plot import make_flight_plot


# =========================================================
#  HAVERSINE DISTANCE
# =========================================================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # metres
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


# =========================================================
#  TASKPOINT MODEL
# =========================================================
class TaskPoint:
    def __init__(self, name, lat, lon, distance_km, precision_turn="N"):
        self.name = name
        self.lat = float(lat)
        self.lon = float(lon)
        self.distance_km = float(distance_km)
        self.precision_turn = precision_turn  # parsed, unused for now


# =========================================================
#  LOAD TASK POINTS FOR SELECTED TASK
# =========================================================
def load_taskpoints_for_task(taskpoints_file, task_number):
    taskpoints = []
    with open(taskpoints_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 5:
                continue

            if row[0] != str(task_number):
                continue

            name = row[1]
            lat = row[2]
            lon = row[3]
            dist = row[4]
            precision_turn = row[5] if len(row) > 5 else "N"

            taskpoints.append(TaskPoint(name, lat, lon, dist, precision_turn))

    return taskpoints


# =========================================================
#  LOAD IGC FIXES
# =========================================================
def load_igc_positions(filename):
    fixes = []
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            if not line.startswith("B"):
                continue

            hh = int(line[1:3])
            mm = int(line[3:5])
            ss = int(line[5:7])
            timestamp = f"{hh:02d}:{mm:02d}:{ss:02d}"

            lat_deg = int(line[7:9])
            lat_min = float(line[9:14]) / 1000.0
            lat_hemi = line[14]
            lat = lat_deg + lat_min / 60.0
            if lat_hemi == "S":
                lat = -lat

            lon_deg = int(line[15:18])
            lon_min = float(line[18:23]) / 1000.0
            lon_hemi = line[23]
            lon = lon_deg + lon_min / 60.0
            if lon_hemi == "W":
                lon = -lon

            fixes.append((timestamp, lat, lon))

    return fixes


# =========================================================
#  SCORING (STATE MACHINE + PHOTO LOGIC)
# =========================================================
def score_points(points, fixes, HG_score, TP_score, HIT_RADIUS_M=250):
    state = {}
    for p in points:
        pname = p["name"]
        upper = pname.upper()
        is_photo = "PHOTO" in upper

        state[pname] = {
            "is_photo": is_photo,
            "in_zone": False,
            "completed": False,
            "best_dist": float("inf"),
            "best_time": "",
        }

    for (t, lat, lon) in fixes:
        for p in points:
            pname = p["name"]
            plat = p["lat"]
            plon = p["lon"]
            st = state[pname]

            d = haversine(plat, plon, lat, lon)

            if st["is_photo"]:
                if d < st["best_dist"]:
                    st["best_dist"] = d
                    st["best_time"] = t
                continue

            if st["completed"]:
                continue

            inside = d <= HIT_RADIUS_M

            if inside:
                if not st["in_zone"]:
                    st["in_zone"] = True
                    st["best_dist"] = d
                    st["best_time"] = t
                else:
                    if d < st["best_dist"]:
                        st["best_dist"] = d
                        st["best_time"] = t
            else:
                if st["in_zone"]:
                    st["completed"] = True
                    st["in_zone"] = False

    results = []
    for p in points:
        pname = p["name"]
        st = state[pname]
        upper = pname.upper()

        if st["is_photo"]:
            dist_val = round(st["best_dist"], 1) if st["best_dist"] < float("inf") else 0
            results.append({
                "name": pname,
                "time": st["best_time"],
                "dist": dist_val,
                "hit": "",
                "score": 0,
                "time_score": 0,
            })
            continue

        if st["best_dist"] <= HIT_RADIUS_M:
            if "HG" in upper:
                score = HG_score
            else:
                score = TP_score
            hit = "Y"
            dist_val = round(st["best_dist"], 1)
        else:
            score = 0
            hit = "N"
            dist_val = 0

        results.append({
            "name": pname,
            "time": st["best_time"],
            "dist": dist_val,
            "hit": hit,
            "score": score,
            "time_score": 0,
        })

    return results


# =========================================================
#  SORT POINTS
# =========================================================
def sort_points(results):
    def extract_number(name):
        m = re.search(r'(\d+)$', name)
        return int(m.group(1)) if m else None

    def sort_key(r):
        n = r["name"].upper()

        if n.startswith("SP"):
            cat = 0
        elif "TP" in n:
            cat = 1
        elif "HG" in n:
            cat = 2
        elif n.startswith("FP"):
            cat = 3
        elif "PHOTO" in n:
            cat = 4
        else:
            cat = 5

        num = extract_number(n)
        if num is None:
            num = 9999

        return (cat, num, n)

    return sorted(results, key=sort_key)



# =========================================================
#  MAIN GUI + LOGIC
# =========================================================
def run(DataDir):
    root = tk.Toplevel()
    root.geometry("750x700")
    root.lift()
    root.focus_force()
    root.grab_set()

    # Load CompDetails.csv
    comp_path = os.path.join(DataDir, "CompDetails.csv")
    comp = {}
    with open(comp_path, newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                comp[row[0].strip()] = row[1].strip()

    comp_name = comp.get("name", "Unknown Competition")
    root.title(f"Score Navigation Task — {comp_name}")

    igc_dir = os.path.join(DataDir, comp["igcFileLocation"])
    taskpoints_file = os.path.join(DataDir, "TaskPoints.csv")
    scores_dir = os.path.join(DataDir, "scores")
    os.makedirs(scores_dir, exist_ok=True)

    # Load all IGC files
    all_igc_files = [
        f for f in os.listdir(igc_dir)
        if f.lower().endswith(".igc")
    ]

    igc_regex = re.compile(r"^(\d+)T(\d{2})V(\d+)R1_(.+)\.igc$")

    def igc_sort_key(filename):
        m = igc_regex.match(filename)
        if not m:
            return (999999, 999999, filename.lower())
        pilotNo = int(m.group(1))
        taskNo = int(m.group(2))
        version = int(m.group(3))
        pilotName = m.group(4)
        return (pilotNo, taskNo, version, pilotName.lower())

    all_igc_files.sort(key=igc_sort_key)

    # Status bar helper
    def update_status(msg):
        status_text.config(state="normal")
        status_text.insert("end", msg + "\n")
        status_text.see("end")

        lines = status_text.get("1.0", "end-1c").split("\n")
        if len(lines) > 10:
            status_text.delete("1.0", f"{len(lines)-10}.0")

        status_text.config(state="disabled")

        log(msg)

    # GUI Layout
    tk.Label(root, text=comp_name, font=("Arial", 14, "bold")).pack(pady=10)

    frame = tk.Frame(root)
    frame.pack(pady=5, padx=20, fill="x")

    row = 0

    tk.Label(frame, text="Task No:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
    task_var = tk.StringVar()
    task_dd = ttk.Combobox(
        frame,
        textvariable=task_var,
        values=[str(i) for i in range(1, 11)],
        width=10,
        state="readonly",
    )
    task_dd.grid(row=row, column=1, sticky="w", padx=5, pady=5)
    row += 1

    tk.Label(frame, text="IGC File:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
    pilot_var = tk.StringVar()
    pilot_dd = ttk.Combobox(
        frame,
        textvariable=pilot_var,
        values=[],
        width=40,
        state="readonly",
    )
    pilot_dd.grid(row=row, column=1, sticky="w", padx=5, pady=5)
    row += 1

    tk.Label(frame, text="SP Time (hh:mm:ss):").grid(row=row, column=0, sticky="e", padx=5, pady=5)
    sptime_var = tk.StringVar(value="09:00:00")
    tk.Entry(frame, textvariable=sptime_var, width=12).grid(
        row=row, column=1, sticky="w", padx=5, pady=5
    )
    row += 1

    tk.Label(frame, text="Generate Plot:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
    plotyn_var = tk.StringVar(value="Y")
    ttk.Combobox(
        frame,
        textvariable=plotyn_var,
        values=["Y", "N"],
        width=5,
        state="readonly",
    ).grid(row=row, column=1, sticky="w", padx=5, pady=5)
    row += 1

    tk.Label(frame, text="Timing Mode:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
    timing_var = tk.StringVar(value="None")
    ttk.Combobox(
        frame,
        textvariable=timing_var,
        values=["None", "fixed", "SP"],
        width=10,
        state="readonly",
    ).grid(row=row, column=1, sticky="w", padx=5, pady=5)
    row += 1

    tk.Label(frame, text="Ground Speed (kph):").grid(row=row, column=0, sticky="e", padx=5, pady=5)
    ground_var = tk.StringVar(value="0")
    tk.Entry(frame, textvariable=ground_var, width=10).grid(
        row=row, column=1, sticky="w", padx=5, pady=5
    )
    row += 1

    tk.Label(frame, text="HG Score:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
    hg_var = tk.StringVar(value=comp.get("HG-score", "0"))
    tk.Entry(frame, textvariable=hg_var, width=10).grid(
        row=row, column=1, sticky="w", padx=5, pady=5
    )
    row += 1

    tk.Label(frame, text="TP Score:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
    tp_var = tk.StringVar(value=comp.get("TP-score", "0"))
    tk.Entry(frame, textvariable=tp_var, width=10).grid(
        row=row, column=1, sticky="w", padx=5, pady=5
    )
    row += 1

    tk.Label(frame, text="Photo Score:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
    photo_var = tk.StringVar(value=comp.get("photo-score", "0"))
    tk.Entry(frame, textvariable=photo_var, width=10).grid(
        row=row, column=1, sticky="w", padx=5, pady=5
    )
    row += 1

    tk.Label(frame, text="Time Score:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
    time_var = tk.StringVar(value=comp.get("time-Score", "0"))
    tk.Entry(frame, textvariable=time_var, width=10).grid(
        row=row, column=1, sticky="w", padx=5, pady=5
    )
    row += 1

    status_frame = tk.Frame(root)
    status_frame.pack(fill="both", expand=True, padx=20, pady=5)

    status_text = tk.Text(status_frame, height=10, width=80, state="disabled")
    status_text.pack(side="left", fill="both", expand=True)

    status_scroll = tk.Scrollbar(status_frame, command=status_text.yview)
    status_scroll.pack(side="right", fill="y")

    status_text.config(yscrollcommand=status_scroll.set)

    def reset_task_dependent_fields():
        sptime_var.set("09:00:00")
        photo_var.set(comp.get("photo-score", "0"))
        timing_var.set("None")
        ground_var.set("0")
        update_status("Task changed — settings cleared.")

    def reset_pilot_dependent_fields():
        sptime_var.set("09:00:00")
        photo_var.set(comp.get("photo-score", "0"))
        timing_var.set("None")
        ground_var.set("0")
        update_status("Pilot changed — settings reset.")

    def load_previous_settings(csv_path):
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) > 0 and row[0] == "data":
                        prev_sp_time = row[2] if len(row) > 2 else "09:00:00"
                        prev_photo   = row[6] if len(row) > 6 else comp.get("photo-score", "0")
                        prev_timing  = row[7] if len(row) > 7 else "None"
                        prev_ground  = row[8] if len(row) > 8 else "0"
                        return prev_sp_time, prev_photo, prev_timing, prev_ground
        except Exception:
            pass
        return None

#    def refresh_igc_list(*args):
    def refresh_igc_list(*args):
        task = task_var.get()

        pilot_var.set("")
        pilot_dd["values"] = []

        if not task:
            reset_task_dependent_fields()
            update_status("No task selected.")
            return

        taskNo_file = f"{int(task):02d}"
        filtered = []
        for f in all_igc_files:
            m = igc_regex.match(f)
            if m and m.group(2) == taskNo_file:
                filtered.append(f[:-4])

        filtered.sort(key=lambda name_no_ext: igc_sort_key(name_no_ext + ".igc"))
        pilot_dd["values"] = filtered

        reset_task_dependent_fields()

        update_status(
            f"Task {task} selected. {len(pilot_dd['values'])} IGC file(s) available."
        )

    task_var.trace_add("write", refresh_igc_list)

    def on_pilot_selected(*args):
        task = task_var.get()
        selected = pilot_var.get()

        if not task or not selected:
            return

        # Always reset BEFORE checking for previous CSV
        reset_pilot_dependent_fields()

        base_name = selected
        csv_path = os.path.join(scores_dir, base_name + ".csv")

        if os.path.exists(csv_path):
            settings = load_previous_settings(csv_path)
            if settings:
                prev_sp_time, prev_photo, prev_timing, prev_ground = settings

                sptime_var.set(prev_sp_time)
                photo_var.set(prev_photo)
                timing_var.set(prev_timing)
                ground_var.set(prev_ground)

                update_status("Loaded previous settings from CSV.")
            else:
                update_status("CSV found but no previous settings row detected.")
        else:
            update_status("No previous CSV found for this flight.")

    pilot_var.trace_add("write", on_pilot_selected)

    # -----------------------------------------------------
    # do_score logic (TIMING INTEGRATED)
    # -----------------------------------------------------
    def do_score():
        try:
            if not task_var.get():
                messagebox.showerror("Error", "Please select a Task No.")
                root.grab_set()
                return
            if not pilot_var.get():
                messagebox.showerror("Error", "Please select an IGC file.")
                root.grab_set()
                return
            selected = pilot_var.get()
            base_name = selected
            m = igc_regex.match(base_name + ".igc")
            if not m:
                messagebox.showerror("Error", f"Filename format not recognised:\n{selected}")
                root.grab_set()
                return
            pilotNo = m.group(1)
            taskNo_file = m.group(2)
            taskNo_display = str(int(taskNo_file))
            igc_file = os.path.join(igc_dir, base_name + ".igc")
            if not os.path.exists(igc_file):
                msg = (
                    "Selected IGC file does not exist.\n\n"
                    f"IGC directory: {igc_dir}\n"
                    f"Filename: {base_name}.igc\n"
                )
                messagebox.showerror("IGC File Not Found", msg)
                root.grab_set()
                return
            update_status(f"Processing {base_name}.igc (Pilot {pilotNo}, Task {taskNo_display})")

            # Load taskpoints (NEW MODEL)
            taskpoints = load_taskpoints_for_task(taskpoints_file, taskNo_display)

            # NEW: Precise filter for valid gate/point names
            # Matches: SP*, FP*, *TP*, *HG*, *PHOTO*, *photo*
            filtered_points = []
            skipped = []
            for tp in taskpoints:
                upper = tp.name.upper()
                if (upper.startswith("SP") or
                    upper.startswith("FP") or
                    "TP" in upper or
                    "HG" in upper or
                    "PHOTO" in upper or
                    "PHOTO" in upper):  # extra check for lowercase variants
                    filtered_points.append(tp)
                else:
                    skipped.append(tp.name)

            if skipped:
                update_status(f"Skipped {len(skipped)} invalid points: {', '.join(skipped[:5])}{'...' if len(skipped) > 5 else ''}")
            else:
                update_status(f"All {len(taskpoints)} points are valid gates")

            # Use only filtered points for scoring
            taskpoints = filtered_points

            # Load IGC fixes
            fixes = load_igc_positions(igc_file)
            update_status(f"Loaded {len(fixes)} fixes, {len(taskpoints)} valid task points")

            # Convert TaskPoint objects to dicts for existing scoring logic
            points_for_scoring = [
                {"name": tp.name, "lat": tp.lat, "lon": tp.lon, "dist": tp.distance_km}
                for tp in taskpoints
            ]

            # Run zone scoring
            results = score_points(points_for_scoring, fixes, int(hg_var.get()), int(tp_var.get()))
            results = sort_points(results)

            # Extract actual SP time from zone scoring (for SP timing mode)
            sp_actual_time = None
            for r in results:
                if r["name"].upper().startswith("SP"):
                    sp_actual_time = r["time"]
                    break

            # Build a dict of hit status for timing
            hit_map = {r["name"]: (r["hit"] == "Y") for r in results}

            # -----------------------------------------------------
            # TIMING SCORING (NEW)
            # -----------------------------------------------------
            timing_scores = compute_timing_scores(
                sp_time_str=sptime_var.get(),
                gs_kph=float(ground_var.get()),
                mode=timing_var.get(),
                max_score=int(time_var.get()),
                taskpoints=taskpoints,
                fixes=fixes,
                hit_map=hit_map,
                sp_actual_time=sp_actual_time,
            )

            # Inject timing scores into results
            for r in results:
                tinfo = timing_scores.get(r["name"], {"score": 0, "expected": ""})
                r["time_score"] = tinfo["score"]
                r["expected_time"] = tinfo["expected"]

            # -----------------------------------------------------
            # Totals
            # -----------------------------------------------------
            tp_total = sum(
                r["score"]
                for r in results
                if ("SP" in r["name"].upper()
                    or "TP" in r["name"].upper()
                    or "FP" in r["name"].upper())
            )
            hg_total = sum(r["score"] for r in results if "HG" in r["name"].upper())
            time_total = sum(r["time_score"] for r in results)
            photo_total = int(photo_var.get())
            sp_total = sum(r["score"] for r in results if r["name"].upper().startswith("SP"))
            sp_time = sptime_var.get()
            timing_mode = timing_var.get()
            ground_speed = ground_var.get()

            csv_path = os.path.join(scores_dir, base_name + ".csv")
            pdf_path = os.path.join(scores_dir, base_name + ".pdf")
            plot_path = os.path.join(scores_dir, base_name + "_plot.png")

            # -----------------------------------------------------
            # Write CSV (TIMING INCLUDED)
            # -----------------------------------------------------
            with open(csv_path, "w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow([base_name])
                w.writerow(["name", "time", "expected_time", "dist_m", "hit", "score", "time_score"])
                for row_res in results:
                    name = row_res["name"]
                    t = row_res["time"]
                    dist = f"{row_res['dist']:.0f}"
                    if "PHOTO" in name.upper():
                        w.writerow([name, t, "", dist, "", "", ""])
                    else:
                        w.writerow([
                            name,
                            t,
                            row_res["expected_time"],
                            dist,
                            row_res["hit"],
                            row_res["score"],
                            row_res["time_score"],
                        ])
                w.writerow([])
                w.writerow([
                    "SUMMARY",
                    f"SP={sp_time}",
                    f"ground_speed={ground_speed}",
                    f"tp_total={tp_total}",
                    f"hg_total={hg_total}",
                    f"time_total={time_total}",
                    f"photo_total={photo_total}",
                ])

                # NEW: Log the summary line to debug.log
                summary_line = f"SUMMARY: SP={sp_time}, GS={ground_speed}, TP={tp_total}, HG={hg_total}, Time={time_total}, Photo={photo_total}"
                log(summary_line)

                run_timestamp = datetime.now().isoformat(timespec="seconds")
                w.writerow([
                    "data",
                    run_timestamp,
                    sp_time,
                    tp_total,
                    hg_total,
                    time_total,
                    photo_total,
                    timing_mode,
                    ground_speed,
                ])

            # -----------------------------------------------------
            # Plot (optional)
            # -----------------------------------------------------
            if plotyn_var.get() == "Y":
                make_flight_plot(fixes, points_for_scoring, plot_path)

            # -----------------------------------------------------
            # PDF (TIMING INCLUDED)
            # -----------------------------------------------------
            c = canvas.Canvas(pdf_path, pagesize=A4)
            width, height = A4
            y = height - 40
            c.setFont("Helvetica-Bold", 14)
            c.drawString(40, y, f"{comp_name} — {base_name}")
            y -= 35
            c.setFont("Helvetica-Bold", 10)
            c.drawString(40, y, "Name")
            c.drawString(120, y, "Time")
            c.drawString(200, y, "Expected")
            c.drawString(270, y, "Dist(m)")
            c.drawString(330, y, "Hit")
            c.drawString(380, y, "Score")
            c.drawString(420, y, "TimeScore")
            c.line(40, y - 3, 500, y - 3)
            y -= 15
            c.setFont("Helvetica", 9)
            row_step = 13

            col_x = [40, 110, 190, 260, 320, 370, 410, 500]
            for row_res in results:
                name = row_res["name"]
                t = row_res["time"]
                dist = f"{row_res['dist']:.0f}"
                if "PHOTO" in name.upper():
                    hit = score_val = time_score_val = ""
                else:
                    hit = row_res["hit"]
                    score_val = str(row_res["score"])
                    time_score_val = str(row_res["time_score"])
                c.setLineWidth(0.2)
                c.setStrokeGray(0.85)
                c.line(40, y - 2, 500, y - 2)
                for x in col_x:
                    c.line(x, y + 10, x, y - 5)
                c.drawString(40, y, name)
                c.drawString(120, y, t)
                c.drawString(200, y, row_res["expected_time"])
                c.drawString(280, y, dist)
                c.drawString(340, y, hit)
                c.drawString(380, y, score_val)
                c.drawString(430, y, time_score_val)
                y -= row_step
                if y < 80:
                    break
            y -= 20
            c.setFont("Helvetica-Bold", 10)
            c.drawString(
                40,
                y,
                f"SUMMARY: SP={sp_time}, GS={ground_speed}, "
                f"TP={tp_total}, HG={hg_total}, Time={time_total}, Photo={photo_total}, "
                f"Timing={timing_mode}",
            )

            # Footer on plot page
            footer_text = f"Generated: {datetime.now().isoformat(timespec='seconds')}   File: {os.path.basename(pdf_path)}"
            c.setFont("Helvetica", 8)
            c.drawString(40, 20, "MegaScore Goblin")
            c.drawRightString(width - 40, 20, footer_text)

            if plotyn_var.get() == "Y":
                c.showPage()
                c.setFont("Helvetica-Bold", 14)
                c.drawString(40, height - 40, f"{comp_name} — {base_name}")
                try:
                    c.drawImage(plot_path, 10, height - 600, width=620, height=520)
                except Exception:
                    pass
                c.showPage()
            c.save()

            update_status("Scoring complete. CSV and PDF updated.")
            root.lift()
            root.focus_force()
            root.grab_set()

        except Exception as e:
            messagebox.showerror("Unexpected Error", str(e))
            root.grab_set()
            update_status(f"Error: {e}")
    # -----------------------------------------------------
    # Buttons
    # -----------------------------------------------------
    button_frame = tk.Frame(root)
    button_frame.pack(pady=10)

    ok_btn = tk.Button(
        button_frame,
        text="OK",
        width=12,
        fg="blue",
        command=do_score,
    )
    ok_btn.pack(side="left", padx=10)

    cancel_btn = tk.Button(
        button_frame,
        text="Cancel",
        width=12,
        command=root.destroy,
    )
    cancel_btn.pack(side="left", padx=10)

