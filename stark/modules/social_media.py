"""
STARK Social Media Module v3
Fixed: No Selenium (causes Chrome conflict)
Uses webbrowser + pyautogui for everything
"""

import time
import webbrowser
import pyautogui

pyautogui.FAILSAFE = False


class SocialMediaModule:
    def __init__(self, voice):
        self._voice = voice
        print("[STARK Social] Initialised.")

    # ── Instagram ─────────────────────────────────────────────────────────────
    def open_instagram(self):
        webbrowser.open("https://www.instagram.com")
        self._voice.speak("Opening Instagram, Sir.")

    def open_instagram_reels(self):
        webbrowser.open("https://www.instagram.com/reels/")
        self._voice.speak(
            "Instagram Reels is open, Sir. "
            "Say scroll down for next reel.")

    def open_instagram_trending(self):
        webbrowser.open("https://www.instagram.com/explore/")
        self._voice.speak("Instagram Explore is open Sir.")

    def instagram_next_reel(self):
        # Scroll down to go to next reel
        time.sleep(0.5)
        pyautogui.scroll(-800)
        time.sleep(0.3)
        self._voice.speak("Next reel, Sir.")

    def instagram_prev_reel(self):
        time.sleep(0.5)
        pyautogui.scroll(800)
        time.sleep(0.3)
        self._voice.speak("Previous reel, Sir.")

    def instagram_send_dm(self, username: str, message: str):
        webbrowser.open("https://www.instagram.com/direct/inbox/")
        self._voice.speak(f"Instagram DMs open Sir. Please message {username}.")

    # ── YouTube ───────────────────────────────────────────────────────────────
    def open_youtube_trending(self):
        webbrowser.open("https://www.youtube.com/feed/trending")
        self._voice.speak("Opening YouTube trending, Sir.")

    def open_youtube_trending_india(self):
        webbrowser.open(
            "https://www.youtube.com/feed/trending"
            "?bp=4gIcGhpyZWdpb25fY29kZT1JTiZjbD1lbi1JTg%3D%3D")
        self._voice.speak("Opening YouTube trending India, Sir.")

    # ── Scroll ────────────────────────────────────────────────────────────────
    def scroll_down_page(self, amount: int = 3):
        pyautogui.scroll(-amount * 300)

    def scroll_up_page(self, amount: int = 3):
        pyautogui.scroll(amount * 300)

    # ── Snapchat ──────────────────────────────────────────────────────────────
    def snapchat_open(self):
        webbrowser.open("https://web.snapchat.com")
        self._voice.speak("Opening Snapchat Sir.")

    def snapchat_send_message(self, username: str, message: str):
        webbrowser.open("https://web.snapchat.com")
        self._voice.speak(f"Snapchat open Sir. Please message {username}.")