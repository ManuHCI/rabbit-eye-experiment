import os
import sys
from pathlib import Path


# PyInstaller's one-file extraction needs explicit Tcl/Tk paths before any
# module imports tkinter. This is especially important with Anaconda builds.
if getattr(sys, "frozen", False) and sys.platform == "win32":
    _bundle_root = Path(sys._MEIPASS)
    # PyInstaller's Tk runtime hook sets these variables before tkinter is
    # imported. Anaconda's Tcl build needs tkinter imported first, then the
    # extracted bundle paths set before the first Tk/Tcl interpreter is made.
    os.environ.pop("TCL_LIBRARY", None)
    os.environ.pop("TK_LIBRARY", None)
    import tkinter as _tkinter_preload
    os.environ["TCL_LIBRARY"] = str(_bundle_root / "_tcl_data")
    os.environ["TK_LIBRARY"] = str(_bundle_root / "_tk_data")


# Edit these lines when the credit text needs to be changed. Rebuild the
# executable afterward for the changes to appear in the standalone app.
APP_CREDITS = {
    "developer": "Designed and developed by",
    "developer_name": "Dr. Manu Kumar Shetty",
    "developer_title": "Professor of Pharmacology",
    "ai_credit": "with assistance from generative AI tools",
    "contributors": "Contributed by the Faculties of the Department of Pharmacology",
    "organization": "Maulana Azad Medical College, New Delhi  -  Academic Year 2025-26",
    "funding": "Funded by MRU, MAMC  -  Nodal Officer: Dr. Bhupinder Kalra",
}


from ui.display import enable_high_dpi

enable_high_dpi()

import tkinter as tk
from ui.display import configure_application_display
from ui.experiment_app import ExperimentApp

if __name__ == "__main__":
    root = tk.Tk()
    configure_application_display(root)
    app = ExperimentApp(root, credits=APP_CREDITS)
    root.mainloop()

