"""
STARK Alarms v2 — Fixed: alarm now speaks properly
Uses a thread-safe queue to send alarm messages to main thread
"""

import threading
import time
import json
import os
import re
import datetime
import queue
import platform

ALARMS_FILE  = "stark_alarms.json"

# Global queue — main thread reads this and speaks
alarm_queue = queue.Queue()


def _beep():
    try:
        if platform.system() == "Windows":
            import winsound
            for _ in range(4):
                winsound.Beep(1000, 500)
                time.sleep(0.1)
        else:
            print("\a\a\a")
    except Exception:
        print("\a")


class AlarmModule:
    def __init__(self, voice):
        self._voice   = voice
        self._alarms  = self._load()
        self._running = True
        self._lock    = threading.Lock()

        # Start scheduler
        t = threading.Thread(target=self._scheduler_loop, daemon=True)
        t.start()

        # Start speaker — reads from queue and speaks on this thread
        s = threading.Thread(target=self._speaker_loop, daemon=True)
        s.start()

        print("[STARK Alarms] Initialised. Scheduler running.")

    # ── Persistence ───────────────────────────────────────────────────────────
    def _load(self):
        if os.path.exists(ALARMS_FILE):
            try:
                with open(ALARMS_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save(self):
        with open(ALARMS_FILE, "w") as f:
            json.dump(self._alarms, f, indent=2)

    # ── Speaker loop (runs in its own thread, calls voice.speak) ─────────────
    def _speaker_loop(self):
        """Continuously reads alarm_queue and speaks the message."""
        while self._running:
            try:
                msg = alarm_queue.get(timeout=1)
                _beep()
                self._voice.speak(msg)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[Alarm speaker] {e}")

    # ── Set alarm ─────────────────────────────────────────────────────────────
    def set_alarm(self, time_str: str, label: str = "Alarm") -> None:
        alarm_time = self._parse_time(time_str)
        if not alarm_time:
            self._voice.speak(f"Sorry Sir, I couldn't understand the time. Please say something like 7:30 PM.")
            return
        entry = {"id": int(time.time()), "type": "alarm",
                 "time": alarm_time, "label": label, "active": True}
        with self._lock:
            self._alarms.append(entry)
            self._save()
        self._voice.speak(f"Alarm set for {alarm_time}, Sir. I will remind you: {label}.")
        print(f"[Alarm] Set → {alarm_time} — {label}")

    def set_reminder(self, minutes: int, label: str = "Reminder") -> None:
        fire_time = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        time_str  = fire_time.strftime("%H:%M")
        entry = {"id": int(time.time()), "type": "reminder",
                 "time": time_str, "label": label, "active": True}
        with self._lock:
            self._alarms.append(entry)
            self._save()
        human = f"{minutes} minutes" if minutes < 60 else f"{minutes//60} hour(s)"
        self._voice.speak(f"Reminder set for {human} from now at {time_str}, Sir.")

    def set_recurring(self, every_minutes: int, label: str) -> None:
        entry = {"id": int(time.time()), "type": "recurring",
                 "every_minutes": every_minutes, "last_fired": None,
                 "label": label, "active": True}
        with self._lock:
            self._alarms.append(entry)
            self._save()
        self._voice.speak(f"Recurring reminder set every {every_minutes} minutes, Sir.")

    def list_alarms(self) -> None:
        with self._lock:
            active = [a for a in self._alarms if a.get("active")]
        if not active:
            self._voice.speak("You have no active alarms, Sir.")
            return
        self._voice.speak(f"You have {len(active)} active reminder(s), Sir.")
        for a in active[:3]:
            if a["type"] == "recurring":
                self._voice.speak(f"Every {a['every_minutes']} minutes: {a['label']}")
            else:
                self._voice.speak(f"At {a['time']}: {a['label']}")

    def cancel_alarm(self, label_or_time: str) -> None:
        with self._lock:
            for a in self._alarms:
                if (label_or_time.lower() in a.get("label","").lower()
                        or label_or_time in a.get("time","")):
                    a["active"] = False
                    self._save()
                    self._voice.speak(f"Cancelled: {a['label']}, Sir.")
                    return
        self._voice.speak(f"No alarm matching that found, Sir.")

    def cancel_all(self) -> None:
        with self._lock:
            for a in self._alarms:
                a["active"] = False
            self._save()
        self._voice.speak("All alarms cancelled, Sir.")

    # ── Scheduler ─────────────────────────────────────────────────────────────
    def _scheduler_loop(self):
        while self._running:
            now     = datetime.datetime.now()
            now_str = now.strftime("%H:%M")
            with self._lock:
                alarms = list(self._alarms)

            for a in alarms:
                if not a.get("active"):
                    continue
                if a["type"] in ("alarm","reminder"):
                    # Use a 90-second window so lag or sleep never misses an alarm
                    try:
                        alarm_dt = datetime.datetime.strptime(a["time"], "%H:%M").replace(
                            year=now.year, month=now.month, day=now.day)
                        diff = (now - alarm_dt).total_seconds()
                        # Fire if within the past 90 seconds (handles lag)
                        # "fired_date" prevents double-firing on the same day
                        already_fired = a.get("fired_date") == now.strftime("%Y-%m-%d")
                        if 0 <= diff < 90 and not already_fired:
                            self._fire(a)
                            with self._lock:
                                a["active"] = False
                                a["fired_date"] = now.strftime("%Y-%m-%d")
                                self._save()
                    except Exception:
                        # Fallback to exact match if datetime parse fails
                        if a["time"] == now_str:
                            self._fire(a)
                            with self._lock:
                                a["active"] = False
                                self._save()
                elif a["type"] == "recurring":
                    last  = a.get("last_fired")
                    every = a["every_minutes"]
                    if last is None:
                        should = True
                    else:
                        last_dt = datetime.datetime.fromisoformat(last)
                        should  = (now - last_dt).total_seconds() >= every * 60
                    if should:
                        self._fire(a)
                        with self._lock:
                            a["last_fired"] = now.isoformat()
                            self._save()
            time.sleep(30)

    def _fire(self, alarm: dict):
        label = alarm.get("label", "Alarm")
        print(f"\n[STARK ALARM] ⏰ {label}")
        # Put in queue — speaker thread will say it aloud
        alarm_queue.put(f"Sir! {label}! {label}!")

    def _parse_time(self, time_str: str) -> str:
        # Normalise: "p.m." -> "PM", "a.m." -> "AM"
        s = time_str.strip().upper()
        s = s.replace("P.M.", "PM").replace("A.M.", "AM")
        s = s.replace("P. M.", "PM").replace("A. M.", "AM")
        # Match HH:MM AM/PM
        match = re.search(r"(\d{1,2}):(\d{2})\s*(AM|PM)?", s)
        if match:
            h, m, ampm = int(match.group(1)), int(match.group(2)), match.group(3)
            if ampm == "PM" and h != 12: h += 12
            if ampm == "AM" and h == 12: h = 0
            return f"{h:02d}:{m:02d}"
        # Match H AM/PM (no minutes)
        match = re.search(r"(\d{1,2})\s*(AM|PM)", s)
        if match:
            h, ampm = int(match.group(1)), match.group(2)
            if ampm == "PM" and h != 12: h += 12
            if ampm == "AM" and h == 12: h = 0
            return f"{h:02d}:00"
        return ""

    def stop(self):
        self._running = False