#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox
import os

# =========================================================
#  README / HELP WINDOW
# =========================================================
def run(DataDir):
    """
    Opens a scrollable help window. Loads text from README.txt
    located in the DataDir. If missing, displays a default message.
    """

    # -----------------------------------------------------
    # Create window
    # -----------------------------------------------------
    root = tk.Toplevel()
    root.geometry("900x650")
    root.title("MegaScore – Help / README")
    root.lift()
    root.focus_force()
    root.grab_set()

    # -----------------------------------------------------
    # Layout
    # -----------------------------------------------------
    frame = tk.Frame(root)
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    text_widget = tk.Text(frame, wrap="word", font=("Consolas", 10))
    text_widget.pack(side="left", fill="both", expand=True)

    scroll = tk.Scrollbar(frame, command=text_widget.yview)
    scroll.pack(side="right", fill="y")
    text_widget.configure(yscrollcommand=scroll.set)

    # -----------------------------------------------------
    # Load README text
    # -----------------------------------------------------
    readme_path = os.path.join(DataDir, "README.txt")

    if os.path.exists(readme_path):
        try:
            with open(readme_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            content = f"Error reading README.txt:\n{e}"
    else:
        # Fallback default text (your supplied content)
        content = (
            "MegaScore – Help / README\n"
            "===================================\n\n"
            "thank you for bothering to look at the readme text, just looking puts you in the group of people likely to succeed\n\n"
            "to get started you need a directory to put all the data files in. this can be anywhere, but you do need it. "
            "it will end up with your task info, score and results. the structure will be created as we go, but the base directory must exist. create it now.\n\n"
            "use the DataDir option on this menu to select it. you will need to do this each time you start the software.\n\n"
            "once you have set the DataDir, next thing is populateComp. here you need to set the parameters for the comp. "
            "the key bits are setting the directory where you are going to place the igc files. this can be the directory where the RFdownloader has placed them.\n\n"
            "you also need the pilot file, again this can be the same file as used for RFdownloader, but careful to check the names in that file are sensible, "
            "you don't want things like 'daft bob' or 'silly billy' appearing in the results.\n\n"
            "you can pop back and change things if you need to.\n\n"
            "Moving on you need to load some task data. this can be done by importing a task from Pesto, from a google earth KML file or from a csv file. "
            "the format is pretty simple:\n\n"
            "    <taskNO> <Point> <lat> <long> <dist> <PT>\n"
            "PT is optional.\n\n"
            "once you are happy with your tasks, it's on to scoring. the concept here is to evaluate the igc files against the task in question, "
            "and produce a score for a single pilot. you get a pdf file you can give them, should you wish.\n\n"
            "once you are done with the scoring for all your pilots, use the results tab to create a results pdf file for that task, "
            "so you can stick it on the wall.\n\n"
            "hopefully this will get you going, if not you will need to look at the written docs or see the video.\n\n"
            "share and enjoy\n"
        )

    # -----------------------------------------------------
    # Insert text
    # -----------------------------------------------------
    text_widget.insert("end", content)
    text_widget.config(state="disabled")

    # -----------------------------------------------------
    # Close button
    # -----------------------------------------------------
    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=5)

    tk.Button(
        btn_frame,
        text="Close",
        width=12,
        command=lambda: (root.grab_release(), root.destroy())
    ).pack()

    root.wait_window()

