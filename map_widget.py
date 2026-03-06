# map_widget.py
import tkinter as tk
from tkintermapview import TkinterMapView
import math

class MapWidget(tk.Frame):
    def __init__(self, parent, get_mode, get_selected_point_id, on_insert_click, on_move_click):
        super().__init__(parent)
        self.get_mode = get_mode
        self.get_selected_point_id = get_selected_point_id
        self.on_insert_click = on_insert_click
        self.on_move_click = on_move_click

        self.markers = {}           # id → marker object
        self.selected_circle = None
        self.selected_id = None

        self.map = TkinterMapView(self, width=800, height=600, corner_radius=0)
        self.map.pack(fill="both", expand=True)
        self.map.set_position(54.5, -2.5)
        self.map.set_zoom(8)

        self.map.add_left_click_map_command(self._handle_map_click)

    def _handle_map_click(self, coords):
        lat, lon = coords
        mode = self.get_mode()
        if mode in ("insert", "insertHG", "insertPhoto"):
            self.on_insert_click(lat, lon)
        elif mode == "move":
            pid = self.get_selected_point_id()
            if pid is not None:
                self.on_move_click(pid, lat, lon)

    # ── New efficient methods ─────────────────────────────────────
    def add_marker(self, point_id, lat, lon):
        marker = self.map.set_marker(lat, lon, text=str(point_id))
        marker.point_id = point_id
        self.markers[point_id] = marker

    def move_marker(self, point_id, lat, lon):          # ← this was the slow part
        if point_id in self.markers:
            self.markers[point_id].set_position(lat, lon)   # native, instant
        else:
            self.add_marker(point_id, lat, lon)

    def select_point(self, point_id, lat, lon):
        self._update_circle(lat, lon)
        self.selected_id = point_id
        # gentle recenter only when needed
        cur = self.map.get_position()
        if abs(cur[0] - lat) > 0.02 or abs(cur[1] - lon) > 0.02:
            self.map.set_position(lat, lon, marker=False)

    def move_circle(self, point_id, lat, lon):   # alias for manager
        if self.selected_id == point_id:
            self._update_circle(lat, lon)

    def _update_circle(self, lat, lon):
        if self.selected_circle:
            self.selected_circle.delete()
        pts = self._circle_points(lat, lon, 250)
        self.selected_circle = self.map.set_polygon(pts, outline_color="blue", border_width=2)

    def delete_point(self, point_id):
        if point_id in self.markers:
            self.markers[point_id].delete()
            del self.markers[point_id]
        if self.selected_id == point_id and self.selected_circle:
            self.selected_circle.delete()
            self.selected_circle = None
            self.selected_id = None

    def _circle_points(self, lat, lon, radius_m):
        pts = []
        R = 6378137.0
        for a in range(0, 360, 10):
            rad = math.radians(a)
            dlat = (radius_m * math.cos(rad)) / R
            dlon = (radius_m * math.sin(rad)) / (R * math.cos(math.radians(lat)))
            pts.append((lat + math.degrees(dlat), lon + math.degrees(dlon)))
        return pts

    # Bonus: batch load (used by new _load_csv)
    def batch_add_markers(self, points_dict):
        for pid, p in points_dict.items():
            self.add_marker(pid, p["lat"], p["lon"])
