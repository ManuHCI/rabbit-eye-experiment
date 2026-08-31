import tkinter as tk
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from ui.display import set_window_size
from ui.branding import add_corner_attribution

class DogBPSimulation:
    WINDOW_DURATION = 240  # seconds

    def __init__(self, master):
        self.master = master
        self.master.title("Dog BP Simulation Experiment")
        set_window_size(self.master, 1000, 820, 820, 620)
        self.master.config(bg="#f0f8ff")

        # Baseline simulation parameters
        self.baseline_map = 120  # mmHg
        self.baseline_hr = 72    # bpm
        self.current_explanation = "Baseline state. No drug administered."
        self.injection_history = []
        self.current_offset = 0

        # Setup Matplotlib figure and initial plot
        self.fig = Figure(figsize=(7, 5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.setup_initial_plot()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.master)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas.draw()

        # Setup control panels and labels
        self.setup_controls()
        add_corner_attribution(self.master, bg="#f0f8ff", fg="#607789")

    def setup_initial_plot(self):
        self.ax.clear()
        self.ax.set_xlim(0, self.WINDOW_DURATION)
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("BP (mmHg)", color="blue")
        self.ax.set_ylim(80, 180)
        # Create a twin y-axis for pulse
        self.ax2 = self.ax.twinx()
        self.ax2.set_ylabel("Pulse (bpm)", color="red")
        self.ax2.set_ylim(40, 140)
        # Plot baseline lines
        self.ax.plot([0, self.WINDOW_DURATION], [self.baseline_map, self.baseline_map], 'k--')
        self.ax2.plot([0, self.WINDOW_DURATION], [self.baseline_hr, self.baseline_hr], 'k:')
        self.ax.set_title("Continuous Dog BP and Pulse Simulation")

    @staticmethod
    def gaussian(t, center, width):
        return np.exp(-((t - center)**2) / (2 * width**2))

    def simulate_drug_effect(self, drug, dose, t, previous_map=None, previous_hr=None):
        noise_map = np.random.normal(0, 0.5, size=t.shape)
        noise_hr  = np.random.normal(0, 0.5, size=t.shape)
        if previous_map is None or previous_hr is None:
            previous_map = np.full_like(t, self.baseline_map)
            previous_hr = np.full_like(t, self.baseline_hr)

        # Determine receptor states based on previous injections
        alpha_blocked = "Phenoxybenzamine" in [e["drug"] for e in self.injection_history]
        beta_blocked = "Propranolol" in [e["drug"] for e in self.injection_history]
        muscarinic_blocked = "Atropine" in [e["drug"] for e in self.injection_history]

        # Handle antagonists
        if drug == "Phenoxybenzamine":
            map_effect = -15 * dose * self.gaussian(t, center=10, width=4)
            hr_effect = +10 * dose * self.gaussian(t, center=10, width=4)
            explanation = "Phenoxybenzamine: Non-competitive α1/α2 blockade lowers BP, increases HR."
        elif drug == "Propranolol":
            map_effect = +10 * dose * self.gaussian(t, center=10, width=4)
            hr_effect = -15 * dose * self.gaussian(t, center=10, width=4)
            explanation = "Propranolol: β1/β2 blockade reduces HR, slightly increases BP."
        elif drug == "Atropine":
            map_effect = np.zeros_like(t)
            hr_effect = +15 * dose * self.gaussian(t, center=10, width=4)
            explanation = "Atropine: Muscarinic blockade increases HR."
        # Handle agonists
        elif drug == "Epinephrine":
            if alpha_blocked:
                map_effect = -50 * dose * self.gaussian(t, center=15, width=4)
                hr_effect = +30 * dose * self.gaussian(t, center=15, width=4)
                explanation = "Epinephrine after Phenoxybenzamine: Vasomotor reversal - β2 lowers BP, β1 increases HR."
            elif beta_blocked:
                map_effect = +60 * dose * self.gaussian(t, center=10, width=4)
                hr_effect = -15 * dose * self.gaussian(t, center=12, width=4)
                explanation = "Epinephrine after Propranolol: α1 increases BP, reflex bradycardia."
            elif muscarinic_blocked:
                if dose <= 0.5:
                    map_effect = -40 * dose * self.gaussian(t, center=15, width=4)
                    hr_effect = +20 * dose * self.gaussian(t, center=15, width=4)
                    explanation = "Low dose Epinephrine after Atropine: β2 lowers BP, β1 increases HR (no reflex)."
                elif 0.4 <= dose < 1.0:
                    map_effect = (40 * dose * self.gaussian(t, center=8, width=3) -
                                  30 * dose * self.gaussian(t, center=20, width=4))
                    hr_effect = +15 * dose * self.gaussian(t, center=15, width=4)
                    explanation = "Moderate dose Epinephrine after Atropine: Biphasic response."
                else:
                    map_effect = +60 * dose * self.gaussian(t, center=10, width=4)
                    hr_effect = +10 * dose * self.gaussian(t, center=12, width=4)
                    explanation = "High dose Epinephrine after Atropine: α1 increases BP, HR rises (no reflex)."
            else:
                if dose <= 0.5:
                    map_effect = -40 * dose * self.gaussian(t, center=15, width=4)
                    hr_effect = +20 * dose * self.gaussian(t, center=15, width=4)
                    explanation = "Low dose Epinephrine: β2 vasodilation lowers BP, β1 increases HR."
                elif 0.4 <= dose < 1.0:
                    map_effect = (40 * dose * self.gaussian(t, center=8, width=3) -
                                  30 * dose * self.gaussian(t, center=20, width=4))
                    hr_effect = +15 * dose * self.gaussian(t, center=15, width=4)
                    explanation = "Moderate dose Epinephrine: Biphasic response."
                else:
                    map_effect = +60 * dose * self.gaussian(t, center=10, width=4)
                    hr_effect = -15 * dose * self.gaussian(t, center=12, width=4)
                    explanation = "High dose Epinephrine: α1 vasoconstriction increases BP, reflex bradycardia."
        elif drug == "Norepinephrine":
            if alpha_blocked:
                map_effect = -10 * dose * self.gaussian(t, center=10, width=4)
                hr_effect = +5 * dose * self.gaussian(t, center=10, width=4)
                explanation = "Norepinephrine after Phenoxybenzamine: Minimal BP rise, slight HR increase."
            elif beta_blocked:
                map_effect = +50 * dose * self.gaussian(t, center=8, width=3)
                hr_effect = -20 * dose * self.gaussian(t, center=8, width=3)
                explanation = "Norepinephrine after Propranolol: α1 increases BP, reflex bradycardia."
            elif muscarinic_blocked:
                map_effect = +50 * dose * self.gaussian(t, center=8, width=3)
                hr_effect = 0 * self.gaussian(t, center=8, width=3)
                explanation = "Norepinephrine after Atropine: BP rises, HR stable."
            else:
                map_effect = +50 * dose * self.gaussian(t, center=8, width=3)
                hr_effect = -20 * dose * self.gaussian(t, center=8, width=3)
                explanation = "Norepinephrine: α1 increases BP, reflex bradycardia."
        elif drug == "Isoprenaline":
            if beta_blocked:
                map_effect = 0 * self.gaussian(t, center=10, width=3)
                hr_effect = 0 * self.gaussian(t, center=10, width=3)
                explanation = "Isoprenaline after Propranolol: No change due to β-blockade."
            else:
                map_effect = -30 * dose * self.gaussian(t, center=10, width=3)
                hr_effect = +50 * dose * self.gaussian(t, center=10, width=3)
                explanation = "Isoprenaline: β2 lowers BP, β1 increases HR."
        elif drug == "Acetylcholine":
            if muscarinic_blocked:
                if dose >= 1.5:
                    map_effect = +25 * dose * self.gaussian(t, center=10, width=4)
                    hr_effect = +15 * dose * self.gaussian(t, center=10, width=4)
                    explanation = ("High-dose Acetylcholine after Atropine: Nicotinic ganglionic "
                                   "and adrenal medullary stimulation increases BP and HR.")
                else:
                    map_effect = 0 * self.gaussian(t, center=10, width=4)
                    hr_effect = 0 * self.gaussian(t, center=10, width=4)
                    explanation = "Acetylcholine after Atropine: No response due to muscarinic blockade."
            else:
                map_effect = -40 * dose * self.gaussian(t, center=10, width=4)
                hr_effect = -25 * dose * self.gaussian(t, center=10, width=4)
                explanation = "Acetylcholine: M3 lowers BP, M2 decreases HR."
        elif drug == "Ephedrine":
            prior_doses = sum(
                event.get("drug") == "Ephedrine" for event in self.injection_history
            )
            remaining_effect = 0.5 ** prior_doses
            map_effect = +45 * dose * remaining_effect * self.gaussian(t, center=12, width=6)
            hr_effect = +22 * dose * remaining_effect * self.gaussian(t, center=12, width=6)
            explanation = ("Ephedrine: Indirect sympathomimetic response. Repeated doses show "
                           "tachyphylaxis due to depletion of stored noradrenaline.")
        elif drug == "Saline":
            map_effect = np.zeros_like(t)
            hr_effect = np.zeros_like(t)
            explanation = "Saline: No pharmacological effect."
        else:
            map_effect = np.zeros_like(t)
            hr_effect = np.zeros_like(t)
            explanation = "Unknown drug selection."

        map_curve = previous_map + map_effect + noise_map
        hr_curve = previous_hr + hr_effect + noise_hr
        return map_curve, hr_curve, explanation

    def update_continuous_graph(self):
        while len(self.fig.axes) > 1:
            self.fig.delaxes(self.fig.axes[-1])
        self.ax.clear()
        self.ax.set_xlim(0, self.WINDOW_DURATION)
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("BP (mmHg)", color="blue")
        self.ax.set_ylim(80, 180)
        self.ax2 = self.ax.twinx()
        self.ax2.set_ylabel("Pulse (bpm)", color="red")
        self.ax2.set_ylim(40, 140)
        self.ax.plot([0, self.WINDOW_DURATION], [self.baseline_map, self.baseline_map], 'k--')
        self.ax2.plot([0, self.WINDOW_DURATION], [self.baseline_hr, self.baseline_hr], 'k:')
        for event in self.injection_history:
            self.ax.plot(event['time_array'], event['map_curve'], color="blue")
            self.ax2.plot(event['time_array'], event['hr_curve'], color="red", linestyle="--")
            self.ax.annotate(event['drug'],
                        xy=(event['start_time'], 82),
                        xytext=(event['start_time'], 92),
                        arrowprops=dict(arrowstyle="->", color="black"),
                        ha='center', fontsize=8)
        self.ax.set_title("Continuous Dog BP and Pulse Simulation")
        self.canvas.draw()

    def update_numeric_labels(self, last_map, last_hr):
        idx_map = np.argmax(np.abs(last_map - self.baseline_map))
        idx_hr = np.argmax(np.abs(last_hr - self.baseline_hr))
        self.map_label.config(text=f"Peak BP: {last_map[idx_map]:.1f} mmHg")
        self.hr_label.config(text=f"Peak Pulse: {last_hr[idx_hr]:.1f} bpm")

    def update_explanation(self, text):
        self.explanation_label.config(text=text)

    def reset_simulation(self):
        self.injection_history = []
        self.current_offset = 0
        while len(self.fig.axes) > 1:
            self.fig.delaxes(self.fig.axes[-1])
        self.ax.clear()
        self.ax.set_xlim(0, self.WINDOW_DURATION)
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("BP (mmHg)", color="blue")
        self.ax.set_ylim(80, 180)
        self.ax2 = self.ax.twinx()
        self.ax2.set_ylabel("Pulse (bpm)", color="red")
        self.ax2.set_ylim(40, 140)
        self.ax.plot([0, self.WINDOW_DURATION], [self.baseline_map, self.baseline_map], 'k--')
        self.ax2.plot([0, self.WINDOW_DURATION], [self.baseline_hr, self.baseline_hr], 'k:')
        self.ax.set_title("Continuous Dog BP and Pulse Simulation")
        self.canvas.draw()
        self.map_label.config(text="Peak BP: N/A")
        self.hr_label.config(text="Peak Pulse: N/A")
        self.update_explanation("Reset to baseline state.")

    def inject_drug(self, drug, dose):
        t = np.linspace(0, 60, 121)
        if self.injection_history:
            prev_event = self.injection_history[0]
            prev_map = prev_event['map_curve'][-1] * np.ones_like(t)
            prev_hr = prev_event['hr_curve'][-1] * np.ones_like(t)
        else:
            prev_map = None
            prev_hr = None
        new_map, new_hr, explanation = self.simulate_drug_effect(drug, dose, t, prev_map, prev_hr)
        for event in self.injection_history:
            event['time_array'] += 60
            event['start_time'] += 60
        new_event = {
            "start_time": 0,
            "time_array": t,
            "map_curve": new_map,
            "hr_curve": new_hr,
            "drug": drug,
            "dose": dose,
            "explanation": explanation
        }
        self.injection_history.insert(0, new_event)
        if len(self.injection_history) > 4:
            self.injection_history.pop()
        self.current_offset += 60
        self.update_continuous_graph()
        self.update_numeric_labels(new_map, new_hr)
        self.update_explanation(explanation)

    def setup_controls(self):
        antagonist_frame = tk.Frame(self.master, bg="#f0f8ff")
        antagonist_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        tk.Label(antagonist_frame, text="Select Antagonist:", bg="#f0f8ff", font=("Segoe UI", 12)).pack(side=tk.LEFT, padx=5)
        antagonist_options = ["Phenoxybenzamine", "Propranolol", "Atropine", "Saline"]
        antagonist_var = tk.StringVar(value=antagonist_options[0])
        tk.OptionMenu(antagonist_frame, antagonist_var, *antagonist_options).pack(side=tk.LEFT, padx=5)
        tk.Label(antagonist_frame, text="Dose (mcg/kg):", bg="#f0f8ff", font=("Segoe UI", 12)).pack(side=tk.LEFT, padx=5)
        antag_dose_scale = tk.Scale(antagonist_frame, from_=0.1, to=2.0, resolution=0.1,
                                    orient=tk.HORIZONTAL, bg="#f0f8ff", length=150)
        antag_dose_scale.set(1.0)
        antag_dose_scale.pack(side=tk.LEFT, padx=5)
        antag_button = tk.Button(antagonist_frame, text="Inject Antagonist", font=("Segoe UI", 12),
                                 command=lambda: self.inject_drug(antagonist_var.get(), antag_dose_scale.get()),
                                 bg="lightcoral", relief="raised")
        antag_button.pack(side=tk.LEFT, padx=5)
        agonist_frame = tk.Frame(self.master, bg="#f0f8ff")
        agonist_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        tk.Label(agonist_frame, text="Select Agonist:", bg="#f0f8ff", font=("Segoe UI", 12)).pack(side=tk.LEFT, padx=5)
        agonist_options = ["Epinephrine", "Norepinephrine", "Isoprenaline", "Acetylcholine", "Ephedrine", "Saline"]
        agonist_var = tk.StringVar(value=agonist_options[0])
        tk.OptionMenu(agonist_frame, agonist_var, *agonist_options).pack(side=tk.LEFT, padx=5)
        tk.Label(agonist_frame, text="Dose (mcg/kg):", bg="#f0f8ff", font=("Segoe UI", 12)).pack(side=tk.LEFT, padx=5)
        agonist_dose_scale = tk.Scale(agonist_frame, from_=0.1, to=2.0, resolution=0.1,
                                      orient=tk.HORIZONTAL, bg="#f0f8ff", length=150)
        agonist_dose_scale.set(1.0)
        agonist_dose_scale.pack(side=tk.LEFT, padx=5)
        agonist_button = tk.Button(agonist_frame, text="Inject Agonist", font=("Segoe UI", 12),
                                   command=lambda: self.inject_drug(agonist_var.get(), agonist_dose_scale.get()),
                                   bg="lightgreen", relief="raised")
        agonist_button.pack(side=tk.LEFT, padx=5)
        reset_button = tk.Button(self.master, text="Reset Experiment", font=("Segoe UI", 12),
                                 command=self.reset_simulation, bg="orange", relief="raised")
        reset_button.pack(side=tk.TOP, pady=5)
        label_frame = tk.Frame(self.master, bg="#f0f8ff")
        label_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        self.map_label = tk.Label(label_frame, text="Peak BP: N/A", font=("Segoe UI", 12), bg="#f0f8ff")
        self.map_label.pack(side=tk.LEFT, padx=10)
        self.hr_label = tk.Label(label_frame, text="Peak Pulse: N/A", font=("Segoe UI", 12), bg="#f0f8ff")
        self.hr_label.pack(side=tk.LEFT, padx=10)
        self.explanation_label = tk.Label(self.master, text="Experiment Explanation: " + self.current_explanation,
                                       font=("Segoe UI", 12), bg="#f0f8ff", wraplength=800, justify=tk.LEFT)
        self.explanation_label.pack(side=tk.TOP, padx=10, pady=5)
