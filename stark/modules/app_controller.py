"""
STARK App Controller v4
Fixed:
  - YouTube search + autoplay songs/videos properly
  - Spotify search + play songs
  - Close apps and websites properly
  - Open any website by name
"""

import webbrowser
import time
import os
import subprocess
import pyautogui
import config

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    _SELENIUM_OK = True
except ImportError:
    _SELENIUM_OK = False

pyautogui.FAILSAFE = False
pyautogui.PAUSE    = 0.2

KEEPALIVE_JS = """
if (!window.__stark_alive) {
    window.__stark_alive = true;
    Object.defineProperty(navigator,'webdriver',{get:()=>undefined});
    setInterval(function(){
        var v=document.querySelector('video');
        if(v && v.paused) v.play();
        document.dispatchEvent(new MouseEvent('mousemove',{bubbles:true,
            cancelable:true,view:window,
            clientX:Math.random()*100+400,clientY:Math.random()*100+300}));
    },25000);
    setInterval(function(){
        var o=document.querySelector('.ytp-pause-overlay');
        if(o) o.style.display='none';
        var b=document.querySelector('.ytp-pause-overlay-container button');
        if(b) b.click();
    },5000);
}
"""


class AppController:
    def __init__(self, voice):
        self._voice  = voice
        self._driver = None
        self._open_sites = {}   # track open sites for closing
        print("[STARK AppCtrl] Initialised.")

    def _open_url(self, url: str) -> None:
        webbrowser.open(url)
        time.sleep(1)

    # ── Selenium driver ───────────────────────────────────────────────────────
    def _get_driver(self):
        if self._driver:
            try:
                _ = self._driver.title
                return self._driver
            except Exception:
                self._driver = None
        if not _SELENIUM_OK:
            return None
        try:
            opts = webdriver.ChromeOptions()
            opts.add_argument("--disable-blink-features=AutomationControlled")
            opts.add_experimental_option("excludeSwitches", ["enable-automation"])
            opts.add_experimental_option("useAutomationExtension", False)
            opts.add_argument("--start-maximized")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument(
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            self._driver = webdriver.Chrome(
                service=ChromeService(ChromeDriverManager().install()), options=opts)
            self._driver.execute_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
            return self._driver
        except Exception as e:
            print(f"[AppCtrl Chrome error] {e}")
            return None

    # ══════════════════════════════════════════════════════════════════════════
    # YOUTUBE — search and autoplay
    # ══════════════════════════════════════════════════════════════════════════

    def play_youtube(self, query: str) -> None:
        driver = self._get_driver()
        if driver:
            self._voice.speak(f"Playing {query} on YouTube, Sir.")
            url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
            driver.get(url)
            time.sleep(3)
            try:
                # Click first actual video
                videos = driver.find_elements(By.CSS_SELECTOR, "ytd-video-renderer a#thumbnail")
                if videos:
                    videos[0].click()
                    time.sleep(4)
                    driver.execute_script(KEEPALIVE_JS)
                    self._voice.speak("Playing now, Sir.")
                    return
            except Exception as e:
                print(f"[YT] {e}")

        # Fallback — open search in browser
        self._voice.speak(f"Searching YouTube for {query}, Sir.")
        webbrowser.open(f"https://www.youtube.com/results?search_query={query.replace(' ','+')}")

    # ══════════════════════════════════════════════════════════════════════════
    # SPOTIFY — search and play songs
    # ══════════════════════════════════════════════════════════════════════════

    def play_spotify(self, query: str) -> None:
        """Open Spotify search — only in default browser, no double opening."""
        self._voice.speak(f"Opening Spotify for {query}, Sir.")
        # Use Spotify URI to open in Spotify app if installed, else browser
        import urllib.parse as _up
        search_url = f"https://open.spotify.com/search/{_up.quote(query)}"
        webbrowser.open(search_url)
        self._voice.speak(
            f"Spotify is open with {query}, Sir. Click the first song to play.")

    # ══════════════════════════════════════════════════════════════════════════
    # CLOSE apps / websites
    # ══════════════════════════════════════════════════════════════════════════

    def close_app(self, app_name: str) -> None:
        """Close an app or website by name."""
        app_lower = app_name.lower()

        # Close browser tab if Selenium driver is open
        if self._driver:
            try:
                title = self._driver.title.lower()
                if any(w in title for w in [app_lower, "youtube", "spotify",
                                             "netflix", "amazon", "hotstar"]):
                    self._driver.close()
                    self._driver = None
                    self._voice.speak(f"Closed {app_name}, Sir.")
                    return
            except Exception:
                pass

        # Close by process name (Windows)
        process_map = {
            "chrome":     "chrome.exe",
            "firefox":    "firefox.exe",
            "edge":       "msedge.exe",
            "spotify":    "Spotify.exe",
            "notepad":    "notepad.exe",
            "calculator": "Calculator.exe",
            "vlc":        "vlc.exe",
            "word":       "WINWORD.EXE",
            "excel":      "EXCEL.EXE",
            "powerpoint": "POWERPNT.EXE",
            "vscode":     "Code.exe",
            "vs code":    "Code.exe",
            "telegram":   "Telegram.exe",
            "whatsapp":   "WhatsApp.exe",
        }

        for key, proc in process_map.items():
            if key in app_lower:
                os.system(f"taskkill /f /im {proc} >nul 2>&1")
                self._voice.speak(f"Closed {app_name}, Sir.")
                return

        # Close current active window
        pyautogui.hotkey("alt", "F4")
        self._voice.speak(f"Closed the active window, Sir.")

    def close_tab(self) -> None:
        pyautogui.hotkey("ctrl", "w")
        self._voice.speak("Tab closed, Sir.")

    def close_browser(self) -> None:
        """Close Chrome/Edge browser."""
        pyautogui.hotkey("ctrl", "shift", "w")
        self._voice.speak("Browser closed, Sir.")

    # ══════════════════════════════════════════════════════════════════════════
    # YouTube controls
    # ══════════════════════════════════════════════════════════════════════════

    def youtube_skip_ad(self) -> None:
        driver = self._get_driver()
        if not driver: return
        try:
            for sel in [".ytp-skip-ad-button", ".ytp-ad-skip-button",
                        "button.ytp-ad-skip-button-modern"]:
                try:
                    btn = WebDriverWait(driver, 4).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
                    btn.click()
                    self._voice.speak("Ad skipped, Sir.")
                    return
                except Exception:
                    continue
            self._voice.speak("No skippable ad right now, Sir.")
        except Exception:
            pass

    def youtube_pause_resume(self) -> None:
        driver = self._get_driver()
        if driver:
            try:
                driver.execute_script(
                    "var v=document.querySelector('video');"
                    "if(v){v.paused?v.play():v.pause();}")
                self._voice.speak("Done, Sir.")
                return
            except Exception:
                pass
        pyautogui.press("space")
        self._voice.speak("Done, Sir.")

    def youtube_next(self) -> None:
        driver = self._get_driver()
        if driver:
            try:
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.SHIFT + "n")
                time.sleep(2)
                driver.execute_script(KEEPALIVE_JS)
                self._voice.speak("Next video, Sir.")
                return
            except Exception:
                pass
        pyautogui.hotkey("shift", "n")
        self._voice.speak("Next video, Sir.")

    def youtube_previous(self) -> None:
        driver = self._get_driver()
        if driver:
            try:
                driver.back()
                time.sleep(2)
                driver.execute_script(KEEPALIVE_JS)
                self._voice.speak("Previous video, Sir.")
                return
            except Exception:
                pass
        pyautogui.hotkey("alt", "left")

    # ══════════════════════════════════════════════════════════════════════════
    # Open sites
    # ══════════════════════════════════════════════════════════════════════════

    def open_youtube(self):
        self._open_url(config.YOUTUBE_URL)
        self._voice.speak("Opening YouTube, Sir.")

    def open_spotify(self):
        self._open_url(config.SPOTIFY_URL)
        self._voice.speak("Opening Spotify, Sir.")

    def open_netflix(self):
        self._open_url(config.NETFLIX_URL)
        self._voice.speak("Opening Netflix, Sir.")

    def open_prime(self):
        self._open_url(config.PRIME_URL)
        self._voice.speak("Opening Amazon Prime, Sir.")

    def open_hotstar(self):
        self._open_url(config.HOTSTAR_URL)
        self._voice.speak("Opening JioHotstar, Sir.")

    def open_whatsapp_web(self):
        self._open_url(config.WHATSAPP_WEB_URL)
        self._voice.speak("Opening WhatsApp, Sir.")

    def open_url(self, url: str):
        if not url.startswith("http"):
            url = "https://" + url
        self._open_url(url)
        self._voice.speak(f"Opening {url}, Sir.")

    def open_app(self, app_name: str):
        pyautogui.hotkey("win", "s")
        time.sleep(0.8)
        pyautogui.typewrite(app_name, interval=0.05)
        time.sleep(0.8)
        pyautogui.press("enter")
        self._voice.speak(f"Opening {app_name}, Sir.")

    def close_driver(self):
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None