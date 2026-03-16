"""
STARK Meeting Assistant
Transparent overlay window that shows AI answers during online meetings.
The window stays on top and is NOT visible to screen-share (no audio).
"""

import threading
import tkinter as tk


class MeetingAssistant:
    def __init__(self):
        self._window  = None
        self._label   = None
        self._running = False
        print("[STARK Meeting] Initialised.")

    # ── Show / hide ───────────────────────────────────────────────────────────
    def show_answer(self, text: str) -> None:
        """Display answer on the floating overlay."""
        if not self._running:
            self._start_window()
        self._update_text(text)

    def hide(self) -> None:
        if self._window:
            try:
                self._window.withdraw()
            except Exception:
                pass

    # ── Internal window ───────────────────────────────────────────────────────
    def _start_window(self) -> None:
        self._running = True
        t = threading.Thread(target=self._run_tk, daemon=True)
        t.start()
        # Give tk time to init
        import time
        time.sleep(0.4)

    def _run_tk(self) -> None:
        self._window = tk.Tk()
        self._window.title("STARK Answer")
        self._window.attributes("-topmost", True)
        self._window.attributes("-alpha", 0.88)          # slight transparency
        self._window.overrideredirect(True)               # no title bar
        self._window.configure(bg="#0A0A0A")

        # Position: bottom-right corner
        sw = self._window.winfo_screenwidth()
        sh = self._window.winfo_screenheight()
        w, h = 600, 160
        x, y = sw - w - 20, sh - h - 60
        self._window.geometry(f"{w}x{h}+{x}+{y}")

        header = tk.Label(
            self._window,
            text="⚡ STARK  —  Meeting Answer",
            bg="#0A0A0A", fg="#00FF88",
            font=("Consolas", 10, "bold"),
            anchor="w",
        )
        header.pack(fill="x", padx=8, pady=(6, 0))

        self._label = tk.Label(
            self._window,
            text="",
            bg="#0A0A0A", fg="#FFFFFF",
            font=("Consolas", 11),
            wraplength=580,
            justify="left",
            anchor="nw",
        )
        self._label.pack(fill="both", expand=True, padx=8, pady=4)

        close_btn = tk.Button(
            self._window,
            text="✕  Close",
            bg="#1A1A1A", fg="#FF4444",
            relief="flat",
            font=("Consolas", 9),
            command=self._window.withdraw,
        )
        close_btn.pack(side="right", padx=8, pady=4)

        self._window.mainloop()

    def _update_text(self, text: str) -> None:
        def _do():
            if self._label:
                self._label.config(text=text)
            if self._window:
                self._window.deiconify()
        if self._window:
            self._window.after(0, _do)
        else:
            # window not ready yet - retry shortly
            import time, threading
            def _retry():
                time.sleep(0.6)
                self._update_text(text)
            threading.Thread(target=_retry, daemon=True).start()
