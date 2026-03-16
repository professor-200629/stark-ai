"""
STARK AI Brain  v8.0
New: Folder Manager, Location, Screen Time, Amazon search, WhatsApp calls,
     Companion mode, Activity recognition, Goal tracking
"""

import time
import re
import requests
import json
import webbrowser
import urllib.parse
import config

from modules.memory         import Memory
from modules.voice          import VoiceModule
from modules.app_controller import AppController
from modules.messaging      import MessagingModule
from modules.screen_monitor import ScreenMonitor
from modules.camera_monitor import CameraMonitor
from modules.meeting_assist import MeetingAssistant
from modules.social_media   import SocialMediaModule
from modules.file_explorer  import FileExplorerModule
from modules.agent          import agent_search, needs_agent_search, route_intent
try:
    from modules.email_module  import EmailModule
    _EMAIL_OK = True
except Exception: _EMAIL_OK = False

from modules.alarms         import AlarmModule
from modules.security       import SecurityModule
from modules.system_control import SystemControl


# ── System commands  -  NEVER trigger web search ───────────────────────────────
SYSTEM_COMMANDS = {
    "volume","brightness","scroll","screenshot","alarm","reminder","camera",
    "open","close","play","pause","resume","next","previous","mute","lock",
    "sleep","shutdown","restart","minimize","maximize","refresh","copy","paste",
    "save","tab","window","file","folder","desktop","downloads","whatsapp",
    "spotify","youtube","netflix","telegram","instagram","snapchat","remind",
    "security","register","stark","hello","hi","hey","good","morning","evening",
    "night","afternoon","how are you","thank","bye","exit","quit","stop","start",
    "delete","remove","write","generate","create","make","check","watch",
    "navigate","directions","maps","notepad",
}

WEB_SEARCH_TRIGGERS = [
    "best place","best restaurant","best hotel","best shop","best food",
    "near me","in tirupati","in hyderabad","in bangalore","in chennai",
    "in delhi","in mumbai","in india","nearby","nearest",
    "latest","current","today","right now","news","price","stock",
    "score","result","who won","release date","launch","update",
    "weather","temperature","forecast","climate",
    "new movie","new film","releasing","releasing now","movies releasing",
    "upcoming movie","box office","new songs","trending","came out",
    "this week","recently released","latest movie","latest song",
    "new album","ott release","streaming now","new release",
    "how to","step by step","guide","tutorial","tips to win",
    "how do i","how can i","what are the steps","explain me",
    "review","rating","compare","which one","should i buy",
    "recommend","suggest","best product","products for",
    "flights","trains","bus","ticket","booking",
    "hackathon","challenge","competition","contest","win",
]

# ══════════════════════════════════════════════════════════════════════════
# INTENT ROUTER  -  decides what STARK should do with each query
# ══════════════════════════════════════════════════════════════════════════

def classify_intent(query: str) -> str:
    """
    Returns: "system" | "local" | "web" | "ai"
    system = volume, brightness, screenshot, alarm etc
    local  = read file, open folder, screen, camera
    web    = movies, weather, news, restaurants, prices
    ai     = general knowledge, chat, explain
    """
    q = query.lower().strip()
    words = q.split()
    first = words[0] if words else ""

    # SYSTEM commands  -  hardware control
    system_starts = (
        "increase","decrease","raise","lower","reduce",
        "volume","brightness","mute","scroll","lock",
        "sleep","shutdown","restart","minimize","maximize",
        "take screenshot","take a screenshot","open screenshot",
        "delete screenshot","set alarm","cancel alarm",
        "remind me","navigate to","directions to","close",
        "open spotify","open youtube","open netflix","open amazon",
        "play youtube","play spotify","send message","whatsapp",
        "open maps","open chrome","open notepad","save","copy","paste",
    )
    for s in system_starts:
        if q.startswith(s):
            return "system"
    if first in {"increase","decrease","raise","lower","mute","scroll",
                 "lock","sleep","shutdown","restart","minimize","maximize",
                 "open","close","play","pause","take","delete","save",
                 "navigate","send","call","remind","cancel","set","write"}:
        return "system"

    # LOCAL commands  -  file, screen, camera actions
    local_keywords = [
        "read the text","read text","read screen","read this",
        "read the file","open file","open folder","check file",
        "fix file","edit file","create file","delete file",
        "what is on screen","summarise screen","summarize screen",
        "watch my screen","check my code","check for errors",
        "look at me","my emotion","how do i look","camera",
        "screenshot","my screen time","screen time",
    ]
    for k in local_keywords:
        if k in q:
            return "local"

    # WEB queries  -  need live internet data
    web_keywords = [
        "latest","this week","today","tonight","right now","current",
        "new movie","movies releasing","releasing this week","upcoming movie",
        "box office","ott release","trending","news","weather","forecast",
        "price","stock","score","result","who won","near me","nearby",
        "best restaurant","best hotel","best place","near","around me",
        "what time does","is open","opening hours",
    ]
    for k in web_keywords:
        if k in q:
            return "web"

    # Question forms -> AI knowledge (not web unless time-sensitive)
    if any(q.startswith(w+" ") for w in ["what","who","why","when","where",
                                          "how","which","explain","define",
                                          "tell me about","describe"]):
        return "ai"

    return "ai"


# ═══════════════════════════════════════════════════════════════════════════════
# INTENT ROUTER  -  decides what to do with every command
# ═══════════════════════════════════════════════════════════════════════════════

def classify_intent(query: str) -> str:
    """
    Returns: "system" | "local" | "web" | "ai"
    system = control laptop (volume, brightness, screenshot, apps)
    local  = read files, screen, camera, alarms
    web    = search internet for real-time info
    ai     = answer from AI knowledge
    """
    q = query.lower().strip()
    words = q.split()
    first = words[0] if words else ""

    # SYSTEM  -  laptop control commands
    system_starts = (
        "increase","decrease","raise","lower","reduce","turn up","turn down",
        "mute","unmute","volume","brightness","scroll","lock","sleep",
        "shutdown","restart","minimize","maximize","open","close","play",
        "pause","resume","take","navigate","directions","send","call",
        "save","copy","paste","write","generate","set alarm","remind",
        "delete screenshot","open screenshot","take screenshot",
    )
    for s in system_starts:
        if q.startswith(s):
            return "system"

    # LOCAL  -  file/screen/camera actions
    local_keywords = [
        "read the text","read text","read screen","read this",
        "read file","check file","open file","fix file","review folder",
        "check errors","watch my screen","screen errors","debug code",
        "what is on screen","summarise screen","camera","take photo",
        "screenshot","alarm","reminder","memory","note this",
    ]
    for kw in local_keywords:
        if kw in q:
            return "local"

    # WEB  -  real-time internet data needed
    web_keywords = [
        "latest","this week","today","tonight","right now","current",
        "new movie","releasing","released","upcoming","trending","viral",
        "news","weather","temperature","price","stock","score","result",
        "who won","near me","nearby","restaurant","hotel","hospital",
        "best place","in tirupati","in delhi","in mumbai","in india",
        "flights","trains","book","review","rating","compare",
        "hackathon","event","competition","what is happening",
    ]
    for kw in web_keywords:
        if kw in q:
            return "web"

    # Question words  -  use AI knowledge
    if any(q.startswith(w) for w in ["what","who","why","how","when","where",
                                      "which","is","are","can","does","do",
                                      "tell me","explain","describe"]):
        return "ai"

    return "ai"


def needs_web_search(query: str) -> bool:
    """Search web for factual questions  -  never for system commands."""
    q = query.lower().strip()
    words = q.split()
    first = words[0] if words else ""

    # HARD BLOCK  -  these NEVER search web, no matter what
    hard_block_starts = (
        "increase","decrease","raise","lower","reduce","turn up","turn down",
        "volume","brightness","mute","scroll","lock","sleep","shutdown","restart",
        "open","close","play","pause","take a","take screenshot","set alarm",
        "remind","cancel","navigate","send message","write in","generate",
        "save","copy","paste","minimize","maximize","zoom",
    )
    for block in hard_block_starts:
        if q.startswith(block):
            return False

    # If ANY of these appear anywhere in command  -  never search web
    never_search = [
        "volume","brightness","screenshot","alarm","reminder",
        "scroll down","scroll up","scroll to",
        "increase volume","decrease volume","raise volume","lower volume",
        "increase brightness","decrease brightness","increase the volume",
        "decrease the volume","increase the brightness","decrease the brightness",
        "mute","unmute","louder","quieter","brighter","dimmer",
        "lock screen","sleep mode","shutdown","restart","minimize","maximize",
        "take screenshot","open screenshot","delete screenshot",
        "set alarm","cancel alarm","remind me",
        "open spotify","open youtube","open netflix","open amazon",
        "play youtube","play spotify","pause","resume","next video",
        "send message","whatsapp","navigate to","directions to",
        "open maps","close app","close window","close tab",
        "copy","paste","save file","new tab","task manager",
        "open folder","review folder","generate code","write in notepad",
    ]
    for phrase in never_search:
        if phrase in q:
            return False

    # First word system commands
    pure_system = {
        "increase","decrease","raise","lower","reduce","turn up","turn down",
        "open","close","play","pause","take","delete","scroll","set",
        "lock","sleep","shutdown","restart","exit","quit","bye","mute",
        "minimize","maximize","copy","paste","save","write","generate",
        "navigate","send","call","remind","cancel",
    }
    if first in pure_system:
        return False

    # Short greetings
    if len(words) <= 2 and first in {"hi","hello","hey","thanks","bye","ok","yes","no"}:
        return False

    # Short greetings  -  no search needed
    if len(words) <= 2 and first in {"hi","hello","hey","thanks","bye","ok","yes","no"}:
        return False

    # ALWAYS search for real-world factual questions
    always_search = [
        # Places & local
        "restaurant","hotel","shop","store","mall","cinema","theatre","hospital",
        "near","nearby","best place","tirupati","hyderabad","bangalore","in india",
        # Movies & entertainment
        "movie","film","releasing","released","ott","streaming","song","album",
        "actor","actress","director","box office","trending","viral","trailer",
        # Current info
        "latest","current","now","today","price","cost","rate","stock",
        "news","update","winner","score","result","match","weather","forecast",
        # Facts & knowledge
        "who is","who was","who won","what is","when is","when was","where is",
        "how much","how many","how to","which is","which are","hackathon","event",
        # Products & tech
        "iphone","samsung","laptop","phone","buy","review","compare","vs","better",
        # Food & local
        "recipe","biryani","food","dish","cuisine","cook","hotel","resort",
    ]
    if any(t in q for t in always_search):
        return True

    # Any question form  -  search
    if q.endswith("?") or any(q.startswith(w+" ") for w in
            ["what","when","where","who","why","how","which","is","are","can",
             "does","do","tell","explain","describe","list","give"]):
        return True

    return False


# ── Prompts ───────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = f"""You are {config.STARK_NAME}, a brilliant AI assistant like JARVIS.
Always address the user as '{config.USER_NAME}'.

CRITICAL  -  CURRENT DATE: Today is March 16, 2026. The current year is 2026.
ALWAYS use 2026 for age calculations, "current year" references, and time-based answers.
NEVER say "as of 2023"  -  that is wrong. Always use 2026.

NO HALLUCINATION RULE:
- If you are not 100% sure of a fact, say "I am not certain, Sir"
- For cricket/sports stats: only state facts you are confident about
- For ages: calculate using current year 2026 minus birth year
- For movies: only mention movies you know exist  -  do not invent

ANSWER QUALITY  -  LIKE CHATGPT:
- Rich, detailed, well-structured answers
- Use numbered lists, bullet points when helpful
- For people: name, born, known for, current status (use 2026)
- For food/places: why famous, examples, cultural context
- For events: what it is, how to join, prizes
- For products: name, price in INR , where to buy in India

FUZZY UNDERSTANDING:
- If user says a name that sounds like a known person/movie, suggest the correct name
- Example: "Narendra 2" -> suggest "Did you mean Dhurandhar 2?"
- Handle speech-to-text errors and partial names intelligently

RULES:
- Current year is ALWAYS 2026
- Accurate answers only  -  no invented facts
- Support 50+ languages
- Never say you cannot do something"""

COMPANION_PROMPT = f"""You are STARK, a warm AI companion, coach, and best friend.
Address user as Sir. Be natural, warm, encouraging, funny when appropriate.
You are their: productivity coach, social wingman, life advisor, and cheerleader.

Companion behaviors:
- Notice what they are doing and offer contextual help
- Celebrate milestones enthusiastically
- Give encouragement and positive energy
- Suggest breaks with specific activities (stretch, water, quick quiz)
- Help with social situations (dates, conversations, gifts)
- Give personalized advice based on their goals
- Use phrases like "We've got this Sir!" and "You're doing amazing!"
- Be like a supportive teammate, not a robot"""

WEB_PROMPT = f"""You are {config.STARK_NAME} a brilliant AI assistant like JARVIS.
Address user as '{config.USER_NAME}'.
CURRENT DATE: March 16, 2026. Current year: 2026.

ANSWER STYLE - MATCH CHATGPT QUALITY:
Rich, detailed, well-structured answers with numbered steps and categories.

FOR TRAVEL: Cover 1) How to get there with transport options
2) Flight options airlines duration price 3) Visa requirements
4) Famous places with descriptions 5) Best time + budget estimate.

FOR PEOPLE: Full name, born, nationality, known for, current status.
Calculate age as 2026 minus birth year.

FOR MOVIES: Title, director, cast, release date, plot, ratings.

FOR FOOD/PLACES: Why famous, what to try, where, price range.

RULES:
- Use retrieved search data as primary source
- Supplement with knowledge if needed
- NEVER invent facts - if unsure say so honestly
- Current year is ALWAYS 2026
- Give complete structured answers not just 1-2 lines
- Use Indian Rupee for Indian prices"""


# ── AI backends ───────────────────────────────────────────────────────────────

def _call_ai(messages: list) -> str:
    mode = config.AI_MODE.lower()
    # Clean messages  -  remove empty content that causes 400 errors
    messages = [m for m in messages if m.get("content","").strip()]
    if not messages:
        return "No message to process, Sir."
    try:
        if mode == "groq":
            if config.GROQ_API_KEY == "YOUR_GROQ_API_KEY_HERE":
                return "Sir, please add your Groq API key in config.py"
            resp = requests.post(config.GROQ_URL,
                json={"model": config.GROQ_MODEL, "messages": messages,
                      "max_tokens": 1024},
                headers={"Authorization": f"Bearer {config.GROQ_API_KEY}",
                         "Content-Type": "application/json"}, timeout=30)
            if resp.status_code == 400:
                print(f"[Groq 400] {resp.text[:200]}")
                # Try with simpler message  -  just the last user message
                simple = [m for m in messages if m["role"] in ("system","user")][-2:]
                resp2 = requests.post(config.GROQ_URL,
                    json={"model": config.GROQ_MODEL, "messages": simple,
                          "max_tokens": 1024},
                    headers={"Authorization": f"Bearer {config.GROQ_API_KEY}",
                             "Content-Type": "application/json"}, timeout=30)
                if resp2.status_code == 200:
                    return resp2.json()["choices"][0]["message"]["content"].strip()
                print(f"[Groq retry 400] {resp2.text[:200]}")
                return "I am having trouble connecting to my AI brain, Sir. Please check your Groq key."
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()

        elif mode == "openrouter":
            if config.OPENROUTER_API_KEY == "YOUR_OPENROUTER_API_KEY_HERE":
                return ("Sir, please add your OpenRouter API key in config.py. "
                        "Get a free key at openrouter.ai")
            resp = requests.post(config.OPENROUTER_URL,
                json={"model": config.OPENROUTER_MODEL, "messages": messages},
                headers={"Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                         "Content-Type": "application/json",
                         "HTTP-Referer": "https://stark-ai.local",
                         "X-Title": "STARK AI"},
                timeout=30)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()

        elif mode == "gemini":
            if config.GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
                return "Sir, please add your Gemini API key in config.py"
            parts = [{"role": "user" if m["role"]=="user" else "model",
                      "parts":[{"text": m["content"]}]}
                     for m in messages if m["role"] != "system"]
            url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
                   f"{config.GEMINI_MODEL}:generateContent?key={config.GEMINI_API_KEY}")
            resp = requests.post(url, json={"contents": parts}, timeout=30)
            resp.raise_for_status()
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

        else:  # ollama
            resp = requests.post(config.OLLAMA_URL,
                json={"model": config.OLLAMA_MODEL, "messages": messages, "stream": False},
                timeout=60)
            resp.raise_for_status()
            return resp.json()["message"]["content"].strip()

    except requests.exceptions.ConnectionError:
        return (f"Sir, cannot connect to {mode}. "
                f"{'Please run: ollama serve' if mode=='ollama' else 'Check internet.'}")
    except Exception as e:
        return f"AI error: {e}"


def ask_ai_free(msg: str, history: list = None, system_override: str = "") -> str:
    if not msg or not msg.strip():
        return ""
    sys_p    = system_override or SYSTEM_PROMPT
    # Only send system + last user message to avoid bad history errors
    messages = [
        {"role": "system",  "content": sys_p[:1000]},
        {"role": "user",    "content": msg[:800]},
    ]
    return _call_ai(messages)


def _search_google(query: str) -> list:
    """Scrape Google search results."""
    results = []
    try:
        ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/120.0.0.0 Safari/537.36")
        url  = (f"https://www.google.com/search?q={urllib.parse.quote(query)}"
                f"&num=6&hl=en&gl=in")
        resp = requests.get(url, timeout=8, headers={
            "User-Agent": ua, "Accept-Language": "en-IN,en;q=0.9"})
        html = resp.text
        # Extract all text snippets
        snips = re.findall(
            r'<div[^>]*class="[^"]*(?:VwiC3b|s3v9rd|hgKElc|yXK7lf)[^"]*"[^>]*>(.*?)</div>',
            html, re.DOTALL)
        for s in snips[:8]:
            clean = re.sub(r'<[^>]+>','',s)
            clean = clean.replace("&amp;","&").replace("&#39;","'")                          .replace("&quot;",'"').replace("&#x27;","'").strip()
            if clean and len(clean) > 30:
                results.append(clean)
        # Also try BingBot snippet pattern
        if not results:
            snips2 = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
            for s in snips2[:5]:
                clean = re.sub(r'<[^>]+>','',s).strip()
                if clean and len(clean) > 40:
                    results.append(clean)
    except Exception as e:
        print(f"[Google] {e}")
    return results[:5]


def _search_ddg(query: str) -> list:
    """DuckDuckGo HTML search."""
    results = []
    try:
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        url  = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        resp = requests.get(url, timeout=8, headers={"User-Agent": ua})
        snips = re.findall(
            r'class="result__snippet"[^>]*>(.*?)</a>',
            resp.text, re.DOTALL)
        for s in snips[:6]:
            clean = re.sub(r'<[^>]+>','',s).strip()
            if clean and len(clean) > 30:
                results.append(clean)
    except Exception as e:
        print(f"[DDG] {e}")
    return results[:5]


def _search_wikipedia(query: str) -> list:
    """Wikipedia API search."""
    results = []
    try:
        term = re.sub(r'(what is|who is|what are|define|explain|tell me about)','',
                      query.lower()).strip()
        url  = (f"https://en.wikipedia.org/w/api.php?action=query"
                f"&list=search&srsearch={urllib.parse.quote(term)}"
                f"&format=json&srlimit=2&srprop=snippet")
        resp = requests.get(url, timeout=5,
            headers={"User-Agent":"STARK-AI/1.0"})
        hits = resp.json().get("query",{}).get("search",[])
        for h in hits:
            snippet = re.sub(r'<[^>]+>','',h.get("snippet","")).strip()
            if snippet:
                results.append(f"{h.get('title','')}: {snippet}")
    except Exception as e:
        print(f"[Wiki] {e}")
    return results


def _search_movies_tmdb(query: str) -> list:
    """TMDB for real movie data  -  no API key needed for basic queries."""
    results = []
    try:
        # Use TMDB without API key via public endpoint
        # Now playing in India
        url = "https://api.themoviedb.org/3/movie/now_playing?language=en-IN&region=IN&page=1"
        # Try without key first (public)
        resp = requests.get(url, timeout=5,
            headers={"User-Agent":"STARK-AI"})
        if resp.status_code == 401:
            # Need API key  -  use web scrape instead
            url2 = f"https://www.google.com/search?q={urllib.parse.quote(query + ' 2026 release date India')}&num=5&hl=en"
            resp2 = requests.get(url2, timeout=8,
                headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            snips = re.findall(
                r'<div[^>]*class="[^"]*VwiC3b[^"]*"[^>]*>(.*?)</div>',
                resp2.text, re.DOTALL)
            for s in snips[:5]:
                clean = re.sub(r'<[^>]+>','',s).strip()
                if clean and len(clean) > 20:
                    results.append(clean)
            return results
        data = resp.json()
        movies = data.get("results",[])[:5]
        for m in movies:
            results.append(
                f"{m.get('title','')} - Released: {m.get('release_date','')} "
                f"- Rating: {m.get('vote_average','')} - {m.get('overview','')[:80]}")
    except Exception as e:
        print(f"[TMDB] {e}")
    return results


def web_search(query: str) -> str:
    """Delegate to agent system."""
    from modules.agent import agent_search
    return agent_search(query)


def search_and_answer(question: str, history: list = None) -> str:
    """Full RAG pipeline: search -> context -> LLM -> answer."""
    print(f"[STARK Agent] Processing: {question[:60]}")

    context = web_search(question)

    q = question.lower()
    time_sensitive = any(w in q for w in [
        "this week","today","tonight","right now","current","latest",
        "new movie","releasing","upcoming","trending","news"])

    if context:
        prompt = (
            f"User asked: {question}\n\n"
            f"Retrieved data:\n{context}\n\n"
            f"Answer using this data as primary source. "
            f"Be specific  -  use real names, places, ratings from the data. "
            f"If data is insufficient, use your knowledge to supplement. "
            f"Be concise and accurate."
        )
        messages = [{"role":"system","content":WEB_PROMPT},
                    {"role":"user","content":prompt}]
        return _call_ai(messages)

    if time_sensitive:
        return (f"Sir, I could not access live data right now. "
                f"Please check Google for the latest information.")

    return ask_ai_free(question, history)



# ═══════════════════════════════════════════════════════════════════════════════
# BRAIN
# ═══════════════════════════════════════════════════════════════════════════════

class AIBrain:
    def __init__(self, memory, voice, app, messaging, screen,
                 camera, meeting, alarms, security, sysctl):
        self._memory         = memory
        self._voice          = voice
        self._app            = app
        self._msg            = messaging
        self._screen         = screen
        self._camera         = camera
        self._meeting        = meeting
        self._alarms         = alarms
        self._security       = security
        self._sys            = sysctl
        self._social         = SocialMediaModule(voice)
        self._files          = FileExplorerModule(voice, self._ask_ai)
        self._travel         = None
        self._screentime     = None
        self._location       = None
        self._folder_mgr     = None
        self._companion_mode = False
        self._last_nearby     = ""   # last "near me" search
        self._email           = EmailModule(voice, self._ask_ai) if _EMAIL_OK else None
        print(f"[STARK Brain v8] Online  -  AI: {config.AI_MODE.upper()}")

    def set_travel(self, t):       self._travel     = t
    def set_screentime(self, s):   self._screentime = s
    def set_location(self, l):     self._location   = l
    def set_folder_manager(self,f):self._folder_mgr = f

    def _ask_ai(self, msg: str, system_override: str = "") -> str:
        history = self._memory.get_recent_history(8)
        if needs_web_search(msg):
            return search_and_answer(msg, history)
        return ask_ai_free(msg, history, system_override)

    # ══════════════════════════════════════════════════════════════════════════
    def process_command(self, command: str, raw_text: str = "") -> None:
        cmd = command.lower().strip()

        # ── TRAVEL PLANNING  -  catch before navigation ────────────────────────────
        travel_keywords = ["travel to","trip to","visit","tourism","famous places",
                           "how to go to","want to go to","planning to go","i want to travel",
                           "places to visit","tourist places","best places in","sightseeing",
                           "flight to","how to reach","visa for","hotels in"]
        is_travel = any(w in cmd for w in travel_keywords)
        # Only trigger if it is clearly travel planning (not just "navigate to nearby")
        if is_travel and any(w in cmd for w in ["paris","london","dubai","singapore",
                                                 "new york","mumbai","delhi","goa",
                                                 "bangkok","bali","europe","america",
                                                 "international","abroad","foreign",
                                                 "famous places","tourist","tourism",
                                                 "places to visit","step by step"]):
            # Extract destination
            dest = cmd
            for n in ["i want to travel to","travel to","trip to","visit","how to go to",
                      "want to go to","planning to go to","i am in tirupati",
                      "i am in","tell me","step by step","famous places","what are the",
                      "can you tell me","so tell me"]:
                dest = dest.replace(n,"").strip()
            dest = re.sub(r'\s+',' ',dest).strip()
            # Origin
            origin = "Tirupati"
            if "from" in cmd:
                origin_part = cmd.split("from")[-1].split("to")[0].strip()
                if origin_part and len(origin_part) < 30:
                    origin = origin_part
            # Ask AI for rich travel plan
            self._voice.speak(f"Let me plan your trip to {dest}, Sir.")
            answer = search_and_answer(
                f"Travel guide: How to travel from {origin} to {dest}? "
                f"Include: 1) How to get there step by step, 2) Flight options, "
                f"3) Visa requirements for Indian passport, 4) Famous places to visit, "
                f"5) Best time to visit, 6) Estimated budget. "
                f"Give a complete structured travel guide.")
            self._voice.speak(answer)
            return

        # ── CLOSE / DELETE commands  -  catch before everything ────────────────────
        if any(w in cmd for w in ("delete all screenshots","delete screenshots",
                                   "remove all screenshots","clear screenshots")):
            import os as _os, glob as _glob
            folder = "stark_screenshots"
            if _os.path.exists(folder):
                files = _glob.glob(_os.path.join(folder, "*.png"))
                for f in files:
                    try: _os.remove(f)
                    except: pass
                self._voice.speak(f"Deleted {len(files)} screenshots, Sir.")
            else:
                self._voice.speak("No screenshots folder found, Sir.")
            return

        if any(w in cmd for w in ("close screenshot","close the screenshot",
                                   "hide screenshot","close image viewer")):
            import pyautogui as _pg
            _pg.hotkey("alt","F4")
            self._voice.speak("Closed the screenshot, Sir.")
            return

        if any(w in cmd for w in ("close google maps","close maps","close chrome",
                                   "close browser","close edge","close firefox")):
            target = "chrome" if "chrome" in cmd else                      "msedge" if "edge" in cmd else                      "firefox" if "firefox" in cmd else                      "chrome"
            os.system(f"taskkill /f /im {target}.exe >nul 2>&1")
            self._voice.speak(f"Closed {target}, Sir.")
            return

        # ── CLOSE apps  -  catch before open/maps ─────────────────────────────────
        if cmd.startswith("close") or (cmd.startswith("shut") and "down" not in cmd):
            target = cmd.replace("close the","").replace("close","").strip()
            if not target:
                self._sys.close_active_window(); return
            close_map = {
                "google maps":"chrome.exe","maps":"chrome.exe",
                "chrome":"chrome.exe","browser":"chrome.exe",
                "edge":"msedge.exe","firefox":"firefox.exe",
                "spotify":"Spotify.exe","notepad":"notepad.exe",
                "youtube":"chrome.exe","whatsapp":"chrome.exe",
            }
            import os as _os
            for key, proc in close_map.items():
                if key in target:
                    _os.system(f"taskkill /f /im {proc} >nul 2>&1")
                    self._voice.speak(f"Closed {key}, Sir.")
                    return
            # Close active window as fallback
            self._sys.close_active_window()
            self._voice.speak(f"Closed, Sir.")
            return

        # ── NAVIGATION  -  catch first before anything else ─────────────────────
        nav_words = ("navigate to","directions to","take me to","how to reach",
                     "route to","can you navigate","open navigation","go to",
                     "navigate to the location","take me there","show me the way",
                     "show directions","open directions")
        if any(w in cmd for w in nav_words):
            dest = cmd
            for n in sorted(nav_words, key=len, reverse=True):
                dest = dest.replace(n,"").strip()
            dest = re.sub(r'^(the |this |that )', '', dest).strip()

            # If no destination extracted, use last nearby search
            if not dest or dest in ("location","place","there","it","that"):
                dest = self._last_nearby or "current location"

            import webbrowser as _wb, urllib.parse as _up
            # Get city for better accuracy
            if self._location:
                loc = self._location.detect_location()
                city = loc.get("city","") if loc else ""
                if city and not any(c in dest.lower() for c in [city.lower(),"tirupati","hyderabad","bangalore"]):
                    dest_query = f"{dest} {city}"
                else:
                    dest_query = dest
            else:
                dest_query = dest

            url = f"https://www.google.com/maps/dir/?api=1&destination={_up.quote(dest_query)}"
            _wb.open(url)
            self._voice.speak(f"Opening Google Maps navigation to {dest}, Sir.")
            return

        # ══════════════════════════════════════════════════════════════════════
        # LIVE LOCATION
        # ══════════════════════════════════════════════════════════════════════
        if any(w in cmd for w in ("my current location","where am i","what is my location",
                                   "my location","current location","what city am i in",
                                   "where am i now","track my location","my gps")):
            if self._location:
                self._location.speak_location()
            return

        if any(w in cmd for w in ("show my location on map","show me on map",
                                   "open my location","show location on maps")):
            if self._location:
                self._location.show_on_map()
            return

        if any(w in cmd for w in ("start location tracking","track my location live",
                                   "location tracking on")):
            if self._location:
                self._location.start_tracking()
            return

        # ══════════════════════════════════════════════════════════════════════
        # EMAIL
        # ══════════════════════════════════════════════════════════════════════
        if any(w in cmd for w in ("open email","open gmail","check email","check gmail",
                                   "open my email")):
            if self._email:
                self._email.open_gmail()
            else:
                import webbrowser as _wb
                _wb.open("https://mail.google.com")
                self._voice.speak("Opening Gmail, Sir.")
            return

        if any(w in cmd for w in ("read my emails","read emails","read my mail",
                                   "how many emails","check my inbox","unread emails")):
            if self._email:
                self._email.read_emails(5)
            return

        if any(w in cmd for w in ("summarise email","summarize email","what does this email say",
                                   "read this email","what is this email about")):
            if self._email:
                self._email.summarise_current_email(self._screen)
            return

        if "email from" in cmd or "email about" in cmd:
            keyword = cmd.replace("email from","").replace("email about","").strip()
            if keyword and self._email:
                self._email.read_specific_email(keyword)
            return

        # ══════════════════════════════════════════════════════════════════════
        # INSTAGRAM REELS
        # ══════════════════════════════════════════════════════════════════════
        if any(w in cmd for w in ("open instagram reels","play reels","instagram reels",
                                   "open reels","show reels","play instagram")):
            self._social.open_instagram_reels(); return

        if any(w in cmd for w in ("trending instagram","instagram trending","explore instagram",
                                   "instagram explore","trending reels","show trending reels")):
            self._social.open_instagram_trending(); return

        if any(w in cmd for w in ("next reel","skip reel","next video reel")):
            self._social.instagram_next_reel(); return

        if any(w in cmd for w in ("previous reel","prev reel","go back reel")):
            self._social.instagram_prev_reel(); return

        # ══════════════════════════════════════════════════════════════════════
        # YOUTUBE TRENDING
        # ══════════════════════════════════════════════════════════════════════
        if any(w in cmd for w in ("youtube trending","trending youtube","what is trending",
                                   "trending videos","trending on youtube","show trending")):
            if "india" in cmd:
                self._social.open_youtube_trending_india()
            else:
                self._social.open_youtube_trending()
            return

        # ══════════════════════════════════════════════════════════════════════
        # SCROLL (social media aware)
        # ══════════════════════════════════════════════════════════════════════
        if "scroll down" in cmd:
            n = _extract_number(cmd) or 3
            self._social.scroll_down_page(n)
            return
        if "scroll up" in cmd:
            n = _extract_number(cmd) or 3
            self._social.scroll_up_page(n)
            return

        # ── Time/Date  -  answer directly ───────────────────────────────────────
        if any(w in cmd for w in ("what time","current time","what is the time",
                                   "tell me the time","what's the time")):
            import datetime as _dt
            now = _dt.datetime.now()
            self._voice.speak(
                f"It is {now.strftime('%I:%M %p')}, Sir.")
            return

        if any(w in cmd for w in ("what date","today date","what is today",
                                   "what day is today","current date")):
            import datetime as _dt
            now = _dt.datetime.now()
            self._voice.speak(
                f"Today is {now.strftime('%A, %d %B %Y')}, Sir.")
            return

        # ── Greetings  -  answer directly, no AI, no web search ───────────────
        if any(w in cmd for w in ("hello","hi stark","hey stark","hello stark",
                                   "good morning","good afternoon","good evening",
                                   "good night","how are you","what's up","sup")):
            import random, datetime
            h = datetime.datetime.now().hour
            greet = "Good morning" if h<12 else "Good afternoon" if h<17 else "Good evening"
            responses = [
                f"Hello Sir! How can I help you today?",
                f"{greet} Sir! I am online and ready.",
                f"Hello Sir! STARK is fully operational. What do you need?",
            ]
            self._voice.speak(random.choice(responses))
            return

        # ── Companion / boredom ───────────────────────────────────────────────
        if any(w in cmd for w in ("i am bored","i'm bored","feeling bored",
                                   "lonely","talk with me","entertain me",
                                   "keep me company","let's chat","let's talk")):
            self._companion_mode = True
            import random
            self._voice.speak(random.choice([
                "Of course Sir! I'm always here. What's on your mind?",
                "Let's talk Sir! Tell me about your day.",
                "I'm right here Sir! Want to hear something interesting?",
                "We've got time Sir! What shall we talk about?",
            ]))
            return

        # ── Camera ────────────────────────────────────────────────────────────
        if any(w in cmd for w in ("start camera","open camera","camera on")):
            self._camera.start_background()
            self._voice.speak("Camera live, Sir."); return
        if any(w in cmd for w in ("what do you see","look at me","my emotion",
                                   "how do i look","identify")):
            self._voice.speak(self._camera.describe_now()); return

        # ── Screenshot ────────────────────────────────────────────────────────
        if any(w in cmd for w in ("open screenshot","show screenshot","view screenshot",
                                   "open the screenshot","show the screenshot")):
            self._sys.open_last_screenshot(); return
        if any(w in cmd for w in ("take screenshot","take a screenshot",
                                   "capture screen","screenshot")):
            self._sys.take_screenshot(); return

        # ── Images ────────────────────────────────────────────────────────────
        if cmd.strip() in ("images","image","pictures","photos","show images"):
            history = self._memory.get_recent_history(2)
            last_topic = ""
            if history:
                for h in reversed(history):
                    if h["role"]=="user" and len(h["content"])>3:
                        last_topic = h["content"]; break
            query = last_topic or "products"
            webbrowser.open(
                f"https://www.google.com/search?q={urllib.parse.quote(query)}&tbm=isch")
            self._voice.speak(f"Opened Google Images for {last_topic or query}, Sir.")
            return

        if any(w in cmd for w in ("show me images","find images","image of",
                                   "picture of","show pictures","search images")):
            query = cmd
            for n in ["show me images of","show images of","find images of",
                      "image of","picture of","show pictures of","search images of",
                      "show me","show","find","search","images","pictures"]:
                query = query.replace(n,"").strip()
            if not query:
                self._voice.speak("What images, Sir?"); query = self._voice.listen()
            if query:
                webbrowser.open(
                    f"https://www.google.com/search?q={urllib.parse.quote(query)}&tbm=isch")
                self._voice.speak(f"Opened Google Images for {query}, Sir.")
            return

        # ── Screen reading ────────────────────────────────────────────────────
        if any(w in cmd for w in ("read the screen","read screen","read paragraph",
                                   "read the text","read text","read this text",
                                   "read what is on screen","read it",
                                   "read this page","read the page")):
            self._screen.speak_screen(); return

        if any(w in cmd for w in ("scroll down and read","read and scroll",
                                   "continuous read","keep reading","read continuously",
                                   "scroll and read","read full page","read everything")):
            self._screen.read_full_page(self._ask_ai); return

        if any(w in cmd for w in ("summarise screen","what is on screen",
                                   "summarize screen","summarise this","summarize this",
                                   "what does it say","tell me what is on screen")):
            self._screen.read_and_summarise(self._ask_ai); return

        # Image identification  -  "who is this", "identify image"
        # Image identification  -  take screenshot + Gemini vision
        if any(w in cmd for w in ("who is this","who is in the image","who is that",
                                   "identify this person","what is in the image",
                                   "identify the image","who are they","what do you see",
                                   "who is on screen","tell me his name","tell me her name",
                                   "what is his name","whose photo","identify this",
                                   "stark identify","tell me who","what is in front")):
            self._voice.speak("Let me look at your screen, Sir.")
            try:
                import pyautogui as _pg, base64, io
                from PIL import Image as _Img
                screenshot = _pg.screenshot()
                buf = io.BytesIO()
                screenshot.save(buf, format="PNG")
                img_b64 = base64.b64encode(buf.getvalue()).decode()
                # Try Gemini vision
                try:
                    import config as _cfg, requests as _req
                    if getattr(_cfg,"GEMINI_API_KEY","") not in ("","YOUR_GEMINI_API_KEY_HERE"):
                        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
                               f"gemini-1.5-flash:generateContent?key={_cfg.GEMINI_API_KEY}")
                        r = _req.post(url, json={"contents":[{"parts":[
                            {"text":"Who is this person? What is in this image? Give full name and details if possible. Be specific."},
                            {"inline_data":{"mime_type":"image/png","data":img_b64}}
                        ]}]}, timeout=15)
                        if r.status_code == 200:
                            ans = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                            self._voice.speak(ans[:300])
                            return
                except Exception as ge:
                    print(f"[Gemini vision] {ge}")
                # Fallback: read screen text
                text = self._screen.read_screen()
                if text:
                    ans = self._ask_ai(
                        f"From this screen text, identify who or what is shown. "
                        f"Give specific names:\n{text[:1500]}")
                    self._voice.speak(ans)
                else:
                    self._voice.speak(
                        "Sir, to identify images I need your Gemini API key. "
                        "Please add GEMINI_API_KEY to config.py.")
            except Exception as e:
                print(f"[Image ID] {e}")
                self._voice.speak("Could not identify image, Sir.")
            return
        if any(w in cmd for w in ("check for errors","check my code","debug code",
                                   "watch my screen","check my screen","check codes",
                                   "watch screen and check","screen and check"))                 and "file" not in cmd:
            self._voice.speak("Scanning your screen for code, Sir.")
            code = self._screen.get_screen_code()
            if code:
                answer = self._ask_ai(f"Find any errors in this code. Be specific:\n\n{code[:3000]}")
                self._voice.speak(answer)
            else:
                self._voice.speak("No code found on your screen, Sir.")
            return

        # ══════════════════════════════════════════════════════════════════════
        # SCREEN TIME & ACTIVITY
        # ══════════════════════════════════════════════════════════════════════
        if any(w in cmd for w in ("screen time","my screen time","how long",
                                   "time spent","productivity report","activity report")):
            if self._screentime:
                summary = self._screentime.get_today_summary()
                self._voice.speak(summary)
                print(summary)
            return

        if any(w in cmd for w in ("what am i doing","current activity",
                                   "what are you seeing","observe me")):
            if self._screentime:
                self._voice.speak(self._screentime.get_current_activity())
                self._screentime.observe_and_comment()
            return

        if any(w in cmd for w in ("set goal","my goal","add goal","track goal")):
            self._voice.speak("What is your goal, Sir?")
            goal_name = self._voice.listen()
            self._voice.speak("What activity? For example: python, react, writing")
            activity = self._voice.listen()
            self._voice.speak("How many hours per day?")
            try: hours = float(re.search(r'[\d.]+', self._voice.listen()).group())
            except: hours = 2.0
            if self._screentime and goal_name and activity:
                self._screentime.set_goal(goal_name, activity, hours)
            return

        if any(w in cmd for w in ("my goals","show goals","list goals")):
            if self._screentime:
                summary = self._screentime.list_goals()
                self._voice.speak(summary)
                print(summary)
            return

        if any(w in cmd for w in ("end of day","daily reflection","reflect today",
                                   "how was my day")):
            if self._screentime:
                self._screentime.end_of_day_reflection()
            return

        # ══════════════════════════════════════════════════════════════════════
        # LOCATION & NEARBY
        # ══════════════════════════════════════════════════════════════════════
        if any(w in cmd for w in ("where am i","my location","current location",
                                   "detect location","what city am i in")):
            if self._location: self._location.speak_location()
            return

        # "near me" or "nearby X"  -  open Google Maps directly
        # Skip nearby if it's about movies/entertainment/info queries
        _is_entertainment = any(w in cmd for w in
            ("movie","film","song","show","series","book","game","news",
             "error","code","bug","release","releasing","trending"))
        if not _is_entertainment and any(w in cmd for w in (
                "near me","nearby","nearest","close to me",
                "is there a","are there any","medical shop",
                "pharmacy","hospital","mall","theatre")):
            place_type = _extract_place_type(cmd)
            if not place_type:
                self._voice.speak("What are you looking for near you, Sir?")
                place_type = self._voice.listen()
            if place_type:
                self._last_nearby = place_type
                if self._location:
                    self._location.find_nearby(place_type)
                else:
                    import webbrowser as _wb, urllib.parse as _up
                    _wb.open(f"https://www.google.com/maps/search/{_up.quote(place_type + ' near me')}")
                    self._voice.speak(
                        f"Opened Google Maps showing {place_type} near you, Sir. "
                        f"Say navigate to go to the nearest one.")
            return

        # ── Ride booking ─────────────────────────────────────────────────────────
        if any(w in cmd for w in ("rapido","ola cab","uber","book cab","book ride",
                                   "book auto","book taxi","check taxi","check auto",
                                   "check rapido","check ola","check uber")):
            if "rapido" in cmd:
                webbrowser.open("https://rapido.bike")
                self._voice.speak("Opened Rapido for you, Sir. You can book an auto or bike.")
            elif "uber" in cmd:
                webbrowser.open("https://m.uber.com")
                self._voice.speak("Opened Uber for you, Sir.")
            else:
                webbrowser.open("https://www.olacabs.com")
                self._voice.speak("Opened Ola Cabs for you, Sir.")
            return

        if any(w in cmd for w in ("check any taxi","check any auto","book a ride",
                                   "rapido or ola","ola or uber","taxi or auto",
                                   "any cab","any taxi","any auto")):
            webbrowser.open("https://rapido.bike")
            import time as _t; _t.sleep(1)
            webbrowser.open("https://www.olacabs.com")
            _t.sleep(1)
            webbrowser.open("https://m.uber.com")
            self._voice.speak(
                "Opened Rapido, Ola, and Uber for you, Sir. "
                "You can check and book a taxi or auto from any of them.")
            return

        # Navigate  -  opens Google Maps directly
        if any(w in cmd for w in ("navigate to","directions to","take me to",
                                   "how to reach","route to","can you navigate")):
            dest = cmd
            for n in ["can you navigate to","navigate to","directions to",
                      "take me to","how to reach","route to"]:
                dest = dest.replace(n,"").strip()
            if dest:
                url = f"https://www.google.com/maps/dir/?api=1&destination={urllib.parse.quote(dest)}"
                webbrowser.open(url)
                self._voice.speak(f"Opened Google Maps navigation to {dest}, Sir.")
            return

        # Google Maps search
        if any(w in cmd for w in ("google maps","in maps","on maps",
                                   "search location","find location","open maps")):
            query = cmd
            for n in ["search the location","search location","find location",
                      "in google maps","on google maps","google maps","open maps",
                      "in maps","on maps","search","find","the","in","on"]:
                query = query.replace(n," ").strip()
            query = re.sub(r'\s+', ' ', query).strip()
            if query:
                webbrowser.open(
                    f"https://www.google.com/maps/search/{urllib.parse.quote(query)}")
                self._voice.speak(f"Opening Google Maps for {query}, Sir.")
            else:
                webbrowser.open("https://maps.google.com")
                self._voice.speak("Opening Google Maps, Sir.")
            return

        # ══════════════════════════════════════════════════════════════════════
        # FOLDER MANAGER
        # ══════════════════════════════════════════════════════════════════════
        if any(w in cmd for w in ("open stark folder","open my folder",
                                   "open folder","open project")):
            folder_name = cmd
            for n in ["open stark folder","open my folder","open folder",
                      "open project","open"]:
                folder_name = folder_name.replace(n,"").strip()
            if not folder_name:
                self._voice.speak("Which folder, Sir?")
                folder_name = self._voice.listen()
            if folder_name and self._folder_mgr:
                self._folder_mgr.open_folder(folder_name.strip())
            return

        if any(w in cmd for w in ("review folder","review all files","check all files",
                                   "review my code","review my project","check folder",
                                   "give review","check all","review the folder")):
            # Extract folder name from command
            folder_name = cmd
            for n in ["review folder","review all files","check all files",
                      "review my code","review my project","check folder",
                      "give review","check all files in","check all","review the folder",
                      "in file explorer","file explorer","there is a folder",
                      "name","and","review","check","give","stark","sir","please"]:
                folder_name = folder_name.replace(n,"").strip()
            folder_name = folder_name.strip()
            if self._folder_mgr:
                if folder_name and len(folder_name) > 1:
                    path = self._folder_mgr.open_folder(folder_name)
                    if path:
                        self._folder_mgr.review_folder(path)
                else:
                    self._folder_mgr.review_folder()
            return

        if any(w in cmd for w in ("fix all errors","fix folder","fix all files",
                                   "fix errors in folder")):
            if self._folder_mgr:
                self._folder_mgr.fix_folder_errors()
            return

        if any(w in cmd for w in ("add feature","add a feature","add functionality")):
            self._voice.speak("Which file, Sir?")
            fname = self._voice.listen()
            self._voice.speak("What feature should I add?")
            feature = self._voice.listen(phrase_limit=30)
            if fname and feature and self._folder_mgr:
                self._folder_mgr.add_feature(fname.strip(), feature)
            return

        if any(w in cmd for w in ("generate code file","create code file",
                                   "generate a","create a new file","make a new file")):
            self._voice.speak("What should the code do, Sir?")
            description = self._voice.listen(phrase_limit=30)
            self._voice.speak("What language? Python, JavaScript, HTML, Java?")
            lang = self._voice.listen() or "python"
            self._voice.speak("What should the file be named?")
            fname = self._voice.listen()
            if description and fname and self._folder_mgr:
                self._folder_mgr.generate_code_file(description, fname.strip(), lang)
            return

        if "list folder" in cmd or "list files" in cmd or "show files" in cmd:
            if self._folder_mgr:
                self._folder_mgr.list_folder()
            return

        # ══════════════════════════════════════════════════════════════════════
        # AMAZON SEARCH
        # ══════════════════════════════════════════════════════════════════════
        if "amazon" in cmd and any(w in cmd for w in ("search","find","buy",
                                                        "order","look for","show")):
            query = cmd
            for n in ["search on amazon","search amazon","find on amazon",
                      "buy on amazon","on amazon","amazon","search","find","buy"]:
                query = query.replace(n,"").strip()
            if not query:
                self._voice.speak("What product, Sir?")
                query = self._voice.listen()
            if query:
                url = f"https://www.amazon.in/s?k={urllib.parse.quote(query)}"
                webbrowser.open(url)
                self._voice.speak(f"Searching Amazon for {query}, Sir.")
            return

        # Flipkart search
        if "flipkart" in cmd and any(w in cmd for w in ("search","find","buy")):
            query = cmd
            for n in ["search flipkart","on flipkart","flipkart","search","find","buy"]:
                query = query.replace(n,"").strip()
            if not query:
                self._voice.speak("What product, Sir?")
                query = self._voice.listen()
            if query:
                webbrowser.open(
                    f"https://www.flipkart.com/search?q={urllib.parse.quote(query)}")
                self._voice.speak(f"Searching Flipkart for {query}, Sir.")
            return

        # ══════════════════════════════════════════════════════════════════════
        # VOLUME / BRIGHTNESS / SCROLL (NO web search)
        # ══════════════════════════════════════════════════════════════════════
        # Volume  -  check brightness NOT in command
        if any(w in cmd for w in ("volume up","raise volume","louder","vol up",
                                   "increase the volume","increase volume","turn up volume"))                 and "brightness" not in cmd:
            self._sys.volume_up(_extract_number(cmd) or 10); return
        if any(w in cmd for w in ("volume down","lower volume","quieter","vol down",
                                   "decrease the volume","decrease volume","turn down volume",
                                   "reduce volume"))                 and "brightness" not in cmd:
            self._sys.volume_down(_extract_number(cmd) or 10); return
        if any(w in cmd for w in ("mute","mute volume","silence")):
            self._sys.volume_mute(); return
        # Brightness  -  check volume NOT in command
        if any(w in cmd for w in ("brightness up","brighter","increase brightness",
                                   "increase the brightness","more brightness",
                                   "raise brightness"))                 and "volume" not in cmd:
            self._sys.brightness_up(_extract_number(cmd) or 10); return
        if any(w in cmd for w in ("brightness down","dimmer","decrease brightness",
                                   "decrease the brightness","less brightness",
                                   "reduce brightness","lower brightness"))                 and "volume" not in cmd:
            self._sys.brightness_down(_extract_number(cmd) or 10); return
        if "scroll down" in cmd: self._sys.scroll_down(); return
        if "scroll up"   in cmd: self._sys.scroll_up(); return
        if "scroll to top"    in cmd: self._sys.scroll_to_top(); return
        if "scroll to bottom" in cmd: self._sys.scroll_to_bottom(); return

        # ── System power ──────────────────────────────────────────────────────
        if any(w in cmd for w in ("lock screen","lock my screen")):
            self._sys.lock_screen(); return
        if any(w in cmd for w in ("sleep mode","sleep pc","put to sleep")):
            if self._voice.confirm("Sleep Sir?"):
                self._sys.sleep_pc(); return
        if any(w in cmd for w in ("shutdown","shut down","power off")):
            if self._voice.confirm("Shut down Sir?"):
                self._sys.shutdown_pc(); return
        if any(w in cmd for w in ("restart","reboot")):
            if self._voice.confirm("Restart Sir?"):
                self._sys.restart_pc(); return

        # ── Window control ────────────────────────────────────────────────────
        if "minimize" in cmd: self._sys.minimize_window(); return
        if "maximize" in cmd: self._sys.maximize_window(); return
        if "new tab"  in cmd: self._sys.new_tab();        return
        if "task manager" in cmd: self._sys.open_task_manager(); return
        # ── Write code to Notepad ────────────────────────────────────────────────
        if any(w in cmd for w in ("write in notepad","write to notepad","open notepad and write",
                                   "write code in notepad","save in notepad","notepad")):
            what = raw_text or command
            for noise in ["write in notepad","write to notepad","open notepad and write",
                          "write code in notepad","save in notepad","in notepad","stark","sir"]:
                what = what.lower().replace(noise,"").strip()
            self._voice.speak("Generating the code and opening Notepad, Sir.")
            code = self._ask_ai(
                f"Write this: {what}. Return ONLY the code/content, no explanation, no markdown.")
            if "```" in code:
                code = "\n".join(l for l in code.splitlines() if not l.strip().startswith("```"))
            tmp = os.path.join(os.path.expanduser("~"), "Desktop", "stark_output.py")
            try:
                with open(tmp,"w") as f: f.write(code)
                import subprocess
                subprocess.Popen(["notepad.exe", tmp])
                self._voice.speak(f"Code written and opened in Notepad, Sir.")
            except Exception as e:
                self._voice.speak(f"Could not open Notepad, Sir. {e}")
            print(f"\n[Notepad Code]\n{code}\n")
            return

        if any(w in cmd for w in ("open file explorer","open explorer")):
            self._sys.open_file_explorer(); return

        # ── Close ─────────────────────────────────────────────────────────────
        if cmd.startswith("close") or ("close" in cmd and
                any(w in cmd for w in ("app","window","tab","browser",
                                       "youtube","spotify","netflix","amazon"))):
            target = re.sub(r'close (the |this |)?', '', cmd).strip()
            self._app.close_app(target) if target else self._sys.close_active_window()
            return

        # ══════════════════════════════════════════════════════════════════════
        # PLAY  -  Spotify & YouTube
        # ══════════════════════════════════════════════════════════════════════
        if "spotify" in cmd and any(w in cmd for w in ("play","songs","music","open")):
            query = _extract_spotify_query(cmd)
            if not query:
                self._voice.speak("What songs, Sir?"); query = self._voice.listen()
            if query:
                import urllib.parse as _up, webbrowser as _wb, time as _t
                self._voice.speak(f"Opening Spotify for {query}, Sir.")
                # Open Spotify search  -  will auto-play first result
                search_url = f"https://open.spotify.com/search/{_up.quote(query)}"
                _wb.open(search_url)
                _t.sleep(3)
                # Press Enter to play first result
                import pyautogui as _pg
                _pg.hotkey("ctrl", "alt", "space")  # Spotify play shortcut
            return

        if "play" in cmd and ("youtube" in cmd or _is_media(cmd)):
            query = _extract_play_query(cmd)
            if not query:
                self._voice.speak("What shall I play, Sir?"); query = self._voice.listen()
            if query: self._app.play_youtube(query)
            return

        if any(w in cmd for w in ("skip ad",)): self._app.youtube_skip_ad(); return
        if any(w in cmd for w in ("next video","play next")): self._app.youtube_next(); return
        if any(w in cmd for w in ("previous video","play previous")): self._app.youtube_previous(); return
        if "pause" in cmd and "video" in cmd: self._app.youtube_pause_resume(); return
        if "resume" in cmd and "video" in cmd: self._app.youtube_pause_resume(); return

        # ══════════════════════════════════════════════════════════════════════
        # OPEN websites
        # ══════════════════════════════════════════════════════════════════════
        if any(w in cmd for w in ("open youtube",)): self._app.open_youtube(); return
        if any(w in cmd for w in ("open spotify",)): self._app.open_spotify(); return
        if any(w in cmd for w in ("open netflix",)): self._app.open_netflix(); return
        if any(w in cmd for w in ("open prime","prime video","amazon prime")): self._app.open_prime(); return
        if any(w in cmd for w in ("open hotstar","jio hotstar")): self._app.open_hotstar(); return
        if any(w in cmd for w in ("open whatsapp",)): self._app.open_whatsapp_web(); return

        if cmd.startswith("open "):
            target = cmd.replace("open ","").strip()
            site   = _extract_website(target)
            if site: self._app.open_url(site); return
            else:    self._app.open_app(target); return

        if any(w in cmd for w in ("search for","search on google")):
            query = cmd
            for n in ["search for","search on google","google search"]:
                query = query.replace(n,"").strip()
            if query:
                webbrowser.open(
                    f"https://www.google.com/search?q={urllib.parse.quote(query)}")
                self._voice.speak(f"Searching Google for {query}, Sir.")
            return

        # ══════════════════════════════════════════════════════════════════════
        # WEATHER
        # ══════════════════════════════════════════════════════════════════════
        if any(w in cmd for w in ("weather","temperature","forecast")):
            city = _extract_city_from_cmd(cmd)
            if not city and self._location:
                loc = self._location.detect_location()
                city = loc.get("city","Tirupati")
            city = city or "Tirupati"
            try:
                resp = requests.get(
                    f"https://wttr.in/{urllib.parse.quote(city)}?format=%C+%t+Humidity:%h",
                    timeout=5)
                if resp.status_code == 200 and resp.text.strip():
                    self._voice.speak(f"Weather in {city}: {resp.text.strip()}, Sir.")
                else: raise Exception()
            except Exception:
                self._voice.speak(
                    search_and_answer(f"current weather in {city}"))
            return

        # ══════════════════════════════════════════════════════════════════════
        # ALARMS & REMINDERS
        # ══════════════════════════════════════════════════════════════════════
        if any(w in cmd for w in ("set alarm","alarm at","wake me","wake me up")):
            t = _extract_time_full(cmd)
            if not t:
                self._voice.speak("What time, Sir?"); t = self._voice.listen()
            # Get label
            label = "Alarm"
            for trigger in ["to drink water","to eat","to take medicine","to call",
                            "to study","to workout","to sleep","to wake up"]:
                if trigger in cmd:
                    label = trigger.replace("to ","").capitalize()
                    break
            self._alarms.set_alarm(t.strip(), label); return

        if any(w in cmd for w in ("remind me","set reminder","reminder in")):
            mins  = _extract_minutes(cmd)
            label = _extract_reminder_label(cmd)
            if not mins:
                self._voice.speak("How many minutes, Sir?")
                try: mins = int(re.search(r'\d+', self._voice.listen()).group())
                except: mins = 30
            if not label:
                self._voice.speak("What shall I remind you about?")
                label = self._voice.listen() or "Reminder"
            self._alarms.set_reminder(mins, label); return

        if "every" in cmd and "remind" in cmd:
            mins  = _extract_minutes(cmd)
            label = _extract_reminder_label(cmd)
            if mins: self._alarms.set_recurring(mins, label or "Reminder"); return

        if any(w in cmd for w in ("show alarms","list alarms","my alarms")):
            self._alarms.list_alarms(); return
        if any(w in cmd for w in ("cancel alarm","stop alarm")):
            if "all" in cmd: self._alarms.cancel_all()
            else:
                t = cmd.replace("cancel alarm","").replace("stop alarm","").strip()
                if t: self._alarms.cancel_alarm(t)
            return

        # ══════════════════════════════════════════════════════════════════════
        # SECURITY
        # ══════════════════════════════════════════════════════════════════════
        if any(w in cmd for w in ("register my face","register face")):
            self._security.register_owner(); return
        if any(w in cmd for w in ("start security","activate security","security on")):
            self._security.start_monitoring(); return
        if any(w in cmd for w in ("stop security","security off")):
            self._security.stop_monitoring(); return

        # ══════════════════════════════════════════════════════════════════════
        # TRAVEL
        # ══════════════════════════════════════════════════════════════════════
        if self._travel:
            if any(w in cmd for w in ("travel guide","trip to","i am traveling")):
                city = _extract_city_from_cmd(cmd)
                if not city: self._voice.speak("Which city?"); city = self._voice.listen()
                if city: self._travel.travel_guide(city.strip()); return
            if "plan trip" in cmd or "itinerary" in cmd:
                city = _extract_city_from_cmd(cmd)
                if not city: self._voice.speak("Which city?"); city = self._voice.listen()
                m = re.search(r'(\d+)\s*day', cmd)
                days = int(m.group(1)) if m else 2
                if city: self._travel.plan_trip(city.strip(), days); return

        # ══════════════════════════════════════════════════════════════════════
        # FILE EXPLORER
        # ══════════════════════════════════════════════════════════════════════
        if any(w in cmd for w in ("go to desktop","open desktop")):
            self._files.go_to_desktop(); return
        if any(w in cmd for w in ("go to downloads","open downloads")):
            self._files.go_to_downloads(); return
        if "read file" in cmd:
            f = _extract_filename(cmd)
            if not f: self._voice.speak("Which file?"); f = self._voice.listen()
            if f: self._files.read_and_speak_file(f.strip()); return
        if ("check" in cmd or "errors in" in cmd) and "file" in cmd:
            f = _extract_filename(cmd)
            if not f: self._voice.speak("Which file?"); f = self._voice.listen()
            if f: self._files.check_file_for_errors(f.strip()); return
        if "fix file" in cmd:
            f = _extract_filename(cmd)
            if not f: self._voice.speak("Which file?"); f = self._voice.listen()
            if f: self._files.ai_fix_file(f.strip()); return
        if "delete line" in cmd:
            f, n = _extract_file_line(cmd)
            if not f: self._voice.speak("Which file?"); f = self._voice.listen()
            if not n:
                self._voice.speak("Which line?")
                try: n = int(self._voice.listen())
                except: n = 1
            self._files.delete_line(f, n); return
        if "add line" in cmd or "add code" in cmd:
            f = _extract_filename(cmd)
            if not f: self._voice.speak("Which file?"); f = self._voice.listen()
            self._voice.speak("What should the line say?")
            l = self._voice.listen(phrase_limit=30)
            if f and l: self._files.add_line(f.strip(), l); return
        if any(w in cmd for w in ("create file","new file")):
            f = _extract_filename(cmd)
            if not f: self._voice.speak("File name?"); f = self._voice.listen()
            if f: self._files.create_file(f.strip()); return
        if "delete file" in cmd:
            f = _extract_filename(cmd)
            if not f: self._voice.speak("Which file?"); f = self._voice.listen()
            if f: self._files.delete_file(f.strip()); return
        if "open vscode" in cmd:
            self._files.open_in_vscode(_extract_filename(cmd) or ""); return

        # ══════════════════════════════════════════════════════════════════════
        # WHATSAPP  -  improved call
        # ══════════════════════════════════════════════════════════════════════
        if any(w in cmd for w in ("send message","send a message","whatsapp message",
                                   "send on whatsapp","send in whatsapp",
                                   "message to mummy","tell mummy","message mummy",
                                   "say hi to mummy","send to mummy")) \
                and "instagram" not in cmd:
            contact, message = _extract_whatsapp_message(cmd, raw_text)
            if not contact: self._voice.speak("Who?"); contact = self._voice.listen()
            if not message: self._voice.speak("What?"); message = self._voice.listen()
            if contact and message: self._msg.whatsapp_send(contact, message)
            return

        # WhatsApp VIDEO call
        if any(w in cmd for w in ("video call","whatsapp video","video call to",
                                   "whatsapp video call","make a video call",
                                   "make video call","video call on whatsapp")):
            contact = cmd
            for n in ["make a video call on whatsapp to","make a video call to",
                      "video call on whatsapp to","video call on whatsapp",
                      "whatsapp video call to","whatsapp video call",
                      "video call to","video call","whatsapp video",
                      "make a","make","on whatsapp","whatsapp","video","call","to"]:
                contact = contact.replace(n,"").strip()
            contact = contact.strip()
            if not contact:
                self._voice.speak("Who should I video call, Sir?")
                contact = self._voice.listen()
            if contact:
                self._msg.whatsapp_video_call(contact)
            return

        if ("call" in cmd or "make call" in cmd or "whatsapp call" in cmd) \
                and "whatsapp" in cmd:
            # "call mummy in whatsapp" / "make call to mummy on whatsapp"
            contact = cmd
            for n in ["make call to","whatsapp call to","call to","call in whatsapp",
                      "call on whatsapp","make call","whatsapp call","in whatsapp",
                      "on whatsapp","whatsapp","call"]:
                contact = contact.replace(n,"").strip()
            contact = re.sub(r'\s+', ' ', contact).strip()
            if not contact:
                self._voice.speak("Who should I call on WhatsApp, Sir?")
                contact = self._voice.listen()
            if contact:
                # Resolve contact name to number
                number = config.CONTACTS.get(contact.lower(), "")
                if number:
                    confirmed = self._voice.confirm(
                        f"Shall I call {contact} on WhatsApp, Sir?")
                    if confirmed:
                        url = f"https://web.whatsapp.com/send?phone={number}"
                        webbrowser.open(url)
                        self._voice.speak(
                            f"WhatsApp is open for {contact}, Sir. "
                            f"Please click the call button.")
                else:
                    self._voice.speak(
                        f"I don't have {contact}'s number saved, Sir. "
                        f"Please add it to config.py contacts.")
            return

        # ── Social ────────────────────────────────────────────────────────────
        if "instagram" in cmd and any(w in cmd for w in ("send","message","dm")):
            user = _extract_social_target(cmd, "instagram")
            if not user: self._voice.speak("Who?"); user = self._voice.listen()
            self._voice.speak("What message?")
            msg = self._voice.listen(phrase_limit=30)
            if user and msg: self._social.instagram_send_dm(user.strip(), msg)
            return

        if ("snapchat" in cmd or "snap" in cmd) and any(w in cmd for w in ("send","message")):
            user = _extract_social_target(cmd, "snapchat")
            if not user: self._voice.speak("Who?"); user = self._voice.listen()
            self._voice.speak("What message?")
            msg = self._voice.listen(phrase_limit=30)
            if user and msg: self._social.snapchat_send_message(user.strip(), msg)
            return

        # ── Meeting ───────────────────────────────────────────────────────────
        if any(w in cmd for w in ("meeting question","show answer","help in meeting")):
            self._voice.speak("What is the question, Sir?")
            q = self._voice.listen(timeout=10, phrase_limit=30)
            if q:
                ans = self._ask_ai(q)
                self._meeting.show_answer(ans)
                print(f"[Meeting Answer]\n{ans}")
            return

        # ── Save contact by voice ─────────────────────────────────────────────────
        if any(w in cmd for w in ("save number","save contact","add contact",
                                   "add number","store number","remember number")):
            parts = cmd
            for n in ["save number","save contact","add contact","add number",
                      "store number","remember number"]:
                parts = parts.replace(n,"").strip()
            words = parts.split()
            name = ""; number = ""
            for w in words:
                cleaned = w.replace("+","").replace("-","")
                if cleaned.isdigit() and len(cleaned) >= 10:
                    number = ("+" if w.startswith("+") else "+91") + cleaned.lstrip("91").lstrip("0") if not w.startswith("+") else w
                elif cleaned not in ("plus","91","zero","one","two","three"):
                    if not name: name = w
            if not name:
                self._voice.speak("What is the contact name, Sir?")
                name = (self._voice.listen() or "").strip().lower()
            if not number:
                self._voice.speak("What is the phone number with country code?")
                raw = self._voice.listen() or ""
                digits = "".join(c for c in raw if c.isdigit())
                number = "+" + digits if digits else ""
            if name and number:
                try:
                    import config as _cfg
                    _cfg.CONTACTS[name] = number
                    # Persist to config.py
                    cfg_txt = open("config.py").read()
                    if f'"{name}"' not in cfg_txt:
                        cfg_txt = cfg_txt.replace("CONTACTS = {",
                            f'CONTACTS = {{"{name}": "{number}", ')
                        open("config.py","w").write(cfg_txt)
                    self._voice.speak(f"Saved! {name} is now {number}, Sir.")
                    print(f"[Contact] {name} -> {number}")
                except Exception as e:
                    self._voice.speak(f"Saved in memory, Sir. {name} is {number}.")
            return

        # ── Memory ────────────────────────────────────────────────────────────
        if any(w in cmd for w in ("remember","note this","save this")):
            info = cmd.replace("remember","").replace("note this","") \
                      .replace("save this","").strip()
            if info:
                self._memory.add_note(f"note_{int(time.time())}", info)
                self._voice.speak("Saved, Sir.")
            return
        if "what do you know about me" in cmd:
            self._voice.speak(self._memory.summary()); return

        # ══════════════════════════════════════════════════════════════════════
        # SMART FALLBACK
        # ══════════════════════════════════════════════════════════════════════
        history = self._memory.get_recent_history(8)

        if self._companion_mode:
            answer = ask_ai_free(raw_text or command, history, COMPANION_PROMPT)
        else:
            # Use intent router to decide what to do
            intent = classify_intent(cmd)
            print(f"[Intent] {intent} -> {cmd[:50]}")

            if intent == "web":
                answer = search_and_answer(raw_text or command, history)
            elif intent == "local":
                # Local actions handled above  -  if reached here, just AI answer
                answer = ask_ai_free(raw_text or command, history)
            else:
                # AI knowledge  -  no web search needed
                answer = ask_ai_free(raw_text or command, history)

        self._voice.speak(answer)
        self._memory.add_history("user",      raw_text or command)
        self._memory.add_history("assistant", answer)

        # Auto-open Google Images for product questions
        if any(w in cmd for w in ["suggest","recommend","best product","products for",
                                   "cream for","oil for","shampoo for","medicine for",
                                   "tablet for","phone for","which product"]):
            search_q = raw_text or command
            for n in ["suggest","recommend","best","which","what","products","for me",
                      "stark","please","sir","tell me","give me"]:
                search_q = search_q.lower().replace(n,"").strip()
            if search_q:
                import threading as _t
                def _open_images():
                    time.sleep(3)
                    url = f"https://www.google.com/search?q={urllib.parse.quote(search_q + ' India')}&tbm=isch"
                    webbrowser.open(url)
                    self._voice.speak("I have opened product images in your browser, Sir.")
                _t.Thread(target=_open_images, daemon=True).start()

    # ── Health monitor ────────────────────────────────────────────────────────
    def health_monitor(self):
        import random
        last_water    = time.time()
        last_break    = time.time()
        last_sleep_msg= 0
        work_start    = time.time()

        water_msgs = [
            f"Drink some water, {config.USER_NAME}. Staying hydrated keeps the mind sharp.",
            f"Time for water, {config.USER_NAME}. You have been working hard.",
            f"Please drink some water, {config.USER_NAME}.",
        ]
        break_msgs = [
            f"Take a 2-minute break, {config.USER_NAME}. Stand up and stretch.",
            f"You have been working for a while, {config.USER_NAME}. Take a short break.",
            f"Break time, {config.USER_NAME}. Rest your eyes for 2 minutes.",
        ]

        while True:
            time.sleep(60)
            now  = time.time()
            hour = __import__("datetime").datetime.now().hour

            # Water reminder every 45 min
            if (now - last_water) >= config.WATER_REMINDER_MINS * 60:
                self._voice.speak(random.choice(water_msgs))
                last_water = now

            # Break reminder every 60 min
            if (now - last_break) >= config.BREAK_REMINDER_MINS * 60:
                self._voice.speak(random.choice(break_msgs))
                last_break = now

            # Late night sleep reminder (11 PM - 2 AM)
            if hour in (23, 0, 1, 2) and (now - last_sleep_msg) > 3600:
                if hour == 23:
                    self._voice.speak(
                        f"It is getting late, {config.USER_NAME}. "
                        f"Please consider finishing up and getting some rest soon.")
                else:
                    self._voice.speak(
                        f"Sir, it is {hour} AM and you are still working. "
                        f"Please take a rest. Sleep well  -  we will continue tomorrow morning. "
                        f"Good night, {config.USER_NAME}.")
                last_sleep_msg = now

            # Long work session alert (after 2 hours continuous)
            if (now - work_start) >= 7200:
                self._voice.speak(
                    f"{config.USER_NAME}, you have been working for over 2 hours. "
                    f"Please take a proper break  -  even 5 minutes will help.")
                work_start = now  # reset counter


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_media(cmd):
    return any(k in cmd for k in ("song","songs","movie","trailer","video","music",
                                   "watch","listen","telugu","hindi","english","album",
                                   "bhajan","devotional","classical"))

def _extract_play_query(cmd):
    for p in ("play ","search and play ","youtube play ","open youtube and play "):
        if p in cmd:
            q = cmd.split(p,1)[1].strip()
            for n in ["on youtube","in youtube","youtube"]:
                q = q.replace(n,"").strip()
            return q
    return ""

def _extract_spotify_query(cmd):
    q = cmd
    for n in ["open spotify","play on spotify","on spotify","spotify",
              "play","songs","music","open"]:
        q = q.replace(n," ").strip()
    return re.sub(r'\s+', ' ', q).strip() if len(q.strip()) > 2 else ""

def _extract_place_type(cmd):
    # Clean command first  -  remove noise words that cause "ny" bug
    clean = cmd.lower()
    for noise in ["is there any","is there a","are there any","are there",
                  "can you find","find me","show me","search for",
                  "near me","nearby","nearest","close to me"]:
        clean = clean.replace(noise, " ").strip()
    clean = clean.strip()

    places = {
        "medical store": ["medical store","pharmacy","medicine shop","chemist","drug store","medical"],
        "hospital":      ["hospital","clinic","doctor","emergency"],
        "mall":          ["mall","shopping mall","shopping center","shopping centre"],
        "theatre":       ["theatre","cinema","movie hall","pvr","inox","movie theater"],
        "atm":           ["atm","cash machine"],
        "petrol pump":   ["petrol pump","petrol station","fuel station","gas station"],
        "restaurant":    ["restaurant","hotel","food","dining","eat"],
        "park":          ["park","garden","ground"],
        "gym":           ["gym","fitness center","workout"],
        "bank":          ["bank","banking"],
        "school":        ["school","college","university"],
        "supermarket":   ["supermarket","grocery store","big bazaar","more"],
    }
    for place_type, keywords in places.items():
        if any(k in cmd for k in keywords):
            return place_type

    # Return cleaned remainder after removing trigger words
    if clean and len(clean) > 2:
        # Remove leftover stop words
        for stop in ["any","a","the","some","find","search","show","there","near","me","nearby"]:
            clean = re.sub(r"\b" + stop + r"\b", "", clean).strip()
        clean = re.sub(r"\s+", " ", clean).strip()
        if clean and len(clean) > 2:
            return clean
    return ""

def _extract_path(cmd):
    # Check if command contains a path-like string
    import re
    m = re.search(r'[A-Za-z]:\\[\\w\s]+|/[/\w\s]+', cmd)
    return m.group() if m else ""

def _extract_whatsapp_message(cmd: str, raw: str) -> tuple:
    raw_lower = raw.lower()
    for pattern in [
        r'send\s+(?:message\s+to|to)\s+(\w+)\s+(.+?)(?:\s+in\s+whatsapp|$)',
        r'send\s+(\w+)\s+(.+?)(?:\s+in\s+whatsapp|\s+on\s+whatsapp|$)',
        r'message\s+(\w+)\s+(?:saying\s+)?(.+?)(?:\s+in\s+whatsapp|$)',
    ]:
        m = re.search(pattern, raw_lower, re.IGNORECASE)
        if m:
            contact = m.group(1).strip()
            message = m.group(2).strip()
            for noise in ["in whatsapp","on whatsapp","whatsapp"]:
                message = message.replace(noise,"").strip()
            if contact and message:
                return contact, message
    for name in config.CONTACTS.keys():
        if name in raw_lower:
            idx     = raw_lower.index(name)
            contact = name
            rest    = raw[idx + len(name):].strip()
            for noise in ["in whatsapp","on whatsapp","whatsapp","saying","say"]:
                rest = rest.lower().replace(noise,"").strip()
            return contact, rest
    return "", ""

def _extract_number(cmd):
    m = re.search(r'(\d+)', cmd)
    return int(m.group(1)) if m else None

def _extract_time_full(cmd: str) -> str:
    s = cmd.lower()
    s = s.replace("p.m.","pm").replace("a.m.","am")
    for pat in [r'(\d{1,2}):(\d{2})\s*(am|pm)',
                r'(\d{1,2})\s*(am|pm)',
                r'(\d{1,2}):(\d{2})']:
        m = re.search(pat, s)
        if m:
            g = m.groups()
            if len(g)==3: h,mins,ampm = int(g[0]),int(g[1]),g[2]
            elif len(g)==2 and g[1] in ("am","pm"): h,mins,ampm = int(g[0]),0,g[1]
            elif len(g)==2: h,mins,ampm = int(g[0]),int(g[1]),""
            else: continue
            if ampm=="pm" and h!=12: h+=12
            if ampm=="am" and h==12: h=0
            return f"{h:02d}:{mins:02d}"
    return ""

def _extract_minutes(cmd):
    m = re.search(r'in\s+(\d+)\s*(minute|min|hour|hr)', cmd)
    if m:
        n,u = int(m.group(1)),m.group(2)
        return n*60 if "hour" in u or u=="hr" else n
    m = re.search(r'every\s+(\d+)\s*(minute|min|hour|hr)', cmd)
    if m:
        n,u = int(m.group(1)),m.group(2)
        return n*60 if "hour" in u or u=="hr" else n
    return None

def _extract_reminder_label(cmd):
    for t in ("remind me to","remind me about","reminder to","reminder for"):
        if t in cmd:
            part = cmd.split(t,1)[1]
            part = re.sub(r'in\s+\d+\s*(minute|min|hour|hr)s?','',part)
            return part.strip()
    return ""

def _extract_city_from_cmd(cmd):
    stop = {"find","hotel","best","famous","local","stark","sir","what","which",
            "where","tell","show","the","a","an","is","me","my","weather",
            "temperature","guide","trip","plan","visit","flights","flight"}
    for t in ["in ","for ","to ","at ","visiting ","of "]:
        if t in cmd:
            part  = cmd.split(t,1)[1].strip()
            words = [w for w in part.split() if w not in stop]
            if words: return " ".join(words[:3])
    return ""

def _extract_website(name: str) -> str:
    sites = {
        "amazon":"https://www.amazon.in","flipkart":"https://www.flipkart.com",
        "google":"https://www.google.com","youtube":"https://www.youtube.com",
        "spotify":"https://open.spotify.com","netflix":"https://www.netflix.com",
        "instagram":"https://www.instagram.com","facebook":"https://www.facebook.com",
        "twitter":"https://www.twitter.com","x":"https://www.x.com",
        "whatsapp":"https://web.whatsapp.com","gmail":"https://mail.google.com",
        "github":"https://www.github.com","wikipedia":"https://www.wikipedia.org",
        "chatgpt":"https://chat.openai.com","prime":"https://www.primevideo.com",
        "hotstar":"https://www.jiohotstar.com","swiggy":"https://www.swiggy.com",
        "zomato":"https://www.zomato.com","myntra":"https://www.myntra.com",
        "meesho":"https://www.meesho.com","paytm":"https://www.paytm.com",
        "linkedin":"https://www.linkedin.com","reddit":"https://www.reddit.com",
        "stackoverflow":"https://stackoverflow.com","maps":"https://maps.google.com",
        "irctc":"https://www.irctc.co.in","makemytrip":"https://www.makemytrip.com",
        "naukri":"https://www.naukri.com","udemy":"https://www.udemy.com",
        "coursera":"https://www.coursera.org","bing":"https://www.bing.com",
    }
    n = name.lower().strip()
    for key, url in sites.items():
        if key in n: return url
    m = re.search(r'([\w]+\.(com|in|org|net|io|co))', n)
    if m: return "https://" + m.group(1)
    return ""

def _extract_filename(cmd):
    for w in cmd.split():
        if "." in w and len(w) > 2: return w
    stop = {"file","the","a","my","please","sir","in","on","read","open",
            "check","fix","delete","create","stark","errors","code","edit"}
    return next((w for w in reversed(cmd.split()) if w not in stop), "")

def _extract_file_line(cmd):
    f = _extract_filename(cmd)
    n = re.findall(r'\d+', cmd)
    return f, int(n[0]) if n else None

def _extract_social_target(cmd, platform):
    noise = {platform,"instagram","snapchat","snap","send","message","dm",
             "call","on","to","open","profile","stark","and","video"}
    return next((w for w in cmd.split() if w not in noise), "")