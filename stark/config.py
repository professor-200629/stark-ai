# ════════════════════════════════════════════════════════════
#  STARK config.py  — All FREE AI Options
# ════════════════════════════════════════════════════════════

# ── CHOOSE YOUR AI MODE ───────────────────────────────────
# Options: "groq" | "openrouter" | "gemini" | "ollama"
AI_MODE = "groq"

# ── OPTION 1: GROQ (Fastest free — recommended) ───────────
# Get free key at: https://console.groq.com
GROQ_API_KEY    = ""
GROQ_MODEL      = "llama-3.1-8b-instant"   # Current fast model
GROQ_URL        = "https://api.groq.com/openai/v1/chat/completions"

# ── OPTION 2: OPENROUTER (100% Free models) ───────────────
# Get free key at: https://openrouter.ai  (sign up → API keys)
# Free models available:
#   "meta-llama/llama-3.3-70b-instruct:free"  ← Best quality
#   "qwen/qwen3-coder-480b-a35b:free"         ← Best for coding
#   "microsoft/phi-4:free"                    ← Fast and smart
#   "mistralai/mistral-7b-instruct:free"      ← Lightweight
OPENROUTER_API_KEY = "YOUR_OPENROUTER_API_KEY_HERE"
OPENROUTER_MODEL   = "meta-llama/llama-3.3-70b-instruct:free"
OPENROUTER_URL     = "https://openrouter.ai/api/v1/chat/completions"

# ── OPTION 3: GOOGLE GEMINI (Free tier) ───────────────────
# Get free key at: https://aistudio.google.com/app/apikey
GEMINI_API_KEY  = "AIzaSyDHv_mq3Vv2ktFCN1wPKN5vOEKckeURn0E"
GEMINI_MODEL    = "gemini-1.5-flash"

# ── OPTION 4: OLLAMA (Offline) ────────────────────────────
OLLAMA_MODEL    = "llama3"
OLLAMA_URL      = "http://localhost:11434/api/chat"

# ── STARK SETTINGS ────────────────────────────────────────
STARK_NAME      = "STARK"
USER_NAME       = "Sir"
WAKE_WORD       = "stark"
REQUIRE_WAKE    = False
MEMORY_FILE     = "stark_memory.json"

# ── CONTACTS (add more by voice: "save number name +91XXXXXXXXXX") ──
CONTACTS = {
    "mummy" : "+918309351685",
}

# ── HEALTH REMINDERS ──────────────────────────────────────
WATER_REMINDER_MINS   = 45
BREAK_REMINDER_MINS   = 60
SLEEP_REMINDER_HOUR   = 23

# ── CAMERA ────────────────────────────────────────────────
CAMERA_INDEX          = 0
EMOTION_CHECK_SECS    = 10

# ── SCREEN ────────────────────────────────────────────────
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ── BROWSER ───────────────────────────────────────────────
YOUTUBE_URL       = "https://www.youtube.com"
SPOTIFY_URL       = "https://open.spotify.com"
NETFLIX_URL       = "https://www.netflix.com"
PRIME_URL         = "https://www.primevideo.com"
HOTSTAR_URL       = "https://www.jiohotstar.com"
WHATSAPP_WEB_URL  = "https://web.whatsapp.com"

TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"

# ── STARK API ─────────────────────────────────────────────
STARK_API_KEY  = "stark-secret-2024"
STARK_API_PORT = 5000