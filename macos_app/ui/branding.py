"""Shared public-beta branding for application windows."""

import tkinter as tk


PUBLIC_BETA_LINE = "macOS Public Beta  •  Version 1.0  •  MAMC, New Delhi"
MAMC_ATTRIBUTION = "MAMC, New Delhi"


def add_corner_attribution(parent, bg="#173b57", fg="#cfe2f3"):
    """Place a small, unobtrusive institutional credit in a window corner."""
    label = tk.Label(
        parent,
        text=MAMC_ATTRIBUTION,
        font=("Segoe UI", 8),
        bg=bg,
        fg=fg,
        padx=5,
        pady=2,
    )
    label.place(relx=1.0, rely=1.0, x=-7, y=-5, anchor="se")
    label.lift()
    return label
