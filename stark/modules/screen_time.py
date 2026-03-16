"""
STARK Screen Time & Activity Monitor
─────────────────────────────────────
Features:
  - Detects what you are doing (coding, writing, browsing, designing)
  - Tracks productive time per activity
  - Skill growth tracker (hours per language)
  - Break reminders based on actual screen activity
  - Goal tracking
  - End of day reflection
  - Micro-coaching based on detected activity
  - Milestone celebrations
"""

import time
import json
import os
import re
import threading
import datetime
import pyautogui
from PIL import ImageGrab
import pytesseract
import config

SCREENTIME_FILE = "stark_screentime.json"
GOALS_FILE      = "stark_goals.json"

# Activity detection keywords
ACTIVITY_PATTERNS = {
    "python":     ["def ", "import ", "print(", "class ", ".py", "python", "pip"],
    "javascript": ["function", "const ", "let ", "var ", "console.log", ".js", "react"],
    "html":       ["<html", "<div", "<body", "<head", "<!DOCTYPE", ".html", "css"],
    "java":       ["public class", "void main", "System.out", ".java"],
    "coding":     ["def ", "function", "class ", "import", "return", "for(", "while("],
    "writing":    ["word", "docs", "notepad", "essay", "paragraph", "chapter"],
    "designing":  ["figma", "canva", "photoshop", "illustrator", "design"],
    "browsing":   ["youtube", "facebook", "instagram", "twitter", "netflix", "reddit"],
    "gaming":     ["game", "steam", "minecraft", "roblox", "fortnite"],
    "studying":   ["pdf", "slides", "lecture", "notes", "study", "chapter"],
    "excel":      ["excel", ".xlsx", "spreadsheet", "formula", "=sum"],
}

CODING_TIPS = {
    "python": [
        "Try using list comprehensions — they are faster and cleaner Sir.",
        "The 'enumerate()' function is very useful for loops with index.",
        "Use f-strings instead of .format() for cleaner code.",
        "Consider using 'dataclasses' for simple data containers.",
    ],
    "javascript": [
        "Use 'const' by default, 'let' only when reassigning Sir.",
        "Arrow functions make callbacks much cleaner.",
        "Optional chaining (?.) prevents undefined errors cleanly.",
        "Async/await is cleaner than promise chains.",
    ],
    "html": [
        "Use semantic HTML tags like <article>, <section>, <nav> Sir.",
        "CSS Grid is powerful for complex layouts.",
        "Always add alt text to images for accessibility.",
        "Use CSS variables for consistent theming.",
    ],
    "coding": [
        "Break large functions into smaller, focused ones Sir.",
        "Write comments explaining WHY, not just WHAT.",
        "Use meaningful variable names — code should read like English.",
        "Test small pieces of code before building larger features.",
    ],
}

ENCOURAGEMENTS = [
    "You're doing great, Sir! Keep going.",
    "Excellent focus, Sir! You're making real progress.",
    "That's impressive work, Sir!",
    "You're on fire today, Sir!",
    "Great consistency, Sir! This is how skills are built.",
]

BREAK_SUGGESTIONS = [
    "Take a 5-minute walk Sir — it refreshes the mind.",
    "Look away from the screen for 20 seconds Sir — your eyes need rest.",
    "Drink some water and stretch Sir.",
    "Take 10 deep breaths Sir — clears mental fog.",
    "Stand up and stretch for 2 minutes Sir.",
]


class ScreenTimeMonitor:
    def __init__(self, voice, ask_ai_fn):
        self._voice        = voice
        self._ask_ai       = ask_ai_fn
        self._running      = False
        self._data         = self._load_data()
        self._goals        = self._load_goals()
        self._current_act  = "idle"
        self._act_start    = time.time()
        self._session_acts = {}   # activity → seconds this session
        self._last_tip_time = 0
        self._last_check_time = 0
        self._milestone_shown = set()
        self._thread       = None
        print("[STARK ScreenTime] Initialised.")

    # ── Persistence ───────────────────────────────────────────────────────────
    def _load_data(self) -> dict:
        if os.path.exists(SCREENTIME_FILE):
            try:
                with open(SCREENTIME_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "daily":    {},    # date → {activity: seconds}
            "total":    {},    # activity → total seconds ever
            "sessions": 0,
            "streaks":  {},
        }

    def _load_goals(self) -> list:
        if os.path.exists(GOALS_FILE):
            try:
                with open(GOALS_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save(self):
        with open(SCREENTIME_FILE, "w") as f:
            json.dump(self._data, f, indent=2)

    def _save_goals(self):
        with open(GOALS_FILE, "w") as f:
            json.dump(self._goals, f, indent=2)

    # ── Start monitoring ──────────────────────────────────────────────────────
    def start(self):
        self._running = True
        self._data["sessions"] = self._data.get("sessions", 0) + 1
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        print("[ScreenTime] Monitoring started.")

    def stop(self):
        self._running = False

    # ── Detection loop ────────────────────────────────────────────────────────
    def _monitor_loop(self):
        check_interval = 30   # check every 30 seconds
        tip_interval   = 600  # give tip every 10 minutes
        milestone_check = 300 # check milestones every 5 minutes

        while self._running:
            time.sleep(check_interval)
            now = time.time()

            # Detect current activity
            activity = self._detect_activity()
            self._update_activity(activity)

            # Give contextual tip every 10 minutes
            # Tips disabled — no spam
            pass  # self._give_tip(activity)

            # Check milestones every 5 minutes
            if now - self._last_check_time > milestone_check:
                self._check_milestones()
                self._last_check_time = now

    # ── Detect activity from screen ───────────────────────────────────────────
    def _detect_activity(self) -> str:
        try:
            # Take small screenshot of title bar area
            shot = ImageGrab.grab(bbox=(0, 0, 1920, 50))
            text = pytesseract.image_to_string(shot).lower()

            for activity, keywords in ACTIVITY_PATTERNS.items():
                if any(k.lower() in text for k in keywords):
                    return activity

            # Check taskbar area too
            shot2 = ImageGrab.grab(bbox=(0, 0, 800, 100))
            text2 = pytesseract.image_to_string(shot2).lower()
            for activity, keywords in ACTIVITY_PATTERNS.items():
                if any(k.lower() in text2 for k in keywords):
                    return activity

        except Exception:
            pass
        return "general"

    # ── Update activity time ──────────────────────────────────────────────────
    def _update_activity(self, activity: str):
        now  = time.time()
        date = datetime.date.today().isoformat()

        # Update session tracker
        if activity not in self._session_acts:
            self._session_acts[activity] = 0
        self._session_acts[activity] += 30   # 30 second intervals

        # Update daily data
        if date not in self._data["daily"]:
            self._data["daily"][date] = {}
        if activity not in self._data["daily"][date]:
            self._data["daily"][date][activity] = 0
        self._data["daily"][date][activity] += 30

        # Update total
        if activity not in self._data["total"]:
            self._data["total"][activity] = 0
        self._data["total"][activity] += 30

        # Detect activity change
        if activity != self._current_act:
            if self._current_act != "idle" and self._current_act != "general":
                self._voice.speak(
                    f"Switching from {self._current_act} to {activity}, Sir."
                )
            self._current_act = activity
            self._act_start   = now

        self._save()

    # ── Give contextual tip ───────────────────────────────────────────────────
    def _give_tip(self, activity: str):
        import random
        tips = CODING_TIPS.get(activity, CODING_TIPS.get("coding", []))
        if tips:
            tip = random.choice(tips)
            self._voice.speak(f"Quick tip, Sir: {tip}")

    # ── Check milestones ──────────────────────────────────────────────────────
    def _check_milestones(self):
        import random
        date    = datetime.date.today().isoformat()
        today   = self._data["daily"].get(date, {})
        total_today = sum(today.values())

        milestones = [
            (3600,   "You've been productive for 1 hour today, Sir! Keep it up!"),
            (7200,   "Two hours of solid work today, Sir! Excellent focus!"),
            (10800,  "Three hours in, Sir! You're doing amazing work!"),
            (18000,  "Five hours of productivity, Sir! Incredible dedication!"),
        ]

        for seconds, message in milestones:
            key = f"{date}_{seconds}"
            if total_today >= seconds and key not in self._milestone_shown:
                self._milestone_shown.add(key)
                import threading as _mt
                _mt.Thread(target=self._voice.speak, args=(message,), daemon=True).start()

        # Check goals
        for goal in self._goals:
            if goal.get("activity") == self._current_act:
                target = goal.get("daily_hours", 2) * 3600
                current = today.get(self._current_act, 0)
                key = f"{date}_goal_{goal.get('name','')}"
                if current >= target and key not in self._milestone_shown:
                    self._milestone_shown.add(key)
                    self._voice.speak(
                        f"Sir! You have reached your daily goal of "
                        f"{goal.get('daily_hours')} hours for {goal.get('name')}! "
                        f"That is amazing progress!"
                    )

    # ── Commands ──────────────────────────────────────────────────────────────
    def get_today_summary(self) -> str:
        date  = datetime.date.today().isoformat()
        today = self._data["daily"].get(date, {})

        if not today:
            return "No screen activity recorded today yet, Sir."

        lines = [f"Today's screen time summary, Sir:"]
        total = 0
        for act, secs in sorted(today.items(), key=lambda x: -x[1]):
            hrs  = secs // 3600
            mins = (secs % 3600) // 60
            if hrs > 0:
                lines.append(f"  {act.capitalize()}: {hrs}h {mins}m")
            elif mins > 0:
                lines.append(f"  {act.capitalize()}: {mins} minutes")
            total += secs

        total_hrs  = total // 3600
        total_mins = (total % 3600) // 60
        lines.append(f"  Total: {total_hrs}h {total_mins}m")
        return "\n".join(lines)

    def get_current_activity(self) -> str:
        elapsed = int(time.time() - self._act_start)
        mins    = elapsed // 60
        return (f"You are currently doing {self._current_act}, Sir. "
                f"You have been at it for {mins} minutes.")

    def set_goal(self, name: str, activity: str, daily_hours: float):
        self._goals.append({
            "name":        name,
            "activity":    activity,
            "daily_hours": daily_hours,
            "created":     datetime.date.today().isoformat(),
        })
        self._save_goals()
        self._voice.speak(
            f"Goal set, Sir: {daily_hours} hours of {activity} per day "
            f"toward your goal of {name}."
        )

    def list_goals(self) -> str:
        if not self._goals:
            return "No goals set yet, Sir."
        lines = ["Your active goals, Sir:"]
        for g in self._goals:
            lines.append(f"  • {g['name']} — {g['daily_hours']}h/day of {g['activity']}")
        return "\n".join(lines)

    def end_of_day_reflection(self):
        summary = self.get_today_summary()
        self._voice.speak(summary)
        self._voice.speak(
            "Sir, what felt hardest today? And what felt easiest? "
            "Tell me and I will note it for your progress tracking."
        )

    def observe_and_comment(self):
        """Proactively comment on what user is doing."""
        activity = self._detect_activity()
        import random
        comments = {
            "python":     "I see you are coding in Python, Sir. Want me to help debug or suggest a library?",
            "javascript": "I notice you are working in JavaScript, Sir. Want me to review your code or suggest shortcuts?",
            "html":       "You are building a webpage, Sir. Want me to check your HTML structure?",
            "writing":    "I see you are writing, Sir. Want me to help outline your ideas or improve the text?",
            "designing":  "You are designing something, Sir. Want me to suggest color palettes or layouts?",
            "browsing":   "I notice you are browsing, Sir. Is there something specific I can help you find?",
            "studying":   "You are studying, Sir. Want me to quiz you or summarise what you are reading?",
        }
        comment = comments.get(activity,
            f"I can see you are busy, Sir. Let me know if you need any help.")
        self._voice.speak(comment)