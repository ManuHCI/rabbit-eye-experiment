#!/usr/bin/env python3
"""
=============================================================================
RABBIT EYE EXPERIMENT SIMULATOR  (v3 — Interactive Tools)
Developed by
Computer-Assisted Learning (CAL) Software
Department of Pharmacology, Maulana Azad Medical College, New Delhi

For 2nd Year MBBS Students

INTERACTIVE TOOLS:
  📏 Ruler   — Click & drag across pupil to measure diameter in mm
  🔦 Torch   — Move mouse near pupil; watch it constrict (or not)
  🧹 Cotton  — Click & drag swab to cornea; eye blinks (or stays open)
  👁  Conjunctiva — Click to inspect
  ✋  Tone    — Click to palpate

Requirements: Python 3.8+, Pillow  (pip install Pillow)
Run: python rabbit_eye_experiment_v3.py [path/to/images]
=============================================================================
"""

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageDraw
import os, sys, math

# =============================================================================
# PHARMACOLOGY DATA
# =============================================================================
BASELINE = {
    "pupil_size": "normal", "pupil_mm": 6.0,
    "light_reflex": "present", "corneal_reflex": "present",
    "conjunctiva": "normal", "conjunctiva_desc": "Normal, pink vasculature",
    "tone": "normal", "tone_desc": "Normal IOP (~15-20 mmHg)",
    "pupil_image": "Normal_pupil",
}

DRUG_DATA = {
    "Atropine (1%)": {
        "class": "Anticholinergic (M3 antagonist)",
        "pupil_size": "mydriasis", "pupil_mm": 9.0,
        "light_reflex": "absent", "corneal_reflex": "present",
        "conjunctiva": "no_change", "conjunctiva_desc": "No significant change",
        "tone": "increased", "tone_desc": "Increased IOP (~25-30 mmHg) — angle closure",
        "mechanism": "M3 antagonist → sphincter pupillae relaxation (mydriasis)\n"
                     "+ cycloplegia. Abolishes light reflex.",
        "onset": "20-30 min", "duration": "7-10 days",
        "pupil_image": "Mydriasis", "color": "#ef4444",
    },
    "Lignocaine (4%)": {
        "class": "Local Anaesthetic",
        "pupil_size": "normal", "pupil_mm": 6.0,
        "light_reflex": "present", "corneal_reflex": "absent",
        "conjunctiva": "no_change", "conjunctiva_desc": "No significant change",
        "tone": "normal", "tone_desc": "No change in IOP",
        "mechanism": "Na⁺ channel block → abolishes corneal sensation.\n"
                     "No autonomic effect on pupil.",
        "onset": "1-5 min", "duration": "30-60 min",
        "pupil_image": "Normal_pupil", "color": "#3b82f6",
    },
    "Cocaine (4%)": {
        "class": "NA Reuptake Inhibitor + LA",
        "pupil_size": "mydriasis", "pupil_mm": 8.5,
        "light_reflex": "sluggish", "corneal_reflex": "absent",
        "conjunctiva": "blanched", "conjunctiva_desc": "Blanched — vasoconstriction",
        "tone": "normal", "tone_desc": "No significant change",
        "mechanism": "Blocks NA reuptake → mydriasis.\n"
                     "Also LA → abolishes corneal reflex.\nVasoconstriction → blanching.",
        "onset": "5-10 min", "duration": "1-2 hours",
        "pupil_image": "Mydriasis", "color": "#8b5cf6",
    },
    "Ephedrine (1%)": {
        "class": "Mixed Sympathomimetic",
        "pupil_size": "mydriasis", "pupil_mm": 8.0,
        "light_reflex": "sluggish", "corneal_reflex": "present",
        "conjunctiva": "blanched", "conjunctiva_desc": "Mild blanching — vasoconstriction",
        "tone": "normal", "tone_desc": "No significant change",
        "mechanism": "Releases NA + direct α₁ → mydriasis.\n"
                     "Sluggish light reflex. Corneal reflex intact.",
        "onset": "10-20 min", "duration": "3-6 hours",
        "pupil_image": "Mydriasis", "color": "#f59e0b",
    },
    "Pilocarpine (1%)": {
        "class": "Cholinomimetic (M3 agonist)",
        "pupil_size": "miosis", "pupil_mm": 3.0,
        "light_reflex": "present", "corneal_reflex": "present",
        "conjunctiva": "congested", "conjunctiva_desc": "Congested — vasodilation",
        "tone": "decreased", "tone_desc": "Decreased IOP (~10-15 mmHg)",
        "mechanism": "M3 agonist → sphincter pupillae contracts (miosis).\n"
                     "Opens trabecular meshwork → ↓ IOP.",
        "onset": "10-20 min", "duration": "4-8 hours",
        "pupil_image": "Miosis", "color": "#10b981",
    },
}

# =============================================================================
C = {
    "bg": "#0f172a", "bg2": "#1e293b", "bg3": "#0a0e1a",
    "gold": "#daa520", "gold_dim": "#c0a060",
    "text": "#e2e8f0", "text2": "#94a3b8", "text3": "#64748b",
    "green": "#22c55e", "red": "#ef4444", "blue": "#3b82f6",
    "amber": "#f59e0b", "card": "#111b33",
}


def get_image_path(image_dir, key):
    for ext in ['.png', '.jpg', '.jpeg', '.PNG']:
        p = os.path.join(image_dir, key + ext)
        if os.path.exists(p):
            return p
    return os.path.join(image_dir, key + ".png")


# =============================================================================
# EYE CANVAS — handles all interactive drawing on one eye
# =============================================================================
class EyeCanvas(tk.Canvas):
    """Canvas for a single eye with interactive tool overlays."""

    # Image centre coordinates (after placing image)
    IMG_CX = 160
    IMG_CY = 200
    # Approx radius (in px) of the iris in the photographs
    IRIS_PX = 95
    # Iris real diameter in mm (rabbit)
    IRIS_MM = 10.0

    def __init__(self, parent, eye_data, image_dir, side, experiment_frame):
        super().__init__(parent, width=340, height=440, bg=C["bg"], highlightthickness=0)
        self.eye_data = eye_data
        self.image_dir = image_dir
        self.side = side
        self.exp = experiment_frame

        # State
        self.photo = None           # normal / drug eye image
        self.close_photo = None     # closed-eye (blink) image
        self.miosis_photo = None    # constricted pupil image (for light reflex)
        self.is_blinking = False
        self.is_constricted = False # currently showing miosis image (torch)

        # Ruler state
        self.ruler_start = None
        self.ruler_line_id = None
        self.ruler_cap1 = None
        self.ruler_cap2 = None
        self.ruler_bg = None
        self.ruler_label = None

        # Torch state
        self.torch_glow = None
        self.torch_icon = []
        self.torch_label = None
        self.torch_near = False

        # Cotton swab state
        self.swab_items = []
        self.swab_touched = False
        self.swab_target = None

        self._load_eye_image()
        self._preload_close_image()
        self._preload_miosis_image()

    # ---- image loading ----
    def _load_eye_image(self):
        img_key = self.eye_data.get("pupil_image", "Normal_pupil")
        img_path = get_image_path(self.image_dir, img_key)
        if os.path.exists(img_path):
            try:
                img = Image.open(img_path)
                scale = min(320 / img.width, 420 / img.height)
                img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
                self.photo = ImageTk.PhotoImage(img)
                self.create_image(self.IMG_CX, self.IMG_CY, image=self.photo, tags="eyeimg")
            except Exception:
                self.create_text(self.IMG_CX, self.IMG_CY, text=img_key, fill=C["text3"])
        else:
            self.create_text(self.IMG_CX, self.IMG_CY, text=f"Not found:\n{img_key}",
                             fill=C["text3"], font=("Helvetica", 10))

    def _preload_close_image(self):
        close_path = get_image_path(self.image_dir, "Close")
        if os.path.exists(close_path):
            try:
                img = Image.open(close_path)
                scale = min(320 / img.width, 420 / img.height)
                img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
                self.close_photo = ImageTk.PhotoImage(img)
            except Exception:
                self.close_photo = None

    def _preload_miosis_image(self):
        """Preload constricted-pupil image for light reflex demonstration."""
        miosis_path = get_image_path(self.image_dir, "Miosis")
        if os.path.exists(miosis_path):
            try:
                img = Image.open(miosis_path)
                scale = min(320 / img.width, 420 / img.height)
                img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
                self.miosis_photo = ImageTk.PhotoImage(img)
            except Exception:
                self.miosis_photo = None

    def _show_constricted(self):
        """Swap to miosis (constricted pupil) image when torch is near."""
        if self.miosis_photo and not self.is_constricted and not self.is_blinking:
            self.is_constricted = True
            self.delete("eyeimg")
            self.create_image(self.IMG_CX, self.IMG_CY, image=self.miosis_photo, tags="eyeimg")

    def _show_normal(self):
        """Restore normal eye image when torch moves away."""
        if self.is_constricted:
            self.is_constricted = False
            self.delete("eyeimg")
            if self.photo:
                self.create_image(self.IMG_CX, self.IMG_CY, image=self.photo, tags="eyeimg")

    def _show_blink(self):
        """Show closed eye image for blink, then restore after 600ms."""
        if self.close_photo and not self.is_blinking:
            self.is_blinking = True
            self.delete("eyeimg")
            self.delete("swab")
            self.delete("swab_target")
            self.create_image(self.IMG_CX, self.IMG_CY, image=self.close_photo, tags="eyeimg")
            # Add text to make it obvious
            self.create_text(self.IMG_CX, 30, text="👁 Eye BLINKED ✓",
                             fill=C["green"], font=("Helvetica", 12, "bold"), tags="blinktext")
            self.after(800, self._restore_eye)

    def _restore_eye(self):
        self.delete("eyeimg")
        self.delete("blinktext")
        if self.photo:
            self.create_image(self.IMG_CX, self.IMG_CY, image=self.photo, tags="eyeimg")
        self.is_blinking = False
        self.is_constricted = False

    # ---- pixel ↔ mm conversion ----
    def px_to_mm(self, px_distance):
        return (px_distance / (self.IRIS_PX * 2)) * self.IRIS_MM

    # ---- clear all overlays ----
    def clear_overlays(self):
        for tag in ("ruler", "torch", "swab", "swab_target", "blinktext"):
            self.delete(tag)
        self.ruler_start = None
        self.torch_near = False
        self.swab_touched = False
        # Restore normal image if we were showing constricted or blink
        if self.is_constricted or self.is_blinking:
            self._restore_eye()

    # ================================================================
    # RULER — click & drag
    # ================================================================
    def ruler_press(self, event):
        self.clear_overlays()
        self.ruler_start = (event.x, event.y)

    def ruler_drag(self, event):
        if not self.ruler_start:
            return
        sx, sy = self.ruler_start
        ex, ey = event.x, event.y
        self.delete("ruler")

        # Main dashed line
        self.create_line(sx, sy, ex, ey, fill="#ffd700", width=2, dash=(6, 3), tags="ruler")

        # End caps (perpendicular ticks)
        dx, dy = ex - sx, ey - sy
        length = math.sqrt(dx * dx + dy * dy) or 1
        nx, ny = -dy / length * 10, dx / length * 10
        self.create_line(sx - nx, sy - ny, sx + nx, sy + ny, fill="#ffd700", width=2, tags="ruler")
        self.create_line(ex - nx, ey - ny, ex + nx, ey + ny, fill="#ffd700", width=2, tags="ruler")

        # Measurement label
        px_dist = math.sqrt((ex - sx) ** 2 + (ey - sy) ** 2)
        mm = self.px_to_mm(px_dist)
        mx, my = (sx + ex) / 2, (sy + ey) / 2 - 16
        self.create_rectangle(mx - 36, my - 11, mx + 36, my + 11,
                              fill="black", outline="#ffd700", width=1, tags="ruler")
        self.create_text(mx, my, text=f"{mm:.1f} mm", fill="#ffd700",
                         font=("Consolas", 12, "bold"), tags="ruler")

    def ruler_release(self, event):
        if not self.ruler_start:
            return
        sx, sy = self.ruler_start
        px_dist = math.sqrt((event.x - sx) ** 2 + (event.y - sy) ** 2)
        mm = self.px_to_mm(px_dist)
        self.ruler_start = None

        data = self.eye_data
        self.exp.show_result(
            f"📏 PUPIL SIZE — {self.side.upper()} EYE",
            f"Measured: {mm:.1f} mm\n"
            f"Expected: ~{data['pupil_mm']} mm\n\n"
            f"State: {data['pupil_size'].upper()}\n\n"
            + ("Dilator pupillae dominant (sympathetic)."
               if data["pupil_size"] == "mydriasis"
               else "Sphincter pupillae dominant (parasympathetic)."
               if data["pupil_size"] == "miosis"
               else "Normal balanced autonomic tone."),
            data["pupil_size"] == "normal"
        )

    # ================================================================
    # TORCH — mouse-move proximity
    # ================================================================
    def torch_move(self, event):
        self.delete("torch")
        tx, ty = event.x, event.y

        # Distance from pupil centre
        dist = math.sqrt((tx - self.IMG_CX) ** 2 + (ty - self.IMG_CY) ** 2)
        near = dist < 120
        was_near = self.torch_near
        self.torch_near = near

        # Glow circle (larger when near)
        glow_r = 65 if near else 35
        self.create_oval(tx - glow_r, ty - glow_r, tx + glow_r, ty + glow_r,
                         fill="#fff9c4", outline="", stipple="gray25", tags="torch")

        # Torch body
        self.create_rectangle(tx - 10, ty - 6, tx + 10, ty + 6,
                              fill="#555555", outline="#888888", tags="torch")
        self.create_rectangle(tx - 5, ty + 6, tx + 5, ty + 20,
                              fill="#444444", outline="#666666", tags="torch")
        # Bulb
        self.create_oval(tx - 5, ty - 11, tx + 5, ty - 1,
                         fill="#fff9c4" if near else "#fff176", outline="", tags="torch")

        # ---- IMAGE SWAP based on proximity and reflex ----
        reflex = self.eye_data["light_reflex"]
        if near and not was_near:
            # Torch just got close — swap image if reflex present
            if reflex == "present":
                self._show_constricted()  # swap to Miosis image
            # sluggish: could show slight change, but miosis image is good enough
            elif reflex == "sluggish":
                self._show_constricted()
            # absent: do nothing, keep original image
        elif not near and was_near:
            # Torch moved away — restore original image
            self._show_normal()

        # Status text
        if near:
            if reflex == "present":
                txt, clr = "Pupil CONSTRICTS ✓  (see miosis)", C["green"]
            elif reflex == "sluggish":
                txt, clr = "Pupil constricts SLOWLY ⚠", C["amber"]
            else:
                txt, clr = "NO constriction ✗  (pupil unchanged)", C["red"]
            self.create_text(self.IMG_CX, 425, text=txt, fill=clr,
                             font=("Helvetica", 11, "bold"), tags="torch")

            self.exp.show_result(
                f"🔦 LIGHT REFLEX — {self.side.upper()} EYE",
                f"Response: {reflex.upper()}\n\n"
                + ("✓ Pupil constricts on light exposure.\n"
                   "Image changed to MIOSIS (constricted pupil).\n"
                   "Sphincter pupillae functional."
                   if reflex == "present"
                   else "⚠ Delayed/incomplete constriction.\n"
                   "Sympathetic dominance partially overrides."
                   if reflex == "sluggish"
                   else "✗ NO constriction on light.\n"
                   "Pupil image remains UNCHANGED.\n"
                   "Sphincter pupillae paralysed."),
                reflex == "present"
            )
        else:
            self.create_text(self.IMG_CX, 425, text="🔦 Move torch closer to the pupil",
                             fill=C["text3"], font=("Helvetica", 10), tags="torch")

    def torch_leave(self, event):
        self.delete("torch")
        if self.torch_near:
            self._show_normal()  # restore original image
        self.torch_near = False

    # ================================================================
    # COTTON SWAB — click & drag, blink on cornea contact
    # ================================================================
    def swab_press(self, event):
        self.clear_overlays()
        self.swab_touched = False
        # Show pulsing target zone on the cornea
        self.create_oval(self.IMG_CX - 45, self.IMG_CY - 45,
                         self.IMG_CX + 45, self.IMG_CY + 45,
                         outline="#ffd700", width=2, dash=(6, 4), tags="swab_target")
        self.create_text(self.IMG_CX, self.IMG_CY + 65,
                         text="↑ Drag cotton swab to this zone",
                         fill="#ffd700", font=("Helvetica", 10, "bold"), tags="swab_target")

    def swab_drag(self, event):
        if self.swab_touched or self.is_blinking:
            return
        self.delete("swab")
        sx, sy = event.x, event.y

        # ---- Draw a large visible cotton swab ----
        # Cotton tip (big white circle)
        self.create_oval(sx - 10, sy - 10, sx + 10, sy + 10,
                         fill="white", outline="#bbbbbb", width=2, tags="swab")
        # Wooden stick
        self.create_line(sx + 8, sy - 8, sx + 55, sy - 55,
                         fill="#d4b896", width=5, tags="swab")
        self.create_line(sx + 8, sy - 8, sx + 55, sy - 55,
                         fill="#e8d5b8", width=3, tags="swab")
        # Label near swab
        self.create_text(sx + 60, sy - 60, text="Cotton\nSwab",
                         fill="white", font=("Helvetica", 8), tags="swab", anchor="sw")

        # Check if cotton tip is touching cornea (centre of eye image)
        dist = math.sqrt((sx - self.IMG_CX) ** 2 + (sy - self.IMG_CY) ** 2)
        if dist < 55:
            self.swab_touched = True
            self.delete("swab_target")
            self.delete("swab")

            reflex = self.eye_data["corneal_reflex"]
            if reflex == "present":
                # Eye BLINKS — show Close.png image
                self._show_blink()
                self.exp.show_result(
                    f"🧹 CORNEAL REFLEX — {self.side.upper()} EYE",
                    "Response: PRESENT\n\n"
                    "✓ Eye BLINKS on corneal touch!\n"
                    "(Image changed to closed eye)\n\n"
                    "Sensory nerves (CN V₁) intact.\n"
                    "Afferent limb of blink reflex functional.",
                    True
                )
            else:
                # Eye stays OPEN — no image change
                self.create_text(self.IMG_CX, 30,
                                 text="✗ Eye stays OPEN — No blink!",
                                 fill=C["red"], font=("Helvetica", 13, "bold"), tags="swab")
                self.create_text(self.IMG_CX, 425,
                                 text="Corneal sensation abolished",
                                 fill=C["red"], font=("Helvetica", 10), tags="swab")
                self.exp.show_result(
                    f"🧹 CORNEAL REFLEX — {self.side.upper()} EYE",
                    "Response: ABSENT\n\n"
                    "✗ NO blink on corneal touch!\n"
                    "(Eye remains open — no image change)\n\n"
                    "Corneal sensation ABOLISHED.\n"
                    "Local anaesthetic blocked Na⁺ channels\n"
                    "in sensory nerve fibres.",
                    False
                )

    def swab_release(self, event):
        if not self.swab_touched:
            self.delete("swab")
            self.delete("swab_target")

    # ================================================================
    # Bind / unbind helpers
    # ================================================================
    def bind_ruler(self):
        self.clear_overlays()
        self.config(cursor="crosshair")
        self.bind("<ButtonPress-1>", self.ruler_press)
        self.bind("<B1-Motion>", self.ruler_drag)
        self.bind("<ButtonRelease-1>", self.ruler_release)
        self.unbind("<Motion>")
        self.unbind("<Leave>")

    def bind_torch(self):
        self.clear_overlays()
        self.config(cursor="none")
        self.unbind("<ButtonPress-1>")
        self.unbind("<B1-Motion>")
        self.unbind("<ButtonRelease-1>")
        self.bind("<Motion>", self.torch_move)
        self.bind("<Leave>", self.torch_leave)

    def bind_cotton(self):
        self.clear_overlays()
        self.config(cursor="crosshair")
        self.bind("<ButtonPress-1>", self.swab_press)
        self.bind("<B1-Motion>", self.swab_drag)
        self.bind("<ButtonRelease-1>", self.swab_release)
        self.unbind("<Motion>")
        self.unbind("<Leave>")

    def bind_click(self, callback):
        self.clear_overlays()
        self.config(cursor="hand2")
        self.bind("<ButtonPress-1>", callback)
        self.unbind("<B1-Motion>")
        self.unbind("<ButtonRelease-1>")
        self.unbind("<Motion>")
        self.unbind("<Leave>")

    def unbind_all_tools(self):
        self.clear_overlays()
        self.config(cursor="")
        for evt in ("<ButtonPress-1>", "<B1-Motion>", "<ButtonRelease-1>",
                    "<Motion>", "<Leave>"):
            self.unbind(evt)


# =============================================================================
# SCREENS
# =============================================================================
class SplashFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg3"])
        self.app = app

        self.canvas = tk.Canvas(
            self,
            width=700,
            height=500,
            bg=C["bg3"],
            highlightthickness=0
        )
        self.canvas.pack(expand=True)

        c = self.canvas

        # ---------- Logo ----------
        logo_path = get_image_path(app.image_dir, "mamc_logo")
        self.logo_alpha = 0

        if os.path.exists(logo_path):
            self.original_logo = Image.open(logo_path).resize((100, 100), Image.LANCZOS)
            self.logo = ImageTk.PhotoImage(self.original_logo)
            self.logo_id = c.create_image(350, 80, image=self.logo)

        # ---------- Titles ----------
        c.create_text(
            350, 165,
            text="RABBIT EYE EXPERIMENT",
            font=("Georgia", 28, "bold"),
            fill=C["gold"]
        )

        c.create_text(
            350, 198,
            text="SIMULATION SOFTWARE",
            font=("Georgia", 14),
            fill=C["gold_dim"]
        )

        c.create_line(210, 220, 490, 220, fill=C["gold"])

        c.create_text(
            350, 255,
            text="Computer-Assisted Learning for 2nd Year MBBS",
            font=("Helvetica", 15, "bold"),
            fill=C["text"]
        )

        # ENTER blinking prompt
        self.enter_id = c.create_text(
            350, 410,
            text="[ Press ENTER to Begin ]",
            font=("Helvetica", 14, "bold"),
            fill=C["gold"]
        )

        # Bottom right credits
        c.create_text(
            680, 430,
            text="Developed by",
            anchor="e",
            font=("Helvetica", 10),
            fill=C["text2"]
        )

        c.create_text(
            680, 450,
            text="Dr. Manu Kumar Shetty",
            anchor="e",
            font=("Helvetica", 11, "bold"),
            fill=C["gold"]
        )

        c.create_text(
            680, 470,
            text="Department of Pharmacology",
            anchor="e",
            font=("Helvetica", 10),
            fill=C["text3"]
        )

        c.create_text(
            680, 488,
            text="Maulana Azad Medical College",
            anchor="e",
            font=("Helvetica", 10),
            fill=C["text3"]
        )

        self.blink_state = True
        self.animate_enter()
        self.fade_logo()

        self.bind_all("<Return>", lambda e: app.show_setup())

    # ---------- Blinking ENTER ----------
    def animate_enter(self):
        if self.blink_state:
            self.canvas.itemconfigure(self.enter_id, state="hidden")
        else:
            self.canvas.itemconfigure(self.enter_id, state="normal")

        self.blink_state = not self.blink_state
        self.after(600, self.animate_enter)

    # ---------- Fade Logo ----------
    def fade_logo(self):
        try:
            self.logo_alpha += 20
            if self.logo_alpha > 255:
                return

            img = self.original_logo.copy()
            img.putalpha(self.logo_alpha)

            self.logo = ImageTk.PhotoImage(img)
            self.canvas.itemconfig(self.logo_id, image=self.logo)

            self.after(80, self.fade_logo)

        except:
            pass


class SetupFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self.selected_drug = tk.StringVar(value="")
        self.drug_eye = tk.StringVar(value="right")

        tk.Label(self, text="EXPERIMENT SETUP", font=("Helvetica", 18, "bold"),
                 bg=C["bg"], fg=C["gold"]).pack(pady=(30, 5))
        tk.Label(self, text="Select drug and choose which eye receives it. "
                            "The other eye gets Normal Saline (control).",
                 font=("Helvetica", 11), bg=C["bg"], fg=C["text2"]).pack(pady=(0, 20))

        main = tk.Frame(self, bg=C["bg"])
        main.pack(expand=True, fill="both", padx=40)

        # Drug selection
        left = tk.Frame(main, bg=C["card"], padx=20, pady=15)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        tk.Label(left, text="SELECT DRUG", font=("Helvetica", 11, "bold"),
                 bg=C["card"], fg=C["text2"]).pack(anchor="w", pady=(0, 10))
        for name, d in DRUG_DATA.items():
            tk.Radiobutton(left, text=f"{name}  ({d['class']})",
                           variable=self.selected_drug, value=name,
                           font=("Helvetica", 12), bg=C["card"], fg=C["text"],
                           selectcolor=C["bg"], activebackground=C["card"],
                           activeforeground=C["gold"], anchor="w", padx=10, pady=6
                           ).pack(fill="x", pady=2)

        # Eye assignment
        right = tk.Frame(main, bg=C["card"], padx=20, pady=15)
        right.pack(side="right", fill="both", expand=True, padx=(10, 0))
        tk.Label(right, text="DRUG EYE ASSIGNMENT", font=("Helvetica", 11, "bold"),
                 bg=C["card"], fg=C["text2"]).pack(anchor="w", pady=(0, 10))
        for val, txt in [("right", "Right Eye → Drug  |  Left Eye → Saline"),
                         ("left",  "Left Eye → Drug  |  Right Eye → Saline")]:
            tk.Radiobutton(right, text=txt, variable=self.drug_eye, value=val,
                           font=("Helvetica", 12), bg=C["card"], fg=C["text"],
                           selectcolor=C["bg"], activebackground=C["card"],
                           activeforeground=C["gold"], anchor="w", padx=10, pady=8
                           ).pack(fill="x", pady=2)
        tk.Label(right, text="\nThe control eye (Normal Saline) shows\n"
                              "baseline parameters for comparison.",
                 font=("Helvetica", 10, "italic"), bg=C["card"], fg=C["text3"],
                 justify="left").pack(anchor="w", pady=(10, 0))

        tk.Button(self, text="💉  Administer Drug & Begin Experiment",
                  font=("Helvetica", 14, "bold"), bg=C["gold"], fg=C["bg3"],
                  activebackground="#c49000", relief="flat", padx=30, pady=12,
                  cursor="hand2", command=self._go
                  ).pack(pady=25)

    def _go(self):
        drug = self.selected_drug.get()
        if not drug:
            messagebox.showwarning("Select Drug", "Please select a drug.")
            return
        self.app.start_experiment(drug, self.drug_eye.get())


# =============================================================================
# EXPERIMENT FRAME
# =============================================================================
class ExperimentFrame(tk.Frame):
    def __init__(self, parent, app, drug_name, drug_eye_side):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self.drug_name = drug_name
        self.drug_eye = drug_eye_side
        self.control_eye = "left" if drug_eye_side == "right" else "right"
        self.drug_data = DRUG_DATA[drug_name]
        self.active_tool = None

        self._build_ui()

    def _eye_data(self, side):
        return self.drug_data if side == self.drug_eye else BASELINE

    # ---- UI ----
    def _build_ui(self):
        # Top bar
        top = tk.Frame(self, bg=C["bg2"], height=45)
        top.pack(fill="x"); top.pack_propagate(False)

        logo_path = get_image_path(self.app.image_dir, "mamc_logo")
        if os.path.exists(logo_path):
            try:
                img = Image.open(logo_path).resize((30, 30), Image.LANCZOS)
                self._logo = ImageTk.PhotoImage(img)
                tk.Label(top, image=self._logo, bg=C["bg2"]).pack(side="left", padx=(10, 6))
            except Exception:
                pass

        tk.Label(top, text="Rabbit Eye Experiment", font=("Helvetica", 13, "bold"),
                 bg=C["bg2"], fg=C["gold"]).pack(side="left")
        tk.Label(top, text=f"  •  Drug: {self.drug_name}",
                 font=("Helvetica", 11), bg=C["bg2"], fg=C["text2"]).pack(side="left")
        tk.Button(top, text="↻ New Experiment", font=("Helvetica", 10),
                  bg=C["bg"], fg=C["text2"], relief="flat", cursor="hand2",
                  command=self.app.show_setup).pack(side="right", padx=10, pady=8)

        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True)

        # ---- Left: Tools ----
        tools_frame = tk.Frame(body, bg=C["card"], width=195)
        tools_frame.pack(side="left", fill="y", padx=(8, 4), pady=8)
        tools_frame.pack_propagate(False)

        tk.Label(tools_frame, text="TOOLS", font=("Helvetica", 10, "bold"),
                 bg=C["card"], fg=C["gold"]).pack(pady=(10, 5))

        tools = [
            ("📏 Ruler",        "ruler",       "Click & drag across pupil"),
            ("🔦 Torch",        "torch",       "Move near pupil to test"),
            ("🧹 Cotton Swab",  "cotton",      "Drag swab to cornea"),
            ("👁 Conjunctiva",  "conjunctiva", "Click to inspect"),
            ("✋ Tone/IOP",     "tone",        "Click to palpate"),
        ]
        self.tool_btns = {}
        for text, tid, tip in tools:
            btn = tk.Button(tools_frame, text=text, font=("Helvetica", 11),
                            bg=C["bg"], fg=C["text"], relief="flat", anchor="w",
                            padx=10, pady=6, cursor="hand2",
                            command=lambda t=tid: self._select_tool(t))
            btn.pack(fill="x", padx=8, pady=2)
            self.tool_btns[tid] = btn
            tk.Label(tools_frame, text=f"  {tip}", font=("Helvetica", 8),
                     bg=C["card"], fg=C["text3"]).pack(fill="x", padx=15)

        self.instruction = tk.Label(tools_frame, text="Select a tool,\nthen use it on an eye",
                                    font=("Helvetica", 9, "italic"),
                                    bg=C["card"], fg=C["gold"], justify="left", wraplength=170)
        self.instruction.pack(pady=(12, 5), padx=10, anchor="w")

        # Mechanism box
        mf = tk.Frame(tools_frame, bg=C["bg"], padx=8, pady=8)
        mf.pack(fill="x", padx=8, pady=(8, 8))
        tk.Label(mf, text="MECHANISM", font=("Helvetica", 9, "bold"),
                 bg=C["bg"], fg=C["amber"]).pack(anchor="w")
        tk.Label(mf, text=self.drug_data["mechanism"], font=("Helvetica", 8),
                 bg=C["bg"], fg=C["text2"], wraplength=160, justify="left").pack(anchor="w", pady=(4, 0))
        tk.Label(mf, text=f"Onset: {self.drug_data['onset']}  •  Duration: {self.drug_data['duration']}",
                 font=("Helvetica", 8), bg=C["bg"], fg=C["text3"]).pack(anchor="w", pady=(4, 0))

        # ---- Centre: Eyes ----
        centre = tk.Frame(body, bg=C["bg"])
        centre.pack(side="left", fill="both", expand=True, padx=4, pady=8)
        eyes = tk.Frame(centre, bg=C["bg"])
        eyes.pack(expand=True)

        for side in ["left", "right"]:
            fr = tk.Frame(eyes, bg=C["bg"])
            fr.pack(side="left", padx=12)
            is_drug = (side == self.drug_eye)
            lbl = f"💉 {self.drug_name}" if is_drug else "💧 Normal Saline"
            clr = self.drug_data["color"] if is_drug else C["green"]
            tk.Label(fr, text=lbl, font=("Helvetica", 10, "bold"),
                     bg=C["bg"], fg=clr).pack(pady=(0, 4))

            ec = EyeCanvas(fr, self._eye_data(side), self.app.image_dir, side, self)
            ec.pack()
            tk.Label(fr, text=f"{side.upper()} EYE", font=("Helvetica", 9, "bold"),
                     bg=C["bg"], fg=C["text3"]).pack(pady=(2, 0))

            if side == "left":
                self.left_eye = ec
            else:
                self.right_eye = ec

        # ---- Right: Results + Comparison ----
        rpanel = tk.Frame(body, bg=C["card"], width=280)
        rpanel.pack(side="right", fill="y", padx=(4, 8), pady=8)
        rpanel.pack_propagate(False)

        tk.Label(rpanel, text="FINDINGS", font=("Helvetica", 10, "bold"),
                 bg=C["card"], fg=C["gold"]).pack(pady=(10, 5))

        self.result_text = tk.Text(rpanel, font=("Consolas", 10), bg=C["bg"],
                                   fg=C["text"], relief="flat", wrap="word",
                                   padx=10, pady=8, height=12)
        self.result_text.pack(fill="x", padx=8)
        self.result_text.tag_configure("title", font=("Helvetica", 11, "bold"), foreground=C["gold"])
        self.result_text.tag_configure("good", foreground=C["green"])
        self.result_text.tag_configure("bad", foreground=C["red"])
        self.result_text.tag_configure("warn", foreground=C["amber"])
        self.result_text.tag_configure("info", foreground=C["text2"], font=("Consolas", 9))
        self.result_text.configure(state="disabled")

        # Comparison
        tk.Label(rpanel, text="COMPARISON", font=("Helvetica", 10, "bold"),
                 bg=C["card"], fg=C["gold"]).pack(pady=(12, 5))
        cf = tk.Frame(rpanel, bg=C["bg"], padx=10, pady=8)
        cf.pack(fill="x", padx=8)

        for col, (h, clr) in enumerate([("Parameter", C["text2"]),
                                         ("Drug", self.drug_data["color"]),
                                         ("Saline", C["green"])]):
            tk.Label(cf, text=h, font=("Helvetica", 9, "bold"),
                     bg=C["bg"], fg=clr).grid(row=0, column=col, padx=4, pady=2, sticky="w")

        rows = [("Pupil", self.drug_data["pupil_size"], "normal"),
                ("Light Ref.", self.drug_data["light_reflex"], "present"),
                ("Corneal Ref.", self.drug_data["corneal_reflex"], "present"),
                ("Conjunctiva", self.drug_data["conjunctiva"], "normal"),
                ("Tone", self.drug_data["tone"], "normal")]
        for r, (param, dv, sv) in enumerate(rows, 1):
            tk.Label(cf, text=param, font=("Helvetica", 9), bg=C["bg"],
                     fg=C["text2"]).grid(row=r, column=0, padx=4, pady=2, sticky="w")
            dc = C["green"] if dv in ("normal", "present", "no_change") else (
                 C["amber"] if dv in ("sluggish", "blanched") else C["red"])
            tk.Label(cf, text=dv.upper(), font=("Helvetica", 9, "bold"),
                     bg=C["bg"], fg=dc).grid(row=r, column=1, padx=4, pady=2)
            tk.Label(cf, text=sv.upper(), font=("Helvetica", 9, "bold"),
                     bg=C["bg"], fg=C["green"]).grid(row=r, column=2, padx=4, pady=2)

    # ---- tool selection ----
    def _select_tool(self, tool_id):
        self.active_tool = tool_id
        for tid, btn in self.tool_btns.items():
            btn.configure(bg=(C["gold"] if tid == tool_id else C["bg"]),
                          fg=(C["bg3"] if tid == tool_id else C["text"]))

        instructions = {
            "ruler":       "📏 Click & drag across the pupil\n    on either eye to measure.",
            "torch":       "🔦 Move your mouse over an eye.\n    Watch the pupil react!",
            "cotton":      "🧹 Click & drag the cotton swab\n    to the centre of the eye.",
            "conjunctiva": "👁 Click on an eye to inspect\n    conjunctival vasculature.",
            "tone":        "✋ Click on an eye to palpate\n    for intraocular pressure.",
        }
        self.instruction.configure(text=instructions.get(tool_id, ""))

        # Bind appropriate events on both eye canvases
        for eye in (self.left_eye, self.right_eye):
            if tool_id == "ruler":
                eye.bind_ruler()
            elif tool_id == "torch":
                eye.bind_torch()
            elif tool_id == "cotton":
                eye.bind_cotton()
            elif tool_id == "conjunctiva":
                eye.bind_click(lambda e, s=eye.side: self._click_conjunctiva(s))
            elif tool_id == "tone":
                eye.bind_click(lambda e, s=eye.side: self._click_tone(s))

    def _click_conjunctiva(self, side):
        data = self._eye_data(side)
        status = data["conjunctiva"]
        desc = data["conjunctiva_desc"]
        ok = status in ("normal", "no_change")
        self.show_result(
            f"👁 CONJUNCTIVA — {side.upper()} EYE",
            f"Status: {status.upper()}\n{desc}\n\n"
            + ("Normal pink vasculature."
               if ok else
               "Congested — parasympathomimetic vasodilation."
               if status == "congested" else
               "Blanched — sympathomimetic vasoconstriction."),
            ok
        )

    def _click_tone(self, side):
        data = self._eye_data(side)
        tone = data["tone"]
        desc = data["tone_desc"]
        ok = tone == "normal"
        self.show_result(
            f"✋ TONE (IOP) — {side.upper()} EYE",
            f"Tone: {tone.upper()}\n{desc}\n\n"
            + ("Normal firmness on palpation."
               if ok else
               "Globe feels HARD — elevated IOP."
               if tone == "increased" else
               "Globe feels SOFT — reduced IOP."),
            ok
        )

    # ---- result display ----
    def show_result(self, title, body, is_good=True):
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("end", title + "\n\n", "title")
        self.result_text.insert("end", body, "good" if is_good else "bad")
        self.result_text.configure(state="disabled")


# =============================================================================
class RabbitEyeApp:
    def __init__(self, root, image_dir=None):
        self.root = root
        self.root.title("Rabbit Eye Experiment — MAMC, New Delhi")
        self.root.configure(bg=C["bg3"])
        if image_dir and os.path.isdir(image_dir):
            self.image_dir = image_dir
        else:
            # Support PyInstaller --onefile (images bundled inside .exe)
            if getattr(sys, 'frozen', False):
                # Running as compiled .exe
                base_dir = sys._MEIPASS
            else:
                # Running as normal .py script
                base_dir = os.path.dirname(os.path.abspath(__file__))

            self.image_dir = os.path.join(base_dir, "images")
            if not os.path.isdir(self.image_dir):
                self.image_dir = base_dir
        try:
            self.root.state('zoomed')
        except Exception:
            try:
                self.root.attributes('-zoomed', True)
            except Exception:
                self.root.geometry("1280x780")
        self.current_frame = None
        self.show_splash()

    def _switch(self, frame):
        if self.current_frame:
            self.current_frame.destroy()
        self.current_frame = frame
        frame.pack(fill="both", expand=True)

    def show_splash(self):
        self._switch(SplashFrame(self.root, self))

    def show_setup(self):
        self._switch(SetupFrame(self.root, self))

    def start_experiment(self, drug, eye):
        self._switch(ExperimentFrame(self.root, self, drug, eye))


def main():
    root = tk.Tk()
    image_dir = sys.argv[1] if len(sys.argv) > 1 else None
    RabbitEyeApp(root, image_dir=image_dir)
    root.mainloop()


if __name__ == "__main__":
    main()
