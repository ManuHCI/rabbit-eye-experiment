import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import os
import shutil
import subprocess
import sys
from PIL import Image, ImageTk

from experiments.dog_bp import DogBPSimulation
from experiments.dog_bp_exam import DogBPExamMode
from experiments.bioassay import BioassaySimulation
from experiments.frog_rectus import FrogRectusSimulation
from experiments.rabbit_eye_practical import RabbitEyeApp
from experiments.combined_exams import (
    RabbitEyeExam,
    FrogRectusExam,
    BioassayExam,
    CombinedExaminerDashboard,
)
from ui.display import (
    configure_application_display,
    enable_high_dpi,
    set_window_size,
)


def resource_path(*parts):
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent
    return base.joinpath(*parts)

class ExperimentApp:
    def __init__(self, root, credits=None):
        self.root = root
        self.credits = credits or {
            "developer": "Designed and developed by",
            "developer_name": "Dr. Manu Kumar Shetty",
            "developer_title": "Professor of Pharmacology",
            "ai_credit": "with assistance from generative AI tools",
            "contributors": "Contributed by the Faculties of the Department of Pharmacology",
            "organization": "Maulana Azad Medical College, New Delhi  -  Academic Year 2025-26",
            "funding": "Funded by MRU, MAMC  -  Nodal Officer: Dr. Bhupinder Kalra",
        }
        configure_application_display(self.root)
        self.root.title("Virtual Pharmacology Laboratory for macOS")
        # Keep the landing page compact enough for smaller laptop displays.
        # The window-sizing helper clamps this to the available screen height.
        set_window_size(self.root, 920, 760, 700, 600, margin_x=120, margin_y=70)
        self.root.config(bg="#e6f3ff")
        self.show_landing_page()
            
    def show_landing_page(self):
        # Color palette and fonts
        primary_color = "#3498db"
        secondary_color = "#2ecc71"
        accent_color = "#9b59b6"
        text_dark = "#2c3e50"
        text_light = "#ecf0f1"
        bg_color = "#f5f9fc"
        
        for widget in self.root.pack_slaves():
            widget.pack_forget()
        self.root.configure(bg=bg_color)
        main_frame = tk.Frame(self.root, bg=bg_color, padx=20, pady=10)
        main_frame.pack(fill="both", expand=True)
        
        # A neutral CAL emblem replaces the large institutional logo so the
        # public edition has an inclusive, recognisable visual identity.
        emblem = tk.Canvas(main_frame, width=104, height=104, bg=bg_color,
                           highlightthickness=0)
        emblem.pack(pady=(8, 2))
        emblem.create_oval(8, 8, 96, 96, fill="#173b57", outline=primary_color, width=4)
        emblem.create_text(52, 45, text="CAL", font=("Segoe UI", 22, "bold"),
                           fill="white")
        emblem.create_text(52, 70, text="PHARMACOLOGY", font=("Segoe UI", 7, "bold"),
                           fill="#bfe3ff")
        
        title_frame = tk.Frame(main_frame, bg=bg_color)
        title_frame.pack(pady=4)
        college_label = tk.Label(title_frame, text="COMPUTER-ASSISTED LEARNING",
                                  font=("Segoe UI", 24, "bold"), fg=primary_color, bg=bg_color)
        college_label.pack()
        separator = tk.Frame(title_frame, height=2, width=400, bg=secondary_color)
        separator.pack(pady=6)
        dept_label = tk.Label(title_frame, text="Virtual Pharmacology Laboratory",
                              font=("Segoe UI", 18, "bold"), fg=accent_color, bg=bg_color)
        dept_label.pack(pady=(5, 0))
        cal_frame = tk.Frame(title_frame, bg=secondary_color, padx=15, pady=7)
        cal_frame.pack(pady=8)
        cal_label = tk.Label(
            cal_frame,
            text="Interactive simulations, practical exercises and assessments for medical education",
            font=("Segoe UI", 11, "bold"), fg=text_light, bg=secondary_color,
        )
        cal_label.pack()
        
        designed_frame = tk.Frame(main_frame, bg=bg_color)
        designed_frame.pack(pady=4)
        designed_label = tk.Label(
            designed_frame,
            text=(
                f'{self.credits["developer"]}\n'
                f'{self.credits["developer_name"]}\n'
                f'{self.credits["developer_title"]}\n'
                f'{self.credits["ai_credit"]}'
            ),
            justify="center",
            font=("Georgia", 11, "italic"),
            fg=text_dark,
            bg=bg_color,
        )
        designed_label.pack(pady=2)

        credits_frame = tk.Frame(main_frame, bg=bg_color)
        credits_frame.pack(pady=3)
        credits = "\n".join(
            (
                self.credits["contributors"],
                self.credits["organization"],
                self.credits["funding"],
            )
        )
        tk.Label(
            credits_frame,
            text=credits,
            justify="center",
            wraplength=760,
            font=("Segoe UI", 10),
            fg=text_dark,
            bg=bg_color,
        ).pack()

        button_frame = tk.Frame(main_frame, bg=bg_color)
        button_frame.pack(pady=10)
        enter_button = tk.Button(button_frame, text="EXPLORE LEARNING MODULES", font=("Segoe UI", 14, "bold"),
                                 bg=secondary_color, fg=text_light,
                                 activebackground=primary_color, activeforeground=text_light,
                                 relief="raised", bd=2, padx=20, pady=10, cursor="hand2",
                                 command=self.show_main_menu)
        enter_button.pack()
        enter_button.bind("<Enter>", lambda e: enter_button.config(bg=primary_color))
        enter_button.bind("<Leave>", lambda e: enter_button.config(bg=secondary_color))
        
        footer_frame = tk.Frame(self.root, bg=text_dark)
        footer_frame.pack(side="bottom", fill="x")
        version_label = tk.Label(footer_frame, text="macOS Public Beta  •  Version 1.0  •  MAMC, New Delhi",
                                 font=("Segoe UI", 8), fg=text_light, bg=text_dark, pady=5)
        version_label.pack()

    def clear_root(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def page_header(self, title, subtitle, back_command=None):
        header = tk.Frame(self.root, bg="#173b57", padx=20, pady=13)
        header.pack(fill="x")
        if back_command:
            tk.Button(header, text="‹ Back", command=back_command,
                      font=("Segoe UI", 10, "bold"), bg="#173b57", fg="white",
                      activebackground="#245779", activeforeground="white",
                      relief="flat", cursor="hand2").pack(side="left", padx=(0, 18))
        text = tk.Frame(header, bg="#173b57")
        text.pack(side="left")
        tk.Label(text, text=title, font=("Segoe UI", 19, "bold"),
                 bg="#173b57", fg="white").pack(anchor="w")
        tk.Label(text, text=subtitle, font=("Segoe UI", 9),
                 bg="#173b57", fg="#cfe2f3").pack(anchor="w", pady=(2, 0))
        tk.Label(header, text="MAMC, New Delhi", font=("Segoe UI", 8),
                 bg="#173b57", fg="#a9c3d5").pack(side="right", anchor="ne")

    def module_card(self, parent, row, column, title, subtitle, color, command):
        card = tk.Frame(parent, bg="white", padx=18, pady=15,
                        highlightbackground="#cbd8e2", highlightthickness=1)
        card.grid(row=row, column=column, sticky="nsew", padx=8, pady=8)
        accent = tk.Frame(card, bg=color, width=6)
        accent.pack(side="left", fill="y", padx=(0, 13))
        content = tk.Frame(card, bg="white")
        content.pack(side="left", fill="both", expand=True)
        tk.Label(content, text=title, font=("Segoe UI", 13, "bold"),
                 bg="white", fg="#173b57").pack(anchor="w")
        tk.Label(content, text=subtitle, font=("Segoe UI", 9),
                 bg="white", fg="#607789", wraplength=270,
                 justify="left").pack(anchor="w", pady=(4, 9))
        tk.Button(content, text="Open module", command=command,
                  font=("Segoe UI", 9, "bold"), bg=color, fg="white",
                  activebackground=color, activeforeground="white",
                  relief="flat", padx=12, pady=5, cursor="hand2").pack(anchor="w")
        return card

    def show_main_menu(self):
        self.clear_root()
        self.root.configure(bg="#eef4f8")
        self.page_header(
            "Virtual Pharmacology Laboratory",
            "Computer-assisted learning in experimental pharmacology",
        )
        body = tk.Frame(self.root, bg="#eef4f8", padx=28, pady=24)
        body.pack(fill="both", expand=True)
        tk.Label(body, text="LEARNING PORTAL", font=("Segoe UI", 10, "bold"),
                 bg="#eef4f8", fg="#607789").pack(anchor="w", pady=(0, 10))
        grid = tk.Frame(body, bg="#eef4f8")
        grid.pack(fill="both", expand=True)
        self.module_card(grid, 0, 0, "Theory & Principles",
                         "Review pharmacological concepts and experimental foundations.",
                         "#607d8b", self.show_theory)
        self.module_card(grid, 0, 1, "Teaching Practicals",
                         "Run guided simulations with observations, tracings and interpretation.",
                         "#1769aa", self.show_practical_options)
        self.module_card(grid, 1, 0, "Student Examinations",
                         "Attempt randomized MBBS and PG assessments with timed submission.",
                         "#8e44ad", self.show_exam_options)
        self.module_card(grid, 1, 1, "Examiner Results",
                         "Open password-protected marks and answer reviews across experiments.",
                         "#237032", self.launch_examiner_results)
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)
        grid.grid_rowconfigure(0, weight=1)
        grid.grid_rowconfigure(1, weight=1)
        tk.Label(self.root,
                 text="macOS Public Beta  •  Version 1.0  •  MAMC, New Delhi",
                 font=("Segoe UI", 8), bg="#20394d", fg="#dce6ed",
                 pady=6).pack(fill="x", side="bottom")

    def show_message(self, msg):
        messagebox.showinfo("Information", msg)

    def show_exam_options(self):
        self.clear_root()
        self.root.configure(bg="#eef4f8")
        self.page_header(
            "Student Examinations",
            "Practical and knowledge assessments • Marks available only to examiners",
            self.show_main_menu,
        )
        body = tk.Frame(self.root, bg="#eef4f8", padx=24, pady=18)
        body.pack(fill="both", expand=True)
        modules = (
            ("Dog BP – MBBS", "Identify two examiner-selected unknown drugs using the experimental setup.",
             "#1769aa", lambda: self.launch_dog_bp_exam("MBBS")),
            ("Dog BP – PG", "Advanced unknown-drug identification using agonists, blockers and dose response.",
             "#8e44ad", lambda: self.launch_dog_bp_exam("PG")),
            ("Rabbit Eye – MBBS", "Compare paired eyes, reflexes, pupil size and ocular tone.",
             "#d68910", self.launch_rabbit_eye_exam),
            ("Frog Rectus – MBBS", "Interpret DRCs, potency, efficacy and competitive antagonism.",
             "#148f77", self.launch_frog_rectus_exam),
            ("Bioassay – MBBS", "Interpolation, matching, dose cycles and quantitative reasoning.",
             "#a04070", self.launch_bioassay_exam),
            ("Examiner Results", "Password-protected marks and answer review for every module.",
             "#237032", self.launch_examiner_results),
        )
        for index, (title, subtitle, color, command) in enumerate(modules):
            self.module_card(body, index // 2, index % 2, title, subtitle, color, command)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        for row in range(3):
            body.grid_rowconfigure(row, weight=1)

    def exit_program(self):
        self.root.quit()

    def show_theory(self):
        messagebox.showinfo("Theory", 
            "This simulation models:\n"
            "1) Autonomic drug effects on BP/HR in a virtual dog.\n"
            "2) Ocular drug effects in the rabbit eye preparation.\n"
            "3) Frog rectus abdominis organ-bath responses and dose-response curves.\n"
            "4) Bioassay of acetylcholine by interpolation on frog rectus abdominis."
        )

    def show_rabbit_eye_experiment(self):
        exp_win = tk.Toplevel(self.root)
        RabbitEyeApp(exp_win, image_dir=str(resource_path("assets", "rabbit_eye")))
        
    def show_practical_options(self):
        self.clear_root()
        self.root.configure(bg="#eef4f8")
        self.page_header(
            "Teaching Practicals",
            "Guided pharmacology simulations with observation and interpretation",
            self.show_main_menu,
        )
        body = tk.Frame(self.root, bg="#eef4f8", padx=28, pady=24)
        body.pack(fill="both", expand=True)
        modules = (
            ("Dog Blood Pressure",
             "Study agonists, antagonists, cardiovascular responses and receptor blockade.",
             "#1769aa", self.launch_dog_bp_experiment),
            ("Rabbit Eye",
             "Compare drug-treated and saline-control eyes using interactive examination tools.",
             "#d68910", self.show_rabbit_eye_experiment),
            ("Frog Rectus Abdominis",
             "Use the built in organ bath simulator and dose response curve.",
             "#148f77", self.launch_frog_rectus_experiment),
            ("Acetylcholine Bioassay",
             "Estimate an unknown by interpolation using standards, wash cycles and tracings.",
             "#a04070", self.launch_bioassay_experiment),
        )
        for index, (title, subtitle, color, command) in enumerate(modules):
            self.module_card(body, index // 2, index % 2,
                             title, subtitle, color, command)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)
        tk.Label(
            self.root,
            text="Select a preparation to begin the guided practical",
            font=("Segoe UI", 8), bg="#20394d", fg="#dce6ed", pady=6,
        ).pack(fill="x", side="bottom")

    # Helper methods for button hover effects
    def on_practical_button_hover(self, event, button):
        """Change button appearance on hover"""
        text = button['text']
        if "Dog BP" in text:
            button.config(bg="#273c75")
        elif "Bioassay" in text:
            button.config(bg="#a3219f")
        elif "Rabbit Eye" in text:
            button.config(bg="#fa983a")
        elif "Drug Dose" in text:
            button.config(bg="#38ada9")
        elif "Return" in text:
            button.config(bg="#6d1122")
    
    def on_practical_button_leave(self, event, button):
        """Restore button appearance when mouse leaves"""
        text = button['text']
        if "Dog BP" in text:
            button.config(bg="#4a69bd")
        elif "Bioassay" in text:
            button.config(bg="#e84393")
        elif "Rabbit Eye" in text:
            button.config(bg="#f6b93b")
        elif "Drug Dose" in text:
            button.config(bg="#78e08f")
        elif "Return" in text:
            button.config(bg="#b71540")

    def launch_dog_bp_experiment(self):
        exp_win = tk.Toplevel(self.root)
        DogBPSimulation(exp_win)

    def launch_dog_bp_exam(self, level="MBBS"):
        exam_win = tk.Toplevel(self.root)
        DogBPExamMode(exam_win, level=level)

    def launch_examiner_results(self):
        result_win = tk.Toplevel(self.root)
        CombinedExaminerDashboard(result_win)

    def launch_rabbit_eye_exam(self):
        exam_win = tk.Toplevel(self.root)
        RabbitEyeExam(exam_win)

    def launch_frog_rectus_exam(self):
        exam_win = tk.Toplevel(self.root)
        FrogRectusExam(exam_win)

    def launch_bioassay_exam(self):
        exam_win = tk.Toplevel(self.root)
        BioassayExam(exam_win)

    def launch_bioassay_experiment(self):
        exp_win = tk.Toplevel(self.root)
        BioassaySimulation(exp_win)

    def launch_frog_rectus_experiment(self):
        exp_win = tk.Toplevel(self.root)
        FrogRectusSimulation(exp_win)


if __name__ == "__main__":
    enable_high_dpi()
    root = tk.Tk()
    configure_application_display(root)
    app = ExperimentApp(root)
    root.mainloop()
