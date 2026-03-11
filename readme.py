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
    root.title("MegaScore Goblin – Help / README")
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
            "MegaScore Goblin – Help / README\n"
            "===================================\n\n"
            "Thank you for bothering to look at the readme text,  just looking here puts you in the group of people likely to succeed.\n\n"
            "This software is intended to help an experienced comp director score comp tasks quickly and without too much manual work. its not an end to end 'how to create and run a comp tool'\n"

            "The app is deliberately simple and flat file bases to allow it to be ported to any operating system, and to allow manual intervention by editing files if something goes wrong.\n\n"
            "To get started you need a directory to put all the data files in. this can be anywhere on your machine, but you do need it. "
            "It will end up with your task info, score and results. the structure will be created as we go, but the base directory must exist. best create it now.\n\n"
            "Use the DataDir option on this menu to select your new directory. you will need to do this each time you start the software.\n\n"
            "You can have more that one dataDir, maybe one for every competition you are running or experimenting with. \n\n"
            "Once you have set the DataDir, next thing is populateComp. here you need to set the basic parameters for the comp, "
            "the key bits are setting the directory where you are going to place the igc files. this can be the directory where the RFdownloader has placed them.\n\n"
            "A pilot file is also needed to associate the pilotName with a comp/logger number,  again this can be the same file as used for RFdownloader, but careful to check the names in that file are sensible as these names will appear in the results\n "
            "The pilot file is only used for tasks that are manually entered "
            "like spot landings or gaggle tasks.  its not used for Nav, turnpoint hunts or circles, but it needs to be in line with the igc file names so you dont mess up the results. \n"
            "you can pop back and change things if you need to later on.\n\n"
            "Moving on you need to load some task data. this can be done by importing a task created in Pesto, from a google earth KML file or native from a csv file. "
            "the file format is pretty simple:\n\n"
            "    <taskNO> <Point> <lat> <long> <dist> <PT>\n"
            "    PT is optional.\n\n"
            "this is the same format used throughout the app including the task master file TaskPoints.csv. \n\n"
            "Newly added is our own taskCreator GUI, this will allow you to create tasks on a map (openStreetmap).i its still a bit basic, but work is ongoing at goblin control. \n\n" 
            "Once you are happy with your tasks, it's on to scoring. the concept here is to evaluate the igc files against the task in question, "
            "and produce a score for a single pilot. You get a pdf file you can give them, should you wish.\n\n"
            "once you are done with the scoring for all your pilots, use the results tab to create a results pdf file for that task, "
            "so you can stick it on the wall.\n\n"
            "Its worth noting that the Circle,spotLanding and Gaggle tools create the results directly,  as they score all the pilots at once\n\n"
            "Hopefully this will get you going, if not you will need to look at the written docs or see the video.\n\n"
            "the Goblin will support you..\n"
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

