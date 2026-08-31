"""High-DPI display helpers for the MAMC CAL desktop application."""

import ctypes
import sys
from tkinter import font as tkfont
from tkinter import ttk


TEXT_MAGNIFICATION = 1.08
_dpi_awareness_requested = False


def enable_high_dpi():
    """Ask Windows for native per-monitor rendering before a Tk window exists."""
    global _dpi_awareness_requested
    if _dpi_awareness_requested or sys.platform != "win32":
        return
    _dpi_awareness_requested = True

    try:
        user32 = ctypes.windll.user32
        user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        user32.SetProcessDpiAwarenessContext.restype = ctypes.c_bool
        if user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return
    except (AttributeError, OSError, ValueError):
        pass

    try:
        # PROCESS_PER_MONITOR_DPI_AWARE
        if ctypes.windll.shcore.SetProcessDpiAwareness(2) in (0, -2147024891):
            return
    except (AttributeError, OSError):
        pass

    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass


def configure_application_display(root):
    """Configure sharp fonts, slightly larger text, and readable ttk controls."""
    if getattr(root, "_mamc_display_configured", False):
        return
    root._mamc_display_configured = True
    root.update_idletasks()
    try:
        dpi = float(root.winfo_fpixels("1i"))
    except Exception:
        dpi = 96.0
    dpi = min(max(dpi, 96.0), 288.0)
    monitor_scale = dpi / 96.0
    root._mamc_monitor_scale = monitor_scale

    # Tk font sizes use points. This preserves the physical font size at the
    # monitor DPI and adds a small readability increase requested for teaching.
    root.tk.call("tk", "scaling", (dpi / 72.0) * TEXT_MAGNIFICATION)

    font_settings = {
        "TkDefaultFont": ("Segoe UI", 10, "normal"),
        "TkTextFont": ("Segoe UI", 10, "normal"),
        "TkMenuFont": ("Segoe UI", 10, "normal"),
        "TkHeadingFont": ("Segoe UI", 10, "bold"),
        "TkCaptionFont": ("Segoe UI", 10, "bold"),
        "TkSmallCaptionFont": ("Segoe UI", 9, "normal"),
        "TkIconFont": ("Segoe UI", 10, "normal"),
        "TkFixedFont": ("Consolas", 10, "normal"),
    }
    for name, (family, size, weight) in font_settings.items():
        try:
            named_font = tkfont.nametofont(name, root=root)
            named_font.configure(family=family, size=size, weight=weight)
        except Exception:
            continue

    root.option_add("*Font", "TkDefaultFont")
    root.option_add("*Menu.Font", "TkMenuFont")

    style = ttk.Style(root)
    style.configure(".", font=("Segoe UI", 10))
    style.configure(
        "Treeview", font=("Segoe UI", 10),
        rowheight=max(27, int(round(27 * monitor_scale))),
    )
    style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
    style.configure("TCombobox", font=("Segoe UI", 10), padding=(5, 4))
    style.configure("TButton", font=("Segoe UI", 10), padding=(7, 5))

    try:
        from matplotlib import rcParams
        rcParams.update({
            "font.family": "Segoe UI",
            "font.size": 10.5,
            "axes.titlesize": 11.5,
            "axes.labelsize": 10.5,
            "xtick.labelsize": 9.5,
            "ytick.labelsize": 9.5,
            "legend.fontsize": 9.5,
        })
    except Exception:
        pass


def display_scale(widget):
    root = widget._root()
    return float(getattr(root, "_mamc_monitor_scale", 1.0))


def set_window_size(window, width, height, min_width=None, min_height=None,
                    margin_x=60, margin_y=80, center=True):
    """Set a DPI-scaled window size while keeping it inside the current screen."""
    scale = display_scale(window)
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    available_width = max(500, screen_width - int(round(margin_x * scale)))
    available_height = max(420, screen_height - int(round(margin_y * scale)))
    target_width = min(int(round(width * scale)), available_width)
    target_height = min(int(round(height * scale)), available_height)

    if center:
        left = max(0, (screen_width - target_width) // 2)
        top = max(0, (screen_height - target_height) // 3)
        window.geometry(f"{target_width}x{target_height}+{left}+{top}")
    else:
        window.geometry(f"{target_width}x{target_height}")

    if min_width is not None and min_height is not None:
        scaled_min_width = min(int(round(min_width * scale)), target_width)
        scaled_min_height = min(int(round(min_height * scale)), target_height)
        window.minsize(scaled_min_width, scaled_min_height)
    return target_width, target_height
