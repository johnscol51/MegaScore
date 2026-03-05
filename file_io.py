# file_io.py
#
# Handles:
#   - DataDir selection
#   - Loading TaskPoints_<taskNo>.csv
#   - Saving TaskPoints_<taskNo>.csv
#
# CSV format:
#   taskNo,pointName,lat,lon,dist,PT
#
# All values are strings on disk; lat/lon/dist are converted to floats on load.

import os
import csv
from tkinter import filedialog, messagebox


# ============================================================
# DataDir selection
# ============================================================
def choose_data_dir(initial_dir=None):
    """
    Open a directory chooser dialog and return the selected path.
    Returns None if cancelled.
    """
    path = filedialog.askdirectory(initialdir=initial_dir)
    if not path:
        return None
    return path


# ============================================================
# Filename helpers
# ============================================================
def taskpoints_filename(task_no):
    """Return the expected filename for a task."""
    return f"TaskPoints_{task_no}.csv"


def taskpoints_path(data_dir, task_no):
    """Return full path to TaskPoints_<taskNo>.csv."""
    return os.path.join(data_dir, taskpoints_filename(task_no))


# ============================================================
# Load CSV
# ============================================================
def load_taskpoints(data_dir, task_no):
    """
    Load TaskPoints_<taskNo>.csv if it exists.
    Supports both:
        - headerless CSV (preferred)
        - CSV with header row (backwards compatible)

    Returns list of dicts:
        { "name", "lat", "lon", "dist", "pt" }
    """

    path = taskpoints_path(data_dir, task_no)
    if not os.path.exists(path):
        return None

    rows = []
    try:
        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)

            for row in reader:
                # Skip empty or malformed rows
                if not row or len(row) < 4:
                    continue

                # Detect and skip header rows
                # Works for both old and new formats
                header_tokens = [c.lower() for c in row]
                if ("taskno" in header_tokens or
                    "pointname" in header_tokens or
                    "lat" in header_tokens):
                    continue

                # Expected format (headerless):
                # 0: taskNo
                # 1: pointName
                # 2: lat
                # 3: lon
                # 4: dist (optional)
                # 5: PT   (optional)

                try:
                    name = row[1].strip()
                    lat = float(row[2])
                    lon = float(row[3])

                    # Defaults if missing
                    dist = float(row[4]) if len(row) > 4 and row[4] else 0.0
                    pt = row[5].strip() if len(row) > 5 and row[5] else "N"

                    rows.append({
                        "name": name,
                        "lat": lat,
                        "lon": lon,
                        "dist": dist,
                        "pt": pt,
                    })

                except Exception:
                    # Skip malformed rows safely
                    continue

        return rows

    except Exception as e:
        messagebox.showerror("Error", f"Failed to load CSV:\n{e}")
        return None


# ============================================================
# Save CSV
# ============================================================
def save_taskpoints(data_dir, task_no, rows):
    """
    Save points to TaskPoints_<taskNo>.csv.
    rows = list of dicts:
        { "name", "lat", "lon", "dist", "pt" }
    """

    if not os.path.isdir(data_dir):
        messagebox.showerror("Error", "Invalid DataDir.")
        return False

    path = taskpoints_path(data_dir, task_no)

    try:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            #writer.writerow(["taskNo", "pointName", "lat", "lon", "dist", "PT"])

            for r in rows:
                writer.writerow([
                    task_no,
                    r["name"],
                    f"{r['lat']:.6f}",
                    f"{r['lon']:.6f}",
                    f"{r['dist']:.2f}",
                    r["pt"],
                ])

        return True

    except Exception as e:
        messagebox.showerror("Error", f"Failed to save CSV:\n{e}")
        return False
# ============================================================
# Load from master TaskPoints.csv (filtered by task_no)
# ============================================================
def load_taskpoints_from_master(master_path, task_no):
    """
    Load points from the master TaskPoints.csv file, filtered to only include
    rows where the first column (task number) matches the given task_no.
    
    Returns list of dicts in the same format as load_taskpoints():
        { "name": ..., "lat": float, "lon": float, "dist": float, "pt": str }
    
    Returns None if file not found or error occurs.
    """
    if not os.path.exists(master_path):
        return None
    
    rows = []
    try:
        with open(master_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                # Skip empty/malformed rows
                if len(row) < 6:
                    continue
                
                # Check task number match (first column)
                if row[0].strip() != str(task_no):
                    continue
                
                # Parse fields
                try:
                    name = row[1].strip()
                    lat = float(row[2])
                    lon = float(row[3])
                    dist = float(row[4]) if row[4].strip() else 0.0
                    pt = row[5].strip() if row[5].strip() else "N"
                    rows.append({
                        "name": name,
                        "lat": lat,
                        "lon": lon,
                        "dist": dist,
                        "pt": pt,
                    })
                except (ValueError, IndexError):
                    # Skip malformed rows silently
                    continue
        
        return rows if rows else None
    
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load master TaskPoints.csv:\n{e}")
        return None

