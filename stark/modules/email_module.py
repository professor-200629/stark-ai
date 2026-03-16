"""
STARK Email Module
──────────────────
Features:
  - Open Gmail in browser
  - Read emails using Selenium
  - Summarise emails with AI
  - Read specific emails by sender or subject
"""

import time
import webbrowser
import re

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service as ChromeService
    from webdriver_manager.chrome import ChromeDriverManager
    _SEL_OK = True
except ImportError:
    _SEL_OK = False


class EmailModule:
    def __init__(self, voice, ask_ai_fn):
        self._voice   = voice
        self._ask_ai  = ask_ai_fn
        self._driver  = None
        print("[STARK Email] Initialised.")

    def _get_driver(self):
        if self._driver:
            try:
                _ = self._driver.title
                return self._driver
            except Exception:
                self._driver = None
        if not _SEL_OK:
            return None
        try:
            import os
            opts = webdriver.ChromeOptions()
            opts.add_argument("--disable-blink-features=AutomationControlled")
            opts.add_experimental_option("excludeSwitches", ["enable-automation"])
            opts.add_experimental_option("useAutomationExtension", False)
            # Use existing Chrome profile so Gmail stays logged in
            user_data = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
            opts.add_argument(f"--user-data-dir={user_data}")
            opts.add_argument("--profile-directory=Default")
            opts.add_argument("--start-maximized")
            self._driver = webdriver.Chrome(
                service=ChromeService(ChromeDriverManager().install()),
                options=opts)
            return self._driver
        except Exception as e:
            print(f"[Email driver] {e}")
            return None

    # ── Open Gmail ────────────────────────────────────────────────────────────
    def open_gmail(self) -> None:
        webbrowser.open("https://mail.google.com")
        self._voice.speak("Opening Gmail, Sir.")

    # ── Read latest emails ────────────────────────────────────────────────────
    def read_emails(self, count: int = 5) -> None:
        self._voice.speak(f"Reading your latest {count} emails, Sir. Please wait.")
        driver = self._get_driver()
        if not driver:
            webbrowser.open("https://mail.google.com")
            self._voice.speak("Gmail is open, Sir. Selenium not available for auto-read.")
            return
        try:
            driver.get("https://mail.google.com")
            time.sleep(4)
            wait = WebDriverWait(driver, 15)

            # Get email rows
            emails = wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "tr.zA")))

            if not emails:
                self._voice.speak("No emails found, Sir.")
                return

            summaries = []
            for i, email in enumerate(emails[:count]):
                try:
                    sender  = email.find_element(By.CSS_SELECTOR, ".yX span").text
                    subject = email.find_element(By.CSS_SELECTOR, ".y6 span").text
                    snippet = ""
                    try:
                        snippet = email.find_element(By.CSS_SELECTOR, ".y2").text
                    except Exception:
                        pass
                    summaries.append(f"{i+1}. From {sender}: {subject}. {snippet[:80]}")
                except Exception:
                    continue

            if summaries:
                text = "Here are your latest emails, Sir. " + " | ".join(summaries[:count])
                self._voice.speak(text)
                print("\n[Emails]\n" + "\n".join(summaries))
            else:
                self._voice.speak("Could not read emails, Sir. Please check Gmail.")

        except Exception as e:
            print(f"[Email read] {e}")
            self._voice.speak("Could not read emails, Sir. Opening Gmail instead.")
            webbrowser.open("https://mail.google.com")

    # ── Read and summarise a specific email ───────────────────────────────────
    def read_specific_email(self, keyword: str = "") -> None:
        self._voice.speak(f"Looking for emails about {keyword}, Sir.")
        driver = self._get_driver()
        if not driver:
            url = f"https://mail.google.com/mail/u/0/#search/{keyword.replace(' ','+')}"
            webbrowser.open(url)
            self._voice.speak(f"Opened Gmail search for {keyword}, Sir.")
            return
        try:
            driver.get("https://mail.google.com")
            time.sleep(3)

            # Search for keyword
            search_box = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[aria-label='Search mail']")))
            search_box.clear()
            search_box.send_keys(keyword)
            search_box.submit()
            time.sleep(3)

            # Click first result
            emails = driver.find_elements(By.CSS_SELECTOR, "tr.zA")
            if emails:
                emails[0].click()
                time.sleep(3)
                # Get email body
                body = ""
                try:
                    body_el = WebDriverWait(driver, 8).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".a3s")))
                    body = body_el.text[:2000]
                except Exception:
                    pass

                if body:
                    summary = self._ask_ai(
                        f"Summarise this email briefly in 3-4 sentences for Sir:\n\n{body}")
                    self._voice.speak(f"Email summary, Sir: {summary}")
                else:
                    self._voice.speak("Email is open, Sir. I could not read the body text.")
            else:
                self._voice.speak(f"No emails found about {keyword}, Sir.")
        except Exception as e:
            print(f"[Email specific] {e}")
            self._voice.speak("Could not find that email, Sir.")

    # ── Summarise open email on screen ────────────────────────────────────────
    def summarise_current_email(self, screen_monitor) -> None:
        self._voice.speak("Reading the email on your screen, Sir.")
        text = screen_monitor.read_screen()
        if text:
            summary = self._ask_ai(
                f"Summarise this email clearly in 3-4 lines for Sir:\n\n{text[:2000]}")
            self._voice.speak(summary)
        else:
            self._voice.speak("Could not read the email on screen, Sir.")