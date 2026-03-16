"""
STARK Travel & Location Intelligence Module
────────────────────────────────────────────
Features:
  - Detect current location (IP-based)
  - Search hotels, restaurants, tourist spots
  - Famous local food suggestions
  - Devotional / temple places
  - Parks, museums, shopping
  - Weather at destination
  - Acts as a local tour guide
  - Uses web search via AI brain
  - No paid API needed
"""

import requests
import json
import webbrowser
import urllib.parse


class TravelModule:
    def __init__(self, voice, ask_ai_fn):
        self._voice  = voice
        self._ask_ai = ask_ai_fn
        self._current_location = None
        print("[STARK Travel] Initialised.")

    # ── Get current location ──────────────────────────────────────────────────
    def get_current_location(self) -> dict:
        """Get approximate location from IP address — no GPS needed."""
        try:
            resp = requests.get("http://ip-api.com/json/", timeout=5)
            data = resp.json()
            if data.get("status") == "success":
                self._current_location = {
                    "city":    data.get("city", ""),
                    "region":  data.get("regionName", ""),
                    "country": data.get("country", ""),
                    "lat":     data.get("lat", 0),
                    "lon":     data.get("lon", 0),
                }
                return self._current_location
        except Exception as e:
            print(f"[Travel] Location error: {e}")
        return {}

    def speak_location(self) -> None:
        loc = self.get_current_location()
        if loc:
            self._voice.speak(
                f"Sir, based on your IP address you appear to be in "
                f"{loc['city']}, {loc['region']}, {loc['country']}."
            )
        else:
            self._voice.speak(
                "I couldn't detect your location automatically, Sir. "
                "Please tell me which city you are in."
            )

    # ── Full travel guide for a city ──────────────────────────────────────────
    def travel_guide(self, city: str) -> None:
        """Give a complete travel guide for a city using AI."""
        self._voice.speak(
            f"Let me prepare a full travel guide for {city}, Sir. One moment."
        )
        guide = self._ask_ai(
            f"Act as an expert local tour guide for {city}. "
            f"Give me a complete guide covering:\n"
            f"1. Top 5 tourist attractions\n"
            f"2. Best hotels (budget + luxury)\n"
            f"3. Famous local food to eat\n"
            f"4. Famous temples / devotional places\n"
            f"5. Best restaurants\n"
            f"6. Best parks and nature spots\n"
            f"7. Shopping areas\n"
            f"8. Travel tips\n"
            f"Be specific, helpful, and friendly. Address the user as Sir."
        )
        self._voice.speak(guide[:500])   # speak first 500 chars
        print(f"\n[STARK Travel Guide — {city}]\n{'─'*50}\n{guide}\n{'─'*50}\n")

    # ── Specific searches ─────────────────────────────────────────────────────
    def find_hotels(self, city: str, budget: str = "any") -> None:
        self._voice.speak(f"Finding hotels in {city}, Sir.")
        result = self._ask_ai(
            f"List the top 5 best hotels in {city} for a {budget} budget. "
            f"Include name, approximate price per night in INR, and why it's recommended. "
            f"Address the user as Sir."
        )
        self._voice.speak(result[:400])
        print(f"\n[Hotels in {city}]\n{result}\n")

        # Open Google Maps hotels search
        query = urllib.parse.quote(f"hotels in {city}")
        webbrowser.open(f"https://www.google.com/maps/search/{query}")

    def find_restaurants(self, city: str, food_type: str = "") -> None:
        self._voice.speak(f"Finding restaurants in {city}, Sir.")
        result = self._ask_ai(
            f"List the top 5 best restaurants in {city}"
            + (f" for {food_type} food" if food_type else "") +
            f". Include name, specialty dish, and price range. Address as Sir."
        )
        self._voice.speak(result[:400])
        print(f"\n[Restaurants in {city}]\n{result}\n")

        query = urllib.parse.quote(f"best restaurants in {city} {food_type}")
        webbrowser.open(f"https://www.google.com/maps/search/{query}")

    def find_local_food(self, city: str) -> None:
        self._voice.speak(f"Let me tell you about famous local food in {city}, Sir.")
        result = self._ask_ai(
            f"What are the most famous local foods, street foods, and must-eat dishes "
            f"in {city}? List top 8 with a short description of each. Address as Sir."
        )
        self._voice.speak(result[:400])
        print(f"\n[Local Food — {city}]\n{result}\n")

    def find_temples(self, city: str) -> None:
        self._voice.speak(f"Searching for devotional and temple places in {city}, Sir.")
        result = self._ask_ai(
            f"List the most famous temples, mosques, churches, and devotional places "
            f"in {city}. Include the deity/religion, significance, and visiting hours if known. "
            f"Address as Sir."
        )
        self._voice.speak(result[:400])
        print(f"\n[Devotional Places — {city}]\n{result}\n")

        query = urllib.parse.quote(f"famous temples in {city}")
        webbrowser.open(f"https://www.google.com/maps/search/{query}")

    def find_tourist_spots(self, city: str) -> None:
        self._voice.speak(f"Finding top tourist attractions in {city}, Sir.")
        result = self._ask_ai(
            f"List the top 10 must-visit tourist attractions in {city}. "
            f"Include a short description and the best time to visit each. Address as Sir."
        )
        self._voice.speak(result[:400])
        print(f"\n[Tourist Spots — {city}]\n{result}\n")

        query = urllib.parse.quote(f"tourist attractions in {city}")
        webbrowser.open(f"https://www.google.com/maps/search/{query}")

    def find_parks(self, city: str) -> None:
        self._voice.speak(f"Finding parks and nature spots in {city}, Sir.")
        result = self._ask_ai(
            f"List the best parks, gardens, lakes, and nature spots in {city}. "
            f"Include entry fees if any and best time to visit. Address as Sir."
        )
        self._voice.speak(result[:300])
        print(f"\n[Parks — {city}]\n{result}\n")

    def find_museums(self, city: str) -> None:
        self._voice.speak(f"Searching museums in {city}, Sir.")
        result = self._ask_ai(
            f"List the best museums, historical sites, and cultural places in {city}. "
            f"Include a brief description of each. Address as Sir."
        )
        self._voice.speak(result[:300])
        print(f"\n[Museums — {city}]\n{result}\n")

    # ── Weather ───────────────────────────────────────────────────────────────
    def get_weather(self, city: str) -> None:
        self._voice.speak(f"Checking weather for {city}, Sir.")
        try:
            resp = requests.get(
                f"https://wttr.in/{urllib.parse.quote(city)}?format=3",
                timeout=5,
            )
            if resp.status_code == 200:
                weather = resp.text.strip()
                self._voice.speak(f"Current weather in {city}: {weather}, Sir.")
                print(f"[Weather] {weather}")
            else:
                raise Exception("API failed")
        except Exception:
            result = self._ask_ai(f"What is the typical weather like in {city}? Be brief. Address as Sir.")
            self._voice.speak(result)

    # ── Open Google Maps ──────────────────────────────────────────────────────
    def open_maps(self, query: str) -> None:
        q = urllib.parse.quote(query)
        webbrowser.open(f"https://www.google.com/maps/search/{q}")
        self._voice.speak(f"Opened Google Maps for {query}, Sir.")

    def open_directions(self, destination: str) -> None:
        q = urllib.parse.quote(destination)
        webbrowser.open(f"https://www.google.com/maps/dir/?api=1&destination={q}")
        self._voice.speak(f"Opening directions to {destination}, Sir.")

    # ── Trip planner ──────────────────────────────────────────────────────────
    def plan_trip(self, city: str, days: int = 2) -> None:
        self._voice.speak(
            f"Planning a {days}-day trip to {city} for you, Sir. Please wait."
        )
        plan = self._ask_ai(
            f"Create a detailed {days}-day travel itinerary for {city}. "
            f"Include morning, afternoon, and evening activities for each day. "
            f"Include food recommendations for each meal. "
            f"Include estimated costs in INR where possible. "
            f"Make it practical and enjoyable. Address as Sir."
        )
        self._voice.speak(
            f"Your {days}-day trip plan for {city} is ready, Sir. "
            f"I am displaying it now."
        )
        print(f"\n[STARK Trip Plan — {city} — {days} days]\n{'═'*54}\n{plan}\n{'═'*54}\n")