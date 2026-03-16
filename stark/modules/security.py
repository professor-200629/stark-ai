"""
STARK Security Module
──────────────────────
Features:
  - Register YOUR face as the owner
  - Live camera monitors for unknown faces
  - Alerts Sir if a stranger is detected
  - Logs all intrusion attempts with timestamp
  - Lock screen when unknown face detected (Windows)
  - Can take a snapshot of the intruder
  - Works silently in background
"""

import cv2
import os
import time
import threading
import json
import platform
import datetime
import numpy as np

KNOWN_FACES_FILE = "stark_known_faces.json"
INTRUDER_LOG     = "stark_intruder_log.json"
SNAPSHOT_DIR     = "stark_snapshots"

# DeepFace lazy import
_deepface = None
def _get_deepface():
    global _deepface
    if _deepface is None:
        from deepface import DeepFace
        _deepface = DeepFace
    return _deepface


class SecurityModule:
    def __init__(self, voice):
        self._voice         = voice
        self._running       = False
        self._owner_registered = False
        self._owner_image   = None   # path to owner face image
        self._thread        = None
        self._log           = self._load_log()
        self._alert_cooldown = 0    # prevent spam alerts
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        self._check_owner()
        print("[STARK Security] Initialised.")

    # ── Load / save ───────────────────────────────────────────────────────────
    def _load_log(self) -> list:
        if os.path.exists(INTRUDER_LOG):
            try:
                with open(INTRUDER_LOG, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_log(self):
        with open(INTRUDER_LOG, "w") as f:
            json.dump(self._log[-100:], f, indent=2)   # keep last 100

    def _check_owner(self):
        """Check if owner face is already registered."""
        if os.path.exists(KNOWN_FACES_FILE):
            try:
                with open(KNOWN_FACES_FILE, "r") as f:
                    data = json.load(f)
                self._owner_image = data.get("owner_image")
                if self._owner_image and os.path.exists(self._owner_image):
                    self._owner_registered = True
                    print("[Security] Owner face registered.")
            except Exception:
                pass

    # ── Register owner face ───────────────────────────────────────────────────
    def register_owner(self) -> None:
        """Capture owner's face and save as reference."""
        self._voice.speak(
            f"Sir, I will take a photo of your face now to register you as the owner. "
            f"Please look at the camera. Taking photo in 3 seconds."
        )
        time.sleep(3)

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self._voice.speak("Cannot access camera, Sir.")
            return

        ret, frame = cap.read()
        cap.release()

        if not ret:
            self._voice.speak("Failed to capture photo, Sir.")
            return

        # Save owner image
        path = os.path.join(SNAPSHOT_DIR, "owner_face.jpg")
        cv2.imwrite(path, frame)

        with open(KNOWN_FACES_FILE, "w") as f:
            json.dump({"owner_image": path}, f)

        self._owner_image      = path
        self._owner_registered = True
        self._voice.speak(
            "Owner face registered successfully, Sir. "
            "Security system is now active."
        )
        print(f"[Security] Owner face saved → {path}")

    # ── Start monitoring ──────────────────────────────────────────────────────
    def start_monitoring(self) -> None:
        """Start background security monitoring."""
        if not self._owner_registered:
            self._voice.speak(
                "Sir, please register your face first. Say: register my face."
            )
            return

        if self._running:
            self._voice.speak("Security monitoring is already running, Sir.")
            return

        self._running = True
        self._thread  = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        self._voice.speak(
            "Security system activated, Sir. "
            "I will alert you if any unknown person is detected."
        )

    def stop_monitoring(self) -> None:
        self._running = False
        self._voice.speak("Security monitoring stopped, Sir.")

    # ── Monitoring loop ───────────────────────────────────────────────────────
    def _monitor_loop(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[Security] Cannot open camera.")
            self._running = False
            return

        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        print("[STARK Security] Monitoring started.")

        while self._running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(1)
                continue

            # Detect faces in frame
            gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))

            if len(faces) > 0:
                is_owner = self._verify_owner(frame)

                if not is_owner and time.time() > self._alert_cooldown:
                    self._alert_intruder(frame)
                    self._alert_cooldown = time.time() + 30  # wait 30s before next alert

            time.sleep(2)   # check every 2 seconds

        cap.release()
        print("[STARK Security] Monitoring stopped.")

    def _verify_owner(self, frame) -> bool:
        """Check if the face in frame matches the owner."""
        if not self._owner_image:
            return True   # no owner registered → don't alert

        try:
            DeepFace = _get_deepface()
            result = DeepFace.verify(
                frame,
                self._owner_image,
                enforce_detection=False,
                silent=True,
            )
            return result.get("verified", False)
        except Exception:
            return True   # if check fails, assume owner (avoid false alerts)

    def _alert_intruder(self, frame) -> None:
        """Alert Sir about an unknown person."""
        # Save snapshot
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot  = os.path.join(SNAPSHOT_DIR, f"intruder_{timestamp}.jpg")
        cv2.imwrite(snapshot, frame)

        # Log it
        entry = {
            "time":     datetime.datetime.now().isoformat(),
            "snapshot": snapshot,
        }
        self._log.append(entry)
        self._save_log()

        print(f"\n[STARK SECURITY] ⚠ UNKNOWN PERSON DETECTED → {snapshot}")

        # Alert voice
        self._voice.speak(
            f"Sir! Security alert! An unknown person has been detected on camera. "
            f"A snapshot has been saved."
        )

        # Optional: lock screen
        # self._lock_screen()

    def _lock_screen(self) -> None:
        """Lock the screen (Windows only)."""
        if platform.system() == "Windows":
            import ctypes
            ctypes.windll.user32.LockWorkStation()

    # ── Manual snapshot ───────────────────────────────────────────────────────
    def take_snapshot(self) -> str:
        """Take a manual snapshot right now."""
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            self._voice.speak("Cannot take snapshot, Sir. Camera not available.")
            return ""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(SNAPSHOT_DIR, f"snapshot_{timestamp}.jpg")
        cv2.imwrite(path, frame)
        self._voice.speak(f"Snapshot saved, Sir.")
        print(f"[Security] Snapshot → {path}")
        return path

    # ── View log ──────────────────────────────────────────────────────────────
    def show_log(self) -> None:
        if not self._log:
            self._voice.speak("No security incidents recorded, Sir.")
            return
        self._voice.speak(
            f"Sir, there have been {len(self._log)} security incident(s) recorded."
        )
        for entry in self._log[-5:]:
            print(f"  [{entry['time']}] Snapshot: {entry['snapshot']}")

    def status(self) -> str:
        state = "ACTIVE" if self._running else "INACTIVE"
        reg   = "YES" if self._owner_registered else "NO — say: register my face"
        return (f"Security: {state} | Owner registered: {reg} | "
                f"Incidents: {len(self._log)}")