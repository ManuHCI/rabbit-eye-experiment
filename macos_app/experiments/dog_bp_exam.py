import hashlib
import json
import os
import random
import sqlite3
import sys
import tkinter as tk
from datetime import datetime
from tkinter import font as tkfont
from tkinter import messagebox, simpledialog, ttk

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from experiments.dog_bp import DogBPSimulation
from ui.display import set_window_size


QUESTION_COUNT = 10
EXAMINER_PASSWORD_HASH = "cfadba7271287e0b7e93524c06f6db748e79bad06754ca3b5cef14029e757568"
if getattr(sys, "frozen", False):
    DATA_DIR = os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
        "MAMC_CAL",
        "exam_data",
    )
else:
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exam_data")
DATABASE_PATH = os.path.join(DATA_DIR, "dog_bp_results.sqlite3")

DRUGS = ["Epinephrine", "Norepinephrine", "Isoprenaline", "Acetylcholine",
         "Ephedrine", "Saline"]
BLOCKERS = ["Phenoxybenzamine", "Propranolol", "Atropine", "Hexamethonium"]
PRACTICAL_DRUGS = [
    "Epinephrine", "Norepinephrine", "Isoprenaline", "Acetylcholine",
    "Ephedrine", "Phenoxybenzamine", "Propranolol", "Atropine", "Saline",
]
KNOWN_AGONISTS = [
    "Epinephrine", "Norepinephrine", "Isoprenaline", "Acetylcholine",
    "Ephedrine", "Saline",
]
KNOWN_BLOCKERS = ["Phenoxybenzamine", "Propranolol", "Atropine"]
PHENOMENA = ["Vasomotor reversal of Dale", "Tachyphylaxis",
             "Nicotinic effect of acetylcholine", "Potentiation"]


def _question(prompt, answer, options, drug, dose=1.0, pretreatment=None,
              sequence=None, explanation=""):
    return {
        "prompt": prompt, "answer": answer, "options": options,
        "drug": drug, "dose": dose, "pretreatment": pretreatment,
        "sequence": sequence, "explanation": explanation,
    }


MBBS_QUESTION_BANK = [
    _question("No blocker was given. Identify the injected drug from the tracing.",
              "Epinephrine", ["Epinephrine", "Norepinephrine", "Isoprenaline", "Acetylcholine"],
              "Epinephrine", 1.2, explanation="High-dose epinephrine raises BP with reflex bradycardia."),
    _question("No blocker was given. Identify the injected drug from the tracing.",
              "Norepinephrine", ["Epinephrine", "Norepinephrine", "Isoprenaline", "Acetylcholine"],
              "Norepinephrine", explanation="Norepinephrine raises BP and causes reflex bradycardia."),
    _question("No blocker was given. Identify the injected drug from the tracing.",
              "Isoprenaline", ["Epinephrine", "Norepinephrine", "Isoprenaline", "Acetylcholine"],
              "Isoprenaline", explanation="Beta-2 vasodilation lowers BP while beta-1 stimulation raises HR."),
    _question("No blocker was given. Identify the injected drug from the tracing.",
              "Acetylcholine", ["Epinephrine", "Norepinephrine", "Isoprenaline", "Acetylcholine"],
              "Acetylcholine", explanation="Muscarinic stimulation lowers BP and HR."),
    _question("The animal was pretreated with Phenoxybenzamine. Identify the unknown agonist.",
              "Epinephrine", ["Epinephrine", "Norepinephrine", "Isoprenaline", "Acetylcholine"],
              "Epinephrine", pretreatment="Phenoxybenzamine",
              explanation="Epinephrine produces a depressor response after alpha blockade."),
    _question("The animal was pretreated with Propranolol. Identify the unknown agonist.",
              "Isoprenaline", ["Epinephrine", "Norepinephrine", "Isoprenaline", "Acetylcholine"],
              "Isoprenaline", pretreatment="Propranolol",
              explanation="Isoprenaline is blocked by propranolol."),
    _question("A hidden blocker was given first, followed by known Epinephrine. Identify the blocker.",
              "Phenoxybenzamine", BLOCKERS, "Epinephrine", pretreatment="Phenoxybenzamine",
              explanation="Alpha blockade converts epinephrine's pressor response into a depressor response."),
    _question("A hidden blocker was given first, followed by known Isoprenaline. Identify the blocker.",
              "Propranolol", BLOCKERS, "Isoprenaline", pretreatment="Propranolol",
              explanation="Propranolol blocks both beta-1 and beta-2 effects of isoprenaline."),
    _question("A hidden blocker was given first, followed by known low-dose Acetylcholine. Identify the blocker.",
              "Atropine", BLOCKERS, "Acetylcholine", pretreatment="Atropine",
              explanation="Atropine blocks the muscarinic depressor response to acetylcholine."),
    _question("Phenoxybenzamine was followed by Epinephrine. Identify the demonstrated phenomenon.",
              "Vasomotor reversal of Dale", PHENOMENA, "Epinephrine", pretreatment="Phenoxybenzamine",
              explanation="Alpha blockade leaves epinephrine's beta-2 vasodilation unopposed."),
    _question("Repeated equal doses of an indirect sympathomimetic were given. Identify the phenomenon.",
              "Tachyphylaxis", PHENOMENA, "Ephedrine", sequence="repeat_ephedrine",
              explanation="Repeated ephedrine loses effect as stored noradrenaline is depleted."),
    _question("After Atropine, a high dose of Acetylcholine was given. Identify the demonstrated effect.",
              "Nicotinic effect of acetylcholine", PHENOMENA, "Acetylcholine", 2.0,
              pretreatment="Atropine",
              explanation="After muscarinic blockade, high-dose ACh stimulates ganglia and adrenal medulla."),
    _question("The animal was pretreated with Atropine. Identify the unknown high-dose agonist.",
              "Acetylcholine", DRUGS[:4], "Acetylcholine", 2.0, pretreatment="Atropine",
              explanation="The remaining pressor response is the nicotinic action of high-dose ACh."),
]


PG_QUESTION_BANK = [
    _question("A hidden blocker was followed by known Epinephrine. Identify the blocker from the reversal.",
              "Phenoxybenzamine", BLOCKERS, "Epinephrine", pretreatment="Phenoxybenzamine",
              explanation="Irreversible alpha blockade unmasks beta-2-mediated vasodilation."),
    _question("A hidden blocker was followed by known Norepinephrine. BP rises but reflex bradycardia is absent. Identify the blocker.",
              "Atropine", BLOCKERS, "Norepinephrine", pretreatment="Atropine",
              explanation="Atropine blocks the vagal component of the baroreceptor reflex."),
    _question("A hidden blocker was followed by known Isoprenaline and produces no response. Identify the blocker.",
              "Propranolol", BLOCKERS, "Isoprenaline", pretreatment="Propranolol",
              explanation="Non-selective beta blockade abolishes isoprenaline responses."),
    _question("After Phenoxybenzamine, identify the unknown agonist producing this response.",
              "Epinephrine", ["Epinephrine", "Norepinephrine", "Isoprenaline", "Acetylcholine"],
              "Epinephrine", pretreatment="Phenoxybenzamine",
              explanation="A depressor response after alpha blockade is characteristic of epinephrine reversal."),
    _question("After Propranolol, identify the unknown agonist producing an unopposed pressor response.",
              "Epinephrine", ["Epinephrine", "Norepinephrine", "Isoprenaline", "Acetylcholine"],
              "Epinephrine", pretreatment="Propranolol",
              explanation="Beta blockade leaves epinephrine's alpha-1 vasoconstriction unopposed."),
    _question("After Atropine, identify the unknown agonist that raises BP without reflex bradycardia.",
              "Norepinephrine", ["Epinephrine", "Norepinephrine", "Isoprenaline", "Acetylcholine"],
              "Norepinephrine", pretreatment="Atropine",
              explanation="Norepinephrine raises BP while atropine prevents vagal bradycardia."),
    _question("Which mechanism best explains this Epinephrine response after Phenoxybenzamine?",
              "Unopposed beta-2-mediated vasodilation",
              ["Unopposed beta-2-mediated vasodilation", "Unopposed alpha-1 vasoconstriction",
               "Muscarinic M2 activation", "Ganglionic blockade"],
              "Epinephrine", pretreatment="Phenoxybenzamine",
              explanation="Alpha receptors are blocked, leaving beta-2 vasodilation unopposed."),
    _question("Repeated Ephedrine produces progressively smaller responses. What is the mechanism?",
              "Depletion of stored noradrenaline",
              ["Depletion of stored noradrenaline", "Irreversible alpha blockade",
               "Inhibition of acetylcholinesterase", "Muscarinic receptor sensitization"],
              "Ephedrine", sequence="repeat_ephedrine",
              explanation="Repeated doses deplete releasable noradrenaline."),
    _question("After Atropine, high-dose Acetylcholine causes a pressor response. What is the mechanism?",
              "Nicotinic stimulation of ganglia and adrenal medulla",
              ["Nicotinic stimulation of ganglia and adrenal medulla", "Muscarinic M3 vasodilation",
               "Direct beta-2 stimulation", "Alpha-1 receptor blockade"],
              "Acetylcholine", 2.0, pretreatment="Atropine",
              explanation="Muscarinic effects are blocked, revealing nicotinic stimulation."),
    _question("Identify the pharmacological phenomenon shown by repeated equal doses.",
              "Tachyphylaxis", PHENOMENA, "Ephedrine", sequence="repeat_ephedrine",
              explanation="This is rapid tolerance to an indirectly acting drug."),
    _question("Identify the phenomenon shown after alpha blockade followed by Epinephrine.",
              "Vasomotor reversal of Dale", PHENOMENA, "Epinephrine", pretreatment="Phenoxybenzamine",
              explanation="Dale's vasomotor reversal follows alpha blockade and epinephrine."),
    _question("A low dose of Acetylcholine gives no response after a hidden blocker. Identify the blocker.",
              "Atropine", BLOCKERS, "Acetylcholine", pretreatment="Atropine",
              explanation="Muscarinic blockade prevents the usual depressor response."),
    _question("After Atropine, identify the high-dose unknown agonist responsible for this pressor tracing.",
              "Acetylcholine", ["Epinephrine", "Norepinephrine", "Isoprenaline", "Acetylcholine"],
              "Acetylcholine", 2.0, pretreatment="Atropine",
              explanation="High-dose ACh reveals a nicotinic pressor effect after muscarinic blockade."),
]


def ensure_database():
    os.makedirs(DATA_DIR, exist_ok=True)
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submitted_at TEXT NOT NULL,
                student_name TEXT NOT NULL,
                roll_number TEXT NOT NULL,
                level TEXT NOT NULL,
                score INTEGER NOT NULL,
                total INTEGER NOT NULL,
                duration_seconds INTEGER NOT NULL,
                answer_details TEXT NOT NULL
            )"""
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS practical_configuration (
                level TEXT PRIMARY KEY,
                unknown_1 TEXT NOT NULL,
                unknown_2 TEXT NOT NULL,
                configured_at TEXT NOT NULL
            )"""
        )


def load_practical_configuration(level):
    ensure_database()
    with sqlite3.connect(DATABASE_PATH) as connection:
        row = connection.execute(
            "SELECT unknown_1, unknown_2 FROM practical_configuration WHERE level = ?",
            (level.upper(),),
        ).fetchone()
    return tuple(row) if row else None


def save_practical_configuration(level, unknown_1, unknown_2):
    if unknown_1 not in PRACTICAL_DRUGS or unknown_2 not in PRACTICAL_DRUGS:
        raise ValueError("Select both unknowns from the supported drug list.")
    if unknown_1 == unknown_2:
        raise ValueError("Unknown 1 and Unknown 2 must be different drugs.")
    ensure_database()
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """INSERT INTO practical_configuration
               (level, unknown_1, unknown_2, configured_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(level) DO UPDATE SET
                   unknown_1 = excluded.unknown_1,
                   unknown_2 = excluded.unknown_2,
                   configured_at = excluded.configured_at""",
            (level.upper(), unknown_1, unknown_2,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )


def examiner_password_is_valid(parent):
    password = simpledialog.askstring(
        "Examiner login", "Enter examiner password:", show="*", parent=parent
    )
    if password is None:
        return False
    valid = hashlib.sha256(password.encode("utf-8")).hexdigest() == EXAMINER_PASSWORD_HASH
    if not valid:
        messagebox.showerror("Access denied", "Incorrect examiner password.", parent=parent)
    return valid


class DogBPExamMode:
    """Examiner-configured practical for identification of two unknown drugs."""

    def __init__(self, master, level="MBBS"):
        self.master = master
        self.level = level.upper()
        self.exam_seconds = 20 * 60 if self.level == "MBBS" else 25 * 60
        self.seconds_left = self.exam_seconds
        self.timer_job = None
        self.exam_in_progress = False
        self.student_name = self.roll_number = ""
        self.unknown_drugs = None
        self.active_test = 0
        self.test_histories = {0: [], 1: []}

        self.master.title(f"Dog BP Unknown-Drug Practical – {self.level}")
        set_window_size(self.master, 1180, 720, 820, 600, margin_x=60, margin_y=90)
        self.master.configure(bg="#eef4f8")

        self.response_model = DogBPSimulation.__new__(DogBPSimulation)
        self.response_model.baseline_map = 120
        self.response_model.baseline_hr = 72
        self.response_model.injection_history = []
        self.master.protocol("WM_DELETE_WINDOW", self.close_exam)
        self.show_start_screen()

    def clear_window(self):
        for widget in self.master.winfo_children():
            widget.destroy()

    def show_start_screen(self):
        self.cancel_timer()
        self.exam_in_progress = False
        self.unknown_drugs = load_practical_configuration(self.level)
        self.clear_window()

        header = tk.Frame(self.master, bg="#173b57", padx=20, pady=13)
        header.pack(fill="x")
        tk.Label(
            header, text=f"Dog BP Unknown-Drug Practical – {self.level}",
            font=("Segoe UI", 20, "bold"), bg="#173b57", fg="white",
        ).pack(anchor="w")
        tk.Label(
            header, text="Identify two examiner-selected drugs by performing pharmacological tests",
            font=("Segoe UI", 9), bg="#173b57", fg="#cfe2f3",
        ).pack(anchor="w", pady=(2, 0))
        tk.Label(header, text="MAMC, New Delhi", font=("Segoe UI", 8),
                 bg="#173b57", fg="#a9c3d5").place(relx=1.0, rely=0.0,
                                                    anchor="ne")

        card = tk.Frame(
            self.master, bg="white", padx=38, pady=25,
            highlightbackground="#cbd8e2", highlightthickness=1,
        )
        card.place(relx=0.5, rely=0.53, anchor="center")
        tk.Label(
            card, text="STUDENT ENTRY", font=("Segoe UI", 10, "bold"),
            fg="#607789", bg="white",
        ).pack(pady=(0, 12))
        form = tk.Frame(card, bg="white")
        form.pack()
        tk.Label(form, text="Student name", font=("Segoe UI", 11, "bold"),
                 bg="white").grid(row=0, column=0, sticky="w", pady=6)
        self.name_entry = tk.Entry(form, width=32, font=("Segoe UI", 11))
        self.name_entry.grid(row=0, column=1, padx=(15, 0), pady=6)
        tk.Label(form, text="Roll number", font=("Segoe UI", 11, "bold"),
                 bg="white").grid(row=1, column=0, sticky="w", pady=6)
        self.roll_entry = tk.Entry(form, width=32, font=("Segoe UI", 11))
        self.roll_entry.grid(row=1, column=1, padx=(15, 0), pady=6)

        ready = self.unknown_drugs is not None
        status_text = (
            "Practical ready: two unknown test solutions have been configured."
            if ready else
            "Examiner setup required before a student can begin."
        )
        tk.Label(
            card, text=status_text,
            font=("Segoe UI", 10, "bold"),
            fg="#237032" if ready else "#a13d2d",
            bg="#eef7f0" if ready else "#fff3f0",
            padx=15, pady=9,
        ).pack(fill="x", pady=(16, 7))
        tk.Label(
            card,
            text=(f"2 unknowns • {self.exam_seconds // 60} minutes • Experimental injections allowed\n"
                  "Drug identities and marks are visible only to the examiner."),
            font=("Segoe UI", 9), fg="#4c6578", bg="#f4f8fb",
            justify="center", padx=15, pady=9,
        ).pack(fill="x", pady=(0, 16))

        buttons = tk.Frame(card, bg="white")
        buttons.pack()
        self.start_button = tk.Button(
            buttons, text="Start Practical", command=self.start_exam,
            state="normal" if ready else "disabled",
            font=("Segoe UI", 11, "bold"), bg="#1769aa", fg="white",
            disabledforeground="#d7e1e8", padx=22, pady=8, cursor="hand2",
        )
        self.start_button.pack(side="left", padx=6)
        tk.Button(
            buttons, text="Examiner Setup", command=self.open_examiner_setup,
            font=("Segoe UI", 10, "bold"), bg="#6a3d8f", fg="white",
            padx=17, pady=8, cursor="hand2",
        ).pack(side="left", padx=6)
        self.name_entry.focus_set()

    def open_examiner_setup(self):
        if not examiner_password_is_valid(self.master):
            return
        current = load_practical_configuration(self.level)
        setup = tk.Toplevel(self.master)
        setup.title(f"Examiner Setup – Dog BP {self.level}")
        set_window_size(setup, 520, 355, 500, 340)
        setup.resizable(False, False)
        setup.configure(bg="#eef4f8")
        setup.transient(self.master)
        setup.grab_set()

        header = tk.Frame(setup, bg="#173b57", padx=18, pady=12)
        header.pack(fill="x")
        tk.Label(header, text="Configure Unknown Test Solutions",
                 font=("Segoe UI", 17, "bold"), bg="#173b57", fg="white").pack(anchor="w")
        tk.Label(header, text=f"{self.level} practical • selections remain hidden from students",
                 font=("Segoe UI", 9), bg="#173b57", fg="#cfe2f3").pack(anchor="w")

        body = tk.Frame(setup, bg="white", padx=28, pady=22,
                        highlightbackground="#cbd8e2", highlightthickness=1)
        body.pack(fill="both", expand=True, padx=18, pady=18)
        defaults = current or (PRACTICAL_DRUGS[0], PRACTICAL_DRUGS[1])
        first_var = tk.StringVar(value=defaults[0])
        second_var = tk.StringVar(value=defaults[1])
        for row, (label, variable) in enumerate((
                ("Unknown 1", first_var), ("Unknown 2", second_var))):
            tk.Label(body, text=label, font=("Segoe UI", 11, "bold"),
                     bg="white", fg="#173b57").grid(row=row, column=0, sticky="w", pady=8)
            ttk.Combobox(
                body, textvariable=variable, values=PRACTICAL_DRUGS,
                state="readonly", width=28, font=("Segoe UI", 10),
            ).grid(row=row, column=1, padx=(18, 0), pady=8)
        tk.Label(
            body,
            text="Choose two different drugs. The student sees only the labels\nUnknown 1 and Unknown 2 during the practical.",
            font=("Segoe UI", 9), bg="#f4f8fb", fg="#4c6578",
            justify="left", padx=10, pady=8,
        ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(9, 14))

        def save_selection():
            try:
                save_practical_configuration(
                    self.level, first_var.get(), second_var.get()
                )
            except ValueError as error:
                messagebox.showwarning("Unknown drugs", str(error), parent=setup)
                return
            messagebox.showinfo(
                "Practical configured",
                f"Unknown 1: {first_var.get()}\nUnknown 2: {second_var.get()}\n\n"
                "These identities will remain hidden on the student screen.",
                parent=setup,
            )
            setup.destroy()
            self.show_start_screen()

        tk.Button(
            body, text="Save Unknown Drugs", command=save_selection,
            font=("Segoe UI", 10, "bold"), bg="#237032", fg="white",
            padx=18, pady=7, cursor="hand2",
        ).grid(row=3, column=0, columnspan=2)

    def start_exam(self):
        name = self.name_entry.get().strip()
        roll = self.roll_entry.get().strip()
        configuration = load_practical_configuration(self.level)
        if configuration is None:
            messagebox.showwarning(
                "Examiner setup", "The examiner must configure two unknown drugs first.",
                parent=self.master,
            )
            return
        if not name or not roll:
            messagebox.showwarning(
                "Student details", "Enter both student name and roll number.",
                parent=self.master,
            )
            return
        self.student_name, self.roll_number = name, roll
        self.unknown_drugs = configuration
        self.seconds_left = self.exam_seconds
        self.exam_in_progress = True
        self.active_test = 0
        self.test_histories = {0: [], 1: []}
        self.build_exam_screen()
        self.refresh_display()
        self.update_timer()

    def build_exam_screen(self):
        self.clear_window()
        header = tk.Frame(self.master, bg="#173b57", padx=14, pady=7)
        header.pack(fill="x")
        tk.Label(
            header, text=f"Dog BP Practical • {self.level} • {self.student_name}",
            font=("Segoe UI", 11, "bold"), bg="#173b57", fg="white",
        ).pack(side="left")
        self.timer_label = tk.Label(
            header, font=("Segoe UI", 12, "bold"),
            bg="#173b57", fg="#ffd166",
        )
        self.timer_label.pack(side="right")
        tk.Label(header, text="MAMC, New Delhi", font=("Segoe UI", 8),
                 bg="#173b57", fg="#a9c3d5").pack(side="right", padx=(8, 12))

        answer_frame = tk.Frame(
            self.master, bg="white", padx=14, pady=9,
            highlightbackground="#cbd8e2", highlightthickness=1,
        )
        answer_frame.pack(side="bottom", fill="x", padx=12, pady=(5, 9))
        tk.Label(
            answer_frame, text="FINAL IDENTIFICATION", font=("Segoe UI", 10, "bold"),
            bg="white", fg="#173b57",
        ).pack(side="left", padx=(0, 14))
        answer_options = list(PRACTICAL_DRUGS)
        random.shuffle(answer_options)
        self.answer_vars = [tk.StringVar(value=""), tk.StringVar(value="")]
        for index, variable in enumerate(self.answer_vars, 1):
            tk.Label(answer_frame, text=f"Unknown {index}", font=("Segoe UI", 9, "bold"),
                     bg="white", fg="#3f5668").pack(side="left", padx=(5, 5))
            ttk.Combobox(
                answer_frame, textvariable=variable, values=answer_options,
                state="readonly", width=18, font=("Segoe UI", 9),
            ).pack(side="left", padx=(0, 8))
        tk.Button(
            answer_frame, text="Submit Practical", command=self.submit_exam,
            font=("Segoe UI", 10, "bold"), bg="#a13d2d", fg="white",
            padx=13, pady=5, cursor="hand2",
        ).pack(side="right", padx=(12, 0))

        body = tk.Frame(self.master, bg="#eef4f8", padx=12, pady=9)
        body.pack(fill="both", expand=True)
        controls = tk.Frame(
            body, bg="white", padx=16, pady=11,
            highlightbackground="#cbd8e2", highlightthickness=1,
        )
        controls.pack(side="left", fill="y", padx=(0, 9))
        # Keep geometry propagation enabled. The control column now requests
        # enough width for its real font metrics, including on high-DPI screens.
        self.controls_frame = controls
        self.build_controls(controls)

        workspace = tk.Frame(body, bg="#eef4f8")
        workspace.pack(side="left", fill="both", expand=True)
        graph_card = tk.Frame(
            workspace, bg="white", highlightbackground="#cbd8e2",
            highlightthickness=1,
        )
        graph_card.pack(fill="both", expand=True)
        self.fig = Figure(figsize=(7.4, 4.0), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_card)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        log_card = tk.Frame(
            workspace, bg="white", padx=9, pady=7,
            highlightbackground="#cbd8e2", highlightthickness=1,
        )
        log_card.pack(fill="x", pady=(7, 0))
        top = tk.Frame(log_card, bg="white")
        top.pack(fill="x", pady=(0, 5))
        tk.Label(top, text="Observation Log", font=("Segoe UI", 10, "bold"),
                 bg="white", fg="#173b57").pack(side="left")
        self.peak_label = tk.Label(
            top, text="Peak BP: —   Peak pulse: —", font=("Segoe UI", 9, "bold"),
            bg="white", fg="#607789",
        )
        self.peak_label.pack(side="right")
        columns = ("trial", "injection", "dose", "bp", "pulse")
        self.log_table = ttk.Treeview(log_card, columns=columns, show="headings", height=3)
        headings = {
            "trial": "Trial", "injection": "Injection shown to student",
            "dose": "Dose", "bp": "Peak BP", "pulse": "Peak pulse",
        }
        table_font = tkfont.Font(root=self.master, family="Segoe UI", size=10)
        samples = {
            "trial": ("Trial", "10"),
            "injection": ("Injection shown to student", "Known: Phenoxybenzamine", "Unknown 2"),
            "dose": ("Dose", "2.0 mcg/kg"),
            "bp": ("Peak BP", "195.0 mmHg"),
            "pulse": ("Peak pulse", "160.0 bpm"),
        }
        widths = {
            column: max(table_font.measure(text) for text in values) + 30
            for column, values in samples.items()
        }
        for column in columns:
            self.log_table.heading(column, text=headings[column])
            self.log_table.column(
                column, width=widths[column], minwidth=widths[column],
                anchor="center", stretch=True,
            )
        self.log_table.pack(fill="x")

    def build_controls(self, parent):
        tk.Label(parent, text="TEST PREPARATION", font=("Segoe UI", 10, "bold"),
                 bg="white", fg="#607789").pack(anchor="w")
        self.test_var = tk.IntVar(value=0)
        switch = tk.Frame(parent, bg="white")
        switch.pack(fill="x", pady=(7, 10))
        for index in (0, 1):
            tk.Radiobutton(
                switch, text=f"Unknown {index + 1}", variable=self.test_var, value=index,
                command=self.switch_test, indicatoron=False, selectcolor="#1769aa",
                bg="#e7eef4", fg="#173b57", activebackground="#cfe2f3",
                font=("Segoe UI", 9, "bold"), padx=8, pady=6,
            ).pack(side="left", fill="x", expand=True, padx=(0, 4) if index == 0 else (4, 0))

        self.active_label = tk.Label(
            parent, text="Working on Unknown 1", font=("Segoe UI", 11, "bold"),
            bg="#eaf3fa", fg="#173b57", padx=8, pady=7,
        )
        self.active_label.pack(fill="x", pady=(0, 9))
        tk.Label(parent, text="Dose (mcg/kg)", font=("Segoe UI", 9, "bold"),
                 bg="white", fg="#3f5668").pack(anchor="w")
        self.dose_var = tk.DoubleVar(value=1.0)
        tk.Scale(
            parent, from_=0.1, to=2.0, resolution=0.1,
            orient="horizontal", variable=self.dose_var, bg="white",
            highlightthickness=0, length=250,
        ).pack(fill="x", pady=(0, 5))
        tk.Button(
            parent, text="Inject Current Unknown", command=self.inject_unknown,
            font=("Segoe UI", 10, "bold"), bg="#a04070", fg="white",
            padx=10, pady=7, cursor="hand2",
        ).pack(fill="x", pady=(0, 12))

        tk.Label(parent, text="KNOWN DRUGS FOR TESTING", font=("Segoe UI", 10, "bold"),
                 bg="white", fg="#607789").pack(anchor="w", pady=(0, 6))
        self.agonist_var = tk.StringVar(value=KNOWN_AGONISTS[0])
        ttk.Combobox(
            parent, textvariable=self.agonist_var, values=KNOWN_AGONISTS,
            state="readonly", font=("Segoe UI", 9),
        ).pack(fill="x")
        tk.Button(
            parent, text="Inject Known Agonist", command=lambda: self.inject_known("agonist"),
            font=("Segoe UI", 9, "bold"), bg="#1769aa", fg="white",
            pady=6, cursor="hand2",
        ).pack(fill="x", pady=(4, 8))
        self.blocker_var = tk.StringVar(value=KNOWN_BLOCKERS[0])
        ttk.Combobox(
            parent, textvariable=self.blocker_var, values=KNOWN_BLOCKERS,
            state="readonly", font=("Segoe UI", 9),
        ).pack(fill="x")
        tk.Button(
            parent, text="Inject Known Blocker", command=lambda: self.inject_known("blocker"),
            font=("Segoe UI", 9, "bold"), bg="#d68910", fg="white",
            pady=6, cursor="hand2",
        ).pack(fill="x", pady=(4, 9))
        tk.Button(
            parent, text="Reset Current Preparation",
            command=self.reset_current_preparation,
            font=("Segoe UI", 9, "bold"), bg="#6c757d", fg="white",
            pady=6, cursor="hand2",
        ).pack(fill="x")
        tip_font = tkfont.Font(root=self.master, family="Segoe UI", size=8)
        tip_wrap = tip_font.measure("Tip: obtain the unknown response, reset if required,")
        tk.Label(
            parent,
            text="Tip: obtain the unknown response, reset if required, then use a known blocker or agonist to test your hypothesis.",
            font=("Segoe UI", 8), bg="#fff8e1", fg="#6b5a20",
            wraplength=tip_wrap, justify="left", padx=8, pady=7,
        ).pack(fill="x", pady=(10, 0))

    def switch_test(self):
        self.active_test = int(self.test_var.get())
        self.active_label.config(text=f"Working on Unknown {self.active_test + 1}")
        self.refresh_display()

    def inject_unknown(self):
        actual_drug = self.unknown_drugs[self.active_test]
        self.perform_injection(actual_drug, f"Unknown {self.active_test + 1}")

    def inject_known(self, kind):
        drug = self.agonist_var.get() if kind == "agonist" else self.blocker_var.get()
        self.perform_injection(drug, f"Known: {drug}")

    def perform_injection(self, actual_drug, public_label):
        history = self.test_histories[self.active_test]
        self.response_model.injection_history = [
            {"drug": event["actual_drug"]} for event in history
        ]
        time = np.linspace(0, 60, 121)
        dose = float(self.dose_var.get())
        baseline_bp = np.full_like(time, self.response_model.baseline_map)
        baseline_pulse = np.full_like(time, self.response_model.baseline_hr)
        bp, pulse, _explanation = self.response_model.simulate_drug_effect(
            actual_drug, dose, time, baseline_bp, baseline_pulse
        )
        peak_bp = float(bp[np.argmax(np.abs(bp - self.response_model.baseline_map))])
        peak_pulse = float(pulse[np.argmax(np.abs(pulse - self.response_model.baseline_hr))])
        start_time = len(history) * 60
        history.append({
            "actual_drug": actual_drug,
            "public_label": public_label,
            "dose": dose,
            "time": time + start_time,
            "bp": bp,
            "pulse": pulse,
            "peak_bp": peak_bp,
            "peak_pulse": peak_pulse,
        })
        self.refresh_display()

    def reset_current_preparation(self, confirm=True):
        if confirm and self.test_histories[self.active_test]:
            if not messagebox.askyesno(
                    "Reset preparation",
                    f"Clear all trials for Unknown {self.active_test + 1}?",
                    parent=self.master):
                return
        self.test_histories[self.active_test] = []
        self.refresh_display()

    def refresh_display(self):
        history = self.test_histories[self.active_test]
        while len(self.fig.axes) > 1:
            self.fig.delaxes(self.fig.axes[-1])
        self.ax.clear()
        pulse_axis = self.ax.twinx()
        window_end = max(240, len(history) * 60)
        self.ax.plot([0, window_end], [120, 120], color="#1769aa", alpha=0.25, linestyle=":")
        pulse_axis.plot([0, window_end], [72, 72], color="#d33f49", alpha=0.25, linestyle=":")
        for event in history:
            self.ax.plot(event["time"], event["bp"], color="#1769aa", linewidth=2)
            pulse_axis.plot(event["time"], event["pulse"], color="#d33f49",
                            linewidth=1.6, linestyle="--")
            start = float(event["time"][0])
            self.ax.axvline(start, color="#607789", alpha=0.22, linestyle=":")
            self.ax.text(start + 2, 190, event["public_label"], fontsize=8,
                         color="#3f5668", va="top")
        self.ax.set_xlim(0, window_end)
        self.ax.set_ylim(45, 195)
        pulse_axis.set_ylim(20, 160)
        self.ax.set_title(
            f"Unknown {self.active_test + 1}: continuous blood pressure and pulse",
            fontsize=11, color="#173b57",
        )
        self.ax.set_xlabel("Experimental time (seconds)", fontsize=9)
        self.ax.set_ylabel("Blood pressure (mmHg)", color="#1769aa", fontsize=9)
        pulse_axis.set_ylabel("Pulse rate (beats/min)", color="#d33f49", fontsize=9)
        self.ax.grid(alpha=0.14)
        self.fig.tight_layout(pad=1.0)
        self.canvas.draw()

        for item in self.log_table.get_children():
            self.log_table.delete(item)
        for index, event in enumerate(history, 1):
            self.log_table.insert(
                "", "end",
                values=(
                    index, event["public_label"], f"{event['dose']:.1f} mcg/kg",
                    f"{event['peak_bp']:.1f} mmHg", f"{event['peak_pulse']:.1f} bpm",
                ),
            )
        if history:
            event = history[-1]
            self.peak_label.config(
                text=(f"Peak BP: {event['peak_bp']:.1f} mmHg   "
                      f"Peak pulse: {event['peak_pulse']:.1f} bpm")
            )
        else:
            self.peak_label.config(text="Peak BP: —   Peak pulse: —")

    def submit_exam(self):
        answers = [variable.get() for variable in self.answer_vars]
        if not all(answers):
            messagebox.showwarning(
                "Final identification", "Identify both Unknown 1 and Unknown 2 before submitting.",
                parent=self.master,
            )
            return
        if not messagebox.askyesno(
                "Submit practical",
                "Submit both final identifications? Answers cannot be changed afterward.",
                parent=self.master):
            return
        self.finish_exam(answers=answers)

    def update_timer(self):
        minutes, seconds = divmod(self.seconds_left, 60)
        self.timer_label.config(text=f"{minutes:02d}:{seconds:02d}")
        if self.seconds_left <= 0:
            answers = [variable.get() for variable in self.answer_vars]
            messagebox.showinfo(
                "Time completed", "Time has ended. Available identifications will be submitted.",
                parent=self.master,
            )
            self.finish_exam(timed_out=True, answers=answers)
            return
        self.seconds_left -= 1
        self.timer_job = self.master.after(1000, self.update_timer)

    def finish_exam(self, timed_out=False, answers=None):
        if not self.exam_in_progress:
            return
        self.cancel_timer()
        answers = list(answers or ("", ""))
        while len(answers) < 2:
            answers.append("")
        score = sum(answer == correct for answer, correct in zip(answers, self.unknown_drugs))
        details = []
        for index, (answer, correct) in enumerate(zip(answers, self.unknown_drugs), 1):
            history = self.test_histories[index - 1]
            details.append({
                "question": f"Identify examiner-configured Unknown {index}",
                "student_answer": answer or "Not answered",
                "correct_answer": correct,
                "explanation": f"Student performed {len(history)} experimental injection(s).",
            })
        try:
            ensure_database()
            with sqlite3.connect(DATABASE_PATH) as connection:
                connection.execute(
                    """INSERT INTO results
                    (submitted_at, student_name, roll_number, level, score, total,
                     duration_seconds, answer_details) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        self.student_name, self.roll_number, self.level, score, 2,
                        self.exam_seconds - self.seconds_left, json.dumps(details),
                    ),
                )
        except (OSError, sqlite3.Error) as error:
            messagebox.showerror(
                "Result storage error", f"Could not save the result:\n{error}",
                parent=self.master,
            )
        self.exam_in_progress = False
        self.show_submission_screen(timed_out)

    def show_submission_screen(self, timed_out):
        self.clear_window()
        card = tk.Frame(
            self.master, bg="white", padx=45, pady=35,
            highlightbackground="#cbd8e2", highlightthickness=1,
        )
        card.place(relx=0.5, rely=0.48, anchor="center")
        tk.Label(card, text="Practical Submitted", font=("Segoe UI", 23, "bold"),
                 fg="#237032", bg="white").pack(pady=(0, 10))
        tk.Label(
            card,
            text=(f"{self.student_name}  •  Roll No. {self.roll_number}\n"
                  f"{self.level} Dog BP Unknown-Drug Practical"),
            font=("Segoe UI", 12), fg="#3f5668", bg="white", justify="center",
        ).pack(pady=8)
        status = (
            "Time expired; available identifications were submitted."
            if timed_out else "Both identifications were saved successfully."
        )
        tk.Label(
            card, text=status + "\nDrug identities and marks are available only through Examiner Results.",
            font=("Segoe UI", 11), fg="#4c6578", bg="#f4f8fb",
            justify="center", padx=18, pady=12,
        ).pack(pady=15)
        buttons = tk.Frame(card, bg="white")
        buttons.pack()
        tk.Button(
            buttons, text="New Student", command=self.show_start_screen,
            bg="#1769aa", fg="white", font=("Segoe UI", 11, "bold"),
            padx=16, pady=7,
        ).pack(side="left", padx=6)
        tk.Button(
            buttons, text="Close", command=self.master.destroy,
            bg="#6c757d", fg="white", font=("Segoe UI", 11),
            padx=16, pady=7,
        ).pack(side="left", padx=6)

    def cancel_timer(self):
        if self.timer_job is not None:
            self.master.after_cancel(self.timer_job)
            self.timer_job = None

    def close_exam(self):
        if self.exam_in_progress and not messagebox.askyesno(
                "Close examination", "The practical is incomplete. Close without submitting?",
                parent=self.master):
            return
        self.cancel_timer()
        self.master.destroy()


class DogBPExaminerDashboard:
    def __init__(self, master):
        self.master = master
        if not examiner_password_is_valid(master):
            self.master.destroy()
            return
        self.master.title("Dog BP – Examiner Results")
        set_window_size(self.master, 950, 600, 780, 480)
        self.build_screen()
        self.load_results()

    def build_screen(self):
        header = tk.Frame(self.master, bg="#173b57", padx=16, pady=12)
        header.pack(fill="x")
        tk.Label(header, text="Dog BP Examiner Results", font=("Segoe UI", 18, "bold"),
                 bg="#173b57", fg="white").pack(side="left")
        tk.Button(header, text="Refresh", command=self.load_results,
                  bg="#2b8a3e", fg="white", padx=12, pady=4).pack(side="right")
        tk.Label(header, text="MAMC, New Delhi", font=("Segoe UI", 8),
                 bg="#173b57", fg="#a9c3d5").pack(side="right", padx=(8, 4))
        columns = ("submitted", "name", "roll", "level", "score")
        self.tree = ttk.Treeview(self.master, columns=columns, show="headings", height=14)
        headings = {"submitted": "Submitted", "name": "Student", "roll": "Roll No.",
                    "level": "Level", "score": "Marks"}
        widths = {"submitted": 155, "name": 220, "roll": 130, "level": 80, "score": 90}
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], anchor="center" if column in ("level", "score") else "w")
        scrollbar = ttk.Scrollbar(self.master, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=16)
        scrollbar.pack(side="left", fill="y", pady=16)
        side = tk.Frame(self.master, bg="#eef4f8", padx=12)
        side.pack(side="right", fill="y", pady=16)
        tk.Button(side, text="View Answer Review", command=self.view_selected,
                  bg="#1769aa", fg="white", width=20, pady=8).pack(pady=6)
        tk.Button(side, text="Close", command=self.master.destroy,
                  bg="#6c757d", fg="white", width=20, pady=8).pack(pady=6)
        self.tree.bind("<Double-1>", lambda _event: self.view_selected())

    def load_results(self):
        ensure_database()
        for item in self.tree.get_children():
            self.tree.delete(item)
        with sqlite3.connect(DATABASE_PATH) as connection:
            rows = connection.execute(
                "SELECT id, submitted_at, student_name, roll_number, level, score, total "
                "FROM results ORDER BY id DESC").fetchall()
        for row in rows:
            result_id, submitted, name, roll, level, score, total = row
            self.tree.insert("", "end", iid=str(result_id),
                             values=(submitted, name, roll, level, f"{score}/{total}"))

    def view_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Select a result", "Select a student result first.", parent=self.master)
            return
        with sqlite3.connect(DATABASE_PATH) as connection:
            row = connection.execute(
                "SELECT student_name, roll_number, level, score, total, answer_details "
                "FROM results WHERE id = ?", (int(selected[0]),)).fetchone()
        if not row:
            return
        name, roll, level, score, total, serialized = row
        details = json.loads(serialized)
        review_window = tk.Toplevel(self.master)
        review_window.title(f"Answer Review – {name}")
        set_window_size(review_window, 850, 650, 700, 500)
        tk.Label(review_window, text=f"{name} • Roll {roll} • {level} • Marks {score}/{total}",
                 font=("Segoe UI", 14, "bold"), fg="#173b57", pady=12).pack()
        text = tk.Text(review_window, wrap="word", font=("Segoe UI", 10), padx=12, pady=10)
        scrollbar = ttk.Scrollbar(review_window, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        for index, detail in enumerate(details, 1):
            correct = detail["student_answer"] == detail["correct_answer"]
            text.insert("end", f"Q{index}. {detail['question']}\n")
            text.insert("end", f"Student: {detail['student_answer']}\n")
            text.insert("end", f"Correct: {detail['correct_answer']}  ({'Correct' if correct else 'Incorrect'})\n")
            text.insert("end", f"Explanation: {detail['explanation']}\n\n")
        text.config(state="disabled")
