<<<<<<< HEAD
# Rabbit Eye Experiment Simulator

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-lightgrey)]()
[![Status: Active](https://img.shields.io/badge/status-active-success)]()

An interactive desktop simulator for the **rabbit eye pharmacology experiment**, designed as an ethical, animal-free alternative for undergraduate (MBBS) pharmacology practical training. Developed at the **Department of Pharmacology, Maulana Azad Medical College (MAMC) & Lok Nayak Hospital, New Delhi**.

> Replaces live-animal demonstrations with a faithful, photograph-based virtual experience that preserves pedagogical value while eliminating animal use.

---

## 📋 Table of Contents

- [Background](#background)
- [Features](#features)
- [Screenshots](#screenshots)
- [Installation](#installation)
- [Usage](#usage)
- [System Requirements](#system-requirements)
- [Educational Use](#educational-use)
- [Contributing](#contributing)
- [License](#license)
- [Citation](#citation)
- [Acknowledgements](#acknowledgements)
- [Contact](#contact)

---

## 🐇 Background

The classical rabbit eye experiment is a cornerstone of autonomic pharmacology teaching, demonstrating the effects of mydriatics, miotics, and local anaesthetics on pupil size, light reflex, and corneal sensitivity. However, conducting this experiment on live animals raises significant ethical, regulatory, and logistical challenges, and is now actively discouraged by the National Medical Commission (NMC) and the Committee for the Purpose of Control and Supervision of Experiments on Animals (CPCSEA).

This simulator is a **3R-compliant (Replacement, Reduction, Refinement)** alternative, built using real photographs of rabbit eyes captured at MAMC, that lets students perform the full experimental workflow virtually — without compromising on learning outcomes.

## ✨ Features

- **Photograph-based realism** — uses actual rabbit eye images from MAMC archives
- **Dual-eye setup** — independent left and right eye for control vs. test comparison
- **Interactive instruments**:
  - 🔦 Movable torch for light reflex testing
  - 📏 Drag-and-drop ruler for pupil measurement
  - 🧵 Cotton swab for corneal reflex assessment
- **Drug library** covering autonomic agents (mydriatics, miotics, anaesthetics)
- **Self-contained executable** — no Python installation required for end users
- **Offline operation** — runs entirely without internet connectivity
- **Designed for non-technical faculty** — single-click `.exe` distribution

## 📸 Screenshots

> *Add screenshots in the `docs/screenshots/` folder and reference them here.*

```
docs/
└── screenshots/
    ├── main_window.png
    ├── drug_selection.png
    └── reflex_test.png
```

## 🚀 Installation

### Option 1: Run from source (recommended for developers)

```bash
# Clone the repository
git clone https://github.com/<your-username>/rabbit-eye-experiment.git
cd rabbit-eye-experiment

# (Optional but recommended) Create a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

### Option 2: Use the pre-built Windows executable

1. Go to the [Releases](../../releases) page
2. Download `RabbitEyeExperiment.exe`
3. Double-click to run — **no installation needed**

> The executable is unsigned. Windows SmartScreen may show a warning; click *More info → Run anyway*.

## 🖱️ Usage

1. **Launch** the application — the main window shows two rabbit eyes (left and right).
2. **Select a drug** from the drug panel (e.g., Atropine, Pilocarpine, Lignocaine).
3. **Apply** the drug to the chosen eye (the other serves as control).
4. **Observe** changes in pupil size, light reflex, and corneal sensitivity.
5. **Use the instruments** (ruler, torch, cotton swab) to perform measurements.
6. **Record observations** in the built-in observation table.
7. **Compare** test vs. control eye to deduce the drug's autonomic action.

## 💻 System Requirements

| Component | Minimum |
|-----------|---------|
| OS | Windows 10 (64-bit) — also runnable from source on macOS/Linux |
| Python | 3.8+ (only if running from source) |
| RAM | 2 GB |
| Disk Space | 100 MB |
| Display | 1366×768 or higher |

## 🎓 Educational Use

This tool is intended for:

- MBBS Phase II Pharmacology practicals
- Postgraduate (MD Pharmacology) demonstrations
- CPCSEA-compliant teaching environments
- Faculty refresher workshops on autonomic pharmacology

Faculty are encouraged to incorporate it into Small Group Discussions (SGDs) and competency-based assessments aligned with the NMC Competency-Based Medical Education (CBME) curriculum.

## 🤝 Contributing

Contributions, bug reports, and pedagogical suggestions are warmly welcome. Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add some feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

For major changes, please open an issue first to discuss what you'd like to change.

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

## 📚 Citation

If you use this simulator in teaching or research, please cite:

```
Shetty, M. K. (2026). Rabbit Eye Experiment Simulator [Computer software].
Department of Pharmacology, Maulana Azad Medical College, New Delhi.
https://github.com/<your-username>/rabbit-eye-experiment
```

## 🙏 Acknowledgements

- **Department of Pharmacology, MAMC & LNH, New Delhi** — for institutional support and source photographs
- **MAMC Faculty Association** — for encouraging open educational resources
- All MBBS and PG students whose feedback shaped iterative improvements

## 📬 Contact

**Dr. Manu Kumar Shetty**
Professor, Department of Pharmacology
Maulana Azad Medical College & Lok Nayak Hospital, New Delhi

For issues and feature requests, please use the [GitHub Issues](../../issues) page.

---

*Built with Python, Tkinter, and a commitment to ethical medical education.*
=======
# rabbit-eye-experiment
An interactive desktop simulator for the rabbit eye pharmacology experiment, designed as an ethical, animal-free alternative for undergraduate (MBBS) pharmacology practical training. 
>>>>>>> d3eb9a02babbce837f8f3816c747b7b48ea1b9bb
