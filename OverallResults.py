#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox
import os
import csv
import re
from datetime import datetime

from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas


# =========================================================
#  MAIN GUI + LOGIC
# =========================================================
def run(DataDir):

    # -----------------------------------------------------
    # Load competition name
    # -----------------------------------------------------
    comp_path = os.path.join(DataDir, "CompDetails.csv")
    comp = {}
    with open(comp_path, newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                comp[row[0].strip()] = row[1].strip()

    comp_name = comp.get("name", "Competition")

    results_dir = os.path.join(DataDir, "results")
    os.makedirs(results_dir, exist_ok=True)

    # -----------------------------------------------------
    # Discover available task results
    # -----------------------------------------------------
    task_files = []
    regex = re.compile(r"^task(\d+)(.*)Results\.csv$", re.IGNORECASE)

    for fname in os.listdir(results_dir):
        m = regex.match(fname)
        if m:
            task_no = int(m.group(1))
            raw_type = m.group(2).strip()

            # Normalise task type
            task_type = raw_type.replace("_", " ").strip()
            if task_type.lower().endswith("results"):
                task_type = task_type[:-7]
            task_type = task_type.strip()
            if task_type == "":
                task_type = "Task"

            # Capitalise nicely
            task_type = " ".join(w.capitalize() for w in task_type.split())

            task_files.append((task_no, task_type, fname))

    task_files.sort(key=lambda x: x[0])

    # -----------------------------------------------------
    # GUI
    # -----------------------------------------------------
    root = tk.Toplevel()
    root.geometry("600x550")
    root.title("Overall Results — Task Selection")
    root.lift()
    root.focus_force()
    root.grab_set()

    tk.Label(root, text=f"{comp_name}", font=("Arial", 14, "bold")).pack(pady=10)
    tk.Label(root, text="Select tasks to include:", font=("Arial", 11)).pack()

    frame = tk.Frame(root)
    frame.pack(pady=10, padx=20, fill="both", expand=True)

    canvas_frame = tk.Canvas(frame)
    scrollbar = tk.Scrollbar(frame, orient="vertical", command=canvas_frame.yview)
    scroll_frame = tk.Frame(canvas_frame)

    scroll_frame.bind(
        "<Configure>",
        lambda e: canvas_frame.configure(scrollregion=canvas_frame.bbox("all"))
    )

    canvas_frame.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas_frame.configure(yscrollcommand=scrollbar.set)

    canvas_frame.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    check_vars = {}

    # Two-line task selector
    for task_no, task_type, fname in task_files:
        var = tk.BooleanVar(value=True)
        check_vars[fname] = var

        row = tk.Frame(scroll_frame)
        row.pack(anchor="w", pady=4)

        cb = tk.Checkbutton(row, variable=var)
        cb.grid(row=0, column=0, rowspan=2, padx=5)

        tk.Label(row, text=f"Task {task_no}", font=("Arial", 10, "bold")).grid(row=0, column=1, sticky="w")
        tk.Label(row, text=task_type, font=("Arial", 9)).grid(row=1, column=1, sticky="w")

    # -----------------------------------------------------
    # PROCESS SELECTION
    # -----------------------------------------------------
    def process_results():

        selected = [f for f, v in check_vars.items() if v.get()]
        if not selected:
            messagebox.showerror("Error", "No tasks selected.")
            return

        pilot_data = {}   # pilot_no → {name, scores{task_no:score}}

        for fname in selected:
            m = regex.match(fname)
            task_no = int(m.group(1))

            csv_path = os.path.join(results_dir, fname)

            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    pilot_no = row.get("pilot_no")
                    pilot_name = row.get("pilot_name")
                    score_str = row.get("score")

                    if not pilot_no or not pilot_name:
                        continue

                    try:
                        score = int(score_str)
                    except:
                        score = 0

                    if pilot_no not in pilot_data:
                        pilot_data[pilot_no] = {
                            "name": pilot_name,
                            "scores": {}
                        }

                    pilot_data[pilot_no]["scores"][task_no] = score

        # -------------------------------------------------
        # Build sorted task list
        # -------------------------------------------------
        selected_task_numbers = sorted(
            list({int(regex.match(f).group(1)) for f in selected})
        )

        # -------------------------------------------------
        # Compute totals
        # -------------------------------------------------
        leaderboard = []

        for pilot_no, pdata in pilot_data.items():
            total = 0
            row_scores = {}

            for t in selected_task_numbers:
                if t in pdata["scores"]:
                    s = pdata["scores"][t]
                    row_scores[t] = s
                    total += s
                else:
                    row_scores[t] = None  # missing → show "-"

            leaderboard.append({
                "pilot_no": pilot_no,
                "pilot_name": pdata["name"],
                "scores": row_scores,
                "total": total,
            })

        leaderboard.sort(key=lambda r: r["total"], reverse=True)

        # -------------------------------------------------
        # Write PDF
        # -------------------------------------------------
        pdf_path = os.path.join(results_dir, "OverallResults.pdf")
        c = canvas.Canvas(pdf_path, pagesize=landscape(A4))
        width, height = landscape(A4)

        # Logo
        c.setFillColorRGB(0.0, 0.2, 0.8)
        c.rect(width - 80, height - 60, 30, 30, fill=1, stroke=0)
        c.setFillColorRGB(1.0, 0.9, 0.0)
        c.rect(width - 45, height - 60, 30, 30, fill=1, stroke=0)
        c.setFillColorRGB(0, 0, 0)

        y = height - 40
        c.setFont("Helvetica-Bold", 18)
        c.drawString(40, y, f"{comp_name} — Overall Leader Board")
        y -= 30

        # Build task label map
        task_labels = {}
        for task_no, task_type, fname in task_files:
            if fname in selected:
                task_labels[task_no] = task_type

        # Header row (two-line task headers)
        c.setFont("Helvetica-Bold", 10)
        col_x = {}

        # Ranking + pilot columns
        c.drawString(40, y, "Rank")
        c.drawString(80, y, "Pilot No")
        c.drawString(160, y, "Pilot Name")

        # Task columns
        x = 300
        for t in selected_task_numbers:
            # First line: T<number>
            c.setFont("Helvetica-Bold", 10)
            c.drawString(x, y, f"T{t}")

            # Second line: task description
            c.setFont("Helvetica", 8)
            c.drawString(x, y - 12, task_labels[t])

            col_x[t] = x
            x += 55  # spacing between task columns

        # Total column
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x, y, "Total")
        total_x = x

        # Move below header block
        y -= 25
        c.line(40, y, width - 40, y)
        y -= 10

        # Rows
        c.setFont("Helvetica", 9)
        row_step = 14
        rank = 1

        for r in leaderboard:
            if y < 40:
                # Footer
                footer = f"Generated: {datetime.now().isoformat(timespec='seconds')}    File: {os.path.basename(pdf_path)}"
                c.setFont("Helvetica", 8)
                # Left side
                c.drawString(40, 20, "MegaScorer Goblin")
                # Right side
                c.drawRightString(width - 40, 20, footer)


                # New page
                c.showPage()
                y = height - 40

                # Logo on new page
                c.setFillColorRGB(0.0, 0.2, 0.8)
                c.rect(width - 80, height - 60, 30, 30, fill=1, stroke=0)
                c.setFillColorRGB(1.0, 0.9, 0.0)
                c.rect(width - 45, height - 60, 30, 30, fill=1, stroke=0)
                c.setFillColorRGB(0, 0, 0)

                c.setFont("Helvetica-Bold", 18)
                c.drawString(40, y, f"{comp_name} — Overall Leader Board (cont.)")
                y -= 30
                c.setFont("Helvetica", 9)

            # Ranking column
            c.drawString(40, y, str(rank))
            rank += 1

            # Pilot columns
            c.drawString(80, y, r["pilot_no"])
            c.drawString(160, y, r["pilot_name"])

            # Task scores
            for t in selected_task_numbers:
                val = r["scores"][t]
                txt = "-" if val is None else str(val)
                c.drawString(col_x[t], y, txt)

            # Total
            c.drawString(total_x, y, str(r["total"]))

            y -= row_step

        # Final footer
        footer = f"Generated: {datetime.now().isoformat(timespec='seconds')}    File: {os.path.basename(pdf_path)}"
        c.setFont("Helvetica", 8)
        # Left side
        c.drawString(40, 20, "MegaScorer Goblin")
        # Right side
        c.drawRightString(width - 40, 20, footer)

        c.save()

        messagebox.showinfo("Saved", f"Overall results saved to:\n{pdf_path}")
        root.grab_release()
        root.destroy()

    # -----------------------------------------------------
    # Buttons
    # -----------------------------------------------------
    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=10)

    tk.Button(
        btn_frame,
        text="OK",
        width=12,
        fg="blue",
        command=process_results,
    ).pack(side="left", padx=10)

    tk.Button(
        btn_frame,
        text="Cancel",
        width=12,
        command=lambda: (root.grab_release(), root.destroy()),
    ).pack(side="left", padx=10)

    root.wait_window()

