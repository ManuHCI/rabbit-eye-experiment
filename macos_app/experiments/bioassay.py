import tkinter as tk
from tkinter import messagebox, ttk

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from ui.display import set_window_size


class BioassaySimulation:
    """Teaching simulation of ACh bioassay by interpolation."""

    STANDARD_CONCENTRATIONS = (0.10, 0.20, 0.40, 0.80, 1.60, 3.20)
    UNKNOWN_CHOICES = (0.30, 0.50, 0.65, 1.00, 1.25, 2.00)
    EMAX_MM = 50.0
    EC50 = 0.72
    HILL_COEFFICIENT = 1.35

    NAVY = "#173b57"
    BLUE = "#1769aa"
    GREEN = "#237032"
    RED = "#a13d2d"
    GOLD = "#d49b16"
    BG = "#eef4f8"
    CARD = "#ffffff"
    TEXT = "#20394d"
    MUTED = "#607789"

    def __init__(self, master):
        self.master = master
        self.master.title("Bioassay of Acetylcholine – Teaching Laboratory")
        set_window_size(master, 1220, 720, 900, 600, margin_x=70, margin_y=100)
        master.configure(bg=self.BG)

        self.rng = np.random.default_rng()
        self.unknown_concentration = 0.0
        self.records = []
        self.trace_segments = []
        self.time_cursor = 0.0
        self.is_washed = True
        self.current_peak = 0.0
        self.trial_number = 0

        self.build_interface()
        self.reset_experiment(confirm=False)

    @classmethod
    def expected_response(cls, concentration):
        concentration = max(float(concentration), 0.0)
        numerator = cls.EMAX_MM * concentration ** cls.HILL_COEFFICIENT
        denominator = cls.EC50 ** cls.HILL_COEFFICIENT + concentration ** cls.HILL_COEFFICIENT
        return numerator / denominator if denominator else 0.0

    def build_interface(self):
        header = tk.Frame(self.master, bg=self.NAVY, padx=20, pady=12)
        header.pack(fill="x")
        tk.Label(
            header, text="BIOASSAY OF ACETYLCHOLINE",
            font=("Segoe UI", 19, "bold"), bg=self.NAVY, fg="white",
        ).pack(anchor="w")
        tk.Label(
            header,
            text="Interpolation method • Frog rectus abdominis preparation • Teaching laboratory",
            font=("Segoe UI", 10), bg=self.NAVY, fg="#cfe2f3",
        ).pack(anchor="w", pady=(3, 0))
        tk.Label(header, text="MAMC, New Delhi", font=("Segoe UI", 8),
                 bg=self.NAVY, fg="#a9c3d5").place(relx=1.0, rely=0.0,
                                                    anchor="ne")

        body = tk.Frame(self.master, bg=self.BG, padx=12, pady=12)
        body.pack(fill="both", expand=True)

        self.control_panel = tk.Frame(
            body, bg=self.CARD, width=310,
            highlightbackground="#cbd8e2", highlightthickness=1,
        )
        self.control_panel.pack(side="left", fill="y", padx=(0, 10))
        self.control_panel.pack_propagate(False)
        self.build_control_panel()

        workspace = tk.Frame(body, bg=self.BG)
        workspace.pack(side="right", fill="both", expand=True)
        self.build_workspace(workspace)

    def section_heading(self, parent, text):
        tk.Label(parent, text=text, font=("Segoe UI", 10, "bold"),
                 bg=self.CARD, fg=self.NAVY).pack(anchor="w", padx=14, pady=(13, 5))

    def build_control_panel(self):
        self.section_heading(self.control_panel, "OBJECTIVE")
        tk.Label(
            self.control_panel,
            text="Estimate the concentration of an unknown acetylcholine solution by comparing its graded contraction with standard responses.",
            font=("Segoe UI", 9), bg=self.CARD, fg=self.TEXT,
            justify="left", wraplength=275,
        ).pack(fill="x", padx=14)

        self.section_heading(self.control_panel, "EXPERIMENTAL CONDITIONS")
        conditions = (
            ("Preparation", "Frog rectus abdominis"),
            ("Agonist", "Acetylcholine"),
            ("Bath fluid", "Frog Ringer solution"),
            ("Temperature", "25 ± 1 °C"),
            ("Contact time", "90 seconds"),
            ("Method", "Interpolation bioassay"),
        )
        grid = tk.Frame(self.control_panel, bg="#f4f8fb", padx=10, pady=8)
        grid.pack(fill="x", padx=14)
        for row, (label, value) in enumerate(conditions):
            tk.Label(grid, text=label, font=("Segoe UI", 8, "bold"),
                     bg="#f4f8fb", fg=self.MUTED).grid(row=row, column=0, sticky="w", pady=2)
            tk.Label(grid, text=value, font=("Segoe UI", 8),
                     bg="#f4f8fb", fg=self.TEXT).grid(row=row, column=1, sticky="w", padx=(9, 0), pady=2)

        self.section_heading(self.control_panel, "ADMINISTER SOLUTION")
        form = tk.Frame(self.control_panel, bg=self.CARD)
        form.pack(fill="x", padx=14)
        tk.Label(form, text="Solution", font=("Segoe UI", 9),
                 bg=self.CARD, fg=self.TEXT).grid(row=0, column=0, sticky="w", pady=4)
        self.solution_var = tk.StringVar(value="Standard")
        self.solution_box = ttk.Combobox(
            form, textvariable=self.solution_var, values=("Standard", "Unknown test"),
            state="readonly", width=18,
        )
        self.solution_box.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=4)
        self.solution_box.bind("<<ComboboxSelected>>", self.update_solution_controls)

        tk.Label(form, text="Standard", font=("Segoe UI", 9),
                 bg=self.CARD, fg=self.TEXT).grid(row=1, column=0, sticky="w", pady=4)
        self.standard_var = tk.StringVar(value=f"{self.STANDARD_CONCENTRATIONS[0]:.2f}")
        self.standard_box = ttk.Combobox(
            form, textvariable=self.standard_var,
            values=tuple(f"{value:.2f}" for value in self.STANDARD_CONCENTRATIONS),
            state="readonly", width=18,
        )
        self.standard_box.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=4)
        tk.Label(form, text="µg/mL", font=("Segoe UI", 8),
                 bg=self.CARD, fg=self.MUTED).grid(row=2, column=1, sticky="w", padx=(8, 0))
        form.grid_columnconfigure(1, weight=1)

        buttons = tk.Frame(self.control_panel, bg=self.CARD)
        buttons.pack(fill="x", padx=14, pady=(9, 0))
        tk.Button(
            buttons, text="Administer", command=self.administer_solution,
            bg=self.BLUE, fg="white", activebackground="#125486",
            font=("Segoe UI", 10, "bold"), padx=10, pady=6,
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(
            buttons, text="Wash tissue", command=self.wash_tissue,
            bg=self.GREEN, fg="white", activebackground="#1b5b29",
            font=("Segoe UI", 10, "bold"), padx=10, pady=6,
        ).pack(side="left", fill="x", expand=True, padx=(4, 0))

        actions = tk.Frame(self.control_panel, bg=self.CARD)
        actions.pack(fill="x", padx=14, pady=9)
        tk.Button(
            actions, text="Estimate unknown", command=self.estimate_unknown,
            bg=self.GOLD, fg="#17202a", font=("Segoe UI", 9, "bold"), pady=6,
        ).pack(fill="x", pady=(0, 5))
        tk.Button(
            actions, text="Reset experiment", command=self.reset_experiment,
            bg="#6c757d", fg="white", font=("Segoe UI", 9), pady=5,
        ).pack(fill="x")

        self.section_heading(self.control_panel, "TEACHING NOTE")
        self.teaching_note = tk.Label(
            self.control_panel, text="", font=("Segoe UI", 9), bg="#fff8e1",
            fg="#594a18", justify="left", wraplength=275, padx=10, pady=9,
        )
        self.teaching_note.pack(fill="x", padx=14, pady=(0, 12))

    def build_workspace(self, parent):
        figure_card = tk.Frame(parent, bg=self.CARD,
                               highlightbackground="#cbd8e2", highlightthickness=1)
        figure_card.pack(fill="both", expand=True)
        self.figure = Figure(figsize=(8.4, 5.0), dpi=100)
        self.trace_axis = self.figure.add_subplot(211)
        self.drc_axis = self.figure.add_subplot(212)
        self.canvas = FigureCanvasTkAgg(self.figure, master=figure_card)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        record_card = tk.Frame(parent, bg=self.CARD,
                               highlightbackground="#cbd8e2", highlightthickness=1)
        record_card.pack(fill="x", pady=(9, 0))
        top = tk.Frame(record_card, bg=self.CARD, padx=10, pady=6)
        top.pack(fill="x")
        tk.Label(top, text="OBSERVATION TABLE", font=("Segoe UI", 10, "bold"),
                 bg=self.CARD, fg=self.NAVY).pack(side="left")
        self.result_label = tk.Label(top, text="Unknown concentration: Not estimated",
                                     font=("Segoe UI", 9, "bold"), bg=self.CARD,
                                     fg=self.RED)
        self.result_label.pack(side="right")

        columns = ("trial", "solution", "concentration", "response", "wash")
        self.record_table = ttk.Treeview(record_card, columns=columns, show="headings", height=5)
        headings = {
            "trial": "Trial", "solution": "Solution", "concentration": "Concentration",
            "response": "Peak contraction", "wash": "Cycle status",
        }
        widths = {"trial": 65, "solution": 155, "concentration": 145,
                  "response": 145, "wash": 135}
        for column in columns:
            self.record_table.heading(column, text=headings[column])
            self.record_table.column(column, width=widths[column], anchor="center")
        self.record_table.pack(fill="x", padx=10, pady=(0, 9))

    def update_solution_controls(self, _event=None):
        if self.solution_var.get() == "Standard":
            self.standard_box.config(state="readonly")
        else:
            self.standard_box.config(state="disabled")

    def measured_response(self, concentration):
        expected = self.expected_response(concentration)
        variation = self.rng.normal(0.0, 0.75)
        return float(np.clip(expected + variation, 0.0, self.EMAX_MM))

    def contraction_segment(self, peak):
        local_time = np.linspace(0, 90, 181)
        response = np.zeros_like(local_time)
        rise = (local_time >= 5) & (local_time < 30)
        plateau = local_time >= 30
        response[rise] = peak * (1 - np.exp(-(local_time[rise] - 5) / 7.0))
        response[plateau] = peak + 0.25 * np.sin(local_time[plateau] / 4.0)
        response += self.rng.normal(0.0, 0.08, size=response.shape)
        return local_time, np.clip(response, 0.0, None)

    def administer_solution(self):
        if not self.is_washed:
            messagebox.showwarning(
                "Wash required",
                "Wash the tissue and allow the tracing to return to baseline before the next dose.",
                parent=self.master,
            )
            return

        is_standard = self.solution_var.get() == "Standard"
        if is_standard:
            concentration = float(self.standard_var.get())
            label = f"Standard {concentration:.2f} µg/mL"
            solution = "Standard"
            display_concentration = f"{concentration:.2f} µg/mL"
        else:
            concentration = self.unknown_concentration
            label = "Unknown test"
            solution = "Unknown test"
            display_concentration = "Unknown"

        response = self.measured_response(concentration)
        local_time, contraction = self.contraction_segment(response)
        shifted_time = local_time + self.time_cursor
        self.trace_segments.append({
            "time": shifted_time, "response": contraction,
            "label": label, "color": self.BLUE if is_standard else self.RED,
        })
        self.time_cursor = float(shifted_time[-1])
        self.current_peak = response
        self.is_washed = False
        self.trial_number += 1
        self.records.append({
            "trial": self.trial_number, "solution": solution,
            "concentration": concentration, "display_concentration": display_concentration,
            "response": response, "washed": False,
        })
        self.refresh_table()
        self.refresh_graphs()
        if is_standard:
            self.teaching_note.config(
                text="A graded standard response has been recorded. Wash the preparation, then continue in ascending concentration order."
            )
        else:
            self.teaching_note.config(
                text="The unknown response is recorded without revealing its concentration. Compare it with the bracketing standards."
            )

    def wash_tissue(self):
        if self.is_washed:
            messagebox.showinfo("Wash", "The tissue is already at baseline.", parent=self.master)
            return
        local_time = np.linspace(0, 45, 91)
        relaxation = self.current_peak * np.exp(-local_time / 9.0)
        shifted_time = local_time + self.time_cursor
        self.trace_segments.append({
            "time": shifted_time, "response": relaxation,
            "label": "Wash", "color": self.GREEN,
        })
        self.time_cursor = float(shifted_time[-1]) + 10.0
        self.current_peak = 0.0
        self.is_washed = True
        if self.records:
            self.records[-1]["washed"] = True
        self.refresh_table()
        self.refresh_graphs()
        self.teaching_note.config(
            text="Washing removes acetylcholine and restores baseline. A consistent dose cycle reduces carry-over and desensitisation."
        )

    def estimate_unknown(self):
        standards = [record for record in self.records if record["solution"] == "Standard"]
        tests = [record for record in self.records if record["solution"] == "Unknown test"]
        distinct = sorted({record["concentration"] for record in standards})
        if len(distinct) < 4 or not tests:
            messagebox.showwarning(
                "Insufficient observations",
                "Record at least four different standard concentrations and one unknown response before estimating.",
                parent=self.master,
            )
            return

        standard_points = []
        for concentration in distinct:
            responses = [record["response"] for record in standards
                         if record["concentration"] == concentration]
            standard_points.append((concentration, float(np.mean(responses))))
        standard_points.sort(key=lambda point: point[1])
        responses = np.array([point[1] for point in standard_points])
        concentrations = np.array([point[0] for point in standard_points])
        test_response = float(np.mean([record["response"] for record in tests]))
        estimated = float(np.interp(test_response, responses, concentrations))
        percentage_error = abs(estimated - self.unknown_concentration) / self.unknown_concentration * 100

        self.estimated_concentration = estimated
        self.result_label.config(
            text=f"Estimated unknown: {estimated:.3f} µg/mL", fg=self.GREEN
        )
        self.teaching_note.config(
            text=(f"Interpolation result: {estimated:.3f} µg/mL. "
                  f"Teaching reference value: {self.unknown_concentration:.3f} µg/mL; "
                  f"error {percentage_error:.1f}%.")
        )
        self.refresh_graphs()
        messagebox.showinfo(
            "Bioassay result",
            f"Estimated unknown concentration: {estimated:.3f} µg/mL\n"
            f"Reference concentration: {self.unknown_concentration:.3f} µg/mL\n"
            f"Percentage error: {percentage_error:.1f}%",
            parent=self.master,
        )

    def refresh_table(self):
        for item in self.record_table.get_children():
            self.record_table.delete(item)
        for record in self.records[-12:]:
            self.record_table.insert(
                "", "end",
                values=(
                    record["trial"], record["solution"], record["display_concentration"],
                    f"{record['response']:.1f} mm",
                    "Washed" if record["washed"] else "Wash required",
                ),
            )

    def refresh_graphs(self):
        self.trace_axis.clear()
        for segment in self.trace_segments:
            self.trace_axis.plot(segment["time"], segment["response"],
                                 color=segment["color"], linewidth=1.8)
            if segment["label"] != "Wash":
                self.trace_axis.annotate(
                    segment["label"],
                    xy=(segment["time"][5], max(segment["response"]) * 0.15 + 1),
                    fontsize=7, color=segment["color"], rotation=20,
                )
        self.trace_axis.set_title("Continuous isotonic contraction tracing", fontsize=10, color=self.NAVY)
        self.trace_axis.set_xlabel("Time (seconds)", fontsize=8)
        self.trace_axis.set_ylabel("Contraction (mm)", fontsize=8)
        self.trace_axis.set_ylim(0, 55)
        self.trace_axis.grid(alpha=0.15)

        self.drc_axis.clear()
        standards = [record for record in self.records if record["solution"] == "Standard"]
        if standards:
            concentrations = sorted({record["concentration"] for record in standards})
            mean_responses = [
                np.mean([record["response"] for record in standards
                         if record["concentration"] == concentration])
                for concentration in concentrations
            ]
            self.drc_axis.semilogx(concentrations, mean_responses, "o-",
                                   color=self.BLUE, linewidth=1.8, label="Standards")
        tests = [record for record in self.records if record["solution"] == "Unknown test"]
        if tests and hasattr(self, "estimated_concentration"):
            mean_test = np.mean([record["response"] for record in tests])
            self.drc_axis.semilogx([self.estimated_concentration], [mean_test], "*",
                                   color=self.RED, markersize=11, label="Interpolated unknown")
        self.drc_axis.set_title("Standard concentration-response curve", fontsize=10, color=self.NAVY)
        self.drc_axis.set_xlabel("Acetylcholine concentration (µg/mL; log scale)", fontsize=8)
        self.drc_axis.set_ylabel("Peak response (mm)", fontsize=8)
        self.drc_axis.set_ylim(0, 55)
        self.drc_axis.grid(True, which="both", alpha=0.15)
        if standards or tests:
            self.drc_axis.legend(fontsize=7, loc="lower right")
        self.figure.tight_layout(pad=1.2)
        self.canvas.draw()

    def reset_experiment(self, confirm=True):
        if confirm and self.records and not messagebox.askyesno(
                "Reset experiment", "Clear all observations and prepare a new unknown?",
                parent=self.master):
            return
        self.unknown_concentration = float(self.rng.choice(self.UNKNOWN_CHOICES))
        self.records = []
        self.trace_segments = []
        self.time_cursor = 0.0
        self.is_washed = True
        self.current_peak = 0.0
        self.trial_number = 0
        if hasattr(self, "estimated_concentration"):
            del self.estimated_concentration
        self.solution_var.set("Standard")
        self.standard_var.set(f"{self.STANDARD_CONCENTRATIONS[0]:.2f}")
        self.standard_box.config(state="readonly")
        self.result_label.config(text="Unknown concentration: Not estimated", fg=self.RED)
        self.teaching_note.config(
            text="Begin with ascending submaximal standards. Wash after every dose, then administer the unknown between two bracketing standards."
        )
        self.refresh_table()
        self.refresh_graphs()
