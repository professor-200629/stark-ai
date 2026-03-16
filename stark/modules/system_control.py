"""
STARK System Control Module
─────────────────────────────
Controls:
  - Volume up/down/mute
  - Brightness up/down
  - Scroll up/down
  - Screenshot + open screenshot
  - Lock screen
  - Sleep / Shutdown / Restart
  - Open any website
  - Close any app
  - Open File Explorer
"""

import os
import time
import subprocess
import platform
import datetime
import pyautogui
from pathlib import Path

# Windows-specific imports
try:
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    _AUDIO_OK = True
except ImportError:
    _AUDIO_OK = False

try:
    import screen_brightness_control as sbc
    _BRIGHTNESS_OK = True
except ImportError:
    _BRIGHTNESS_OK = False

SCREENSHOT_DIR = "stark_screenshots"


class SystemControl:
    def __init__(self, voice):
        self._voice = voice
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        self._last_screenshot = None
        print("[STARK System] Initialised.")

    # ══════════════════════════════════════════════════════════════════════════
    # VOLUME
    # ══════════════════════════════════════════════════════════════════════════

    def volume_up(self, amount: int = 10) -> None:
        presses = max(2, amount // 2)
        try:
            for _ in range(presses):
                pyautogui.press("volumeup")
            self._voice.speak("Volume increased, Sir.")
        except Exception as e:
            print(f"[Volume up] {e}")
            self._voice.speak("Volume increased, Sir.")

    def volume_down(self, amount: int = 10) -> None:
        presses = max(2, amount // 2)
        try:
            for _ in range(presses):
                pyautogui.press("volumedown")
            self._voice.speak("Volume decreased, Sir.")
        except Exception as e:
            print(f"[Volume down] {e}")
            self._voice.speak("Volume decreased, Sir.")

    def volume_mute(self) -> None:
        try:
            pyautogui.press("volumemute")
            self._voice.speak("Volume muted, Sir.")
        except Exception as e:
            print(f"[Mute] {e}")

    def volume_set(self, level: int) -> None:
        try:
            if _AUDIO_OK:
                devices = AudioUtilities.GetSpeakers()
                iface   = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume  = cast(iface, POINTER(IAudioEndpointVolume))
                volume.SetMasterVolumeLevelScalar(level / 100, None)
                self._voice.speak(f"Volume set to {level} percent, Sir.")
        except Exception as e:
            print(f"[Volume set] {e}")

    # ══════════════════════════════════════════════════════════════════════════
    # BRIGHTNESS
    # ══════════════════════════════════════════════════════════════════════════

    def brightness_up(self, amount: int = 10) -> None:
        # Method 1: WMI PowerShell (most reliable on Windows)
        try:
            import subprocess
            ps = (
                f"$b=(Get-CimInstance -Namespace root/WMI "
                f"-ClassName WmiMonitorBrightness).CurrentBrightness; "
                f"$n=[Math]::Min(100,$b+{amount}); "
                f"(Get-CimInstance -Namespace root/WMI "
                f"-ClassName WmiMonitorBrightnessMethods).WmiSetBrightness(1,$n); "
                f"Write-Output $n"
            )
            r = subprocess.run(["powershell","-Command",ps],
                capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and r.stdout.strip():
                self._voice.speak(
                    f"Brightness increased to {r.stdout.strip()} percent, Sir.")
                return
        except Exception as e:
            print(f"[Brightness WMI] {e}")
        # Method 2: screen-brightness-control
        try:
            if _BRIGHTNESS_OK:
                cur = sbc.get_brightness(display=0)[0]
                sbc.set_brightness(min(100, cur + amount), display=0)
                self._voice.speak("Brightness increased, Sir.")
                return
        except Exception as e:
            print(f"[Brightness sbc] {e}")
        # Method 3: keyboard key
        try:
            for _ in range(max(1, amount//5)):
                pyautogui.press("brightnessup")
            self._voice.speak("Brightness increased, Sir.")
        except Exception:
            self._voice.speak("Could not change brightness, Sir.")

    def brightness_down(self, amount: int = 10) -> None:
        try:
            import subprocess
            ps = (
                f"$b=(Get-CimInstance -Namespace root/WMI "
                f"-ClassName WmiMonitorBrightness).CurrentBrightness; "
                f"$n=[Math]::Max(5,$b-{amount}); "
                f"(Get-CimInstance -Namespace root/WMI "
                f"-ClassName WmiMonitorBrightnessMethods).WmiSetBrightness(1,$n); "
                f"Write-Output $n"
            )
            r = subprocess.run(["powershell","-Command",ps],
                capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and r.stdout.strip():
                self._voice.speak(
                    f"Brightness decreased to {r.stdout.strip()} percent, Sir.")
                return
        except Exception as e:
            print(f"[Brightness WMI] {e}")
        try:
            if _BRIGHTNESS_OK:
                cur = sbc.get_brightness(display=0)[0]
                sbc.set_brightness(max(5, cur - amount), display=0)
                self._voice.speak("Brightness decreased, Sir.")
                return
        except Exception as e:
            print(f"[Brightness sbc] {e}")
        try:
            for _ in range(max(1, amount//5)):
                pyautogui.press("brightnessdown")
            self._voice.speak("Brightness decreased, Sir.")
        except Exception:
            self._voice.speak("Could not change brightness, Sir.")

    def brightness_set(self, level: int) -> None:
        try:
            if _BRIGHTNESS_OK:
                sbc.set_brightness(level)
                self._voice.speak(f"Brightness set to {level} percent, Sir.")
        except Exception as e:
            print(f"[Brightness set] {e}")

    # ══════════════════════════════════════════════════════════════════════════
    # SCROLL
    # ══════════════════════════════════════════════════════════════════════════

    def scroll_down(self, clicks: int = 5) -> None:
        pyautogui.scroll(-clicks * 100)
        self._voice.speak("Scrolled down, Sir.")

    def scroll_up(self, clicks: int = 5) -> None:
        pyautogui.scroll(clicks * 100)
        self._voice.speak("Scrolled up, Sir.")

    def scroll_to_top(self) -> None:
        pyautogui.hotkey("ctrl", "Home")
        self._voice.speak("Scrolled to top, Sir.")

    def scroll_to_bottom(self) -> None:
        pyautogui.hotkey("ctrl", "End")
        self._voice.speak("Scrolled to bottom, Sir.")

    # ══════════════════════════════════════════════════════════════════════════
    # SCREENSHOTS
    # ══════════════════════════════════════════════════════════════════════════

    def take_screenshot(self) -> str:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename  = f"screenshot_{timestamp}.png"
        filepath  = os.path.join(SCREENSHOT_DIR, filename)
        try:
            screenshot = pyautogui.screenshot()
            screenshot.save(filepath)
            self._last_screenshot = filepath
            self._voice.speak(f"Screenshot taken and saved, Sir.")
            print(f"[Screenshot] Saved → {filepath}")
            return filepath
        except Exception as e:
            print(f"[Screenshot] {e}")
            self._voice.speak("Could not take screenshot, Sir.")
            return ""

    def open_last_screenshot(self) -> None:
        if self._last_screenshot and os.path.exists(self._last_screenshot):
            os.startfile(self._last_screenshot)
            self._voice.speak("Opening last screenshot, Sir.")
        else:
            # Try to find most recent screenshot
            try:
                files = sorted(Path(SCREENSHOT_DIR).glob("*.png"), key=os.path.getmtime)
                if files:
                    os.startfile(str(files[-1]))
                    self._voice.speak("Opening screenshot, Sir.")
                else:
                    self._voice.speak("No screenshots found, Sir.")
            except Exception:
                self._voice.speak("No screenshots found, Sir.")

    def open_screenshots_folder(self) -> None:
        os.startfile(os.path.abspath(SCREENSHOT_DIR))
        self._voice.speak("Opening screenshots folder, Sir.")

    # ══════════════════════════════════════════════════════════════════════════
    # SYSTEM POWER
    # ══════════════════════════════════════════════════════════════════════════

    def lock_screen(self) -> None:
        self._voice.speak("Locking your screen, Sir.")
        time.sleep(1)
        import ctypes
        ctypes.windll.user32.LockWorkStation()

    def sleep_pc(self) -> None:
        self._voice.speak("Putting your PC to sleep, Sir. Goodnight.")
        time.sleep(2)
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

    def shutdown_pc(self) -> None:
        self._voice.speak("Shutting down your PC, Sir. Goodbye.")
        time.sleep(3)
        os.system("shutdown /s /t 1")

    def restart_pc(self) -> None:
        self._voice.speak("Restarting your PC, Sir. One moment.")
        time.sleep(3)
        os.system("shutdown /r /t 1")

    def cancel_shutdown(self) -> None:
        os.system("shutdown /a")
        self._voice.speak("Shutdown cancelled, Sir.")

    # ══════════════════════════════════════════════════════════════════════════
    # APP CONTROL
    # ══════════════════════════════════════════════════════════════════════════

    def open_website(self, url: str) -> None:
        import webbrowser
        if not url.startswith("http"):
            url = "https://" + url
        webbrowser.open(url)
        self._voice.speak(f"Opening {url}, Sir.")

    def open_file_explorer(self, path: str = "") -> None:
        if path:
            os.startfile(path)
        else:
            subprocess.Popen("explorer")
        self._voice.speak("Opening File Explorer, Sir.")

    def close_active_window(self) -> None:
        pyautogui.hotkey("alt", "F4")
        self._voice.speak("Closed the window, Sir.")

    def minimize_window(self) -> None:
        pyautogui.hotkey("win", "down")
        self._voice.speak("Window minimized, Sir.")

    def maximize_window(self) -> None:
        pyautogui.hotkey("win", "up")
        self._voice.speak("Window maximized, Sir.")

    def switch_window(self) -> None:
        pyautogui.hotkey("alt", "tab")

    def open_task_manager(self) -> None:
        pyautogui.hotkey("ctrl", "shift", "esc")
        self._voice.speak("Opening Task Manager, Sir.")

    def close_app_by_name(self, app_name: str) -> None:
        try:
            os.system(f"taskkill /f /im {app_name}.exe")
            self._voice.speak(f"Closed {app_name}, Sir.")
        except Exception as e:
            self._voice.speak(f"Could not close {app_name}, Sir.")

    # ══════════════════════════════════════════════════════════════════════════
    # KEYBOARD SHORTCUTS
    # ══════════════════════════════════════════════════════════════════════════

    def copy(self):
        pyautogui.hotkey("ctrl", "c")
        self._voice.speak("Copied, Sir.")

    def paste(self):
        pyautogui.hotkey("ctrl", "v")
        self._voice.speak("Pasted, Sir.")

    def select_all(self):
        pyautogui.hotkey("ctrl", "a")
        self._voice.speak("Selected all, Sir.")

    def undo(self):
        pyautogui.hotkey("ctrl", "z")
        self._voice.speak("Undone, Sir.")

    def save_file(self):
        pyautogui.hotkey("ctrl", "s")
        self._voice.speak("Saved, Sir.")

    def new_tab(self):
        pyautogui.hotkey("ctrl", "t")
        self._voice.speak("New tab opened, Sir.")

    def close_tab(self):
        pyautogui.hotkey("ctrl", "w")
        self._voice.speak("Tab closed, Sir.")

    def refresh_page(self):
        pyautogui.press("f5")
        self._voice.speak("Page refreshed, Sir.")