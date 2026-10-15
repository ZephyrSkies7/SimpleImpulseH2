"""
Simple Impulse H2 runner with native game rumble muting, utilising FH2TriggerBridge.

Shows a small status window instead of a console:
  * amber  - waiting for Forza Horizon 2 (azimuth.exe)
  * green  - hooked in and streaming haptics
  * red    - something went wrong (the window says what)

Intensity settings live in config.ini next to the program. Edit the file while the game
is running (changes apply within a second) or use the sliders and press "Save settings".
"""
import configparser
import ctypes
import math
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox

import azimuth_hook

DLL_NAME = "FH2TriggerBridge.dll"
CONFIG_NAME = "config.ini"
UPDATE_INTERVAL = 0.016      # ~60 FPS update rate
RETRY_DELAY = 5.0            # seconds between attach attempts after an error
CONFIG_POLL_SECONDS = 1.0    # how often config.ini is checked for edits

# Intensity multipliers. 1.0 = exactly what the game sends, 0.0 = off.
DEFAULTS = {"motor_intensity": 1.0, "trigger_intensity": 1.0}
MAX_INTENSITY = 2.0

CONFIG_TEMPLATE = """\
; Simple Impulse H2 settings
; Edit this file while the game is running - changes apply within a second.
; (The sliders in the app window change the same values; "Save settings" writes them here.)
;
; 1.0 = full strength as the game sends it, 0.0 = off, up to 2.0 = boosted.

[haptics]
; Main (hand-grip) motors: collisions, surface bumps, engine.
motor_intensity = {motor:.2f}
; Impulse triggers: braking / acceleration slip.
trigger_intensity = {trigger:.2f}
"""


# ---------------------------------------------------------------- helpers ---

def app_dir():
    """Folder the program lives in (the .exe when frozen, this script otherwise)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def find_dll():
    # Next to the exe, then one folder up (running from source/), then the working dir.
    for folder in (app_dir(), os.path.dirname(app_dir()), os.getcwd()):
        path = os.path.join(folder, DLL_NAME)
        if os.path.isfile(path):
            return path
    return None


def load_dll():
    path = find_dll()
    if not path:
        raise RuntimeError(f"{DLL_NAME} was not found. Keep it in the same folder as the program.")
    dll = ctypes.CDLL(path)
    dll.SetControllerRumble.argtypes = [
        ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float
    ]
    dll.SetControllerRumble.restype = None
    return dll


class Status:
    """Tiny thread-safe holder so the worker thread never touches Tk widgets."""

    def __init__(self):
        self._lock = threading.Lock()
        self._state, self._detail = "waiting", ""

    def set(self, state, detail=""):
        with self._lock:
            self._state, self._detail = state, detail

    def get(self):
        with self._lock:
            return self._state, self._detail


# --------------------------------------------------------------- settings ---

def _clamp(v):
    return min(max(v, 0.0), MAX_INTENSITY)


class Settings:
    """Live intensity values, backed by config.ini.

    * get() is what the haptics loop reads every frame.
    * poll() (called from the GUI timer) reloads config.ini when it changes on disk.
    * set() is the sliders; it applies instantly but isn't written until save().
    * A broken config.ini never takes effect: the last good values stay active.
    """

    def __init__(self, path):
        self.path = path
        self._lock = threading.Lock()
        self._values = dict(DEFAULTS)   # what's live right now
        self._saved = dict(DEFAULTS)    # what config.ini says
        self._sig = None                # (mtime_ns, size) of the file we last read/wrote
        self._next_check = 0.0
        self.rev = 0                    # bumps whenever values change because of the file
        self.error = ""
        if not os.path.exists(path):
            self._write(self._values)   # drop a commented default file so people can find it
        self._load()

    # -- file access ---------------------------------------------------------
    def _stat_sig(self):
        try:
            st = os.stat(self.path)
            return (st.st_mtime_ns, st.st_size)
        except OSError:
            return None

    def _parse(self):
        cp = configparser.ConfigParser(inline_comment_prefixes=(";", "#"))
        with open(self.path, encoding="utf-8-sig") as f:
            cp.read_file(f)
        if not cp.has_section("haptics"):
            raise ValueError("missing [haptics] section")
        out = {}
        for key, default in DEFAULTS.items():
            raw = cp.get("haptics", key, fallback=None)
            if raw is None:
                out[key] = default
                continue
            try:
                v = float(raw)
            except ValueError:
                raise ValueError(f"{key} must be a number, not '{raw}'") from None
            if not math.isfinite(v):
                raise ValueError(f"{key} must be a number, not '{raw}'")
            out[key] = _clamp(v)
        return out

    def _write(self, values):
        text = CONFIG_TEMPLATE.format(motor=values["motor_intensity"],
                                      trigger=values["trigger_intensity"])
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, self.path)   # atomic, so a reader never sees a half-written file

    def _load(self):
        sig = self._stat_sig()
        try:
            vals = self._parse()
        except (OSError, ValueError, configparser.Error) as e:
            if isinstance(e, configparser.Error):
                e = "not a valid settings file (expected a [haptics] section with key = value lines)"
            with self._lock:
                self._sig = sig      # don't re-report until the file changes again
                self.error = f"{CONFIG_NAME}: {e}. Keeping previous values."
            return
        with self._lock:
            self._values, self._saved = dict(vals), dict(vals)
            self._sig, self.error = sig, ""
            self.rev += 1

    # -- public API ----------------------------------------------------------
    def poll(self):
        now = time.monotonic()
        if now < self._next_check:
            return
        self._next_check = now + CONFIG_POLL_SECONDS
        sig = self._stat_sig()
        if sig is not None and sig != self._sig:
            self._load()

    def get(self):
        with self._lock:
            return self._values["motor_intensity"], self._values["trigger_intensity"]

    def set(self, key, value):
        with self._lock:
            self._values[key] = _clamp(value)

    def snapshot(self):
        with self._lock:
            return {
                "motor": self._values["motor_intensity"],
                "trigger": self._values["trigger_intensity"],
                "dirty": self._values != self._saved,
                "error": self.error,
                "rev": self.rev,
            }

    def save(self):
        """Write the live values to config.ini. Returns "" on success, else a message."""
        with self._lock:
            vals = dict(self._values)
        try:
            self._write(vals)
        except OSError as e:
            return f"Couldn't save {CONFIG_NAME}: {e.strerror or e}"
        with self._lock:
            self._saved = vals
            self._sig = self._stat_sig()
            self.error = ""
        return ""


# ----------------------------------------------------------------- worker ---

def stream(hk, dll, status, stop, settings):
    """Forward Azimuth's rumble to the controller until the game exits or we're told to stop."""
    # Mute the game executable's native rumble stream so only our managed stream reaches the controller.
    hk.mute_rumble(True)
    status.set("hooked")

    while not stop.is_set() and hk.alive():
        try:
            lm, rm, lt, rt, _calls = hk.levels()
        except OSError:
            break  # game went away mid-read

        motor, trigger = settings.get()

        # Just scale and forward. Which channels win when the trigger is active
        # (the "motor cut") is decided in one place only: FH2TriggerBridge.dll.
        dll.SetControllerRumble(
            ctypes.c_float(lm * motor),
            ctypes.c_float(rm * motor),
            ctypes.c_float(lt * trigger),
            ctypes.c_float(rt * trigger),
        )
        stop.wait(UPDATE_INTERVAL)


def cleanup(hk, dll):
    try:
        dll.SetControllerRumble(0.0, 0.0, 0.0, 0.0)
    except Exception:
        pass
    try:
        # Restores normal game rumble and the original game bytes.
        hk.unhook()
    except Exception:
        pass


def worker(status, stop, settings):
    try:
        dll = load_dll()
    except Exception as e:
        status.set("error", str(e))
        return

    retrying = False
    while not stop.is_set():
        hk = None
        try:
            # After a failed attach the game is already running, so don't re-wait for it to settle.
            hk = azimuth_hook.wait_for_game(stop, status.set, settle=0 if retrying else 8.0)
            if hk is None:
                break
            retrying = False
            stream(hk, dll, status, stop, settings)
        except Exception as e:
            retrying = True
            status.set("error", str(e))
            delay = RETRY_DELAY
        else:
            status.set("waiting")  # game exited
            delay = 2.0            # give the old process a moment to disappear
        finally:
            if hk is not None:
                cleanup(hk, dll)
        stop.wait(delay)


# -------------------------------------------------------------------- GUI ---

COLORS = {
    "waiting":   "#e0a100",
    "attaching": "#e0a100",
    "hooked":    "#2fb344",
    "error":     "#d63939",
}

MESSAGES = {
    "waiting":   ("Waiting for Azimuth\u2026", "Launch Forza Horizon 2 via Azimuth."),
    "attaching": ("Azimuth found \u2013 attaching\u2026", "This takes a few seconds."),
    "hooked":    ("Hooked \u2013 haptics active", "You can minimize this window."),
}

SLIDERS = (
    ("motor_intensity", "Motor intensity"),
    ("trigger_intensity", "Trigger intensity"),
)

FONT = "Segoe UI"


class App:
    def __init__(self, settings):
        self.settings = settings
        self._syncing = False
        self._save_error = ""
        self._rev = -1

        self.root = tk.Tk()
        self.root.title("Simple Impulse H2")
        self.root.resizable(False, False)

        outer = tk.Frame(self.root, padx=16, pady=14)
        outer.pack()

        # --- status ---
        top = tk.Frame(outer)
        top.pack(fill="x")
        self.dot = tk.Canvas(top, width=22, height=22, highlightthickness=0)
        self.dot.grid(row=0, column=0, rowspan=2, padx=(0, 12))
        self.light = self.dot.create_oval(2, 2, 20, 20, fill=COLORS["waiting"], outline="")
        self.title = tk.Label(top, anchor="w", justify="left", width=34, font=(FONT, 11, "bold"))
        self.title.grid(row=0, column=1, sticky="w")
        self.detail = tk.Label(top, anchor="w", justify="left", width=40, wraplength=300,
                               font=(FONT, 9), fg="#666666")
        self.detail.grid(row=1, column=1, sticky="w")

        tk.Frame(outer, height=1, bg="#c8c8c8").pack(fill="x", pady=10)

        # --- sliders ---
        box = tk.Frame(outer)
        box.pack(fill="x")
        self.scales, self.pct = {}, {}
        for row, (key, label) in enumerate(SLIDERS):
            tk.Label(box, text=label, anchor="w", width=15, font=(FONT, 9)).grid(
                row=row, column=0, sticky="w", pady=2)
            scale = tk.Scale(box, from_=0, to=round(MAX_INTENSITY * 100), orient="horizontal",
                             length=210, showvalue=False, resolution=1, highlightthickness=0,
                             command=lambda v, k=key: self.on_slide(k, v))
            scale.grid(row=row, column=1, padx=6)
            pct = tk.Label(box, width=5, anchor="e", font=(FONT, 9, "bold"))
            pct.grid(row=row, column=2)
            self.scales[key], self.pct[key] = scale, pct

        # --- save row ---
        foot = tk.Frame(outer)
        foot.pack(fill="x", pady=(10, 0))
        self.note = tk.Label(foot, anchor="w", justify="left", wraplength=260, font=(FONT, 9))
        self.note.pack(side="left", fill="x", expand=True)
        self.save_btn = tk.Button(foot, text="Save settings", command=self.save, state="disabled")
        self.save_btn.pack(side="right")

        self.stop = threading.Event()
        self.status = Status()
        self.thread = threading.Thread(target=worker, args=(self.status, self.stop, settings),
                                       daemon=True)
        self.thread.start()

        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.refresh()

    # -- slider <-> settings -------------------------------------------------
    def on_slide(self, key, value):
        if self._syncing:
            return
        self.settings.set(key, int(float(value)) / 100.0)
        self._save_error = ""
        self.pct[key].config(text=f"{int(float(value))}%")

    def sync_sliders(self, snap):
        """Move the sliders to match the live values (e.g. after config.ini was edited)."""
        self._syncing = True
        try:
            for key, snap_key in (("motor_intensity", "motor"), ("trigger_intensity", "trigger")):
                percent = round(snap[snap_key] * 100)
                self.scales[key].set(percent)
                self.pct[key].config(text=f"{percent}%")
        finally:
            self._syncing = False

    def save(self):
        self._save_error = self.settings.save()

    # -- periodic refresh ----------------------------------------------------
    def refresh(self):
        self.settings.poll()
        snap = self.settings.snapshot()
        if snap["rev"] != self._rev:
            self._rev = snap["rev"]
            self.sync_sliders(snap)

        state, detail = self.status.get()
        if state == "error":
            title, sub = "Something went wrong", detail
        else:
            title, sub = MESSAGES[state]
        self.dot.itemconfig(self.light, fill=COLORS[state])
        self.title.config(text=title)
        self.detail.config(text=sub)

        problem = snap["error"] or self._save_error
        if problem:
            self.note.config(text=problem, fg=COLORS["error"])
        elif snap["dirty"]:
            self.note.config(text="Unsaved changes (already applied live).", fg="#a26a00")
        else:
            self.note.config(text="Changes apply live. config.ini edits too.", fg="#666666")
        self.save_btn.config(state="normal" if (snap["dirty"] or problem) else "disabled")

        self.root.after(250, self.refresh)

    # -- shutdown ------------------------------------------------------------
    def close(self):
        if self.settings.snapshot()["dirty"]:
            answer = messagebox.askyesnocancel(
                "Simple Impulse H2", "You have unsaved settings. Save them before closing?")
            if answer is None:
                return
            if answer:
                err = self.settings.save()
                if err:
                    messagebox.showerror("Simple Impulse H2", err)
                    return
        # Let the worker restore rumble and un-patch the game before we exit.
        self.stop.set()
        self.thread.join(timeout=3)
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # crisp text on high-DPI screens
    except Exception:
        pass
    App(Settings(os.path.join(app_dir(), CONFIG_NAME))).run()


if __name__ == "__main__":
    main()
