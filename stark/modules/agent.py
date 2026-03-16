"""
STARK Agent System
───────────────────
Proper AI Agent Architecture:
  User → Intent Router → Tool Selector → Execute Tool → Context Builder → LLM → Answer

Tools:
  - web_search    : general queries
  - weather       : weather queries  
  - movie_search  : movies/shows
  - wikipedia     : facts/knowledge
  - calculator    : math
  - local_search  : nearby places
  - news          : latest news

Features:
  - Smart caching (same question = instant answer)
  - Tool confidence scoring
  - Fallback chain
  - Real RAG pipeline
"""

import requests
import re
import json
import os
import time
import hashlib
import urllib.parse
from datetime import datetime

CACHE_FILE  = "stark_cache.json"
CACHE_TTL   = {
    "weather":      600,    # 10 min
    "movie_search": 3600,   # 1 hour
    "news":         300,    # 5 min
    "web_search":   1800,   # 30 min
    "wikipedia":    86400,  # 24 hours
    "calculator":   0,      # no cache needed
}

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"


# ═══════════════════════════════════════════════════════════════════════════════
# CACHE
# ═══════════════════════════════════════════════════════════════════════════════

class Cache:
    def __init__(self):
        self._data = {}
        self._load()

    def _load(self):
        if os.path.exists(CACHE_FILE):
            try:
                self._data = json.load(open(CACHE_FILE))
            except Exception:
                self._data = {}

    def _save(self):
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump(self._data, f)
        except Exception:
            pass

    def _key(self, query: str, tool: str) -> str:
        return hashlib.md5(f"{tool}:{query.lower().strip()}".encode()).hexdigest()

    def get(self, query: str, tool: str):
        key = self._key(query, tool)
        entry = self._data.get(key)
        if not entry:
            return None
        ttl = CACHE_TTL.get(tool, 1800)
        if ttl == 0:
            return None
        if time.time() - entry["time"] > ttl:
            del self._data[key]
            return None
        print(f"[Cache HIT] {tool}: {query[:40]}")
        return entry["result"]

    def set(self, query: str, tool: str, result: str):
        if not result:
            return
        key = self._key(query, tool)
        self._data[key] = {"result": result, "time": time.time()}
        # Keep cache under 500 entries
        if len(self._data) > 500:
            oldest = sorted(self._data.items(), key=lambda x: x[1]["time"])[:100]
            for k, _ in oldest:
                del self._data[k]
        self._save()


_cache = Cache()


# ═══════════════════════════════════════════════════════════════════════════════
# INTENT ROUTER — decides which tool to use
# ═══════════════════════════════════════════════════════════════════════════════

INTENT_MAP = {
    "weather": [
        "weather", "temperature", "forecast", "rain", "sunny", "humid",
        "hot outside", "cold outside", "climate", "will it rain",
    ],
    "movie_search": [
        "movie", "film", "cinema", "releasing", "box office", "ott",
        "bollywood", "tollywood", "hollywood", "new release", "upcoming movie",
        "streaming", "netflix movie", "prime movie", "this week movie",
    ],
    "news": [
        "latest news", "today news", "breaking news", "current news",
        "what happened", "news today", "recent news",
    ],
    "person": [
        "who is", "who was", "age of", "how old is", "born on",
        "birthday of", "biography", "about dhoni", "about modi",
        "about virat", "cricketer", "actor biography", "politician",
        "celebrity", "famous person", "tell me about",
    ],
    "local_search": [
        "near me", "nearby", "nearest", "restaurant near", "hotel near",
        "hospital near", "medical store near", "mall near", "in tirupati",
        "in hyderabad", "in bangalore", "in delhi", "best place in",
    ],
    "wikipedia": [
        "what is", "who is", "who was", "what are", "define", "explain",
        "meaning of", "history of", "how does", "hackathon", "event meaning",
        "what does", "tell me about",
    ],
    "calculator": [
        "calculate", "what is", "how much is", "convert", "percentage of",
        "+ ", "- ", "* ", "/ ", "divided by", "multiplied by", "plus", "minus",
    ],
    "web_search": [
        "latest", "today", "right now", "current", "2025", "2026",
        "this week", "this year", "new model", "price of", "cost of",
        "review of", "best ", "top ", "compare", "vs ", "versus",
        "who won", "score", "result", "launch", "release date",
    ],
}


def route_intent(query: str) -> list:
    """
    Returns list of tools to use in priority order.
    Multiple tools can be selected for better coverage.
    """
    q = query.lower().strip()
    scores = {}

    for intent, keywords in INTENT_MAP.items():
        score = sum(1 for kw in keywords if kw in q)
        if score > 0:
            scores[intent] = score

    if not scores:
        return ["web_search"]

    # Sort by score — highest first
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    tools  = [t for t, _ in ranked]

    # Always add web_search as final fallback
    if "web_search" not in tools:
        tools.append("web_search")

    print(f"[Intent] {tools[:2]} → {q[:50]}")
    return tools


# ═══════════════════════════════════════════════════════════════════════════════
# TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

def tool_weather(query: str) -> str:
    cached = _cache.get(query, "weather")
    if cached: return cached

    city = re.sub(
        r"(weather|temperature|forecast|rain|sunny|humid|climate|"
        r"in|at|for|current|right now|today|what is|how is|tell me|outside)",
        "", query.lower()).strip() or "Tirupati"

    try:
        # Detailed weather
        resp = requests.get(
            f"https://wttr.in/{urllib.parse.quote(city)}"
            f"?format=%l:+%C+%t+Feels+like+%f+Humidity+%h+Wind+%w",
            timeout=5, headers={"User-Agent": UA})
        if resp.status_code == 200 and resp.text.strip():
            result = resp.text.strip()
            _cache.set(query, "weather", result)
            return result
    except Exception: pass
    return ""


def tool_movies(query: str) -> str:
    cached = _cache.get(query, "movie_search")
    if cached: return cached

    result_parts = []

    # TMDB now playing
    try:
        resp = requests.get(
            "https://api.themoviedb.org/3/movie/now_playing"
            "?api_key=8265bd1679663a7ea12ac168da84d2e8&language=en-US&region=IN&page=1",
            timeout=5)
        if resp.status_code == 200:
            movies = resp.json().get("results", [])[:8]
            if movies:
                titles = [f"{m['title']} ({m.get('vote_average',0):.1f}★)" for m in movies]
                result_parts.append("Now in cinemas: " + ", ".join(titles))
    except Exception: pass

    # TMDB upcoming
    try:
        resp = requests.get(
            "https://api.themoviedb.org/3/movie/upcoming"
            "?api_key=8265bd1679663a7ea12ac168da84d2e8&language=en-US&region=IN&page=1",
            timeout=5)
        if resp.status_code == 200:
            movies = resp.json().get("results", [])[:5]
            if movies:
                titles = [m["title"] for m in movies]
                result_parts.append("Upcoming: " + ", ".join(titles))
    except Exception: pass

    # BookMyShow India fallback
    if not result_parts:
        try:
            resp = requests.get(
                "https://in.bookmyshow.com/explore/movies-tirupati",
                timeout=5, headers={"User-Agent": UA})
            titles = re.findall(r'"name"\s*:\s*"([A-Za-z][^"]{2,40})"', resp.text)
            unique = list(dict.fromkeys(titles))[:8]
            if unique:
                result_parts.append("Playing now: " + ", ".join(unique))
        except Exception: pass

    result = " | ".join(result_parts)
    if result:
        _cache.set(query, "movie_search", result)
    return result


def tool_wikipedia(query: str) -> str:
    cached = _cache.get(query, "wikipedia")
    if cached: return cached

    try:
        term = re.sub(
            r"(what is|who is|what are|define|explain|tell me about|"
            r"which is|how does|meaning of|history of|what does)", "",
            query.lower()).strip()
        resp = requests.get(
            f"https://en.wikipedia.org/w/api.php"
            f"?action=query&list=search&srsearch={urllib.parse.quote(term)}"
            f"&format=json&srlimit=2",
            timeout=5, headers={"User-Agent": UA})
        hits = resp.json().get("query",{}).get("search",[])
        parts = []
        for h in hits[:2]:
            snip = re.sub(r"<[^>]+>","",h.get("snippet","")).strip()
            if snip:
                parts.append(f"{h.get('title','')}: {snip}")
        result = " | ".join(parts)
        if result:
            _cache.set(query, "wikipedia", result)
        return result
    except Exception:
        return ""


def tool_calculator(query: str) -> str:
    try:
        import re as _re
        # Extract math expression
        expr = _re.sub(r"(calculate|what is|how much is|equals|=)", "", query.lower())
        expr = expr.replace("plus","+").replace("minus","-")
        expr = expr.replace("multiplied by","*").replace("times","*")
        expr = expr.replace("divided by","/").replace("percent","/100*")
        # Keep only safe math chars
        safe = _re.sub(r"[^0-9+\-*/().\s]","", expr).strip()
        if safe:
            result = eval(safe)
            return f"{safe} = {result}"
    except Exception:
        pass
    return ""


def tool_web_search(query: str) -> str:
    cached = _cache.get(query, "web_search")
    if cached: return cached

    results = []

    # Google scrape
    try:
        resp = requests.get(
            f"https://www.google.com/search?q={urllib.parse.quote(query)}&num=8&hl=en&gl=in",
            timeout=8, headers={
                "User-Agent": UA,
                "Accept-Language": "en-IN,en;q=0.9",
            })
        html = resp.text
        for pattern in [
            r'<div[^>]*class="[^"]*BNeawe[^"]*"[^>]*>(.*?)</div>',
            r'<span[^>]*class="[^"]*ILfuVd[^"]*"[^>]*>(.*?)</span>',
        ]:
            hits = re.findall(pattern, html, re.DOTALL)
            for h in hits[:5]:
                c = re.sub(r'<[^>]+>','',h).strip()
                c = c.replace("&amp;","&").replace("&#39;","'").replace("&quot;",'"')
                c = re.sub(r'\s+',' ',c).strip()
                if c and len(c) > 50 and c not in results:
                    results.append(c)
            if len(results) >= 3: break
    except Exception as e:
        print(f"[Google] {e}")

    # DuckDuckGo fallback
    if len(results) < 2:
        try:
            resp = requests.get(
                f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1",
                timeout=5, headers={"User-Agent": UA})
            d = resp.json()
            if d.get("AbstractText") and len(d["AbstractText"]) > 30:
                results.insert(0, d["AbstractText"])
        except Exception: pass

        try:
            resp = requests.get(
                f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}",
                timeout=6, headers={"User-Agent": UA})
            snips = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
            for s in snips[:4]:
                c = re.sub(r'<[^>]+>','',s).strip()
                if c and len(c) > 40 and c not in results:
                    results.append(c)
        except Exception: pass

    result = " | ".join(results[:4])
    if result:
        _cache.set(query, "web_search", result)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT BUILDER + MAIN AGENT FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════


def tool_person(query: str) -> str:
    """Look up person facts from Wikipedia — accurate birth dates, ages, career."""
    cached = _cache.get(query, "wikipedia")
    if cached: return cached

    # Extract person name
    name = re.sub(
        r"(who is|tell me about|age of|how old is|when was|born|birthday of|"
        r"what is|about|the|a|an|sir|please)", "", query.lower()).strip()

    try:
        # Wikipedia search
        resp = requests.get(
            f"https://en.wikipedia.org/w/api.php"
            f"?action=query&list=search&srsearch={urllib.parse.quote(name)}"
            f"&format=json&srlimit=1",
            timeout=5, headers={"User-Agent": UA})
        hits = resp.json().get("query",{}).get("search",[])
        if not hits:
            return ""

        page_title = hits[0]["title"]

        # Get page extract
        resp2 = requests.get(
            f"https://en.wikipedia.org/w/api.php"
            f"?action=query&titles={urllib.parse.quote(page_title)}"
            f"&prop=extracts&exintro=1&explaintext=1&format=json",
            timeout=5, headers={"User-Agent": UA})
        pages = resp2.json().get("query",{}).get("pages",{})
        for page in pages.values():
            extract = page.get("extract","")
            if extract:
                # Get first 500 chars — most relevant
                result = extract[:600].strip()
                _cache.set(query, "wikipedia", result)
                return result
    except Exception as e:
        print(f"[Person lookup] {e}")
    return ""


def fuzzy_entity_correct(query: str) -> str:
    """
    Correct speech-to-text errors and fuzzy names.
    Returns corrected query or original if no correction needed.
    """
    q = query.lower()

    # Movie name corrections (common STT errors)
    corrections = {
        "narendra 2":    "Dhurandhar 2",
        "dhirendra 2":   "Dhurandhar 2",
        "dhurendra 2":   "Dhurandhar 2",
        "dhurender 2":   "Dhurandhar 2",
        "narendra modi movie": "PM Narendra Modi movie",
        "bahubali 3":    "Baahubali 3",
        "bahubali":      "Baahubali",
        "rr r":          "RRR movie",
        "salaar 2":      "Salaar Part 2",
        "kgf 3":         "KGF Chapter 3",
        "pushpa 3":      "Pushpa 3",
    }

    for wrong, correct in corrections.items():
        if wrong in q:
            print(f"[Fuzzy] Corrected: {wrong} → {correct}")
            return query.replace(wrong, correct)

    return query


TOOL_MAP = {
    "weather":      tool_weather,
    "movie_search": tool_movies,
    "wikipedia":    tool_wikipedia,
    "person":       tool_person,
    "calculator":   tool_calculator,
    "web_search":   tool_web_search,
    "local_search": tool_web_search,
    "news":         tool_web_search,
}


def agent_search(query: str) -> str:
    """
    Full agent pipeline:
    Query → Fuzzy Correct → Intent → Tools → Context → LLM prompt ready
    """
    # Apply fuzzy entity correction first
    query = fuzzy_entity_correct(query)
    tools = route_intent(query)
    context_parts = []

    # Execute top 2 tools
    for tool_name in tools[:2]:
        tool_fn = TOOL_MAP.get(tool_name)
        if not tool_fn:
            continue
        try:
            result = tool_fn(query)
            if result and len(result) > 20:
                context_parts.append(f"[{tool_name}] {result}")
                if len(context_parts) >= 2:
                    break
        except Exception as e:
            print(f"[Tool {tool_name}] {e}")

    context = " | ".join(context_parts)
    print(f"[Agent] Context: {len(context)} chars from {tools[:2]}")
    return context


def needs_agent_search(query: str) -> bool:
    """Decide if we need web search or just AI knowledge."""
    q = query.lower().strip()
    words = q.split()
    first = words[0] if words else ""

    # System commands — never search
    system_starts = (
        "increase","decrease","raise","lower","reduce","turn",
        "volume","brightness","mute","scroll","lock","sleep",
        "shutdown","restart","minimize","maximize","open","close",
        "play","pause","take","navigate","send","call","save",
        "copy","paste","write","generate","set alarm","remind",
        "delete","screenshot",
    )
    for s in system_starts:
        if q.startswith(s):
            return False

    # Always search
    always = [
        "weather","temperature","movie","film","releasing","news",
        "latest","today","right now","current","this week","nearby",
        "near me","best place","restaurant","hotel","hospital","price",
        "score","result","who won","review","compare","vs",
    ]
    return any(w in q for w in always) or q.endswith("?")