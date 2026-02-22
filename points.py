# points.py
#
# FINAL VERSION WITH:
# - SP for first point, TP1, TP2... thereafter
# - Names preserved on move
# - Editable Name, Lat, Lon, Dist, PT in editor
# - Dist as float (2 dp), PT as string (default "0")
# - Move-mode click moves point + updates list
# - CSV export includes id, name, lat, lon, dist, PT

import tkinter as tk
from tkinter import ttk, messagebox


class PointManager:
    def __init__(self, map_add, map_move, map_delete, map_highlight, map_draw_circle, map_remove_circle):
        self.points = {}
        self.next_id = 1
        self.tp_counter = 1

        self.map_add = map_add
        self.map_move = map_move
        self.map_delete = map_delete
        self.map_highlight = map_highlight
        self.map_draw_circle = map_draw_circle
        self.map_remove_circle = map_remove_circle

        self.editor_panel = None
        self.list_panel = None

    def attach_editor_panel(self, panel):
        self.editor_panel = panel

    def attach_list_panel(self, panel):
        self.list_panel = panel

    def clear_all(self):
        for pid in list(self.points.keys()):
            self.map_delete(pid)
        self.points.clear()
        self.next_id = 1
        self.tp_counter = 1

    def add_loaded_point(self, point_id, name, lat, lon, dist, PT):
        try:
            pt_val = int(float(PT.strip())) if PT else 0   # float() handles old "0.0" etc.
        except (ValueError, TypeError):
            pt_val = 0
        pt_val = max(0, min(10, pt_val))                  # clamp
        self.points[point_id] = {"name": name, "lat": lat, "lon": lon, "dist": dist, "PT": pt_val}
        self.map_add(point_id, lat, lon)
        if point_id >= self.next_id:
            self.next_id = point_id + 1
        if name.startswith("TP") and name[2:].isdigit():
            tp_num = int(name[2:])
            if tp_num >= self.tp_counter:
                self.tp_counter = tp_num + 1

    def create_point(self, lat, lon):
        name = self._get_next_name()
        self.points[self.next_id] = {"name": name, "lat": lat, "lon": lon, "dist": 0.0, "PT": 0}
        self.map_add(self.next_id, lat, lon)
        self.list_panel.refresh()
        self.next_id += 1
        if name.startswith("TP"):
            self.tp_counter += 1

    def _get_next_name(self):
        if not self.points:
            return "SP"
        elif self.tp_counter == 1:
            return "TP1"
        else:
            return f"TP{self.tp_counter}"

    def move_point_to(self, point_id, lat, lon):
        if point_id in self.points:
            self.points[point_id]["lat"] = lat
            self.points[point_id]["lon"] = lon
            self.map_move(point_id, lat, lon)
            if self.editor_panel and self.editor_panel.current_point_id == point_id:
                self.map_highlight(point_id, lat, lon)
                self.editor_panel.load_point(
                    point_id,
                    self.points[point_id]["name"],
                    lat,
                    lon,
                    self.points[point_id]["dist"],
                    self.points[point_id]["PT"]
                )
            self.list_panel.refresh()

    def delete_point(self, point_id):
        if point_id in self.points:
            del self.points[point_id]
            self.map_delete(point_id)
            self.list_panel.refresh()
            if self.editor_panel:
                self.editor_panel.clear()

    def edit_point(self, point_id, name, lat, lon, dist, PT):
        if point_id not in self.points:
            return

        # check for duplicate name ───────────────────────────────
        proposed_name = name.strip()
        proposed_upper = proposed_name.upper()
        for pid, p in self.points.items():
            if pid != point_id and p["name"].strip().upper() == proposed_upper:
                if self.editor_panel:
                    from tkinter import messagebox
                    messagebox.showwarning(
                        "Duplicate Name",
                        f"The name '{proposed_name}' is already used by another point.\n"
                        "Please choose a different name."
                    )
                return   # ← stop here — do not update anything

        old_name = self.points[point_id]["name"]
        self.points[point_id] = {"name": proposed_name, "lat": lat, "lon": lon, "dist": dist, "PT": PT}
        self.map_move(point_id, lat, lon)  # Efficient move

        if self.editor_panel and self.editor_panel.current_point_id == point_id:
            self.map_highlight(point_id, lat, lon)

        self.list_panel.refresh()

        # Adjust tp_counter if needed (e.g., if renaming TPx to higher number)
        if old_name.startswith("TP") and proposed_name.startswith("TP"):
            old_num = int(old_name[2:])
            new_num = int(proposed_name[2:])
            if new_num > old_num and new_num >= self.tp_counter:
                self.tp_counter = new_num + 1

    def select_point(self, point_id):
        if point_id in self.points:
            p = self.points[point_id]
            self.map_highlight(point_id, p["lat"], p["lon"])
            if self.editor_panel:
                self.editor_panel.load_point(
                    point_id,
                    p["name"],
                    p["lat"],
                    p["lon"],
                    p["dist"],
                    p["PT"]
                )

    def export_rows(self):
        return sorted(
            [{"name": p["name"], "lat": p["lat"], "lon": p["lon"], "dist": p["dist"], "pt": p["PT"]}
             for p in self.points.values()],
            key=lambda r: (r["name"] != "SP", int(r["name"][2:]) if r["name"].startswith("TP") else 0)
        )  # Simple sort: SP first, then TP1+


# ============================================================
# POINT EDITOR PANEL
# ============================================================

class PointEditorPanel(tk.LabelFrame):
    def __init__(self, parent, manager):
        super().__init__(parent, text="Point Editor")
        self.manager = manager
        self.current_point_id = None   # ← FIXED: use consistent name

        # Labels
        tk.Label(self, text="Name:").grid(row=0, column=0, sticky="w", padx=(6,2), pady=(6,2))
        tk.Label(self, text="Latitude:").grid(row=1, column=0, sticky="w", padx=(6,2), pady=2)
        tk.Label(self, text="Longitude:").grid(row=2, column=0, sticky="w", padx=(6,2), pady=2)
        tk.Label(self, text="Dist:").grid(row=3, column=0, sticky="w", padx=(6,2), pady=2)
        tk.Label(self, text="PT (0–10):").grid(row=4, column=0, sticky="w", padx=(6,2), pady=2)

        # Entry fields
        self.name_var = tk.StringVar()
        self.lat_var  = tk.StringVar()
        self.lon_var  = tk.StringVar()
        self.dist_var = tk.StringVar()
        self.pt_var   = tk.StringVar()

        tk.Entry(self, textvariable=self.name_var, width=15).grid(row=0, column=1, padx=5, pady=(6,2))
        tk.Entry(self, textvariable=self.lat_var,  width=15).grid(row=1, column=1, padx=5, pady=2)
        tk.Entry(self, textvariable=self.lon_var,  width=15).grid(row=2, column=1, padx=5, pady=2)
        tk.Entry(self, textvariable=self.dist_var, width=15).grid(row=3, column=1, padx=5, pady=2)
        tk.Entry(self, textvariable=self.pt_var,   width=15).grid(row=4, column=1, padx=5, pady=2)

        # Apply button
        self.apply_btn = tk.Button(self, text="Apply", command=self._apply, state="disabled")
        self.apply_btn.grid(row=0, column=2, rowspan=5, sticky="ne", padx=8, pady=6)

        # Optional: enable Apply when any field changes
        for var in [self.name_var, self.lat_var, self.lon_var, self.dist_var, self.pt_var]:
            var.trace("w", lambda *args: self._on_field_change())

        self.grid_columnconfigure(1, weight=1)

    def _on_field_change(self):
        if self.current_point_id is not None:
            self.apply_btn.config(state="normal")

    def load_point(self, point_id, name, lat, lon, dist, PT):
        self.current_point_id = point_id          # ← FIXED
        self.name_var.set(name)
        self.lat_var.set(f"{lat:.7f}")
        self.lon_var.set(f"{lon:.7f}")
        self.dist_var.set(f"{dist:.2f}")
        self.pt_var.set(str(int(PT)))       
        self.apply_btn.config(state="disabled")   # reset until user edits

    def clear(self):
        self.current_point_id = None
        self.name_var.set("")
        self.lat_var.set("")
        self.lon_var.set("")
        self.dist_var.set("")
        self.pt_var.set("")
        self.apply_btn.config(state="disabled")

    def _apply(self):
        if self.current_point_id is None:
            return
        try:
            name = self.name_var.get().strip()
            lat = float(self.lat_var.get())
            lon = float(self.lon_var.get())
            dist = float(self.dist_var.get())

            pt_str = self.pt_var.get().strip()
            try:
                PT = int(pt_str)
                PT = max(0, min(10, PT))               # enforce range
            except ValueError:
                PT = 0
                messagebox.showwarning("Invalid PT", "PT must be an integer 0–10.\nUsing 0.")

            if not name:
                messagebox.showwarning("Invalid", "Name cannot be empty")
                return

            self.manager.edit_point(
                self.current_point_id,
                name,
                lat,
                lon,
                dist,
                PT
            )
            self.apply_btn.config(state="disabled")
        except ValueError as e:
            messagebox.showerror("Invalid input", f"Invalid number format:\n{str(e)}")


# ============================================================
# POINT LIST PANEL
# ============================================================

class PointListPanel(tk.LabelFrame):
    def __init__(self, parent, manager):
        super().__init__(parent, text="Points")
        self.manager = manager

        self.tree = ttk.Treeview(
            self,
            columns=("id", "name", "lat", "lon", "dist", "PT"),
            show="headings",
            height=12
        )
        self.tree.heading("id",   text="ID")
        self.tree.heading("name", text="Name")
        self.tree.heading("lat",  text="Latitude")
        self.tree.heading("lon",  text="Longitude")
        self.tree.heading("dist", text="Dist")
        self.tree.heading("PT",   text="PT")

        self.tree.column("id",   width=40,  anchor="center")
        self.tree.column("name", width=80,  anchor="w")
        self.tree.column("lat",  width=100, anchor="e")
        self.tree.column("lon",  width=100, anchor="e")
        self.tree.column("dist", width=60,  anchor="e")
        self.tree.column("PT",   width=40,  anchor="center")

        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        self._suppress_select = False

    def refresh(self):
        selected_id = self.get_selected_point_id()

        self.tree.delete(*self.tree.get_children())

        for point_id, p in sorted(self.manager.points.items(), key=lambda x: x[0]):
            self.tree.insert(
                "",
                "end",
                iid=str(point_id),
                values=(
                    point_id,
                    p["name"],
                    f"{p['lat']:.7f}",
                    f"{p['lon']:.7f}",
                    f"{p['dist']:.2f}",
                    str(p["PT"]),
                )
            )

        if selected_id is not None:
            iid = str(selected_id)
            if iid in self.tree.get_children():
                self._suppress_select = True
                self.tree.selection_set(iid)
                self.tree.see(iid)
                self.tree.after_idle(lambda: setattr(self, "_suppress_select", False))

    def get_selected_point_id(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _on_select(self, event):
        if self._suppress_select:
            return
        point_id = self.get_selected_point_id()
        if point_id is not None:
            self.manager.select_point(point_id)
