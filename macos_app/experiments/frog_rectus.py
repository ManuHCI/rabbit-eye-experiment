import tkinter as tk
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from ui.display import set_window_size
from ui.branding import add_corner_attribution


class FrogRectusSimulation:

    def __init__(self, master):
        self.master = master
        self.master.title("Frog Rectus Abdominis – Organ Bath Simulation")
        set_window_size(self.master, 1000, 820, 820, 600)

        # Practical doses (can be extended later)
        self.doses = [0.05, 0.1, 0.2, 0.4, 0.8]

        # State
        self.time_offset = 0
        self.t = np.linspace(0, 10, 300)
        self.recorded = []   # (mode, dose, peak)

        # Figure
        self.fig = Figure(figsize=(7.5, 5), dpi=100)
        self.ax = self.fig.add_subplot(111)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.master)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.setup_controls()
        self.setup_plot()
        add_corner_attribution(self.master, bg="#f0f0f0", fg="#607789")

    # ---------------- PLOT SETUP ----------------

    def setup_plot(self):
        self.ax.clear()
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Contraction (mm)")
        self.ax.set_title("Frog Rectus Abdominis – Organ Bath Tracing")
        self.ax.set_ylim(0, 75)
        self.canvas.draw()

    # ---------------- PHYSIOLOGY ----------------

    def contraction_curve(self, dose, mode):
        base_peak = 12 + 40 * (dose / max(self.doses))

        if mode == "ACh":
            peak = base_peak
        elif mode == "Physostigmine":
            peak = base_peak * 1.3
        else:  # d-Tubocurarine
            peak = base_peak * 0.6

        return peak * np.exp(-((self.t - 4) ** 2) / 1.5)

    # ---------------- ADMINISTER ----------------

    def administer(self):
        dose = float(self.dose_var.get())
        mode = self.mode_var.get()

        curve = self.contraction_curve(dose, mode)

        color_map = {
            "ACh": "red",
            "Physostigmine": "blue",
            "d-Tubocurarine": "green"
        }

        self.ax.plot(
            self.t + self.time_offset,
            curve,
            color=color_map[mode],
            linewidth=2,
            label=f"{mode} – {dose} ml"
        )

        self.time_offset += 12
        self.ax.legend(fontsize=8)
        self.canvas.draw()

        peak = np.max(curve)
        self.recorded.append((mode, dose, peak))
        self.update_table()

    # ---------------- TABLE ----------------

    def update_table(self):
        self.table.delete(0, tk.END)
        for m, d, p in self.recorded:
            self.table.insert(
                tk.END,
                f"{m:<15}  Dose {d:<4} ml  →  {p:.1f} mm"
            )

    # ---------------- STUDENT DRC ----------------

    def plot_drc(self):
        if not self.recorded:
            return

        drc = tk.Toplevel(self.master)
        drc.title("Log Dose Response Curve")

        fig = Figure(figsize=(6, 5), dpi=100)
        ax = fig.add_subplot(111)

        colors = {
            "ACh": "red",
            "Physostigmine": "blue",
            "d-Tubocurarine": "green"
        }

        for mode in ["ACh", "Physostigmine", "d-Tubocurarine"]:
            data = [(d, p) for m, d, p in self.recorded if m == mode]
            if not data:
                continue

            doses, responses = zip(*data)
            responses = np.array(responses) / max(responses) * 100

            ax.plot(doses, responses, marker="o",
                    color=colors[mode], label=mode)

        ax.set_xscale("log")
        ax.set_xlabel("Log Dose of ACh")
        ax.set_ylabel("% Response")
        ax.set_title("Log Dose Response Curve – Frog Rectus")
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.5)

        canvas = FigureCanvasTkAgg(fig, master=drc)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        canvas.draw()

    # ---------------- STANDARD (EXAM) DRC ----------------

    def plot_standard_frog_rectus_drc(self):
        drc = tk.Toplevel(self.master)
        drc.title("Standard Frog Rectus DRC (Exam Graph)")

        doses = np.array([0.02, 0.05, 0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4])

        ach  = np.array([0, 5, 8, 15, 27, 36, 45, 47, 47])
        phys = np.array([5, 8, 15, 27, 36, 45, 47, 47, 47])
        dtc  = np.array([0, 0, 5, 8, 15, 27, 36, 45, 47])

        ach_pct  = ach  / ach.max()  * 100
        phys_pct = phys / phys.max() * 100
        dtc_pct  = dtc  / dtc.max()  * 100

        fig = Figure(figsize=(7, 5), dpi=100)
        ax = fig.add_subplot(111)

        ax.set_xscale("log")
        ax.plot(doses, ach_pct,  "o-r", label="ACh alone")
        ax.plot(doses, phys_pct, "s-b", label="Physostigmine + ACh")
        ax.plot(doses, dtc_pct,  "^-g", label="d-Tubocurarine + ACh")

        ax.set_xlabel("Log Dose of Acetylcholine (ml)")
        ax.set_ylabel("% Response")
        ax.set_title("Log Dose Response Curve – Frog Rectus Abdominis")
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.5)

        canvas = FigureCanvasTkAgg(fig, master=drc)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        canvas.draw()

    # ---------------- CONTROLS ----------------

    def setup_controls(self):
        top = tk.Frame(self.master)
        top.pack(pady=10)

        self.mode_var = tk.StringVar(value="ACh")
        self.dose_var = tk.StringVar(value="0.05")

        tk.Label(top, text="Select Drug:").grid(row=0, column=0, padx=5)
        tk.OptionMenu(
            top, self.mode_var,
            "ACh", "Physostigmine", "d-Tubocurarine"
        ).grid(row=0, column=1)

        tk.Label(top, text="Select Dose (ml):").grid(row=0, column=2, padx=5)
        tk.OptionMenu(
            top, self.dose_var, *map(str, self.doses)
        ).grid(row=0, column=3)

        tk.Button(
            top, text="Administer",
            bg="#2ecc71", width=15,
            command=self.administer
        ).grid(row=0, column=4, padx=10)

        tk.Button(
            top, text="Plot Dose Response Curve",
            bg="#3498db", width=22,
            command=self.plot_drc
        ).grid(row=0, column=5, padx=10)

        tk.Button(
            top,
            text="Show Standard DRC (Exam Graph)",
            bg="#8e44ad",
            fg="white",
            width=28,
            command=self.plot_standard_frog_rectus_drc
        ).grid(row=1, column=0, columnspan=6, pady=10)

        self.table = tk.Listbox(
            self.master,
            height=7,
            font=("Courier", 11)
        )
        self.table.pack(pady=10)
