#!/usr/bin/env python3
import os
import re
import csv
import math
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from datetime import datetime
from reportlab.pdfbase.pdfmetrics import stringWidth
from utils import log

FT = 3.28084

# ---------------------------------------------------------
# PDF GENERATOR
# ---------------------------------------------------------
def generate_pdf_from_csv(csv_path, pdf_path, comp_name, task_no):
    rows = []
    with open(csv_path, newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            rows.append(row)
    if not rows:
        return
    header = rows[0]
    data_rows = rows[1:]
    sorted_rows = sorted(
        data_rows,
        key=lambda r: float(r[8] or 0),
        reverse=True
    )
    ranked_rows = []
    rank = 1
    for r in sorted_rows:
        r_no_ratio = r[:4] + r[5:]
        ranked_rows.append([str(rank)] + r_no_ratio)
        rank += 1
    pdf_headers = [
        "Rank", "Pilot No", "Pilot Name",
        "Rmin (m)", "Rmax (m)",
        "h_min (ft)", "h_max (ft)", "h_band (ft)",
        "Base", "score", "Notes"
    ]
    c = canvas.Canvas(pdf_path, pagesize=landscape(A4))
    width, height = landscape(A4)
    c.setFillColorRGB(0.0, 0.2, 0.8)
    c.rect(width - 80, height - 60, 30, 30, fill=1, stroke=0)
    c.setFillColorRGB(1.0, 0.9, 0.0)
    c.rect(width - 45, height - 60, 30, 30, fill=1, stroke=0)
    y = height - 40
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, y, f"{comp_name} — Circle Task Results")
    y -= 25
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, f"Task {task_no}")
    y -= 30
    font = "Helvetica"
    font_bold = "Helvetica-Bold"
    font_size = 9
    col_widths = []
    for col_idx in range(len(pdf_headers)):
        header_w = stringWidth(pdf_headers[col_idx], font_bold, 10)
        max_w = header_w
        for row in ranked_rows:
            if col_idx < len(row):
                w = stringWidth(str(row[col_idx]), font, font_size)
                if w > max_w:
                    max_w = w
        col_widths.append(max_w + 12)
    x_positions = [40]
    for w in col_widths[:-1]:
        x_positions.append(x_positions[-1] + w)
    c.setFont(font_bold, 10)
    for i, title in enumerate(pdf_headers):
        c.drawString(x_positions[i], y, title)
    c.line(x_positions[0], y - 3, x_positions[-1] + col_widths[-1], y - 3)
    y -= 15
    c.setFont(font, font_size)
    row_step = 13
    for row in ranked_rows:
        c.setLineWidth(0.2)
        c.setStrokeGray(0.7)
        c.line(x_positions[0], y - 2, x_positions[-1] + col_widths[-1], y - 2)
        for xp in x_positions:
            c.line(xp, y + 10, xp, y - 2)
        for i, cell in enumerate(row):
            c.drawString(x_positions[i], y, str(cell))
        y -= row_step
        if y < 60:
            c.showPage()
            width, height = landscape(A4)
            y = height - 40
            c.setFillColorRGB(0.0, 0.2, 0.8)
            c.rect(width - 80, height - 60, 30, 30, fill=1, stroke=0)
            c.setFillColorRGB(1.0, 0.9, 0.0)
            c.rect(width - 45, height - 60, 30, 30, fill=1, stroke=0)
            c.setFillColorRGB(0, 0, 0)
            c.setFont("Helvetica-Bold", 12)
            c.drawString(40, y, f"{comp_name} — Circle Task Results (cont.)")
            y -= 30
            c.setFont(font_bold, 10)
            for i, title in enumerate(pdf_headers):
                c.drawString(x_positions[i], y, title)
            c.line(x_positions[0], y - 3, x_positions[-1] + col_widths[-1], y - 3)
            y -= 15
            c.setFont(font, font_size)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    footer = f"{timestamp} — {os.path.basename(pdf_path)}"
    c.setFont("Helvetica", 9)
    c.drawRightString(width - 20, 20, footer)
    c.save()

# ---------------------------------------------------------
# IGC parsing
# ---------------------------------------------------------
def parse_igc(path, debug=False):
    track = []
    with open(path, "r", encoding="latin-1") as f:
        for line in f:
            if not line.startswith("B"):
                continue
            lat = float(line[7:9]) + float(line[9:14]) / 60000.0
            if line[14] == "S":
                lat = -lat
            lon = float(line[15:18]) + float(line[18:23]) / 60000.0
            if line[23] == "W":
                lon = -lon
            alt = int(line[25:30])
            alt = int(line[30:35])
            track.append((lat, lon, alt))
    if debug:
        print(f"Parsed {len(track)} B-records from IGC")
        log(f"Parsed {len(track)} B-records from IGC")
    return track

def clean_num(val):
    try:
        f = float(val)
        if f.is_integer():
            return str(int(f))
        return str(f)
    except:
        return str(val)

# ---------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def track_heading(lat1, lon1, lat2, lon2):
    y = math.sin(math.radians(lon2 - lon1)) * math.cos(math.radians(lat2))
    x = (math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) -
         math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.cos(math.radians(lon2 - lon1)))
    h = math.degrees(math.atan2(y, x))
    return (h + 360) % 360

def bearing_CM(CM, lat2, lon2):
    lat1, lon1 = CM
    y = math.sin(math.radians(lon2 - lon1)) * math.cos(math.radians(lat2))
    x = (math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) -
         math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.cos(math.radians(lon2 - lon1)))
    b = math.degrees(math.atan2(y, x))
    return (b + 360) % 360

def side_of_line(lat, lon, p1, p2):
    x, y = lon, lat
    x1, y1 = p1[1], p1[0]
    x2, y2 = p2[1], p2[0]
    return (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)

def norm_angle(d):
    if d > 180:
        return d - 360
    if d < -180:
        return d + 360
    return d

def find_line_cross(track, start_idx, p1, p2):
    last_side = side_of_line(track[start_idx][0], track[start_idx][1], p1, p2)
    for k in range(start_idx + 1, len(track)):
        lat, lon, alt = track[k]
        s = side_of_line(lat, lon, p1, p2)
        if s == 0 or (s > 0 and last_side < 0) or (s < 0 and last_side > 0):
            return k
        last_side = s
    return None

# ---------------------------------------------------------
# Circle scoring
# ---------------------------------------------------------
def score_circle(track, CM, entry_idx, exit_idx):
    radii = []
    alts = []
    for i in range(entry_idx, exit_idx + 1):
        lat, lon, alt = track[i]
        r = haversine(lat, lon, CM[0], CM[1])
        radii.append(r)
        alts.append(alt)
    Rmin = min(radii)
    Rmax = max(radii)
    ratio = Rmin / Rmax if Rmax > 0 else 0.0
    h_min = min(alts)
    h_max = max(alts)
    h_band = h_max - h_min
    h_band_ft = h_band * FT
    cross_sum = 0.0
    CMx, CMy = CM[1], CM[0]
    for i in range(entry_idx, exit_idx):
        lat1, lon1, _ = track[i]
        lat2, lon2, _ = track[i+1]
        x1, y1 = lon1 - CMx, lat1 - CMy
        x2, y2 = lon2 - CMx, lat2 - CMy
        cross = x1 * y2 - y1 * x2
        cross_sum += cross
    if cross_sum < 0:
        return {
            "Rmin": Rmin, "Rmax": Rmax, "ratio": ratio,
            "P_base": 0.0, "P_final": 0.0,
            "penalty_reason": "Clockwise turn detected",
            "h_min": h_min, "h_max": h_max,
            "h_band": h_band, "h_band_ft": h_band_ft,
        }
    if Rmin < 200 or Rmax > 750:
        return {
            "Rmin": Rmin, "Rmax": Rmax, "ratio": ratio,
            "P_base": 0.0, "P_final": 0.0,
            "penalty_reason": "Radius outside range",
            "h_min": h_min, "h_max": h_max,
            "h_band": h_band, "h_band_ft": h_band_ft,
        }
    if ratio <= 0.5:
        return {
            "Rmin": Rmin, "Rmax": Rmax, "ratio": ratio,
            "P_base": 0.0, "P_final": 0.0,
            "penalty_reason": "Rmin/Rmax <= 0.5",
            "h_min": h_min, "h_max": h_max,
            "h_band": h_band, "h_band_ft": h_band_ft,
        }
    P_base = (ratio - 0.5) * 500
    P_base = max(0, min(250, P_base))
    P_final = P_base
    return {
        "Rmin": Rmin, "Rmax": Rmax, "ratio": ratio,
        "P_base": P_base, "P_final": P_final,
        "penalty_reason": None,
        "h_min": h_min, "h_max": h_max,
        "h_band": h_band, "h_band_ft": h_band_ft,
    }

# ---------------------------------------------------------
# SP / CM loader
# ---------------------------------------------------------
def load_SP_CM(taskpoints_file, task_number):
    SP = None
    CM = None
    with open(taskpoints_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 4:
                continue
            if row[0].strip() != str(task_number):
                continue
            name = row[1].strip().upper()
            lat = float(row[2])
            lon = float(row[3])
            if name == "SP":
                SP = (lat, lon)
            elif name == "TP1":
                CM = (lat, lon)
    return SP, CM

# ---------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------
def write_fail(writer, pilot_no, pilot_name, reason):
    writer.writerow([
        pilot_no, pilot_name,
        "0", "0",
        "0",
        "0", "0", "0",
        "0", "0",
        reason,
    ])

def write_score_row(writer, pilot_no, pilot_name, scoring):
    rmin_m = round(scoring["Rmin"], 1)
    rmax_m = round(scoring["Rmax"], 1)
    ratio = round(scoring["ratio"], 3)
    h_min_ft = round(scoring["h_min"] * FT, 1)
    h_max_ft = round(scoring["h_max"] * FT, 1)
    h_band_ft = round(scoring["h_band"] * FT, 1)
    base_score = round(scoring["P_base"], 1)
    final_score = round(scoring["P_final"], 0)
    writer.writerow([
        pilot_no,
        pilot_name,
        clean_num(rmin_m),
        clean_num(rmax_m),
        clean_num(ratio),
        clean_num(h_min_ft),
        clean_num(h_max_ft),
        clean_num(h_band_ft),
        clean_num(base_score),
        clean_num(final_score),
        scoring["penalty_reason"] or "",
    ])

# ---------------------------------------------------------
# Plot saving helper
# ---------------------------------------------------------
def save_plot(track, SP, CM, sp_index, cm_index, turn_start, entry_index, exit_index, scores_dir, igc_name,
              max_after_cm, task_no, pilot_no, pilot_name):
    if sp_index is not None:
        start_idx = sp_index
    else:
        start_idx = 0
    if exit_index is not None:
        end_idx = min(exit_index + 20, len(track) - 1)
    elif cm_index is not None:
        end_idx = min(cm_index + max_after_cm, len(track) - 1)
    else:
        end_idx = min(start_idx + max_after_cm, len(track) - 1)
    subtrack = track[start_idx:end_idx+1]
    lats = [p[0] for p in subtrack]
    lons = [p[1] for p in subtrack]
    plt.figure(figsize=(8, 8))
    plt.scatter(lons, lats, s=5, c="blue", label="Track")
    if SP is not None:
        plt.scatter([SP[1]], [SP[0]], c="green", s=80, marker="x", label="SP")
    if CM is not None:
        plt.scatter([CM[1]], [CM[0]], c="red", s=80, marker="+", label="CM")
    if turn_start is not None and 0 <= turn_start < len(track):
        plt.scatter([track[turn_start][1]], [track[turn_start][0]],
                    c="cyan", s=80, marker="^", label="Turn start")
    if entry_index is not None and 0 <= entry_index < len(track):
        plt.scatter([track[entry_index][1]], [track[entry_index][0]],
                    c="purple", s=80, marker="s", label="Entry")
    if exit_index is not None and 0 <= exit_index < len(track):
        plt.scatter([track[exit_index][1]], [track[exit_index][0]],
                    c="black", s=80, marker="D", label="Exit")
    for idx, (lat, lon, _) in enumerate(subtrack):
        global_idx = start_idx + idx
        if global_idx % 10 == 0:
            plt.text(lon, lat, str(global_idx), fontsize=6)
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.title(f"Circle Task {task_no:02d} — Pilot {pilot_no} — {pilot_name}")
    plt.legend()
    plt.gca().set_aspect("equal", adjustable="box")
    plt.grid(True)
    plt.tight_layout()
    plot_name = os.path.splitext(igc_name)[0] + "_plot.png"
    plot_path = os.path.join(scores_dir, plot_name)
    try:
        plt.savefig(plot_path, dpi=150)
    finally:
        plt.close()

# ---------------------------------------------------------
# Main GUI entry
# ---------------------------------------------------------
def run(DataDir):
    root = tk.Toplevel()
    root.geometry("900x1000")
    root.lift()
    root.focus_force()
    root.grab_set()
    comp_path = os.path.join(DataDir, "CompDetails.csv")
    comp = {}
    with open(comp_path, newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                comp[row[0].strip()] = row[1].strip()
    comp_name = comp.get("name", "Unknown Competition")
    root.title(f"Circle Task Scoring — {comp_name}")
    igc_dir = os.path.join(DataDir, comp["igcFileLocation"])
    scores_dir = os.path.join(DataDir, "scores")
    results_dir = os.path.join(DataDir, "results")
    os.makedirs(scores_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)
    taskpoints_file = os.path.join(DataDir, "TaskPoints.csv")
    igc_regex = re.compile(r"^(\d+)T(\d{2})V(\d+)R1_(.+)\.igc$", re.IGNORECASE)

    def igc_sort_key(filename):
        m = igc_regex.match(filename)
        if not m:
            return (999999, 999999, filename.lower())
        pilotNo = int(m.group(1))
        taskNo = int(m.group(2))
        version = int(m.group(3))
        pilotName = m.group(4)
        return (pilotNo, taskNo, version, pilotName.lower())

    status_frame = tk.Frame(root)
    status_frame.pack(fill="both", expand=True, padx=20, pady=5)
    status_scroll = tk.Scrollbar(status_frame)
    status_scroll.pack(side="right", fill="y")
    status_text = tk.Text(status_frame, wrap="word", state="disabled")
    status_text.pack(side="left", fill="both", expand=True)
    status_text.config(yscrollcommand=status_scroll.set)
    status_scroll.config(command=status_text.yview)
    def update_status(msg):
        status_text.config(state="normal")
        status_text.insert("end", msg + "\n")
        status_text.see("end")
        status_text.config(state="disabled")
    tk.Label(root, text=comp_name, font=("Arial", 14, "bold")).pack(pady=10)
    top_frame = tk.Frame(root)
    top_frame.pack(fill="x", padx=20)
    frame = tk.Frame(top_frame)
    frame.pack(side="left", anchor="n")
    row = 0
    tk.Label(frame, text="Task No:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
    task_var = tk.StringVar()
    ttk.Combobox(
        frame, textvariable=task_var,
        values=[str(i) for i in range(1, 16)],
        width=10, state="readonly"
    ).grid(row=row, column=1, sticky="w", padx=5, pady=5)
    row += 1
    tk.Label(frame, text="Height band limit (ft):").grid(row=row, column=0, sticky="e", padx=5, pady=5)
    hband_var = tk.StringVar(value="600")
    tk.Entry(frame, textvariable=hband_var, width=10).grid(row=row, column=1, sticky="w", padx=5, pady=5)
    row += 1
    tk.Label(frame, text="Generate plots:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
    plot_var = tk.StringVar(value="Y")
    ttk.Combobox(
        frame, textvariable=plot_var,
        values=["Y", "N"], width=5, state="readonly"
    ).grid(row=row, column=1, sticky="w", padx=5, pady=5)
    row += 1
    adv_frame = tk.LabelFrame(top_frame, text="Advanced — do not change unless required")
    adv_frame.pack(side="right", anchor="n", padx=20)
    tk.Label(adv_frame, text="SP radius (m):").pack(anchor="w", padx=5, pady=2)
    sp_r_var = tk.StringVar(value="250")
    tk.Entry(adv_frame, textvariable=sp_r_var, width=10).pack(anchor="w", padx=10)
    tk.Label(adv_frame, text="CM radius (m):").pack(anchor="w", padx=5, pady=2)
    cm_r_var = tk.StringVar(value="80")
    tk.Entry(adv_frame, textvariable=cm_r_var, width=10).pack(anchor="w", padx=10)
    tk.Label(adv_frame, text="Turn start detect (cum left °):").pack(anchor="w", padx=5, pady=2)
    turn_start_deg_var = tk.StringVar(value="10")
    tk.Entry(adv_frame, textvariable=turn_start_deg_var, width=10).pack(anchor="w", padx=10)
    tk.Label(adv_frame, text="Entry delay after turn (sec):").pack(anchor="w", padx=5, pady=2)
    entry_delay_sec_var = tk.StringVar(value="15")
    tk.Entry(adv_frame, textvariable=entry_delay_sec_var, width=10).pack(anchor="w", padx=10)
    tk.Label(adv_frame, text="Entry heading tolerance (±°):").pack(anchor="w", padx=5, pady=2)
    entry_heading_tol_var = tk.StringVar(value="30")
    tk.Entry(adv_frame, textvariable=entry_heading_tol_var, width=10).pack(anchor="w", padx=10)
    tk.Label(adv_frame, text="Exit angle (°):").pack(anchor="w", padx=5, pady=2)
    exit_var = tk.StringVar(value="170")
    tk.Entry(adv_frame, textvariable=exit_var, width=10).pack(anchor="w", padx=10)
    tk.Label(adv_frame, text="Max points after CM:").pack(anchor="w", padx=5, pady=2)
    max_plot_var = tk.StringVar(value="300")
    tk.Entry(adv_frame, textvariable=max_plot_var, width=10).pack(anchor="w", padx=10)
    tk.Label(adv_frame, text="Debug mode:").pack(anchor="w", padx=5, pady=2)
    debug_var = tk.StringVar(value="N")
    ttk.Combobox(
        adv_frame, textvariable=debug_var,
        values=["Y", "N"], width=5, state="readonly"
    ).pack(anchor="w", padx=10)
    button_frame = tk.Frame(root)
    button_frame.pack(pady=10)

    def do_score():
        task_str = task_var.get().strip()
        if not task_str:
            messagebox.showerror("Error", "Please select a Task No.")
            return
        try:
            task_no = int(task_str)
        except ValueError:
            messagebox.showerror("Error", "Invalid Task No.")
            return
        try:
            hband_limit_ft = float(hband_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid height band limit.")
            return
        try:
            SP_R = float(sp_r_var.get())
            CM_R = float(cm_r_var.get())
            turn_start_deg = float(turn_start_deg_var.get())
            entry_delay_sec = int(entry_delay_sec_var.get())
            entry_heading_tol = float(entry_heading_tol_var.get())
            EXIT_ANGLE = float(exit_var.get())
            MAX_PLOT_POINTS_AFTER_CM = int(max_plot_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid parameter value.")
            return
        gen_plots = (plot_var.get().upper() == "Y")
        debug_mode = (debug_var.get().upper() == "Y")
        SP, CM = load_SP_CM(taskpoints_file, task_no)
        if SP is None or CM is None:
            messagebox.showerror("Error", f"SP or CM (TP1) not found for task {task_no}")
            return
        update_status(f"Loaded SP={SP}, CM={CM}")
        update_status(f"Scoring Task {task_no}")
        igc_files = [f for f in os.listdir(igc_dir) if f.lower().endswith(".igc")]
        igc_files.sort(key=igc_sort_key)
        out_csv = os.path.join(results_dir, f"task{task_no:02d}CircleResults.csv")
        with open(out_csv, "w", newline="") as f_out:
            writer = csv.writer(f_out)
            writer.writerow([
                "pilot_no", "pilot_name",
                "Rmin_m", "Rmax_m", "Rmin_Rmax",
                "h_min_ft", "h_max_ft", "h_band_ft",
                "BaseScore", "score",
                "notes"
            ])
            for igc_name in igc_files:
                m = igc_regex.match(igc_name)
                if not m:
                    if re.search(rf"T{task_no:02d}", igc_name, re.IGNORECASE):
                        update_status(f"Skipping unrecognised file for task {task_no}: {igc_name}")
                    continue
                pilot_no = int(m.group(1))
                tno = int(m.group(2))
                pilot_name = m.group(4)
                if tno != task_no:
                    continue

                igc_path = os.path.join(igc_dir, igc_name)
                update_status(f"Processing {igc_name} ({pilot_name})")
                try:
                    track = parse_igc(igc_path, debug=debug_mode)
                except Exception as e:
                    update_status(f" Error reading IGC: {e}")
                    write_fail(writer, pilot_no, pilot_name, "IGC read error")
                    continue
                if len(track) < 10:
                    update_status(" Too few points")
                    write_fail(writer, pilot_no, pilot_name, "Too few points")
                    continue
                if debug_mode:
                    print(f"\n=== DEBUG: {pilot_name} - {igc_name} ===")
                    print(f"Total B-records: {len(track)}")
                    log(f"=== DEBUG: {pilot_name} - {igc_name} ===")
                    log(f"Total B-records: {len(track)}")
                # 1. SP crossing
                sp_index = None
                for i, (lat, lon, alt) in enumerate(track):
                    if haversine(lat, lon, SP[0], SP[1]) <= SP_R:
                        sp_index = i
                        if debug_mode:
                            print(f"[{pilot_name}] SP crossed at index {i}")
                            log(f"[{pilot_name}] SP crossed at index {i}")
                        break
                if sp_index is None:
                    update_status(" SP never crossed")
                    write_fail(writer, pilot_no, pilot_name, "SP never crossed")
                    if debug_mode:
                        print(f"[{pilot_name}] → SP never crossed")
                        log(f"[{pilot_name}] → SP never crossed")
                    continue
                # 2. CM crossing
                cm_index = None
                for j in range(sp_index, len(track)):
                    lat, lon, alt = track[j]
                    if haversine(lat, lon, CM[0], CM[1]) <= CM_R:
                        cm_index = j
                        if debug_mode:
                            print(f"[{pilot_name}] CM crossed at index {j}")
                            log(f"[{pilot_name}] CM crossed at index {j}")
                        break
                if cm_index is None:
                    update_status(" CM never crossed")
                    write_fail(writer, pilot_no, pilot_name, "CM never crossed")
                    if debug_mode:
                        print(f"[{pilot_name}] → CM never crossed")
                        log(f"[{pilot_name}] → CM never crossed")
                    continue
                # 3. Detect start of left turn after CM
                inbound_heading = track_heading(SP[0], SP[1], CM[0], CM[1])
                if debug_mode:
                    print(f"[{pilot_name}] Inbound SP-CM heading: {inbound_heading:.1f}°")
                    log(f"[{pilot_name}] Inbound SP-CM heading: {inbound_heading:.1f}°")
                turn_start = None
                cum_left = 0.0
                last_h = None
                turned_left_of_inbound = False
                for k in range(cm_index + 1, min(cm_index + 600, len(track))):
                    if k == cm_index + 1:
                        last_h = track_heading(track[cm_index][0], track[cm_index][1],
                                               track[k][0], track[k][1])
                        continue
                    h = track_heading(track[k-1][0], track[k-1][1],
                                      track[k][0], track[k][1])
                    d = norm_angle(h - last_h)
                    if not turned_left_of_inbound:
                        if norm_angle(h - inbound_heading) < 0:  # turned left of axis
                            turned_left_of_inbound = True
                            if debug_mode:
                                print(f"[{pilot_name}] Turned left of inbound axis at index {k} (heading {h:.1f}° < {inbound_heading:.1f}°)")
                                log(f"[{pilot_name}] Turned left of inbound axis at index {k} (heading {h:.1f}° < {inbound_heading:.1f}°)")
                        last_h = h
                        continue
                    if d < 0:
                        cum_left += -d
                    if cum_left >= turn_start_deg:
                        turn_start = k
                        if debug_mode:
                            print(f"[{pilot_name}] Left turn confirmed at index {k} (cum left: {cum_left:.2f}°)")
                            log(f"[{pilot_name}] Left turn confirmed at index {k} (cum left: {cum_left:.2f}°)")
                        break
                    last_h = h
                if turn_start is None:
                    update_status(" No clear left turn after CM")
                    write_fail(writer, pilot_no, pilot_name, "No clear left turn after CM")
                    if debug_mode:
                        print(f"[{pilot_name}] → No clear left turn after CM")
                        log(f"[{pilot_name}] → No clear left turn after CM")
                    continue
                # 4. Find entry line cross — after delay and heading check
                entry_start = turn_start + entry_delay_sec  # skip delay points (assume 1 Hz)
                if entry_start >= len(track):
                    update_status(" Entry delay exceeds track length")
                    write_fail(writer, pilot_no, pilot_name, "Entry delay exceeds track length")
                    if debug_mode:
                        print(f"[{pilot_name}] → Entry delay exceeds track length")
                        log(f"[{pilot_name}] → Entry delay exceeds track length")
                    continue
                if debug_mode:
                    print(f"[{pilot_name}] Entry search starts at index {entry_start} (after delay)")
                    log(f"[{pilot_name}] Entry search starts at index {entry_start} (after delay)")
                entry_index = None
                for k in range(entry_start + 1, len(track)):
                    lat, lon, alt = track[k]
                    last_lat, last_lon, last_alt = track[k-1]
                    s = side_of_line(lat, lon, SP, CM)
                    last_s = side_of_line(last_lat, last_lon, SP, CM)
                    if s == 0 or (s > 0 and last_s < 0) or (s < 0 and last_s > 0):
                        # Potential cross — check heading
                        heading_at_cross = track_heading(last_lat, last_lon, lat, lon)
                        expected_heading = norm_angle(inbound_heading - 270)
                        d_heading = norm_angle(heading_at_cross - expected_heading)
                        if abs(d_heading) <= entry_heading_tol:
                            entry_index = k
                            if debug_mode:
                                print(f"[{pilot_name}] Potential entry at index {k}, heading {heading_at_cross:.1f}° - Accepted (within {expected_heading - entry_heading_tol:.1f}° to {expected_heading + entry_heading_tol:.1f}°)")
                                log(f"[{pilot_name}] Potential entry at index {k}, heading {heading_at_cross:.1f}° - Accepted (within {expected_heading - entry_heading_tol:.1f}° to {expected_heading + entry_heading_tol:.1f}°)")
                            break
                        else:
                            if debug_mode:
                                print(f"[{pilot_name}] Potential entry at index {k}, heading {heading_at_cross:.1f}° - Rejected (outside {expected_heading - entry_heading_tol:.1f}° to {expected_heading + entry_heading_tol:.1f}°)")
                                log(f"[{pilot_name}] Potential entry at index {k}, heading {heading_at_cross:.1f}° - Rejected (outside {expected_heading - entry_heading_tol:.1f}° to {expected_heading + entry_heading_tol:.1f}°)")
                if entry_index is None:
                    update_status(" No valid entry line crossed")
                    write_fail(writer, pilot_no, pilot_name, "No valid entry line crossed")
                    if debug_mode:
                        print(f"[{pilot_name}] → No valid entry line crossed")
                        log(f"[{pilot_name}] → No valid entry line crossed")
                    continue
                if debug_mode:
                    print(f"[{pilot_name}] Entry line crossed at index {entry_index}")
                    log(f"[{pilot_name}] Entry line crossed at index {entry_index}")
                # 5. Exit angle + line
                bearing_entry = bearing_CM(CM, track[entry_index][0], track[entry_index][1])
                reached_angle = False
                start_exit_search = None
                for k in range(entry_index + 1, len(track)):
                    b = bearing_CM(CM, track[k][0], track[k][1])
                    d = norm_angle(b - bearing_entry)
                    if d >= EXIT_ANGLE:
                        reached_angle = True
                        start_exit_search = k
                        if debug_mode:
                            print(f"[{pilot_name}] Reached {EXIT_ANGLE}° at index {k} (bearing diff: {d:.1f}°)")
                            log(f"[{pilot_name}] Reached {EXIT_ANGLE}° at index {k} (bearing diff: {d:.1f}°)")
                        break
                if not reached_angle:
                    update_status(f" Never reached {EXIT_ANGLE}° exit angle - scoring to end of track")
                    start_exit_search = len(track) - 1
                    if debug_mode:
                        print(f"[{pilot_name}] → Never reached {EXIT_ANGLE}° - using end of track")
                        log(f"[{pilot_name}] → Never reached {EXIT_ANGLE}° - using end of track")
                exit_index = find_line_cross(track, start_exit_search, SP, CM)
                if exit_index is None:
                    update_status(" Exit line never crossed - scoring to end of track")
                    exit_index = len(track) - 1
                    if debug_mode:
                        print(f"[{pilot_name}] → Exit line never crossed - using end of track")
                        log(f"[{pilot_name}] → Exit line never crossed - using end of track")
                else:
                    if debug_mode:
                        print(f"[{pilot_name}] Exit line crossed at index {exit_index}")
                        log(f"[{pilot_name}] Exit line crossed at index {exit_index}")
                if debug_mode:
                    print(f"[{pilot_name}] Scored arc from index {entry_index} to {exit_index} ({exit_index - entry_index} points)")
                    log(f"[{pilot_name}] Scored arc from index {entry_index} to {exit_index} ({exit_index - entry_index} points)")

                # 7. Scoring
                scoring = score_circle(track, CM, entry_index, exit_index)
                if scoring["h_band_ft"] > hband_limit_ft:
                    scoring["P_final"] *= 0.8
                    if scoring["penalty_reason"]:
                        scoring["penalty_reason"] += "+Height range"
                    else:
                        scoring["penalty_reason"] = "Height band exceeded"
                update_status(
                    f" Rmin={scoring['Rmin']:.1f} "
                    f"Rmax={scoring['Rmax']:.1f} "
                    f"ratio={scoring['ratio']:.3f} "
                    f"P={scoring['P_final']:.0f}"
                )

                if gen_plots:
                    save_plot(
                        track, SP, CM,
                        sp_index, cm_index, turn_start,
                        entry_index, exit_index,
                        scores_dir, igc_name,
                        MAX_PLOT_POINTS_AFTER_CM,
                        task_no, pilot_no, pilot_name
                    )
                write_score_row(writer, pilot_no, pilot_name, scoring)

                # NEW: Refresh GUI after each pilot
                root.update_idletasks()

        update_status(f"Finished scoring Task {task_no}. Results saved to {out_csv}")
        pdf_path = os.path.join(scores_dir, f"task{task_no:02d}Circle.pdf")
        generate_pdf_from_csv(out_csv, pdf_path, comp_name, task_no)
        update_status(f"PDF saved to {pdf_path}")

    tk.Button(
        button_frame,
        text="Score Task",
        width=12,
        bg="#0066cc",
        fg="white",
        command=do_score
    ).pack(side="left", padx=10)
    tk.Button(
        button_frame,
        text="Cancel",
        width=12,
        command=root.destroy
    ).pack(side="left", padx=10)
