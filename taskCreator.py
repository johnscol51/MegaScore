# TaskCreator.py
# MODIFIED VERSION WITH:
# - Added def run(DataDir=None) to make it callable from main app
# - Standalone execution via if __name__ == "__main__"
# - Pre-set DataDir if provided via run()
# - Fixed method definitions to be properly inside the class
# - Now reads/writes TaskPoints CSV from DataDir/imports (creates imports if missing)
# - Task No: input moved to right side (just left of branding)

import tkinter as tk
from tkinter import ttk, messagebox
from map_widget import MapWidget
from points import PointManager, PointEditorPanel, PointListPanel
import file_io
import utils1
import os, sys

class MapPointEditorApp(tk.Toplevel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title("MegaScore — Map Point Editor")
        self.geometry("1300x800")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.app_dir = utils1.appDir()
        self.data_dir = None

        # ------------------- Top bar -------------------
        top = tk.Frame(self)
        top.pack(fill="x", padx=10, pady=5)
        top.grid_columnconfigure(3, weight=1)  # Expand space between DataDir and controls

        # Left side: Select DataDir button + label
        tk.Button(top, text="Select DataDir", command=self._choose_data_dir).grid(row=0, column=0, padx=10, sticky="w")
        self.data_dir_label = tk.Label(top, text="No DataDir selected", fg="gray")
        self.data_dir_label.grid(row=0, column=1, sticky="w", padx=5)

        # Right side: Task No + Load source selector
        right_controls = tk.Frame(top)
        right_controls.grid(row=0, column=4, sticky="e", padx=(20, 5))

        tk.Label(right_controls, text="Task No:").pack(side="left")
        self.task_no_var = tk.StringVar()
        tk.Entry(right_controls, textvariable=self.task_no_var, width=8).pack(side="left", padx=(2, 10))

        # NEW: Load source selector
        self.load_source_var = tk.StringVar(value="imports")
        tk.Label(right_controls, text="Load from:").pack(side="left", padx=(10, 5))
        tk.Radiobutton(right_controls, text="Imports (new)", variable=self.load_source_var,
                       value="imports").pack(side="left")
        tk.Radiobutton(right_controls, text="Master file", variable=self.load_source_var,
                       value="master").pack(side="left")

        # Branding (far right)
        brand = tk.Frame(top)
        brand.grid(row=0, column=5, sticky="e", padx=10)
        tk.Label(brand, text=" ", bg="blue", width=4, height=2).pack(side="left", padx=3)
        tk.Label(brand, text=" ", bg="yellow", width=4, height=2).pack(side="left", padx=3)

        # ------------------- Main area -------------------
        main = tk.Frame(self)
        main.pack(fill="both", expand=True)
        map_frame = tk.Frame(main)
        map_frame.pack(side="left", fill="both", expand=True)
        right = tk.Frame(main)
        right.pack(side="right", fill="y", padx=10, pady=5)

        # Mode
        self.mode_var = tk.StringVar(value="insert")
        mode_frame = tk.LabelFrame(right, text="Mode")
        mode_frame.pack(fill="x", pady=5)
        for text, val in [("Insert", "insert"), ("Move", "move")]:
            tk.Radiobutton(mode_frame, text=text, value=val, variable=self.mode_var).pack(anchor="w")

        # Map
        self.map_widget = MapWidget(
            map_frame,
            get_mode=lambda: self.mode_var.get(),
            get_selected_point_id=lambda: self.list_panel.get_selected_point_id(),
            on_insert_click=self._insert_point,
            on_move_click=self._move_point_from_map
        )
        self.map_widget.pack(fill="both", expand=True)

        # Manager + panels
        self.manager = PointManager(
            map_add=self.map_widget.add_marker,
            map_move=self.map_widget.move_marker,
            map_delete=self.map_widget.delete_point,
            map_highlight=self.map_widget.select_point,
            map_draw_circle=self.map_widget.select_point,
            map_remove_circle=self.map_widget.delete_point
        )
        self.editor_panel = PointEditorPanel(right, self.manager)
        self.editor_panel.pack(fill="x", pady=5)
        self.list_panel = PointListPanel(right, self.manager)
        self.list_panel.pack(fill="both", expand=True, pady=5)
        self.manager.attach_editor_panel(self.editor_panel)
        self.manager.attach_list_panel(self.list_panel)

        tk.Button(right, text="Delete selected", command=self._delete_selected).pack(fill="x", pady=5)

        # Bottom bar
        bottom = tk.Frame(self)
        bottom.pack(fill="x", pady=5)
        tk.Button(bottom, text="Load", width=12, command=self._load_csv).pack(side="left", padx=10)
        tk.Button(bottom, text="Save CSV", width=12, command=self._save_csv).pack(side="left", padx=10)
        tk.Button(bottom, text="Readme", width=12, command=self._open_readme).pack(side="left", padx=10)
        tk.Button(bottom, text="Close", width=12, command=self._on_close).pack(side="left")

        self.status_var = tk.StringVar(value="Ready")
        tk.Label(bottom, textvariable=self.status_var, anchor="w", bg="#e6e6e6").pack(side="right", fill="x", expand=True)

    def _insert_point(self, lat, lon):
        self.manager.create_point(lat, lon)
        self._set_status("Point added")

    def _move_point_from_map(self, point_id, lat, lon):
        self.manager.move_point_to(point_id, lat, lon)
        self._set_status("Point moved")

    def _delete_selected(self):
        pid = self.list_panel.get_selected_point_id()
        if pid is not None:
            self.manager.delete_point(pid)
            self._set_status("Point deleted")

    def _set_status(self, msg):
        self.status_var.set(msg)

    def _choose_data_dir(self):
        path = file_io.choose_data_dir(self.app_dir)
        if path:
            self.data_dir = path
            self.data_dir_label.config(text=path, fg="black")
            self._set_status("DataDir selected")

    # Load / Save — now use imports subfolder
    def _load_csv(self):
        if not self.data_dir or not self.task_no_var.get().strip().isdigit():
            messagebox.showerror("Error", "Select DataDir and enter numeric Task No.")
            return

        task_no = self.task_no_var.get().strip()
        source = self.load_source_var.get()

        if source == "imports":
            # Load from imports subfolder (existing behavior)
            imports_dir = os.path.join(self.data_dir, "imports")
            os.makedirs(imports_dir, exist_ok=True)
            rows = file_io.load_taskpoints(imports_dir, task_no)
            source_desc = "imports"
        else:
            # Load from master TaskPoints.csv using new file_io method
            master_path = os.path.join(self.data_dir, "TaskPoints.csv")
            rows = file_io.load_taskpoints_from_master(master_path, task_no)
            source_desc = "master file"

        if not rows:
            messagebox.showinfo("Not found", f"No points for task {task_no} in {source_desc}.")
            return

        self.manager.clear_all()
        for i, row in enumerate(rows, 1):
            self.manager.add_loaded_point(i, row["name"], row["lat"], row["lon"], row["dist"], row["pt"])
        self.list_panel.refresh()
        self.editor_panel.clear()
        self._set_status(f"Loaded {len(rows)} points from {source_desc}")

    def _save_csv(self):
        if not self.data_dir or not self.task_no_var.get().strip().isdigit():
            messagebox.showerror("Error", "Select DataDir and enter Task No.")
            return

        # Use imports subfolder
        imports_dir = os.path.join(self.data_dir, "imports")
        os.makedirs(imports_dir, exist_ok=True)  # Create if missing

        task_no = self.task_no_var.get().strip()
        rows = self.manager.export_rows()

        # Use the original save function, but pass the imports directory
        if file_io.save_taskpoints(imports_dir, task_no, rows):
            self._set_status("CSV saved")
            messagebox.showinfo("Saved", f"TaskPoints{task_no}.csv saved in imports.")
    # ------------------------------------------------------
    # readme window
    # ------------------------------------------------------
    def _open_readme(self):
        """Open a simple readme window with instructions."""
        win = tk.Toplevel(self)
        win.title("MegaScore — Quick Help")
        win.geometry("600x700")
        win.transient(self)
        win.grab_set()

        text_frame = tk.Frame(win)
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        text = tk.Text(text_frame, wrap="word", font=("Arial", 11))
        text.pack(side="left", fill="both", expand=True)
        scrollbar = tk.Scrollbar(text_frame, command=text.yview)
        scrollbar.pack(side="right", fill="y")
        text.config(yscrollcommand=scrollbar.set)

        readme_content = """
MegaScore Map - goblin Point Editor - Quick Help
Overview
This tool lets you create, edit and manage task points on an OpenStreetMap background.
Points are saved as TaskPoints<taskno>.csv files in DataDir/imports for later importing.
Basic usage:
• Insert mode: click on map to add a point (SP first, then TP1, TP2...)
• Move mode: select point from the list on the right, then click new location on map
• Edit: Point Editor → change name/lat/lon/dist/PT in editor → Apply
• Delete: select a point → Delete selected button
Loading / Saving:
• Set Task No in top bar
• Load: Imports(new) reads existing TaskPoints<taskno>.csv from imports if present
•       Master file  reads  from the main master  TaskPoints.csv in you dataDir if present. 
• Save CSV: writes current points to TaskPoints<taskno>.csv in imports
•           there is currently no save function back to the master file, you need go via a new import 
• Once you have saved your CSV in dataDir/imports you need to use importFromCSV to load to the main app
Point types (by name):
• SP / TP* / FP → standard turnpoints (blue 500m circle)
• *HG* → hidden gates 
• *photo* → photo points 
• you need to ensure that you have TP2 before you create TP3. it only matters when you save the file 

Dist and PT:
• Dist  is the track distance to the point from SP (optional) 
• PT  is the time allowance in integer minutes for a preicion turn (optional) 
• Close this window with the X or the Close button below

the goblin lives in the hope that you find this useful.
        """
        text.insert("1.0", readme_content)
        text.config(state="disabled")
        tk.Button(win, text="Close", command=win.destroy, width=10).pack(pady=10)

    def _on_close(self):
        """Close only this editor window — do not touch the main app."""
        try:
            self.destroy()
        except Exception:
            pass

def run(DataDir=None, parent=None):
    """
    Launch Map Point Editor.
    Tries to reuse existing Tk root if one exists (safer when called from MegaScore.py).
    """
    if parent is not None:
        root = parent
    elif tk._default_root is not None:
        root = tk._default_root
        print("taskCreator: Reusing existing Tk root (from caller)")
    else:
        root = tk.Tk()
        root.withdraw()
        print("taskCreator: Created new hidden Tk root (standalone)")

    app = MapPointEditorApp(parent=root)
    if DataDir and os.path.isdir(DataDir):
        app.data_dir = DataDir
        app.data_dir_label.config(text=DataDir, fg="black")
        app._set_status("DataDir pre-selected")

    if parent is None and tk._default_root is None:
        app.mainloop()

if __name__ == "__main__":
    run()
