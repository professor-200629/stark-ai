"""
STARK Messaging Module v3
Fixed:
  - WhatsApp send — no confirmation, sends directly
  - WhatsApp video/voice call — uses pyautogui to click button
  - No Selenium (causes Chrome crash)
"""

import time
import webbrowser
import re
import config

try:
    import pywhatkit as pwk
    _PWK_OK = True
except ImportError:
    _PWK_OK = False

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    _PG_OK = True
except ImportError:
    _PG_OK = False

try:
    import telegram
    _TG_OK = True
except ImportError:
    _TG_OK = False


class MessagingModule:
    def __init__(self, voice):
        self._voice = voice
        self._tg_bot = None
        if _TG_OK and config.TELEGRAM_BOT_TOKEN != "YOUR_TELEGRAM_BOT_TOKEN_HERE":
            try:
                self._tg_bot = telegram.Bot(token=config.TELEGRAM_BOT_TOKEN)
            except Exception: pass
        print("[STARK Messaging] Initialised.")

    def _resolve_number(self, name_or_number: str) -> str:
        lower = name_or_number.lower().strip()
        for k, v in config.CONTACTS.items():
            if k in lower:
                return v
        digits = "".join(c for c in name_or_number if c.isdigit() or c == "+")
        return digits if digits else ""

    # ══════════════════════════════════════════════════════════════════════════
    # WhatsApp SEND — no confirmation, sends directly
    # ══════════════════════════════════════════════════════════════════════════
    def whatsapp_send(self, contact: str, message: str) -> None:
        number = self._resolve_number(contact)
        if not number:
            self._voice.speak(f"I don't have {contact}'s number saved, Sir.")
            return

        self._voice.speak(f"Sending message to {contact}, Sir.")

        # Method 1: pywhatkit (most reliable)
        if _PWK_OK:
            try:
                pwk.sendwhatmsg_instantly(
                    phone_no=number,
                    message=message,
                    wait_time=10,
                    tab_close=False,
                    close_time=2,
                )
                self._voice.speak(f"Message sent to {contact}, Sir.")
                return
            except Exception as e:
                print(f"[pywhatkit] {e}")

        # Method 2: WhatsApp Web URL + pyautogui Enter
        try:
            import urllib.parse
            url = f"https://web.whatsapp.com/send?phone={number}&text={urllib.parse.quote(message)}"
            webbrowser.open(url)
            time.sleep(8)
            if _PG_OK:
                pyautogui.press("enter")
            self._voice.speak(f"Message sent to {contact}, Sir.")
        except Exception as e:
            print(f"[WhatsApp web] {e}")
            self._voice.speak(f"Could not send message, Sir.")

    # ══════════════════════════════════════════════════════════════════════════
    # WhatsApp CALLS — pyautogui clicks the button
    # ══════════════════════════════════════════════════════════════════════════
    def whatsapp_voice_call(self, contact: str) -> None:
        number = self._resolve_number(contact)
        if not number:
            self._voice.speak(f"I don't have {contact}'s number saved, Sir.")
            return

        self._voice.speak(f"Opening WhatsApp to call {contact}, Sir.")

        # Open WhatsApp Web chat
        webbrowser.open(f"https://web.whatsapp.com/send?phone={number}")
        time.sleep(6)

        if _PG_OK:
            # Try to click the voice call button using image recognition
            try:
                import pyautogui
                # Take screenshot and look for call button
                # WhatsApp voice call button is usually top right
                # Try clicking known position (top right area)
                screen_w, screen_h = pyautogui.size()
                # Voice call button is typically at ~80% width, ~8% height
                call_x = int(screen_w * 0.82)
                call_y = int(screen_h * 0.08)
                pyautogui.click(call_x, call_y)
                time.sleep(1)
                self._voice.speak(f"Voice call started to {contact}, Sir.")
            except Exception as e:
                print(f"[Voice call click] {e}")
                self._voice.speak(
                    f"WhatsApp is open for {contact}, Sir. "
                    f"Please click the call button.")
        else:
            self._voice.speak(
                f"WhatsApp is open for {contact}, Sir. "
                f"Please click the call button.")

    def whatsapp_video_call(self, contact: str) -> None:
        number = self._resolve_number(contact)
        if not number:
            self._voice.speak(f"I don't have {contact}'s number saved, Sir.")
            return

        self._voice.speak(f"Opening WhatsApp video call to {contact}, Sir.")

        webbrowser.open(f"https://web.whatsapp.com/send?phone={number}")
        time.sleep(7)

        if _PG_OK:
            try:
                screen_w, screen_h = pyautogui.size()
                # Video call button is next to voice call button (slightly right)
                vid_x = int(screen_w * 0.85)
                vid_y = int(screen_h * 0.08)
                pyautogui.click(vid_x, vid_y)
                time.sleep(1)
                self._voice.speak(f"Video call started to {contact}, Sir.")
            except Exception as e:
                print(f"[Video call click] {e}")
                self._voice.speak(
                    f"WhatsApp is open for {contact}, Sir. "
                    f"Please click the video call button.")
        else:
            self._voice.speak(
                f"WhatsApp is open for {contact}, Sir. "
                f"Please click the video call button.")

    def whatsapp_call(self, contact: str) -> None:
        self.whatsapp_voice_call(contact)

    # ══════════════════════════════════════════════════════════════════════════
    # Telegram
    # ══════════════════════════════════════════════════════════════════════════
    def telegram_send(self, chat_id: str, message: str) -> None:
        if not self._tg_bot:
            self._voice.speak("Telegram not configured, Sir.")
            return
        try:
            self._tg_bot.send_message(chat_id=chat_id, text=message)
            self._voice.speak("Telegram message sent, Sir.")
        except Exception as e:
            self._voice.speak(f"Telegram failed, Sir.")