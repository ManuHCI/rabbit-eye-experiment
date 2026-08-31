import hashlib
import json
import os
import random
import sqlite3
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

import numpy as np
from PIL import Image, ImageTk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from experiments.bioassay import BioassaySimulation
from experiments.rabbit_eye_practical import BASELINE, DRUG_DATA
from ui.display import set_window_size


QUESTION_COUNT = 10
EXAMINER_PASSWORD_HASH = "cfadba7271287e0b7e93524c06f6db748e79bad06754ca3b5cef14029e757568"


def resource_path(*parts):
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent
    return base.joinpath(*parts)


def exam_data_dir():
    if getattr(sys, "frozen", False):
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "MAMC_CAL" / "exam_data"
    return Path(__file__).resolve().parent.parent / "exam_data"


SUITE_DATABASE = exam_data_dir() / "cal_suite_results.sqlite3"
DOG_DATABASE = exam_data_dir() / "dog_bp_results.sqlite3"


def ensure_suite_database():
    SUITE_DATABASE.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(SUITE_DATABASE) as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submitted_at TEXT NOT NULL,
                experiment TEXT NOT NULL,
                level TEXT NOT NULL,
                student_name TEXT NOT NULL,
                roll_number TEXT NOT NULL,
                score INTEGER NOT NULL,
                total INTEGER NOT NULL,
                duration_seconds INTEGER NOT NULL,
                answer_details TEXT NOT NULL
            )"""
        )


def save_suite_result(experiment, level, name, roll, score, total, duration, details):
    ensure_suite_database()
    with sqlite3.connect(SUITE_DATABASE) as connection:
        connection.execute(
            """INSERT INTO results
               (submitted_at, experiment, level, student_name, roll_number,
                score, total, duration_seconds, answer_details)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), experiment, level,
             name, roll, score, total, duration, json.dumps(details)),
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


class BaseCompactExam:
    """Shared compact, laptop-friendly exam shell."""

    exam_title = "CAL Examination"
    experiment_name = "CAL"
    level = "MBBS"
    exam_seconds = 15 * 60
    question_bank = []

    def __init__(self, master):
        self.master = master
        self.rng = random.Random()
        self.questions = []
        self.answers = []
        self.question_index = 0
        self.seconds_left = self.exam_seconds
        self.timer_job = None
        self.exam_in_progress = False
        self.student_name = ""
        self.roll_number = ""

        set_window_size(master, 1050, 650, 760, 520, margin_x=80, margin_y=120)
        master.title(self.exam_title)
        master.configure(bg="#eef4f8")
        master.protocol("WM_DELETE_WINDOW", self.close_exam)
        self.show_start_screen()

    def clear_window(self):
        for widget in self.master.winfo_children():
            widget.destroy()

    def show_start_screen(self):
        self.cancel_timer()
        self.exam_in_progress = False
        self.clear_window()
        card = tk.Frame(self.master, bg="white", padx=38, pady=28,
                        highlightbackground="#cbd8e2", highlightthickness=1)
        card.place(relx=0.5, rely=0.48, anchor="center")
        tk.Label(card, text=self.exam_title, font=("Segoe UI", 22, "bold"),
                 fg="#173b57", bg="white").pack(pady=(0, 16))
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
        tk.Label(card,
                 text=f"{QUESTION_COUNT} randomized questions • {self.exam_seconds // 60} minutes\n"
                      "Marks are visible only through Examiner Results",
                 font=("Segoe UI", 10), fg="#4c6578", bg="#f4f8fb",
                 justify="center", padx=16, pady=10).pack(fill="x", pady=18)
        tk.Button(card, text="Start Examination", command=self.start_exam,
                  font=("Segoe UI", 12, "bold"), bg="#1769aa", fg="white",
                  padx=24, pady=8, cursor="hand2").pack()
        tk.Label(self.master, text="MAMC, New Delhi", font=("Segoe UI", 8),
                 bg="#eef4f8", fg="#607789").place(relx=1.0, rely=1.0,
                                                     x=-10, y=-8, anchor="se")
        self.name_entry.focus_set()

    def start_exam(self):
        name = self.name_entry.get().strip()
        roll = self.roll_entry.get().strip()
        if not name or not roll:
            messagebox.showwarning("Student details", "Enter both student name and roll number.",
                                   parent=self.master)
            return
        self.student_name, self.roll_number = name, roll
        count = min(QUESTION_COUNT, len(self.question_bank))
        self.questions = [dict(item) for item in self.rng.sample(self.question_bank, count)]
        for question in self.questions:
            question["options"] = list(question["options"])
            self.rng.shuffle(question["options"])
        self.answers = []
        self.question_index = 0
        self.seconds_left = self.exam_seconds
        self.exam_in_progress = True
        self.build_exam_screen()
        self.show_question()
        self.update_timer()

    def build_exam_screen(self):
        self.clear_window()
        header = tk.Frame(self.master, bg="#173b57", padx=14, pady=7)
        header.pack(fill="x")
        self.progress_label = tk.Label(header, font=("Segoe UI", 11, "bold"),
                                       bg="#173b57", fg="white")
        self.progress_label.pack(side="left")
        self.timer_label = tk.Label(header, font=("Segoe UI", 12, "bold"),
                                    bg="#173b57", fg="#ffd166")
        self.timer_label.pack(side="right")
        tk.Label(header, text="MAMC, New Delhi", font=("Segoe UI", 8),
                 bg="#173b57", fg="#a9c3d5").pack(side="right", padx=(8, 12))
        self.next_button = tk.Button(header, text="Next", command=self.submit_answer,
                                     font=("Segoe UI", 10, "bold"), bg="#2b8a3e", fg="white",
                                     padx=13, pady=4, cursor="hand2")
        self.next_button.pack(side="right", padx=(8, 16))
        self.prompt_label = tk.Label(self.master, font=("Segoe UI", 11, "bold"),
                                     fg="#20394d", bg="#eef4f8", wraplength=950,
                                     justify="left", padx=14, pady=7)
        self.prompt_label.pack(fill="x")
        self.visual_frame = tk.Frame(self.master, bg="white")
        self.visual_frame.pack(fill="both", expand=True, padx=14)
        self.build_visual(self.visual_frame)
        answer_frame = tk.Frame(self.master, bg="white", padx=14, pady=8)
        answer_frame.pack(fill="x", padx=14, pady=(7, 9))
        tk.Label(answer_frame, text="Answer:", font=("Segoe UI", 11, "bold"),
                 bg="white", fg="#173b57").pack(side="left", padx=(0, 10))
        self.answer_var = tk.StringVar(value="")
        self.answer_box = ttk.Combobox(answer_frame, textvariable=self.answer_var,
                                      state="readonly", font=("Segoe UI", 11), width=52)
        self.answer_box.pack(side="left", fill="x", expand=True)

    def build_visual(self, parent):
        raise NotImplementedError

    def render_visual(self, question):
        raise NotImplementedError

    def show_question(self):
        question = self.questions[self.question_index]
        number = self.question_index + 1
        total = len(self.questions)
        self.progress_label.config(text=f"{self.experiment_name} • Question {number}/{total}")
        self.prompt_label.config(text=question["prompt"])
        self.answer_var.set("")
        self.answer_box["values"] = question["options"]
        self.render_visual(question)
        self.next_button.config(text="Submit" if number == total else "Next",
                                bg="#a13d2d" if number == total else "#2b8a3e")

    def submit_answer(self):
        selected = self.answer_var.get()
        if not selected:
            messagebox.showwarning("Select an answer", "Select one answer before continuing.",
                                   parent=self.master)
            return
        self.answers.append(selected)
        if self.question_index == len(self.questions) - 1:
            self.finish_exam()
        else:
            self.question_index += 1
            self.show_question()

    def update_timer(self):
        minutes, seconds = divmod(self.seconds_left, 60)
        self.timer_label.config(text=f"{minutes:02d}:{seconds:02d}")
        if self.seconds_left <= 0:
            messagebox.showinfo("Time completed", "Time has ended. The exam will be submitted.",
                                parent=self.master)
            self.finish_exam(timed_out=True)
            return
        self.seconds_left -= 1
        self.timer_job = self.master.after(1000, self.update_timer)

    def finish_exam(self, timed_out=False):
        if not self.exam_in_progress:
            return
        self.cancel_timer()
        while len(self.answers) < len(self.questions):
            self.answers.append("")
        score = sum(answer == question["answer"]
                    for answer, question in zip(self.answers, self.questions))
        details = [
            {"question": question["prompt"], "student_answer": answer or "Not answered",
             "correct_answer": question["answer"], "explanation": question["explanation"]}
            for answer, question in zip(self.answers, self.questions)
        ]
        try:
            save_suite_result(
                self.experiment_name, self.level, self.student_name, self.roll_number,
                score, len(self.questions), self.exam_seconds - self.seconds_left, details,
            )
        except (OSError, sqlite3.Error) as error:
            messagebox.showerror("Result storage error", f"Could not save result:\n{error}",
                                 parent=self.master)
        self.exam_in_progress = False
        self.show_submission_screen(timed_out)

    def show_submission_screen(self, timed_out):
        self.clear_window()
        card = tk.Frame(self.master, bg="white", padx=45, pady=35,
                        highlightbackground="#cbd8e2", highlightthickness=1)
        card.place(relx=0.5, rely=0.48, anchor="center")
        tk.Label(card, text="Examination Submitted", font=("Segoe UI", 23, "bold"),
                 fg="#237032", bg="white").pack(pady=(0, 10))
        tk.Label(card, text=f"{self.student_name} • Roll No. {self.roll_number}\n{self.exam_title}",
                 font=("Segoe UI", 12), fg="#3f5668", bg="white",
                 justify="center").pack(pady=8)
        status = "Time expired; available answers were submitted." if timed_out else "Responses saved successfully."
        tk.Label(card, text=status + "\nMarks are available only through Examiner Results.",
                 font=("Segoe UI", 11), fg="#4c6578", bg="#f4f8fb",
                 justify="center", padx=18, pady=12).pack(pady=15)
        tk.Button(card, text="Close", command=self.master.destroy,
                  bg="#6c757d", fg="white", font=("Segoe UI", 11),
                  padx=18, pady=8).pack()
        tk.Label(self.master, text="MAMC, New Delhi", font=("Segoe UI", 8),
                 bg="#eef4f8", fg="#607789").place(relx=1.0, rely=1.0,
                                                     x=-10, y=-8, anchor="se")

    def cancel_timer(self):
        if self.timer_job is not None:
            self.master.after_cancel(self.timer_job)
            self.timer_job = None

    def close_exam(self):
        if self.exam_in_progress and not messagebox.askyesno(
                "Close examination", "The exam is incomplete. Close without submitting?",
                parent=self.master):
            return
        self.cancel_timer()
        self.master.destroy()


RABBIT_DRUG_OPTIONS = list(DRUG_DATA.keys())
RABBIT_MECHANISMS = [
    "Muscarinic M3 receptor blockade", "Corneal sodium-channel blockade",
    "Inhibition of noradrenaline reuptake", "Muscarinic M3 receptor stimulation",
]


def rabbit_question(prompt, answer, options, drug, findings, explanation):
    return {"prompt": prompt, "answer": answer, "options": options,
            "drug": drug, "findings": findings, "explanation": explanation}


RABBIT_QUESTION_BANK = [
    rabbit_question("Identify the unknown drug from the rabbit-eye findings.", "Atropine (1%)",
                    RABBIT_DRUG_OPTIONS, "Atropine (1%)",
                    "Mydriasis • Light reflex absent • Corneal reflex present • IOP increased",
                    "Atropine blocks M3 receptors, causing mydriasis, cycloplegia and loss of light reflex."),
    rabbit_question("Identify the unknown drug from the rabbit-eye findings.", "Lignocaine (4%)",
                    RABBIT_DRUG_OPTIONS, "Lignocaine (4%)",
                    "Normal pupil • Light reflex present • Corneal reflex absent • IOP unchanged",
                    "Lignocaine blocks corneal sensory sodium channels without altering the pupil."),
    rabbit_question("Identify the unknown drug from the rabbit-eye findings.", "Cocaine (4%)",
                    RABBIT_DRUG_OPTIONS, "Cocaine (4%)",
                    "Mydriasis • Light reflex sluggish • Corneal reflex absent • Conjunctiva blanched",
                    "Cocaine blocks NA reuptake and has local-anaesthetic and vasoconstrictor actions."),
    rabbit_question("Identify the unknown drug from the rabbit-eye findings.", "Ephedrine (1%)",
                    RABBIT_DRUG_OPTIONS, "Ephedrine (1%)",
                    "Mydriasis • Light reflex sluggish • Corneal reflex present • Mild blanching",
                    "Ephedrine is a mixed sympathomimetic; the corneal reflex remains intact."),
    rabbit_question("Identify the unknown drug from the rabbit-eye findings.", "Pilocarpine (1%)",
                    RABBIT_DRUG_OPTIONS, "Pilocarpine (1%)",
                    "Miosis • Light reflex present • Corneal reflex present • IOP decreased",
                    "Pilocarpine stimulates M3 receptors, causing miosis and increased aqueous outflow."),
    rabbit_question("Which mechanism explains the observed mydriasis and absent light reflex?",
                    "Muscarinic M3 receptor blockade", RABBIT_MECHANISMS, "Atropine (1%)",
                    "Mydriasis • Light reflex absent • Corneal reflex present",
                    "Atropine blocks the sphincter pupillae M3 receptor."),
    rabbit_question("Which mechanism explains loss of corneal reflex without a pupil change?",
                    "Corneal sodium-channel blockade", RABBIT_MECHANISMS, "Lignocaine (4%)",
                    "Normal pupil • Corneal reflex absent • Conjunctiva unchanged",
                    "Local anaesthesia blocks corneal afferent impulses."),
    rabbit_question("Which mechanism best explains mydriasis with conjunctival blanching and local anaesthesia?",
                    "Inhibition of noradrenaline reuptake", RABBIT_MECHANISMS, "Cocaine (4%)",
                    "Mydriasis • Corneal reflex absent • Conjunctiva blanched",
                    "Cocaine inhibits NA reuptake and also blocks sodium channels."),
    rabbit_question("Which mechanism explains miosis with reduced intraocular pressure?",
                    "Muscarinic M3 receptor stimulation", RABBIT_MECHANISMS, "Pilocarpine (1%)",
                    "Miosis • Light reflex present • IOP decreased",
                    "M3 activation contracts ciliary muscle and opens trabecular drainage."),
    rabbit_question("Which drug causes mydriasis while preserving the corneal reflex?", "Ephedrine (1%)",
                    RABBIT_DRUG_OPTIONS, "Ephedrine (1%)",
                    "Mydriasis • Sluggish light reflex • Corneal reflex present",
                    "Ephedrine has no local-anaesthetic action."),
    rabbit_question("Which drug is most likely to precipitate angle-closure glaucoma?", "Atropine (1%)",
                    RABBIT_DRUG_OPTIONS, "Atropine (1%)",
                    "Marked mydriasis • Increased IOP",
                    "Atropine-induced mydriasis can obstruct aqueous drainage in a narrow angle."),
    rabbit_question("Which drug lowers IOP by facilitating trabecular outflow?", "Pilocarpine (1%)",
                    RABBIT_DRUG_OPTIONS, "Pilocarpine (1%)",
                    "Miosis • Reduced globe tone",
                    "Pilocarpine contracts ciliary muscle and improves trabecular outflow."),
]


class RabbitEyeExam(BaseCompactExam):
    exam_title = "Rabbit Eye Examination – MBBS"
    experiment_name = "Rabbit Eye"
    question_bank = RABBIT_QUESTION_BANK

    def build_visual(self, parent):
        images = tk.Frame(parent, bg="white")
        images.pack(fill="both", expand=True)

        self.eye_panels = {}
        for column, side in enumerate(("right", "left")):
            panel = tk.Frame(images, bg="#0f172a",
                             highlightbackground="#cbd8e2", highlightthickness=1)
            panel.grid(row=0, column=column, sticky="nsew", padx=4, pady=4)
            title = tk.Label(panel, text="", font=("Segoe UI", 10, "bold"),
                             bg="#173b57", fg="white", pady=5)
            title.pack(fill="x")
            image_label = tk.Label(panel, bg="#0f172a")
            image_label.pack(fill="both", expand=True)
            self.eye_panels[side] = (title, image_label)
        images.grid_columnconfigure(0, weight=1)
        images.grid_columnconfigure(1, weight=1)
        images.grid_rowconfigure(0, weight=1)

        table_frame = tk.Frame(parent, bg="white", padx=4, pady=4)
        table_frame.pack(fill="x")
        columns = ("parameter", "right", "left")
        self.observation_table = ttk.Treeview(
            table_frame, columns=columns, show="headings", height=4
        )
        self.observation_table.heading("parameter", text="Observation")
        self.observation_table.heading("right", text="Right Eye")
        self.observation_table.heading("left", text="Left Eye")
        self.observation_table.column("parameter", width=175, anchor="w")
        self.observation_table.column("right", width=300, anchor="center")
        self.observation_table.column("left", width=300, anchor="center")
        self.observation_table.pack(fill="x")

    def render_visual(self, question):
        drug = DRUG_DATA[question["drug"]]
        treated_side = "right" if self.question_index % 2 == 0 else "left"
        control_side = "left" if treated_side == "right" else "right"
        data_by_side = {treated_side: drug, control_side: BASELINE}

        self.eye_photos = {}
        for side in ("right", "left"):
            data = data_by_side[side]
            image_path = resource_path(
                "assets", "rabbit_eye", data["pupil_image"] + ".png"
            )
            image = Image.open(image_path).convert("RGB")
            image.thumbnail((360, 205), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            self.eye_photos[side] = photo
            title, image_label = self.eye_panels[side]
            role = "UNKNOWN TEST SOLUTION" if side == treated_side else "SALINE CONTROL"
            title.config(text=f"{side.upper()} EYE  •  {role}")
            image_label.config(image=photo)

        for item in self.observation_table.get_children():
            self.observation_table.delete(item)

        def pupil_text(data):
            return f"{data['pupil_size'].title()} ({data['pupil_mm']:.1f} mm)"

        rows = (
            ("Pupil size", pupil_text),
            ("Light reflex", lambda data: data["light_reflex"].title()),
            ("Corneal reflex", lambda data: data["corneal_reflex"].title()),
            ("Tone / IOP", lambda data: data["tone"].title()),
        )
        for label, formatter in rows:
            self.observation_table.insert(
                "", "end",
                values=(label, formatter(data_by_side["right"]),
                        formatter(data_by_side["left"])),
            )


FROG_DRUGS = {
    "Acetylcholine": (100.0, 3e-6, 1.6),
    "Carbachol": (100.0, 1e-6, 1.5),
    "Nicotine": (85.0, 5e-6, 1.3),
    "Succinylcholine": (95.0, 8e-6, 1.2),
}
FROG_DRUG_OPTIONS = list(FROG_DRUGS.keys())


def frog_question(prompt, answer, options, curves, explanation):
    return {"prompt": prompt, "answer": answer, "options": options,
            "curves": curves, "explanation": explanation}


FROG_QUESTION_BANK = [
    frog_question("Identify the unknown agonist from its dose-response curve.", "Acetylcholine",
                  FROG_DRUG_OPTIONS, [("Unknown", "Acetylcholine", 1.0)],
                  "ACh produces a full nicotinic agonist curve with an EC50 near 3 micromolar."),
    frog_question("Identify the most potent unknown agonist from its left-shifted dose-response curve.", "Carbachol",
                  FROG_DRUG_OPTIONS, [("Unknown", "Carbachol", 1.0)],
                  "Carbachol is more potent than ACh and is resistant to acetylcholinesterase."),
    frog_question("Identify the partial agonist from its lower maximum response.", "Nicotine",
                  FROG_DRUG_OPTIONS, [("Unknown", "Nicotine", 1.0)],
                  "Nicotine shows a lower Emax in this preparation because of partial efficacy/desensitisation."),
    frog_question("Identify the depolarising nicotinic agonist from its dose-response curve.", "Succinylcholine",
                  FROG_DRUG_OPTIONS, [("Unknown", "Succinylcholine", 1.0)],
                  "Succinylcholine activates nicotinic receptors and then produces depolarising block."),
    frog_question("Which agonist is more potent in the comparison shown?", "Carbachol",
                  FROG_DRUG_OPTIONS, [("Acetylcholine", "Acetylcholine", 1.0),
                                      ("Carbachol", "Carbachol", 1.0)],
                  "The curve further left is more potent; Carbachol has the lower EC50."),
    frog_question("What change is produced by competitive d-Tubocurarine?", "Parallel rightward shift without reduced Emax",
                  ["Parallel rightward shift without reduced Emax", "Leftward shift with higher Emax",
                   "Reduced Emax without shift", "No change in the curve"],
                  [("ACh alone", "Acetylcholine", 1.0), ("ACh + d-Tubocurarine", "Acetylcholine", 8.0)],
                  "A reversible competitive antagonist increases EC50 without changing maximum efficacy."),
    frog_question("Identify the antagonist producing the parallel rightward shift of the ACh curve.", "d-Tubocurarine",
                  ["d-Tubocurarine", "Atropine", "Neostigmine", "Pilocarpine"],
                  [("ACh alone", "Acetylcholine", 1.0), ("ACh + unknown antagonist", "Acetylcholine", 8.0)],
                  "Frog rectus ACh responses are nicotinic and are competitively blocked by d-Tubocurarine."),
    frog_question("The shifted curve reaches the same maximum. What type of antagonism is shown?", "Reversible competitive antagonism",
                  ["Reversible competitive antagonism", "Irreversible antagonism",
                   "Physiological antagonism", "Chemical antagonism"],
                  [("Control", "Acetylcholine", 1.0), ("With antagonist", "Acetylcholine", 10.0)],
                  "A surmountable parallel right shift with unchanged Emax indicates competitive antagonism."),
    frog_question("Which property is represented by the horizontal position of a DRC?", "Potency",
                  ["Potency", "Efficacy", "Intrinsic activity only", "Tissue viability"],
                  [("Drug A", "Acetylcholine", 1.0), ("Drug B", "Carbachol", 1.0)],
                  "Potency is related to EC50 and the horizontal location of the curve."),
    frog_question("Which property is represented by the maximum height of a DRC?", "Efficacy",
                  ["Efficacy", "Potency", "Affinity alone", "Dose ratio"],
                  [("Full agonist", "Acetylcholine", 1.0), ("Partial agonist", "Nicotine", 1.0)],
                  "Emax reflects efficacy; a lower plateau indicates lower maximum effect."),
    frog_question("Why is the Carbachol curve left of the Acetylcholine curve?", "Carbachol has a lower EC50",
                  ["Carbachol has a lower EC50", "Carbachol has zero efficacy",
                   "ACh is an antagonist", "Carbachol blocks nicotinic receptors"],
                  [("ACh", "Acetylcholine", 1.0), ("Carbachol", "Carbachol", 1.0)],
                  "Lower EC50 means a lower concentration is required for half-maximal response."),
    frog_question("After d-Tubocurarine, a higher ACh dose restores the maximum response. What does this show?", "Surmountable antagonism",
                  ["Surmountable antagonism", "Non-surmountable antagonism",
                   "Tachyphylaxis", "Inverse agonism"],
                  [("ACh control", "Acetylcholine", 1.0), ("ACh after d-Tubocurarine", "Acetylcholine", 12.0)],
                  "Competitive blockade can be overcome by increasing agonist concentration."),
]


class FrogRectusExam(BaseCompactExam):
    exam_title = "Frog Rectus Examination – MBBS"
    experiment_name = "Frog Rectus"
    question_bank = FROG_QUESTION_BANK

    def build_visual(self, parent):
        self.figure = Figure(figsize=(7.5, 3.2), dpi=100)
        self.axis = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=parent)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    @staticmethod
    def response_curve(drug_name, shift):
        emax, ec50, hill = FROG_DRUGS[drug_name]
        doses = np.logspace(-8, -3, 100)
        apparent_ec50 = ec50 * shift
        response = emax * doses ** hill / (apparent_ec50 ** hill + doses ** hill)
        return doses, response

    def render_visual(self, question):
        self.axis.clear()
        colors = ["#1769aa", "#d33f49", "#2b8a3e", "#8e44ad"]
        for index, (label, drug, shift) in enumerate(question["curves"]):
            doses, response = self.response_curve(drug, shift)
            self.axis.plot(doses, response, linewidth=2.2, color=colors[index], label=label)
        self.axis.set_xscale("log")
        self.axis.set_ylim(0, 110)
        self.axis.set_xlabel("Molar concentration (log scale)", fontsize=9)
        self.axis.set_ylabel("Response (%)", fontsize=9)
        self.axis.set_title("Frog Rectus Abdominis Dose-Response Curve", fontsize=11)
        self.axis.grid(True, which="both", linestyle="--", alpha=0.2)
        self.axis.legend(fontsize=8)
        self.figure.tight_layout(pad=1.0)
        self.canvas.draw()


def bioassay_question(prompt, answer, options, visual, explanation):
    return {"prompt": prompt, "answer": answer, "options": options,
            "visual": visual, "explanation": explanation}


BIOASSAY_QUESTION_BANK = [
    bioassay_question(
        "Which isolated preparation is used in this acetylcholine bioassay?",
        "Frog rectus abdominis",
        ["Frog rectus abdominis", "Rabbit jejunum", "Rat diaphragm", "Guinea-pig atrium"],
        {"type": "scheme", "text": "Acetylcholine → Frog rectus abdominis → Graded contraction"},
        "Frog rectus abdominis gives a graded nicotinic contraction to acetylcholine.",
    ),
    bioassay_question(
        "What type of response is required for quantitative bioassay?",
        "Graded response",
        ["Graded response", "All-or-none response", "Quantal mortality", "Irreversible response"],
        {"type": "drc"},
        "A continuously graded response permits comparison of standard and test preparations.",
    ),
    bioassay_question(
        "Why must the tissue be washed between successive doses?",
        "To prevent carry-over and restore baseline",
        ["To prevent carry-over and restore baseline", "To increase the test concentration",
         "To permanently sensitise the tissue", "To change a graded response into a quantal response"],
        {"type": "traces", "labels": ["Dose", "Wash", "Dose"], "amplitudes": [24, 2, 35]},
        "Washing removes agonist, restores baseline and reduces cumulative effects or desensitisation.",
    ),
    bioassay_question(
        "An unknown response lies between two standard responses. Which method estimates its concentration?",
        "Interpolation method",
        ["Interpolation method", "End-point method", "Quantal assay", "Up-and-down method"],
        {"type": "traces", "labels": ["S1", "Test", "S2"], "amplitudes": [20, 31, 42]},
        "Interpolation estimates the unknown from its position between bracketing standard responses.",
    ),
    bioassay_question(
        "Why are submaximal responses preferred for the standard curve?",
        "They discriminate changes in dose more clearly",
        ["They discriminate changes in dose more clearly", "They eliminate biological variation",
         "They always produce zero error", "They make washing unnecessary"],
        {"type": "drc", "highlight": "submaximal"},
        "The steep, submaximal portion of the curve is most sensitive to differences in concentration.",
    ),
    bioassay_question(
        "A 0.20 µg/mL standard gives 20 mm, a 0.80 µg/mL standard gives 40 mm, and the test gives 30 mm. Estimate the test concentration by linear interpolation.",
        "0.50 µg/mL",
        ["0.50 µg/mL", "0.30 µg/mL", "0.80 µg/mL", "1.00 µg/mL"],
        {"type": "interpolation"},
        "The test is halfway between the two responses, so its concentration is 0.20 + 0.5 × 0.60 = 0.50 µg/mL.",
    ),
    bioassay_question(
        "What is the defining procedure in the matching method of bioassay?",
        "Adjust the test dose until its response matches the standard",
        ["Adjust the test dose until its response matches the standard",
         "Use two standard and two test doses in every cycle", "Measure mortality at one dose",
         "Plot only the maximum response"],
        {"type": "traces", "labels": ["Standard", "Test"], "amplitudes": [32, 32]},
        "The test dose is adjusted until it produces the same response as a known standard dose.",
    ),
    bioassay_question(
        "Which doses are used in a three-point bioassay?",
        "Two standard doses and one test dose",
        ["Two standard doses and one test dose", "One standard and one test dose",
         "Two standard and two test doses", "Three test doses only"],
        {"type": "traces", "labels": ["S1", "T", "S2"], "amplitudes": [20, 31, 42]},
        "The three-point design brackets one test response between two standard responses.",
    ),
    bioassay_question(
        "Which doses are used in a four-point bioassay?",
        "Two standard doses and two test doses",
        ["Two standard doses and two test doses", "Two standard doses and one test dose",
         "Four standard doses only", "One dose repeated four times"],
        {"type": "traces", "labels": ["S1", "T1", "S2", "T2"], "amplitudes": [18, 22, 38, 43]},
        "The four-point assay compares two dose levels of standard and test and permits a more robust potency estimate.",
    ),
    bioassay_question(
        "What validates comparison by a parallel-line bioassay?",
        "Standard and test log dose-response lines are parallel",
        ["Standard and test log dose-response lines are parallel", "Both preparations have zero response",
         "The test has a lower maximum", "Only one dose is tested"],
        {"type": "parallel"},
        "Parallel slopes support the assumption that standard and test act through the same response system.",
    ),
    bioassay_question(
        "What does the horizontal position of a concentration-response curve mainly reflect?",
        "Potency",
        ["Potency", "Efficacy only", "Tissue weight", "Contact time only"],
        {"type": "drc"},
        "A curve further left requires a lower concentration for a given response and is therefore more potent.",
    ),
    bioassay_question(
        "Why are standard and test doses alternated and repeated?",
        "To reduce error from time-dependent tissue variation",
        ["To reduce error from time-dependent tissue variation", "To avoid using a standard curve",
         "To make the response all-or-none", "To prevent any wash cycle"],
        {"type": "traces", "labels": ["S", "T", "S", "T"], "amplitudes": [29, 31, 30, 30]},
        "Alternation and replication reduce bias from gradual changes in tissue sensitivity.",
    ),
]


class BioassayExam(BaseCompactExam):
    exam_title = "Bioassay Examination – MBBS"
    experiment_name = "Bioassay"
    question_bank = BIOASSAY_QUESTION_BANK

    def build_visual(self, parent):
        self.figure = Figure(figsize=(7.5, 3.2), dpi=100)
        self.axis = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=parent)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def render_visual(self, question):
        visual = question["visual"]
        visual_type = visual["type"]
        self.axis.clear()

        if visual_type == "drc":
            concentrations = np.logspace(-2, 1, 120)
            responses = [BioassaySimulation.expected_response(value) for value in concentrations]
            self.axis.semilogx(concentrations, responses, color="#1769aa", linewidth=2.3)
            if visual.get("highlight") == "submaximal":
                mask = (np.array(responses) >= 10) & (np.array(responses) <= 40)
                self.axis.fill_between(concentrations, 0, responses, where=mask,
                                       color="#d49b16", alpha=0.25,
                                       label="Preferred submaximal range")
                self.axis.legend(fontsize=8)
            self.axis.set_xlabel("Concentration (µg/mL; log scale)")
            self.axis.set_ylabel("Contraction (mm)")
            self.axis.set_title("Graded concentration-response relationship")
        elif visual_type == "interpolation":
            concentrations = [0.20, 0.50, 0.80]
            responses = [20, 30, 40]
            self.axis.plot([0.20, 0.80], [20, 40], "o-", color="#1769aa",
                           linewidth=2, label="Standards")
            self.axis.plot([0.50], [30], "*", color="#a13d2d", markersize=14,
                           label="Unknown response")
            self.axis.axhline(30, color="#a13d2d", linestyle="--", alpha=0.5)
            self.axis.set_xlim(0.1, 0.9)
            self.axis.set_ylim(0, 50)
            self.axis.set_xlabel("Concentration (µg/mL)")
            self.axis.set_ylabel("Response (mm)")
            self.axis.set_title("Interpolation between bracketing standards")
            self.axis.legend(fontsize=8)
        elif visual_type == "parallel":
            log_dose = np.linspace(-2, 1, 80)
            standard = 50 / (1 + np.exp(-2.3 * (log_dose + 0.6)))
            test = 50 / (1 + np.exp(-2.3 * (log_dose - 0.05)))
            self.axis.plot(log_dose, standard, color="#1769aa", linewidth=2,
                           label="Standard")
            self.axis.plot(log_dose, test, color="#a13d2d", linewidth=2,
                           label="Test")
            self.axis.set_xlabel("Log concentration")
            self.axis.set_ylabel("Response (mm)")
            self.axis.set_title("Parallel-line bioassay")
            self.axis.legend(fontsize=8)
        elif visual_type == "scheme":
            self.axis.axis("off")
            self.axis.text(0.5, 0.58, visual["text"], ha="center", va="center",
                           fontsize=15, color="#173b57",
                           bbox=dict(boxstyle="round,pad=0.8", facecolor="#eef4f8",
                                     edgecolor="#1769aa"))
            self.axis.text(0.5, 0.30, "Quantitative comparison of a test preparation with a reference standard",
                           ha="center", fontsize=10, color="#607789")
        else:
            labels = visual["labels"]
            amplitudes = visual["amplitudes"]
            cursor = 0.0
            for index, (label, amplitude) in enumerate(zip(labels, amplitudes)):
                local = np.linspace(0, 30, 100)
                if label.lower() == "wash":
                    curve = max(amplitudes[index - 1], 1) * np.exp(-local / 5)
                    color = "#237032"
                else:
                    curve = amplitude * np.sin(np.pi * local / 30) ** 2
                    color = "#1769aa" if label.startswith("S") or label == "Standard" else "#a13d2d"
                time = local + cursor
                self.axis.plot(time, curve, color=color, linewidth=2)
                self.axis.text(cursor + 15, max(amplitude, 3) + 2, label,
                               ha="center", fontsize=9, color=color)
                cursor += 32
            self.axis.set_xlim(0, cursor)
            self.axis.set_xlabel("Time")
            self.axis.set_ylabel("Contraction (mm)")
            self.axis.set_title("Isolated-tissue response tracing")

        self.axis.set_ylim(bottom=0)
        self.axis.grid(alpha=0.16)
        self.figure.tight_layout(pad=1.0)
        self.canvas.draw()


class CombinedExaminerDashboard:
    """Password-protected result list for all three experiments."""

    def __init__(self, master):
        self.master = master
        if not examiner_password_is_valid(master):
            master.destroy()
            return
        master.title("Pharmacology CAL – Examiner Results")
        set_window_size(master, 1050, 620, 820, 480)
        self.details_by_item = {}
        self.build_screen()
        self.load_results()

    def build_screen(self):
        header = tk.Frame(self.master, bg="#173b57", padx=16, pady=12)
        header.pack(fill="x")
        tk.Label(header, text="Pharmacology CAL Examiner Results", font=("Segoe UI", 18, "bold"),
                 bg="#173b57", fg="white").pack(side="left")
        tk.Label(header, text="MAMC, New Delhi", font=("Segoe UI", 8),
                 bg="#173b57", fg="#a9c3d5").pack(side="right", padx=(8, 0))
        tk.Button(header, text="Refresh", command=self.load_results,
                  bg="#2b8a3e", fg="white", padx=12, pady=4).pack(side="right")
        columns = ("submitted", "experiment", "level", "name", "roll", "score")
        self.tree = ttk.Treeview(self.master, columns=columns, show="headings", height=16)
        headings = {"submitted": "Submitted", "experiment": "Experiment", "level": "Level",
                    "name": "Student", "roll": "Roll No.", "score": "Marks"}
        widths = {"submitted": 150, "experiment": 140, "level": 70,
                  "name": 210, "roll": 120, "score": 80}
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], anchor="center" if column in ("level", "score") else "w")
        self.tree.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=16)
        scrollbar = ttk.Scrollbar(self.master, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="left", fill="y", pady=16)
        side = tk.Frame(self.master, bg="#eef4f8", padx=12)
        side.pack(side="right", fill="y", pady=16)
        tk.Button(side, text="View Answer Review", command=self.view_selected,
                  bg="#1769aa", fg="white", width=20, pady=8).pack(pady=6)
        tk.Button(side, text="Close", command=self.master.destroy,
                  bg="#6c757d", fg="white", width=20, pady=8).pack(pady=6)
        self.tree.bind("<Double-1>", lambda _event: self.view_selected())

    def load_results(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.details_by_item.clear()
        rows = []
        ensure_suite_database()
        with sqlite3.connect(SUITE_DATABASE) as connection:
            for row in connection.execute(
                    "SELECT id, submitted_at, experiment, level, student_name, roll_number, score, total, answer_details FROM results"):
                result_id, submitted, experiment, level, name, roll, score, total, details = row
                rows.append((submitted, f"suite-{result_id}", experiment, level, name, roll, score, total, details))
        if DOG_DATABASE.exists():
            with sqlite3.connect(DOG_DATABASE) as connection:
                try:
                    dog_rows = connection.execute(
                        "SELECT id, submitted_at, student_name, roll_number, level, score, total, answer_details FROM results"
                    ).fetchall()
                except sqlite3.Error:
                    dog_rows = []
            for row in dog_rows:
                result_id, submitted, name, roll, level, score, total, details = row
                rows.append((submitted, f"dog-{result_id}", "Dog BP", level, name, roll, score, total, details))
        rows.sort(key=lambda item: item[0], reverse=True)
        for submitted, item_id, experiment, level, name, roll, score, total, details in rows:
            self.tree.insert("", "end", iid=item_id,
                             values=(submitted, experiment, level, name, roll, f"{score}/{total}"))
            self.details_by_item[item_id] = (experiment, level, name, roll, score, total, details)

    def view_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Select a result", "Select a student result first.", parent=self.master)
            return
        experiment, level, name, roll, score, total, serialized = self.details_by_item[selected[0]]
        details = json.loads(serialized)
        review = tk.Toplevel(self.master)
        review.title(f"Answer Review – {name}")
        set_window_size(review, 880, 650, 720, 500)
        tk.Label(review, text=f"{name} • Roll {roll} • {experiment} ({level}) • Marks {score}/{total}",
                 font=("Segoe UI", 14, "bold"), fg="#173b57", pady=12).pack()
        text = tk.Text(review, wrap="word", font=("Segoe UI", 10), padx=12, pady=10)
        bar = ttk.Scrollbar(review, command=text.yview)
        text.configure(yscrollcommand=bar.set)
        text.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        for index, detail in enumerate(details, 1):
            correct = detail["student_answer"] == detail["correct_answer"]
            text.insert("end", f"Q{index}. {detail['question']}\n")
            text.insert("end", f"Student: {detail['student_answer']}\n")
            text.insert("end", f"Correct: {detail['correct_answer']} ({'Correct' if correct else 'Incorrect'})\n")
            text.insert("end", f"Explanation: {detail['explanation']}\n\n")
        text.config(state="disabled")
