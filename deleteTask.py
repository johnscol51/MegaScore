#!/usr/bin/env python3
# deleteTask.py
# Modeled on TaskPointsReview.py: lists tasks from TaskPoints.csv on startup.
# Allows user to input a task number and remove all rows for that task.
# Backs up TaskPoints.csv to TaskPoints-old.csv before changes.
# Reports number of rows removed in the GUI.

import tkinter as tk
from tkinter import ttk, messagebox
import os
import csv
import shutil
from utils import log  # for debug logging

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
    def load_csv():
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
                tasks.setdefault(task_no, []).append({
                    "task_no": task_no,
                    "name": point_name,
                    "lat": lat,
                    "lon": lon,
                })
        return tasks, duplicates, incomplete_rows

    # -----------------------------------------------------
    # GUI setup
    # -----------------------------------------------------
    root = tk.Toplevel()
    root.geometry("700x400")
    root.title("Delete Task from TaskPoints.csv")
    root.lift()
    root.focus_force()
    root.grab_set()

    # Options frame (simplified)
    options_frame = tk.Frame(root)
    options_frame.pack(fill="x", padx=10, pady=5)

    debug_var = tk.BooleanVar(value=False)
    tk.Checkbutton(options_frame, text="Log to debug", variable=debug_var).pack(side="left", padx=(30, 0))

    # Delete task section
    tk.Label(options_frame, text="Task to delete:").pack(side="left", padx=(30, 5))
    delete_task_var = tk.StringVar()
    tk.Entry(options_frame, textvariable=delete_task_var, width=6).pack(side="left", padx=(5, 0))

    def delete_task():
        task_to_delete = delete_task_var.get()
        if not task_to_delete.isdigit():
            messagebox.showerror("Error", "Enter a valid task number.")
            return

        # Backup TaskPoints.csv to TaskPoints-old.csv
        backup_path = tp_path.replace(".csv", "-old.csv")
        shutil.copy(tp_path, backup_path)
        log(f"Backup created: {backup_path}")

        # Load all rows
        all_rows = []
        with open(tp_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            all_rows = list(reader)

        # Filter out rows with the task number
        remaining_rows = [row for row in all_rows if len(row) > 0 and row[0] != task_to_delete]
        removed_count = len(all_rows) - len(remaining_rows)

        # Write back the remaining rows
        with open(tp_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(remaining_rows)

        append_line(f"Removed {removed_count} rows for task {task_to_delete}.")
        append_line(f"Backup: {os.path.basename(backup_path)}")
        append_line("")

        # Refresh the task list
        process()

    tk.Button(options_frame, text="Delete Task", command=delete_task).pack(side="left", padx=10)

    text_frame = tk.Frame(root)
    text_frame.pack(fill="both", expand=True, padx=10, pady=5)
    text_widget = tk.Text(text_frame, wrap="word", font=("Consolas", 9), height=15)  # Limit to 15 lines (adjust as needed)
    #text_widget = tk.Text(text_frame, wrap="word", font=("Consolas", 9))
    text_widget.pack(side="left", fill="both", expand=True)
    scroll = tk.Scrollbar(text_frame, command=text_widget.yview)
    scroll.pack(side="right", fill="y")
    text_widget.configure(yscrollcommand=scroll.set)

    def append_line(line=""):
        text_widget.insert("end", line + "\n")
        text_widget.see("end")
        if debug_var.get():
            log(line)

    # -----------------------------------------------------
    # PROCESS (show list immediately)
    # -----------------------------------------------------
    def process():
        text_widget.delete("1.0", "end")
        tasks, duplicates, incomplete_rows = load_csv()

        # Duplicate + incomplete rows
        if duplicates or incomplete_rows:
            append_line("ERRORS:")
            for task_no, point_name in duplicates:
                append_line(f" Duplicate point: Task {task_no}, {point_name}")
            for task_no, row in incomplete_rows:
                tstr = f"Task {task_no}" if task_no else "Task ?"
                append_line(f" {tstr}: Incomplete row: {row}")
            append_line("")

        # Always show the task list
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
        append_line("")

    # Show list immediately
    process()

    # Buttons
    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=5)
    tk.Button(btn_frame, text="Refresh List", width=12, bg="#0066cc", fg="white", command=process).pack(side="left", padx=10)
    tk.Button(btn_frame, text="Close", width=12, command=lambda: (root.grab_release(), root.destroy())).pack(side="left", padx=10)

    root.wait_window()
