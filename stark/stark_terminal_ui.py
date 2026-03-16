"""
STARK Terminal UI v3 — FULLY CONNECTED
────────────────────────────────────────
Run: python stark_terminal_ui.py

This version uses the REAL brain + all modules.
Commands ACTUALLY execute — YouTube opens, WhatsApp sends, screenshots taken, etc.
"""

import os, sys, time, json, re, threading
from datetime import datetime

# ── Add stark folder to path ──────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Install rich if missing ───────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.panel   import Panel
    from rich.text    import Text
    from rich.table   import Table
    from rich.align   import Align
    from rich.rule    import Rule
    from rich         import box
except ImportError:
    os.system("pip install rich -q")
    from rich.console import Console
    from rich.panel   import Panel
    from rich.text    import Text
    from rich.table   import Table
    from rich.align   import Align
    from rich.rule    import Rule
    from rich         import box

try:
    import speech_recognition as sr
except ImportError:
    os.system("pip install SpeechRecognition pyaudio -q")
    import speech_recognition as sr

try:
    import pyttsx3
    _engine = pyttsx3.init()
    _engine.setProperty("rate", 165)
    _engine.setProperty("volume", 1.0)
    for v in _engine.getProperty("voices"):
        if "david" in v.name.lower() or "zira" in v.name.lower():
            _engine.setProperty("voice", v.id)
            break
    TTS_OK = True
except Exception as e:
    print(f"TTS init: {e}")
    TTS_OK = False

# ── Load config ───────────────────────────────────────────────────────────────
import config

# ── Import ALL real STARK modules ─────────────────────────────────────────────
from modules.memory          import Memory
from modules.voice           import VoiceModule
from modules.ai_brain        import AIBrain
from modules.screen_monitor  import ScreenMonitor
from modules.camera_monitor  import CameraMonitor
from modules.meeting_assist  import MeetingAssistant
from modules.messaging       import MessagingModule
from modules.app_controller  import AppController
from modules.alarms          import AlarmModule
from modules.security        import SecurityModule
from modules.system_control  import SystemControl
from modules.travel          import TravelModule
from modules.location        import LocationModule
from modules.folder_manager  import FolderManager

try:
    from modules.screen_time import ScreenTimeMonitor
    SCREENTIME_OK = True
except Exception:
    SCREENTIME_OK = False

con = Console(highlight=False)
P="#00aaff"; G="#c9a84c"; S="#00ff88"; W="#ffaa00"; D="#334466"; T="#ccddee"; M="#556677"; E="#ff4444"

LOGO = """
  ███████╗████████╗ █████╗ ██████╗ ██╗  ██╗
  ██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██║ ██╔╝
  ███████╗   ██║   ███████║██████╔╝█████╔╝ 
  ╚════██║   ██║   ██╔══██║██╔══██╗██╔═██╗ 
  ███████║   ██║   ██║  ██║██║  ██║██║  ██╗
  ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝"""

# ── TTS — main thread only (Windows fix) ─────────────────────────────────────
def _do_speak(text: str):
    if not TTS_OK: return
    clean = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    clean = re.sub(r'\*(.+?)\*',     r'\1', clean)
    clean = re.sub(r'#+\s*',          '',    clean)
    clean = re.sub(r'\n+',            ' ',   clean)
    clean = re.sub(r'\s+',            ' ',   clean).strip()
    chunks = []; cur = ""
    for s in re.split(r'(?<=[.!?])\s+', clean):
        if len(cur)+len(s) < 200: cur += s+" "
        else:
            if cur.strip(): chunks.append(cur.strip())
            cur = s+" "
    if cur.strip(): chunks.append(cur.strip())
    for chunk in chunks:
        try: _engine.say(chunk); _engine.runAndWait()
        except:
            try: _engine.stop(); _engine.say(chunk); _engine.runAndWait()
            except: pass

# ── Custom VoiceModule that intercepts speak() to print + TTS ────────────────
class TerminalVoice(VoiceModule):
    """Override speak() to print to terminal AND speak aloud."""
    def speak(self, text: str) -> None:
        if not text: return
        # Print full answer to terminal
        clean = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        clean = re.sub(r'\*(.+?)\*',     r'\1', clean)
        clean = re.sub(r'#+\s*',          '',    clean)
        clean = re.sub(r'\n+',            ' ',   clean)
        # Clear spinner line first
        sys.stdout.write("\r" + " "*60 + "\r")
        sys.stdout.flush()
        print(f"\n\033[1;36m⚡ STARK\033[0m  {clean}\n", flush=True)
        # Speak aloud on main thread
        _do_speak(text)

# ── Speech recognition ────────────────────────────────────────────────────────
rec = sr.Recognizer()
rec.pause_threshold = 1.0
rec.energy_threshold = 300
rec.dynamic_energy_threshold = True

def listen_mic() -> str:
    with sr.Microphone() as src:
        try:
            rec.adjust_for_ambient_noise(src, duration=0.3)
            audio = rec.listen(src, timeout=6, phrase_time_limit=20)
        except sr.WaitTimeoutError: return ""
        except Exception as e:
            print(f"\033[31m  Mic error: {e}\033[0m"); return ""
    try:
        text = rec.recognize_google(audio, language="en-IN")
        # Auto-correct mishears of "STARK"
        low = text.lower().strip()
        mishears = ["dark","torque","talk","stalk","stock","stark","start","store"]
        # If first word sounds like STARK correction needed
        first = low.split()[0] if low.split() else ""
        if first in ["dark","torque","talk","stalk","stock"] and len(low.split()) > 1:
            text = "stark " + " ".join(text.split()[1:])
            print(f"[Corrected] → {text}")
        print(f"\033[33m  {config.USER_NAME}\033[0m  \033[90m❯\033[0m  \033[97m{text}\033[0m", flush=True)
        return text
    except sr.UnknownValueError: return ""
    except sr.RequestError as e:
        print(f"\033[31m  Speech error: {e}\033[0m"); return ""

# ── Spinner for processing ────────────────────────────────────────────────────
_processing = False

def show_spinner():
    # Simple spinner — just print once and wait, no looping print spam
    sys.stdout.write("  [90m⠋  Processing...[0m\n")
    sys.stdout.flush()
    while _processing:
        time.sleep(0.1)
    sys.stdout.write("\033[1A\033[2K")  # clear the Processing line
    sys.stdout.flush()


# ── Print header ──────────────────────────────────────────────────────────────
def print_header(ai_mode):
    h = datetime.now().hour
    greet = "Good morning" if h<12 else "Good afternoon" if h<17 else "Good evening"
    mc = {"ollama":"#00ff88","groq":"#00aaff","gemini":"#ffaa00"}.get(ai_mode,"#fff")
    t = Text(LOGO, style=f"bold {P}")
    t.append(f"\n  Personal AI OS  v8.0  ·  [{mc}]{ai_mode.upper()}[/]  ·  {greet}, {config.USER_NAME}!",
             style=M)
    con.print(Panel(Align.center(t), border_style=D, box=box.HEAVY_HEAD, padding=(0,2)))
    tbl = Table(box=None, show_header=False, padding=(0,2))
    tbl.add_column(); tbl.add_column(); tbl.add_column(); tbl.add_column(); tbl.add_column(justify="right")
    tbl.add_row(f"[{S}]● ONLINE[/]", f"[{P}]AI: [{mc}]{ai_mode.upper()}[/][/]",
                f"[{W}]● Memory[/]", "[#aa55ff]● Sensors[/]",
                f"[{M}]{datetime.now().strftime('%H:%M:%S')}[/]")
    con.print(tbl); con.print(Rule(style=D)); con.print()

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    global _processing

    os.system("cls" if os.name=="nt" else "clear")

    print_header(config.AI_MODE)

    con.print(f"[{M}]  Initialising all STARK modules...[/]")

    # ── Init all real modules ─────────────────────────────────────────────────
    memory    = Memory()
    voice     = TerminalVoice()     # our custom voice that prints + speaks
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

    location  = LocationModule(voice, brain._ask_ai)
    brain.set_location(location)

    folder_mgr = FolderManager(voice, brain._ask_ai)
    brain.set_folder_manager(folder_mgr)

    if SCREENTIME_OK:
        screentime = ScreenTimeMonitor(voice, brain._ask_ai)
        brain.set_screentime(screentime)
        screentime.start()

    # Start health monitor
    threading.Thread(target=brain.health_monitor, daemon=True).start()

    con.print(f"[{S}]  ✓ All modules online.[/]\n")


    # Show location — wait briefly for GPS to detect
    if location:
        import time as _t
        _t.sleep(2)   # let background GPS thread run first
        city = location._city or "Detecting..."
        con.print(f"[{S}]  Location: {city}, {location._region}[/]")

    # Welcome
    h = datetime.now().hour
    greet_msg = ("Good morning" if h<12 else "Good afternoon" if h<17 else "Good evening")
    greet_msg += f" {config.USER_NAME}! STARK is fully online. Just speak to me."

    con.print(Panel(
        f"[{T}]  {greet_msg}\n\n"
        f"  [{M}]All systems connected — YouTube, WhatsApp, Maps, Screenshots, everything works.[/]\n"
        f"  [{M}]Say [bold]exit[/] or press [bold]Ctrl+C[/] to quit.[/]",
        border_style=P, box=box.ROUNDED,
        title=f"[bold {P}]⚡ Voice Mode — Fully Connected[/]",
        padding=(0, 2)))
    con.print()

    # Speak greeting
    _do_speak(greet_msg)

    # ── Main voice loop ───────────────────────────────────────────────────────
    while True:
        try:
            print(f"\n\033[36m  ● Listening...\033[0m  \033[90m(speak now)\033[0m", flush=True)

            text = listen_mic()

            if not text:
                print(f"\033[90m  (no speech detected)\033[0m", flush=True)
                continue

            # Auto-correct speech-to-text errors for STARK name
            stt_fixes = {"dark ":"stark ","torque ":"stark ","tork ":"stark ",
                         "stock ":"stark ","mark ":"stark ","bark ":"stark ",
                         "clark ":"stark ","spark ":"stark "}
            text_lower = text.lower()
            for wrong, right in stt_fixes.items():
                if text_lower.startswith(wrong):
                    text = right + text[len(wrong):]
                    text_lower = text.lower()
                    break
                text = text.replace(" "+wrong.strip()+" ", " stark ")

            print(f"\n\033[33m  {config.USER_NAME}\033[0m  \033[90m❯\033[0m  \033[97m{text}\033[0m",
                  flush=True)

            # Exit
            if any(w in text.lower() for w in ("exit","quit","goodbye","bye stark","shut down stark")):
                bye = f"Goodbye {config.USER_NAME}. STARK shutting down."
                print(f"\n\033[1;36m⚡ STARK\033[0m  {bye}\n")
                _do_speak(bye)
                alarms.stop()
                camera.stop()
                break

            # Show spinner while processing
            _processing = True
            spin_thread = threading.Thread(target=show_spinner, daemon=True)
            spin_thread.start()

            # ── ACTUALLY EXECUTE the command using the real brain ─────────────
            # This calls app_controller, messaging, screenshot, maps — everything
            brain.process_command(text.lower().strip(), raw_text=text)

            _processing = False
            spin_thread.join(timeout=0.5)

            con.print(Rule(style=D))

        except KeyboardInterrupt:
            print(f"\n\n\033[36m  Goodbye, {config.USER_NAME}.\033[0m\n")
            alarms.stop()
            break
        except Exception as e:
            _processing = False
            print(f"\n\033[31m  Error: {e}\033[0m")
            import traceback; traceback.print_exc()
            continue

if __name__ == "__main__":
    main()