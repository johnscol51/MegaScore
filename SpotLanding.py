#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox
import csv
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


# =========================================================
#  LOAD PILOTS
# =========================================================
def load_pilots(pilot_file):
    pilots = []
    with open(pilot_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                pilots.append((row[0].strip(), row[1].strip()))
    return pilots


# =========================================================
#  MAIN GUI
# =========================================================
def run(DataDir):
    # Load CompDetails.csv to find pilot file
    comp_path = os.path.join(DataDir, "CompDetails.csv")
    comp = {}
    with open(comp_path, newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                comp[row[0].strip()] = row[1].strip()

    pilot_file = os.path.join(DataDir, comp["pilotFile"])
    pilots = load_pilots(pilot_file)

    # NEW: results directory instead of scores
    results_dir = os.path.join(DataDir, "results")
    os.makedirs(results_dir, exist_ok=True)
    scores_dir = os.path.join(DataDir, "scores")
    os.makedirs(scores_dir, exist_ok=True)


    # -----------------------------------------------------
    # GUI SETUP
    # -----------------------------------------------------
    root = tk.Toplevel()
    root.geometry("800x750")
    root.title("Spot Landing Scoring")
    root.lift()
    root.focus_force()
    root.grab_set()

    frame = tk.Frame(root)
    frame.pack(pady=10, padx=20, fill="x")

    # Task selector
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

    # Spot landing type selector
    tk.Label(frame, text="Spot Landing Type:").grid(row=1, column=0, sticky="e", padx=5)
    type_var = tk.StringVar(value="power precision")
    type_dd = ttk.Combobox(
        frame,
        textvariable=type_var,
        values=["power precision", "engine off"],
        width=20,
        state="readonly",
    )
    type_dd.grid(row=1, column=1, sticky="w", padx=5)

    # -----------------------------------------------------
    # TABLE FRAME
    # -----------------------------------------------------
    table_frame = tk.Frame(root)
    table_frame.pack(pady=10, padx=20, fill="both", expand=True)

    headers = ["Pilot No", "Pilot Name", "Landing Box", "Landing Score", "Notes"]
    for col, h in enumerate(headers):
        tk.Label(table_frame, text=h, font=("Arial", 10, "bold")).grid(row=0, column=col, padx=5, pady=5)

    landing_box_options = ["250", "200", "150", "100", "50", "0"]

    table_rows = []  # list of dicts

    # -----------------------------------------------------
    # FUNCTION TO ADD A ROW
    # -----------------------------------------------------
    def add_row(row_index, pilotNo="", pilotName="", landingBox="0", notes=""):
        boxVar = tk.StringVar(value=landingBox)
        scoreVar = tk.StringVar()
        notesVar = tk.StringVar(value=notes)

        def update_score(*args):
            if notesVar.get().strip():
                scoreVar.set("0")
            else:
                scoreVar.set(boxVar.get())

        boxVar.trace_add("write", update_score)
        notesVar.trace_add("write", update_score)
        update_score()

        e_no = tk.Entry(table_frame, width=10)
        e_no.insert(0, pilotNo)
        e_no.grid(row=row_index, column=0, padx=5, pady=2)

        e_name = tk.Entry(table_frame, width=25)
        e_name.insert(0, pilotName)
        e_name.grid(row=row_index, column=1, padx=5, pady=2)

        dd_box = ttk.Combobox(
            table_frame,
            textvariable=boxVar,
            values=landing_box_options,
            width=10,
            state="readonly",
        )
        dd_box.grid(row=row_index, column=2, padx=5, pady=2)

        e_score = tk.Entry(table_frame, textvariable=scoreVar, width=10, state="readonly")
        e_score.grid(row=row_index, column=3, padx=5, pady=2)

        e_notes = tk.Entry(table_frame, textvariable=notesVar, width=20)
        e_notes.grid(row=row_index, column=4, padx=5, pady=2)

        table_rows.append({
            "pilotNo": e_no,
            "pilotName": e_name,
            "boxVar": boxVar,
            "scoreVar": scoreVar,
            "notesVar": notesVar,
        })

    # -----------------------------------------------------
    # POPULATE TABLE (always fresh)
    # -----------------------------------------------------
    def populate_table():
        for widget in table_frame.winfo_children():
            if int(widget.grid_info()["row"]) > 0:
                widget.destroy()
        table_rows.clear()

        row_index = 1
        for pno, pname in pilots:
            add_row(row_index, pilotNo=pno, pilotName=pname, landingBox="0", notes="")
            row_index += 1

        add_row(row_index, pilotNo="", pilotName="", landingBox="0", notes="")
        add_row(row_index + 1, pilotNo="", pilotName="", landingBox="0", notes="")

    task_var.trace_add("write", lambda *args: populate_table())

    # -----------------------------------------------------
    # SAVE CSV + PDF
    # -----------------------------------------------------
    def save_csv():
        task = task_var.get()
        if not task:
            messagebox.showerror("Error", "Please select a task number.")
            return

        # NEW unified CSV filename
        csv_path = os.path.join(results_dir, f"task{task}spotLandingResults.csv")

        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)

            # NEW unified header
            w.writerow(["ranking", "pilot_no", "pilot_name", "score"])

            # Sort rows by score descending
            sorted_rows = sorted(
                table_rows,
                key=lambda r: int(r["scoreVar"].get() or 0),
                reverse=True
            )

            ranking = 1
            for row in sorted_rows:
                pno = row["pilotNo"].get().strip()
                pname = row["pilotName"].get().strip()
                score = row["scoreVar"].get().strip()

                if not pno and not pname:
                    continue

                w.writerow([ranking, pno, pname, score])
                ranking += 1

        # -----------------------------------------------------
        # PDF output (unchanged)
        # -----------------------------------------------------
        pdf_path = os.path.join(scores_dir, f"task{task}spotLanding.pdf")
        c = canvas.Canvas(pdf_path, pagesize=A4)
        width, height = A4

        # Logo
        c.setFillColorRGB(0.0, 0.2, 0.8)
        c.rect(width - 80, height - 60, 30, 30, fill=1, stroke=0)
        c.setFillColorRGB(1.0, 0.9, 0.0)
        c.rect(width - 45, height - 60, 30, 30, fill=1, stroke=0)

        # Title
        y = height - 40
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(40, y, f"{comp.get('name', 'Competition')} — Spot Landing")
        y -= 25

        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, y, f"Task {task}   |   Type: {type_var.get()}")
        y -= 30

        # Table headers
        c.setFont("Helvetica-Bold", 10)
        c.drawString(40, y, "Pilot No")
        c.drawString(120, y, "Pilot Name")
        c.drawString(300, y, "Landing Box")
        c.drawString(380, y, "Score")
        c.drawString(440, y, "Notes")
        c.line(40, y - 3, 550, y - 3)
        y -= 15

        sorted_rows = sorted(
            table_rows,
            key=lambda r: int(r["scoreVar"].get() or 0),
            reverse=True
        )

        c.setFont("Helvetica", 9)
        row_step = 13

        for row in sorted_rows:
            pno = row["pilotNo"].get().strip()
            pname = row["pilotName"].get().strip()
            box = row["boxVar"].get().strip()
            score = row["scoreVar"].get().strip()
            notes = row["notesVar"].get().strip()

            if not pno and not pname:
                continue

            c.setLineWidth(0.2)
            c.setStrokeGray(0.7)
            c.line(40, y - 2, 550, y - 2)

            for x in [40, 120, 300, 380, 440, 550]:
                c.line(x, y + 10, x, y - 2)

            c.setFillColorRGB(0, 0, 0)
            c.drawString(40, y, pno)
            c.drawString(120, y, pname)
            c.drawString(300, y, box)
            c.drawString(380, y, score)
            c.drawString(440, y, notes)

            y -= row_step



            if y < 60:
                # Footer before page break
                footer_text = f"Generated: {datetime.now().isoformat(timespec='seconds')} File: {os.path.basename(pdf_path)}"
                c.setFont("Helvetica", 8)
                c.drawString(40, 20, "MegaScore Goblin")
                c.drawRightString(width - 40, 20, footer_text)
                c.showPage()
                y = height - 40
                c.setFillColorRGB(0.0, 0.2, 0.8)
                c.rect(width - 80, height - 60, 30, 30, fill=1, stroke=0)
                c.setFillColorRGB(1.0, 0.9, 0.0)
                c.rect(width - 45, height - 60, 30, 30, fill=1, stroke=0)
                c.setFillColorRGB(0, 0, 0)
                c.setFont("Helvetica-Bold", 12)
                c.drawString(40, y, f"{comp.get('name', 'Competition')} — Spot Landing (cont.)")
                y -= 30
                c.setFont("Helvetica", 9)
        # Footer on last page
        footer_text = f"Generated: {datetime.now().isoformat(timespec='seconds')} File: {os.path.basename(pdf_path)}"
        c.setFont("Helvetica", 8)
        c.drawString(40, 20, "MegaScore Goblin")
        c.drawRightString(width - 40, 20, footer_text)
        c.save()
        messagebox.showinfo("Saved", f"Spot landing saved to:\n{csv_path}")
        root.grab_release()
        root.destroy()

    # -----------------------------------------------------
    # BUTTONS
    # -----------------------------------------------------
    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=10)

    tk.Button(btn_frame, text="OK", width=12, fg="blue", command=save_csv).pack(side="left", padx=10)
    tk.Button(btn_frame, text="Cancel", width=12, command=lambda: (root.grab_release(), root.destroy())).pack(side="left", padx=10)

    root.wait_window()

