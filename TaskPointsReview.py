#!/usr/bin/env python3
# TaskPointsReview.py

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import os
import csv
import math
import re
from utils import log  # for debug logging

# =========================================================
# Haversine distance (km)
# =========================================================
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# =========================================================
# Parse point type and number
# =========================================================
def parse_point_name(point_name):
    if "-" in point_name:
        _, base = point_name.split("-", 1)
    else:
        base = point_name
    base = base.strip().upper()
    if base.startswith("SP"):
        num = base[2:]
        return "SP", int(num) if num.isdigit() else None, num
    if base.startswith("FP"):
        num = base[2:]
        return "FP", int(num) if num.isdigit() else None, num
    if base.startswith("HG"):
        m = re.match(r"(\d+)(.*)", base[2:])
        return ("HG", int(m.group(1)), m.group(2)) if m else ("HG", None, base[2:])
    if base.startswith("TP"):
        m = re.match(r"(\d+)(.*)", base[2:])
        return ("TP", int(m.group(1)), m.group(2)) if m else ("TP", None, base[2:])
    if "PHOTO" in base or base.startswith("P"):
        return "PHOTO", None, ""
    return None, None, ""

# =========================================================
# Gap detection
# =========================================================
def find_gaps(nums):
    gaps = []
    if len(nums) >= 2:
        for a, b in zip(nums, nums[1:]):
            if b > a + 1:
                gaps.extend(range(a + 1, b))
    return gaps

# =========================================================
# Identical coordinate detection
# =========================================================
def find_identical_coordinates(points):
    coord_map = {}
    warnings = []
    for p in points:
        if p["lat"] is None or p["lon"] is None:
            continue
        key = (round(p["lat"], 6), round(p["lon"], 6))
        coord_map.setdefault(key, []).append(p["name"])
    for (lat, lon), names in coord_map.items():
        if len(names) > 1:
            warnings.append(
                f" WARNING: Points {', '.join(names)} share identical coordinates ({lat}, {lon})"
            )
    return warnings

# =========================================================
# Missing-number handler (ignore or cancel)
# =========================================================
def handle_missing_numbers(ptype, gaps, task_no, append_line, root):
    for missing in gaps:
        if messagebox.askyesno(
            "Missing point",
            f"Task {task_no}: {ptype}{missing} is missing.\nIgnore this missing point?"
        ):
            append_line(f" Missing {ptype}{missing} ignored by user.")
        else:
            append_line(f" ERROR: Missing {ptype}{missing} not ignored. Route calculation cancelled.")
            append_line("")
            root.lift()
            root.focus_force()
            return True
    return False

# =========================================================
# Route summary output
# =========================================================
def emit_route_summary(route, excluded, long_segments, length_km, max_segment_km, show_route, append_line):
    if length_km is not None:
        append_line(f" Estimated task length: {length_km:.1f} km")
    else:
        append_line(" Estimated task length: (cannot compute)")
    for a_name, b_name, dist in long_segments:
        append_line(
            f" WARNING: Segment {a_name} -> {b_name} is {dist:.1f} km "
            f"(exceeds {max_segment_km:.1f} km)"
        )
    for p in excluded:
        append_line(f" Note: {p['name']} excluded from route (ordering not provided or invalid).")
    if show_route and route:
        append_line(" Route: " + " -> ".join(p["name"] for p in route))

# =========================================================
# ROUTE ENGINE
# =========================================================
def build_ordered_route_for_task(task_no, points, ask_order_callback, log_lines, max_segment_km):
    sp_list = [p for p in points if p["ptype"] == "SP"]
    fp_list = [p for p in points if p["ptype"] == "FP"]
    tp_list = [p for p in points if p["ptype"] == "TP"]
    hg_list = [p for p in points if p["ptype"] == "HG"]
    if not sp_list or not fp_list:
        return [], [], None, []
    sp = sp_list[0]
    fp = fp_list[0]

    def base_name(p):
        name = p["name"].strip().upper()
        return name.split("-", 1)[1] if "-" in name else name

    # Handle TPX/HGX
    def resolve_unknown_order(p):
        if p["pnum"] is not None:
            p["exclude_from_route"] = False
            p["must_follow"] = None
            return
        answer = ask_order_callback(
            f"Task {task_no}: Where does {p['name']} fit?\n"
            f"Enter a point it follows (e.g. TP3), or leave blank to exclude."
        )
        if not answer:
            log_lines.append(f"Task {task_no}: Excluding {p['name']} (no ordering).")
            p["exclude_from_route"] = True
            p["must_follow"] = None
        else:
            p["exclude_from_route"] = False
            p["must_follow"] = answer.strip().upper()

    for p in tp_list + hg_list:
        p["exclude_from_route"] = False
        p["must_follow"] = None
        if p["pnum"] is None:
            resolve_unknown_order(p)

    route_candidates = [
        p for p in tp_list + hg_list
        if not p["exclude_from_route"]
    ]

    # -----------------------------------------------------
    # Next-eligible logic
    # -----------------------------------------------------
    def next_allowed_points(current, remaining, route):
        current_base = base_name(current)
        forced = [p for p in remaining if p.get("must_follow") == current_base]
        if forced:
            return forced
        used_tp = sorted(p["pnum"] for p in route if p["ptype"] == "TP" and p["pnum"] is not None)
        used_hg = sorted(p["pnum"] for p in route if p["ptype"] == "HG" and p["pnum"] is not None)
        max_tp = used_tp[-1] if used_tp else 0
        max_hg = used_hg[-1] if used_hg else 0
        tp_candidates = sorted(
            p["pnum"] for p in remaining
            if p["ptype"] == "TP" and p["pnum"] is not None and p["pnum"] > max_tp
        )
        hg_candidates = sorted(
            p["pnum"] for p in remaining
            if p["ptype"] == "HG" and p["pnum"] is not None and p["pnum"] > max_hg
        )
        next_tp = tp_candidates[0] if tp_candidates else None
        next_hg = hg_candidates[0] if hg_candidates else None
        allowed = [
            p for p in remaining
            if (p["ptype"] == "TP" and p["pnum"] == next_tp)
            or (p["ptype"] == "HG" and p["pnum"] == next_hg)
        ]
        return allowed

    # -----------------------------------------------------
    # Build route
    # -----------------------------------------------------
    route = [sp]
    remaining = list(route_candidates)
    while remaining:
        current = route[-1]
        allowed = next_allowed_points(current, remaining, route)
        if not allowed:
            break
        best_p = min(
            allowed,
            key=lambda p: haversine_km(current["lat"], current["lon"], p["lat"], p["lon"])
        )
        route.append(best_p)
        remaining.remove(best_p)
    route.append(fp)

    # Distance + long segments
    total_km = 0.0
    long_segments = []
    for a, b in zip(route, route[1:]):
        d = haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])
        total_km += d
        if d > max_segment_km:
            long_segments.append((a["name"], b["name"], d))

    excluded = [p for p in tp_list + hg_list if p["exclude_from_route"]]

    return route, excluded, total_km, long_segments

# =========================================================
# MAIN GUI + LOGIC
# =========================================================
def run(DataDir):
    tp_path = os.path.join(DataDir, "TaskPoints.csv")
    if not os.path.exists(tp_path):
        messagebox.showerror("Error", f"TaskPoints.csv not found in:\n{DataDir}")
        return

    # -----------------------------------------------------
    # Load CSV
    # -----------------------------------------------------
    tasks = {}
    duplicates = []
    incomplete_rows = []
    seen_keys = set()
    with open(tp_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 5:
                try:
                    task_no = int(row[0])
                except:
                    task_no = None
                incomplete_rows.append((task_no, row))
            if len(row) < 4:
                continue
            try:
                task_no = int(row[0])
            except:
                continue
            point_name = row[1].strip()
            try:
                lat = float(row[2])
                lon = float(row[3])
            except:
                lat = None
                lon = None
            key = (task_no, point_name)
            if key in seen_keys:
                duplicates.append(key)
            else:
                seen_keys.add(key)
            ptype, pnum, psuffix = parse_point_name(point_name)
            tasks.setdefault(task_no, []).append({
                "task_no": task_no,
                "name": point_name,
                "lat": lat,
                "lon": lon,
                "ptype": ptype,
                "pnum": pnum,
                "psuffix": psuffix,
            })

    # -----------------------------------------------------
    # GUI setup
    # -----------------------------------------------------
    root = tk.Toplevel()
    root.geometry("950x650")
    root.title("Task Points Review")
    root.lift()
    root.focus_force()
    root.grab_set()

    options_frame = tk.Frame(root)
    options_frame.pack(fill="x", padx=10, pady=5)

    show_route_var = tk.StringVar(value="list")  # default to List tasks
    debug_var = tk.BooleanVar(value=False)

    tk.Label(options_frame, text="Output detail:").pack(side="left", padx=(0, 10))

    tk.Radiobutton(options_frame, text="List tasks", variable=show_route_var,
                   value="list").pack(side="left")

    tk.Radiobutton(options_frame, text="Task Summary", variable=show_route_var,
                   value="summary").pack(side="left", padx=(10, 20))

    tk.Radiobutton(options_frame, text="Summary with routing", variable=show_route_var,
                   value="route").pack(side="left", padx=(0, 20))

    tk.Checkbutton(options_frame, text="Log to debug", variable=debug_var).pack(side="left", padx=(30, 0))

    tk.Label(options_frame, text="Max segment distance (km):").pack(side="left", padx=(30, 5))
    max_segment_var = tk.StringVar(value="15")
    tk.Entry(options_frame, textvariable=max_segment_var, width=6).pack(side="left", padx=(5, 0))

    text_frame = tk.Frame(root)
    text_frame.pack(fill="both", expand=True, padx=10, pady=5)

    text_widget = tk.Text(text_frame, wrap="word", font=("Consolas", 9))
    text_widget.pack(side="left", fill="both", expand=True)

    scroll = tk.Scrollbar(text_frame, command=text_widget.yview)
    scroll.pack(side="right", fill="y")
    text_widget.configure(yscrollcommand=scroll.set)

    def append_line(line=""):
        text_widget.insert("end", line + "\n")
        text_widget.see("end")
        if debug_var.get():
            log(line)

    def ask_order(prompt):
        return simpledialog.askstring("Point ordering", prompt, parent=root) or ""

    # -----------------------------------------------------
    # PROCESS
    # -----------------------------------------------------
    def process():
        text_widget.delete("1.0", "end")
        log_lines = []  # not used anymore, kept for compatibility

        try:
            max_segment_km = float(max_segment_var.get())
            if max_segment_km <= 0:
                raise ValueError
        except:
            messagebox.showerror("Error", "Max segment distance must be positive.")
            return

        mode = show_route_var.get()

        # Duplicate + incomplete rows
        if duplicates or incomplete_rows:
            append_line("ERRORS:")
            for task_no, point_name in duplicates:
                append_line(f" Duplicate point: Task {task_no}, {point_name}")
            for task_no, row in incomplete_rows:
                tstr = f"Task {task_no}" if task_no else "Task ?"
                append_line(f" {tstr}: Incomplete row: {row}")
            append_line("")

        if mode == "list":
            # New mode: simple task list
            append_line("Task list summary:")
            total_points = 0
            for task_no in sorted(tasks.keys()):
                pts = tasks[task_no]
                count = len(pts)
                total_points += count
                append_line(f"Task {task_no}: {count} points")
            append_line("")
            append_line(f"Total tasks: {len(tasks)}")
            append_line(f"Total points across all tasks: {total_points}")
            return

        # Existing modes: summary / route
        for task_no in sorted(tasks.keys()):
            pts = tasks[task_no]
            append_line(f"Task {task_no}:")

            sp_list = [p for p in pts if p["ptype"] == "SP"]
            fp_list = [p for p in pts if p["ptype"] == "FP"]
            tp_list = [p for p in pts if p["ptype"] == "TP"]
            hg_list = [p for p in pts if p["ptype"] == "HG"]
            photo_list = [p for p in pts if p["ptype"] == "PHOTO"]

            append_line(f" Totals: TP/SP/FP = {len(tp_list)+len(sp_list)+len(fp_list)}, HG = {len(hg_list)}, PHOTO = {len(photo_list)}")

            # Task type classification
            if len(sp_list) >= 1 and len(tp_list) >= 1 and len(fp_list) == 0 and len(hg_list) == 0:
                append_line(" Task type: Turn Point Hunt (SP + TPs, no HGs)")
            elif len(sp_list) == 1 and len(tp_list) == 1 and len(fp_list) == 0:
                append_line(" Task type: Circle Task (SP + single TP used as CM)")
            elif len(sp_list) >= 1 and len(tp_list) >= 1 and len(hg_list) >= 1 and len(fp_list) >= 1:
                append_line(" Task type: Navigation Task")
            else:
                append_line(" Task type: Unknown")

            # Missing-number detection
            tp_nums = sorted({p["pnum"] for p in tp_list if p["pnum"]})
            hg_nums = sorted({p["pnum"] for p in hg_list if p["pnum"]})
            tp_gaps = find_gaps(tp_nums)
            hg_gaps = find_gaps(hg_nums)

            # Missing TP
            if handle_missing_numbers("TP", tp_gaps, task_no, append_line, root):
                continue

            # Missing HG
            if handle_missing_numbers("HG", hg_gaps, task_no, append_line, root):
                continue

            # Identical coordinates
            for warning in find_identical_coordinates(pts):
                append_line(warning)

            # Route calculation (skip if list mode, but we already returned above)
            if not sp_list or not fp_list:
                append_line(" Estimated task length: (SP and FP required)")
                append_line("")
                continue

            route, excluded, length_km, long_segments = build_ordered_route_for_task(
                task_no, pts, ask_order, log_lines, max_segment_km
            )

            emit_route_summary(
                route, excluded, long_segments, length_km,
                max_segment_km, (mode == "route"), append_line
            )
            append_line("")

        if log_lines:
            append_line("Details:")
            for line in log_lines:
                append_line(" " + line)

    # Buttons
    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=5)

    tk.Button(btn_frame, text="Run", width=12, bg="#0066cc", fg="white", command=process).pack(side="left", padx=10)
    tk.Button(btn_frame, text="Close", width=12, command=lambda: (root.grab_release(), root.destroy())).pack(side="left", padx=10)

    root.wait_window()
