"""
STARK Screen Monitor  v2
Fixed:
  - Reads only meaningful text (skips tabs, browser UI, ads)
  - Can scroll down and read full page
  - Summarise mode
  - Smart filtering
"""

import pytesseract
from PIL import ImageGrab
import pyautogui
import time
import os
import config

# Set tesseract path — use config value if it exists, otherwise let pytesseract
# find it on the system PATH (works on Linux/macOS without change)
if os.path.isfile(config.TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_PATH
elif os.name == "nt":
    # Common Windows fallback paths
    _fallbacks = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for _fb in _fallbacks:
        if os.path.isfile(_fb):
            pytesseract.pytesseract.tesseract_cmd = _fb
            break

# Words that indicate UI chrome / browser tabs to ignore
IGNORE_PATTERNS = [
    "google", "chrome", "microsoft", "edge", "firefox",
    "file edit view", "new tab", "address bar",
    "sign in", "sign up", "cookie", "accept all",
    "advertisement", "sponsored", "promoted",
    "youtube.com", "facebook.com", "twitter.com",
    "http://", "https://", "www.",
    "©", "privacy policy", "terms of service",
    "all rights reserved", "subscribe", "bell icon",
    "like share", "comments", "views", "ago",
]


def _is_noise(line: str) -> bool:
    """Return True if line is browser UI, ads, or irrelevant."""
    l = line.lower().strip()
    if len(l) < 3:
        return True
    if any(p in l for p in IGNORE_PATTERNS):
        return True
    # Skip lines that are just symbols or numbers
    if sum(c.isalpha() for c in l) < 3:
        return True
    return False


def _clean_text(raw: str) -> str:
    """Filter raw OCR text to keep only meaningful content."""
    lines = raw.splitlines()
    clean = []
    for line in lines:
        line = line.strip()
        if line and not _is_noise(line):
            clean.append(line)
    return "\n".join(clean)


class ScreenMonitor:
    def __init__(self, voice):
        self._voice = voice
        print("[STARK Screen] Initialised.")

    # ── Capture and clean ─────────────────────────────────────────────────────
    def read_screen(self) -> str:
        try:
            screenshot = ImageGrab.grab()
            raw  = pytesseract.image_to_string(screenshot)
            return _clean_text(raw).strip()
        except Exception as e:
            print(f"[Screen read error] {e}")
            return ""

    # ── Speak screen text (filtered) ──────────────────────────────────────────
    def speak_screen(self) -> None:
        text = self.read_screen()
        if not text:
            self._voice.speak("I cannot read any text on the screen right now, Sir.")
            return
        self._voice.speak("Reading the main content on your screen, Sir.")
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        # Speak first 40 meaningful lines
        chunk = " ".join(lines[:40])
        if len(chunk) > 800:
            chunk = chunk[:800]
        self._voice.speak(chunk)

    # ── Scroll down and read full page ────────────────────────────────────────
    def read_full_page(self, ask_ai_fn=None) -> str:
        """
        Scroll to top, then scroll down reading each section.
        If ask_ai_fn provided, returns AI summary instead of raw text.
        """
        self._voice.speak("Reading the full page for you, Sir. Scrolling down.")

        # Go to top first
        pyautogui.hotkey("ctrl", "Home")
        time.sleep(1)

        all_text = []
        scroll_steps = 6  # how many scroll downs

        for i in range(scroll_steps):
            text = self.read_screen()
            if text:
                all_text.append(text)
            time.sleep(0.5)
            pyautogui.scroll(-800)  # scroll down
            time.sleep(1)

        full = "\n".join(all_text)
        full = _clean_text(full)

        # Deduplicate lines
        seen  = set()
        dedup = []
        for line in full.splitlines():
            if line not in seen:
                seen.add(line)
                dedup.append(line)
        full = "\n".join(dedup)

        if ask_ai_fn:
            self._voice.speak("I have read the full page. Let me summarise it for you, Sir.")
            summary = ask_ai_fn(
                f"Summarise this page content clearly and briefly for Sir. "
                f"Focus on the most important points only:\n\n{full[:4000]}"
            )
            self._voice.speak(summary)
            return summary
        else:
            lines = [l for l in full.splitlines() if l.strip()]
            chunk = " ".join(lines[:50])
            if len(chunk) > 1000: chunk = chunk[:1000]
            self._voice.speak(chunk)
            return full

    # ── Read and summarise ────────────────────────────────────────────────────
    def read_and_summarise(self, ask_ai_fn) -> str:
        """Read current screen and give AI summary."""
        text = self.read_screen()
        if not text:
            self._voice.speak("Nothing meaningful to read on screen, Sir.")
            return ""
        self._voice.speak("Let me summarise what I see on your screen, Sir.")
        summary = ask_ai_fn(
            f"Summarise this screen content briefly and clearly. "
            f"Skip any navigation, ads, or browser UI. Focus on main content:\n\n{text[:3000]}"
        )
        self._voice.speak(summary)
        return summary

    # ── Code analysis ─────────────────────────────────────────────────────────
    def get_screen_code(self) -> str:
        return self.read_screen()

    # ── Region read ───────────────────────────────────────────────────────────
    def read_region(self, x, y, w, h) -> str:
        try:
            shot = ImageGrab.grab(bbox=(x, y, x+w, y+h))
            return pytesseract.image_to_string(shot).strip()
        except Exception as e:
            print(f"[Region read] {e}")
            return ""