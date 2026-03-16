"""
STARK v8.0 — Complete Personal AI Operating System
"""

import threading
import time
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from modules.voice          import VoiceModule
from modules.ai_brain       import AIBrain
from modules.screen_monitor import ScreenMonitor
from modules.camera_monitor import CameraMonitor
from modules.memory         import Memory
from modules.meeting_assist import MeetingAssistant
from modules.messaging      import MessagingModule
from modules.app_controller import AppController
from modules.alarms         import AlarmModule
from modules.security       import SecurityModule
from modules.travel         import TravelModule
from modules.system_control import SystemControl
from modules.screen_time    import ScreenTimeMonitor
from modules.location       import LocationModule
from modules.folder_manager import FolderManager


def greet(voice):
    hour = datetime.now().hour
    if   hour < 12: msg = "Good morning"
    elif hour < 17: msg = "Good afternoon"
    else:           msg = "Good evening"
    voice.speak(
        f"{msg}, {config.USER_NAME}! "
        f"STARK v8 is fully online. All systems ready."
    )


def main():
    print("\n" + "═"*52)
    print("   ███████╗████████╗ █████╗ ██████╗ ██╗  ██╗")
    print("   ██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██║ ██╔╝")
    print("   ███████╗   ██║   ███████║██████╔╝█████╔╝ ")
    print("   ╚════██║   ██║   ██╔══██║██╔══██╗██╔═██╗ ")
    print("   ███████║   ██║   ██║  ██║██║  ██║██║  ██╗")
    print("   ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝")
    print("   Personal AI Operating System  v8.0")
    print("═"*52 + "\n")

    # ── Init all modules ──────────────────────────────────────────────────────
    memory    = Memory()
    voice     = VoiceModule()
    app       = AppController(voice)
    messaging = MessagingModule(voice)
    screen    = ScreenMonitor(voice)
    camera    = CameraMonitor(voice)
    meeting   = MeetingAssistant()
    alarms    = AlarmModule(voice)
    security  = SecurityModule(voice)
    sysctl    = SystemControl(voice)

    brain     = AIBrain(memory, voice, app, messaging, screen,
                        camera, meeting, alarms, security, sysctl)

    travel    = TravelModule(voice, brain._ask_ai)
    brain.set_travel(travel)

    screentime = ScreenTimeMonitor(voice, brain._ask_ai)
    brain.set_screentime(screentime)

    location   = LocationModule(voice, brain._ask_ai)
    brain.set_location(location)

    folder_mgr = FolderManager(voice, brain._ask_ai)
    brain.set_folder_manager(folder_mgr)

    # ── Start all background services ─────────────────────────────────────────
    threading.Thread(target=brain.health_monitor, daemon=True).start()
    screentime.start()

    greet(voice)
    print("[STARK] All systems online. Listening...\n")

    # ── Main voice loop ───────────────────────────────────────────────────────
    while True:
        try:
            text = voice.listen()
            if not text:
                continue
            command = text.lower().strip()

            if config.REQUIRE_WAKE:
                if config.WAKE_WORD not in command:
                    continue
                command = command.replace(config.WAKE_WORD, "").strip()
                if not command:
                    voice.speak(f"Yes {config.USER_NAME}?")
                    text    = voice.listen() or ""
                    command = text.lower().strip()

            if command:
                brain.process_command(command, raw_text=text)

        except KeyboardInterrupt:
            voice.speak(f"Goodbye {config.USER_NAME}. STARK shutting down.")
            screentime.stop()
            security.stop_monitoring()
            alarms.stop()
            camera.stop()
            brain.stop_health_monitor()
            break
        except Exception as e:
            print(f"[STARK ERROR] {e}")


if __name__ == "__main__":
    main()