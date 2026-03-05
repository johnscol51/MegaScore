# readDebug.py
# View the last N lines of debug.log in a scrollable window
# Called from MegaScore.py or standalone

import os
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

def run(DataDir=None):
    # Try to get the log path from utils (set by MegaScore)
    log_path = None
    try:
        from utils import _log_path
        log_path = _log_path
    except ImportError:
        pass

    if not log_path or not isinstance(log_path, str) or not log_path.strip():
        messagebox.showwarning("No Log Path", "Debug log path not set in utils.\nCannot open log viewer.")
        return

    if not os.path.isfile(log_path):
        messagebox.showinfo("No Log File", f"Log file not found:\n{log_path}")
        return

    # GUI window
    dlg = tk.Toplevel()
    dlg.title("Debug Log Viewer")
    dlg.geometry("900x550")  # Your compact size
    dlg.minsize(600, 500)
    dlg.transient(tk._default_root if tk._default_root else None)
    dlg.grab_set()
    dlg.focus_set()

    # Top controls
    top_frame = ttk.Frame(dlg, padding=10)
    top_frame.pack(fill="x")

    ttk.Label(top_frame, text="Last lines:").pack(side="left", padx=5)
    lines_var = tk.IntVar(value=200)
    lines_spin = ttk.Spinbox(top_frame, from_=50, to=2000, increment=50, textvariable=lines_var, width=6)
    lines_spin.pack(side="left", padx=5)

    ttk.Button(top_frame, text="Refresh", command=lambda: load_logs()).pack(side="left", padx=10)

    # Frame for text + horizontal scrollbar
    text_frame = ttk.Frame(dlg)
    text_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Horizontal scrollbar (below text area, above Close button)
    x_scroll = ttk.Scrollbar(text_frame, orient="horizontal")
    x_scroll.pack(fill="x", side="bottom")

    # Text area with vertical scrollbar (ScrolledText)
    text_area = scrolledtext.ScrolledText(
        text_frame,
        wrap=tk.NONE,                # Enable horizontal scrolling for long lines
        font=("Consolas", 10),
        bg="#f8f8f8",
        xscrollcommand=x_scroll.set
    )
    text_area.pack(fill="both", expand=True)

    # Link horizontal scrollbar to text area
    x_scroll.config(command=text_area.xview)

    def load_logs():
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                n = lines_var.get()
                last_n = lines[-n:] if n > 0 and len(lines) >= n else lines
                text_area.delete("1.0", tk.END)
                text_area.insert(tk.END, "".join(last_n))
                text_area.see(tk.END)  # scroll to bottom
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read log file:\n{e}")

    # Initial load
    load_logs()

    # Blue Close button at very bottom
    style = ttk.Style()
    style.configure("Blue.TButton", background="#0066cc", foreground="white", font=("Helvetica", 10, "bold"))

    ttk.Button(dlg, text="Close", width=10, command=dlg.destroy,
               style="Blue.TButton").pack(pady=10)

    dlg.protocol("WM_DELETE_WINDOW", dlg.destroy)
