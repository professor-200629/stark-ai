"""
STARK Voice Module  v3
Fixed: Speaks FULL answer by splitting into small chunks
No truncation — reads everything completely
"""

import pyttsx3
import speech_recognition as sr
import threading
import re
import config


def _clean_for_speech(text: str) -> str:
    """Remove markdown formatting before speaking."""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*',     r'\1', text)
    text = re.sub(r'#+\s*',          '',    text)
    text = re.sub(r'https?://\S+',   '',    text)
    text = re.sub(r'\n+',            ' ',   text)
    text = re.sub(r'\s+',            ' ',   text)
    return text.strip()


def _split_into_chunks(text: str, chunk_size: int = 200) -> list:
    """
    Split long text into speakable chunks at sentence boundaries.
    Each chunk max ~200 chars so TTS never times out.
    """
    clean = _clean_for_speech(text)
    if len(clean) <= chunk_size:
        return [clean]

    # Split at sentence endings
    sentences = re.split(r'(?<=[.!?])\s+', clean)
    chunks  = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) <= chunk_size:
            current += sentence + " "
        else:
            if current.strip():
                chunks.append(current.strip())
            current = sentence + " "

    if current.strip():
        chunks.append(current.strip())

    return chunks if chunks else [clean[:chunk_size]]


class VoiceModule:
    def __init__(self):
        self._engine = pyttsx3.init()
        self._engine.setProperty("rate",   170)
        self._engine.setProperty("volume", 1.0)

        voices = self._engine.getProperty("voices")
        for v in voices:
            if "david" in v.name.lower() or "zira" in v.name.lower() \
                    or "english" in v.name.lower():
                self._engine.setProperty("voice", v.id)
                break

        self._speak_lock = threading.Lock()
        self._recogniser = sr.Recognizer()
        self._recogniser.pause_threshold          = 1.0
        self._recogniser.energy_threshold         = 300
        self._recogniser.dynamic_energy_threshold = True

        print("[STARK Voice] Initialised.")

    # ── Speak — reads FULL text in chunks ────────────────────────────────────
    def speak(self, text: str) -> None:
        if not text:
            return

        # Always print full answer
        print(f"\n[STARK] → {text}\n")

        chunks = _split_into_chunks(text, chunk_size=200)

        with self._speak_lock:
            for chunk in chunks:
                if not chunk.strip():
                    continue
                try:
                    self._engine.say(chunk)
                    self._engine.runAndWait()
                except Exception as e:
                    print(f"[Voice TTS error] {e}")
                    # Try reinitialising engine
                    try:
                        self._engine = pyttsx3.init()
                        self._engine.setProperty("rate",   170)
                        self._engine.setProperty("volume", 1.0)
                        self._engine.say(chunk)
                        self._engine.runAndWait()
                    except Exception:
                        pass

    # ── Listen ────────────────────────────────────────────────────────────────
    def listen(self, timeout: int = 5, phrase_limit: int = 15) -> str:
        with sr.Microphone() as source:
            try:
                self._recogniser.adjust_for_ambient_noise(source, duration=0.3)
                print("[STARK] Listening…")
                audio = self._recogniser.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_limit,
                )
            except sr.WaitTimeoutError:
                return ""
            except Exception as e:
                print(f"[Voice listen error] {e}")
                return ""

        try:
            text = self._recogniser.recognize_google(audio, language="en-IN")
            print(f"[You said] {text}")
            return text
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            print(f"[Voice recognition error] {e}")
            return ""

    # ── Confirm ───────────────────────────────────────────────────────────────
    def confirm(self, question: str) -> bool:
        self.speak(question)
        ans = self.listen(timeout=6).lower()
        return any(w in ans for w in ("yes","yeah","yep","sure","ok",
                                      "okay","do it","go ahead","confirm"))