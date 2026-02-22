#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox
import csv
import os
import re
from datetime import datetime

from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas


# =========================================================
#  LOAD COMP DETAILS
# =========================================================
def load_comp_details(comp_path):
    comp = {}
    with open(comp_path, newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                comp[row[0].strip()] = row[1].strip()
    return comp


# =========================================================
#  LOAD NAV SCORE CSV FOR ONE PILOT/TASK
# =========================================================
def load_nav_score(csv_path):
    """
    Returns a dict with:
      pilotNo, pilotName, sp_time, ground_speed,
      tp_total, hg_total, time_total, photo_total, raw_score
    based on the 'data' row and SUMMARY semantics from ScoreNavTask.
    """
    base_name = os.path.basename(csv_path)
    m = re.match(r"^(\d+)T(\d{2})V(\d+)R1_(.+)\.csv$", base_name)
    if not m:
        return None

    pilotNo = m.group(1)
    pilotName = m.group(4)

    sp_time = ""
    ground_speed = 0
    tp_total = 0
    hg_total = 0
    time_total = 0
    photo_total = 0

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) == 0:
                continue
            if row[0] == "data":
                # data, run_timestamp, sp_time, tp_total, hg_total, time_total, photo_total, timing_mode, ground_speed
                sp_time = row[2]
                tp_total = int(row[3])
                hg_total = int(row[4])
                time_total = int(row[5])
                photo_total = int(row[6])
                ground_speed = int(float(row[8])) if len(row) > 8 and row[8] else 0
                break

    raw_score = tp_total + hg_total + time_total + photo_total

    return {
        "pilotNo": pilotNo,
        "pilotName": pilotName,
        "sp_time": sp_time,
        "ground_speed": ground_speed,
        "tp_total": tp_total,
        "hg_total": hg_total,
        "time_total": time_total,
        "photo_total": photo_total,
        "raw_score": raw_score,
    }


# =========================================================
#  MAIN GUI
# =========================================================
def run(DataDir):
    comp_path = os.path.join(DataDir, "CompDetails.csv")
    comp = load_comp_details(comp_path)

    scores_dir = os.path.join(DataDir, "scores")
    results_dir = os.path.join(DataDir, "results")
    os.makedirs(results_dir, exist_ok=True)

    root = tk.Toplevel()
    root.geometry("900x600")
    root.title("Navigation Results")
    root.lift()
    root.focus_force()
    root.grab_set()
    root.protocol("WM_DELETE_WINDOW", lambda: (root.grab_release(), root.destroy()))

    frame = tk.Frame(root)
    frame.pack(pady=10, padx=20, fill="x")

    tk.Label(frame, text="Task Number:").grid(row=0, column=0, sticky="e", padx=5)
    task_var = tk.StringVar()
    task_dd = ttk.Combobox(
        frame,
        textvariable=task_var,
        values=[str(i) for i in range(1, 16)],
        width=10,
        state="readonly",
    )
    task_dd.grid(row=0, column=1, sticky="w", padx=5)

    # Table: Pilot No, Pilot Name, Notes, Penalty
    table_frame = tk.Frame(root)
    table_frame.pack(pady=10, padx=20, fill="both", expand=True)

    headers = ["Pilot No", "Pilot Name", "Notes", "Penalty (%)"]
    for col, h in enumerate(headers):
        tk.Label(table_frame, text=h, font=("Arial", 10, "bold")).grid(row=0, column=col, padx=5, pady=5)

    table_rows = []  # each: {pilotNo, pilotName, notesVar, penaltyVar, data}

    penalty_options = ["0", "20", "40", "50", "100"]

    # -----------------------------------------------------
    # POPULATE TABLE FOR SELECTED TASK
    # -----------------------------------------------------
    def populate_table():
        for widget in table_frame.winfo_children():
            if int(widget.grid_info()["row"]) > 0:
                widget.destroy()
        table_rows.clear()

        task = task_var.get()
        if not task:
            return

        taskNo_file = f"{int(task):02d}"
        # Find all score CSVs for this task
        nav_files = []
        for f in os.listdir(scores_dir):
            if not f.lower().endswith(".csv"):
                continue
            m = re.match(r"^(\d+)T(\d{2})V(\d+)R1_(.+)\.csv$", f)
            if m and m.group(2) == taskNo_file:
                nav_files.append(f)

        nav_files.sort()

        row_index = 1
        for fname in nav_files:
            csv_path = os.path.join(scores_dir, fname)
            info = load_nav_score(csv_path)
            if not info:
                continue

            notesVar = tk.StringVar(value="")
            penaltyVar = tk.StringVar(value="0")

            e_no = tk.Entry(table_frame, width=10)
            e_no.insert(0, info["pilotNo"])
            e_no.config(state="readonly")
            e_no.grid(row=row_index, column=0, padx=5, pady=2)

            e_name = tk.Entry(table_frame, width=30)
            e_name.insert(0, info["pilotName"])
            e_name.config(state="readonly")
            e_name.grid(row=row_index, column=1, padx=5, pady=2)

            e_notes = tk.Entry(table_frame, textvariable=notesVar, width=25)
            e_notes.grid(row=row_index, column=2, padx=5, pady=2)

            dd_penalty = ttk.Combobox(
                table_frame,
                textvariable=penaltyVar,
                values=penalty_options,
                width=5,
                state="readonly",
            )
            dd_penalty.grid(row=row_index, column=3, padx=5, pady=2)

            table_rows.append({
                "pilotNo": info["pilotNo"],
                "pilotName": info["pilotName"],
                "notesVar": notesVar,
                "penaltyVar": penaltyVar,
                "data": info,
            })

            row_index += 1

    task_var.trace_add("write", lambda *args: populate_table())

    # -----------------------------------------------------
    # SAVE RESULTS (CSV + PDF)
    # -----------------------------------------------------
    def save_results():
        task = task_var.get()
        if not task:
            messagebox.showerror("Error", "Please select a task number.")
            return

        if not table_rows:
            messagebox.showerror("Error", "No pilots found for this task.")
            return

        # Compute raw scores with penalties applied
        results = []
        for row in table_rows:
            info = row["data"]
            notes = row["notesVar"].get().strip()
            penalty_str = row["penaltyVar"].get().strip()
            penalty_pct = int(penalty_str) if penalty_str else 0

            raw = int(info["raw_score"])
            adjusted_raw = int(raw * (100 - penalty_pct) / 100)

            results.append({
                "pilotNo": info["pilotNo"],
                "pilotName": info["pilotName"],
                "sp_time": info["sp_time"],
                "ground_speed": info["ground_speed"],
                "tp_total": info["tp_total"],
                "hg_total": info["hg_total"],
                "photo_total": info["photo_total"],
                "time_total": info["time_total"],
                "raw_score": adjusted_raw,
                "penalty_pct": penalty_pct,
                "notes": notes,
            })

        # Normalise scores
        highest = max(r["raw_score"] for r in results) if results else 0
        if highest <= 0:
            for r in results:
                r["score"] = 0
        else:
            for r in results:
                r["score"] = int(r["raw_score"] * (1000 / highest))

        # Sort by score descending
        results.sort(key=lambda r: r["score"], reverse=True)

        # Assign ranking
        rank = 1
        for r in results:
            r["rank"] = rank
            rank += 1

        # Write CSV
        csv_path = os.path.join(results_dir, f"task{task}NavResults.csv")
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow([
                "ranking",
                "pilot_no",
                "pilot_name",
                "SP_time",
                "ground_speed",
                "TP_score",
                "HG_score",
                "photo_score",
                "time_score",
                "raw_score",
                "score",
                "penalty_pct",
                "notes",
            ])
            for r in results:
                w.writerow([
                    r["rank"],
                    r["pilotNo"],
                    r["pilotName"],
                    r["sp_time"],
                    r["ground_speed"],
                    r["tp_total"],
                    r["hg_total"],
                    r["photo_total"],
                    r["time_total"],
                    r["raw_score"],
                    r["score"],
                    r["penalty_pct"],
                    r["notes"],
                ])

        # Write PDF
        pdf_path = os.path.join(results_dir, f"task{task}NavResults.pdf")
        c = canvas.Canvas(pdf_path, pagesize=landscape(A4))
        width, height = landscape(A4)

        # Logo
        c.setFillColorRGB(0.0, 0.2, 0.8)
        c.rect(width - 80, height - 60, 30, 30, fill=1, stroke=0)
        c.setFillColorRGB(1.0, 0.9, 0.0)
        c.rect(width - 45, height - 60, 30, 30, fill=1, stroke=0)

        # Title
        y = height - 40
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(40, y, f"{comp.get('name', 'Competition')} — Navigation Results")
        y -= 25

        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, y, f"Task {task}")
        y -= 30

        # Headers
        c.setFont("Helvetica-Bold", 9)
        c.drawString(40, y, "Rank")
        c.drawString(70, y, "Pilot No")
        c.drawString(120, y, "Pilot Name")
        c.drawString(260, y, "SP Time")
        c.drawString(320, y, "GS")
        c.drawString(350, y, "TP")
        c.drawString(380, y, "HG")
        c.drawString(410, y, "Photo")
        c.drawString(450, y, "Time")
        c.drawString(490, y, "Raw")
        c.drawString(530, y, "Score")
        c.drawString(570, y, "Pen%")
        c.drawString(610, y, "Notes")
        c.line(40, y - 3, 820 - 40, y - 3)
        y -= 15

        c.setFont("Helvetica", 8)
        row_step = 12

        for r in results:
            if y < 60:

                # Footer before page break
                footer_text = f"Generated: {datetime.now().isoformat(timespec='seconds')}    File: {os.path.basename(pdf_path)}"
                c.setFont("Helvetica", 8)
                c.drawString(40, 20, footer_text)

                c.showPage()
                y = height - 40

                # Logo on new page
                c.setFillColorRGB(0.0, 0.2, 0.8)
                c.rect(width - 80, height - 60, 30, 30, fill=1, stroke=0)
                c.setFillColorRGB(1.0, 0.9, 0.0)
                c.rect(width - 45, height - 60, 30, 30, fill=1, stroke=0)

                c.setFillColorRGB(0, 0, 0)
                c.setFont("Helvetica-Bold", 12)
                c.drawString(40, y, f"{comp.get('name', 'Competition')} — Navigation Results (cont.)")
                y -= 30
                c.setFont("Helvetica-Bold", 9)
                c.drawString(40, y, "Rank")
                c.drawString(70, y, "Pilot No")
                c.drawString(120, y, "Pilot Name")
                c.drawString(260, y, "SP Time")
                c.drawString(320, y, "GS")
                c.drawString(350, y, "TP")
                c.drawString(380, y, "HG")
                c.drawString(410, y, "Photo")
                c.drawString(450, y, "Time")
                c.drawString(490, y, "Raw")
                c.drawString(530, y, "Score")
                c.drawString(570, y, "Pen%")
                c.drawString(610, y, "Notes")
                c.line(40, y - 3, 820 - 40, y - 3)
                y -= 15
                c.setFont("Helvetica", 8)

            # Horizontal separator
            c.setLineWidth(0.2)
            c.setStrokeGray(0.7)
            c.line(40, y - 2, 820 - 40, y - 2)

            # Row text
            c.setFillColorRGB(0, 0, 0)
            c.drawString(40, y, str(r["rank"]))
            c.drawString(70, y, r["pilotNo"])
            c.drawString(120, y, r["pilotName"])
            c.drawString(260, y, r["sp_time"])
            c.drawString(320, y, str(r["ground_speed"]))
            c.drawString(350, y, str(r["tp_total"]))
            c.drawString(380, y, str(r["hg_total"]))
            c.drawString(410, y, str(r["photo_total"]))
            c.drawString(450, y, str(r["time_total"]))
            c.drawString(490, y, str(r["raw_score"]))
            c.drawString(530, y, str(r["score"]))
            c.drawString(570, y, str(r["penalty_pct"]))
            c.drawString(610, y, r["notes"][:30])

            y -= row_step

        # Final page footer
        footer_text = f"Generated: {datetime.now().isoformat(timespec='seconds')}    File: {os.path.basename(pdf_path)}"
        c.setFont("Helvetica", 8)
        c.drawString(40, 20, footer_text)

        c.save()

        messagebox.showinfo("Saved", f"Results saved to:\n{csv_path}\n{pdf_path}")
        root.grab_release()
        root.destroy()

    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=10)

    tk.Button(
        btn_frame,
        text="OK",
        width=12,
        bg="#0066cc",
        fg="white",
        command=save_results,
    ).pack(side="left", padx=10)

    tk.Button(
        btn_frame,
        text="Cancel",
        width=12,
        command=lambda: (root.grab_release(), root.destroy()),
    ).pack(side="left", padx=10)

    root.wait_window()

