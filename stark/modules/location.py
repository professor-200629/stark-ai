"""
STARK Location Module v4 — Fully Automatic
────────────────────────────────────────────
No manual config needed. STARK detects location automatically:
1. Starts GPS server in background
2. Opens browser silently to get real GPS
3. Updates every time STARK starts
"""

import requests
import webbrowser
import urllib.parse
import threading
import time
import json
import os
import subprocess
import socket


LOCATION_CACHE = "stark_location.json"
GPS_PORT       = 8765


class LocationModule:
    def __init__(self, voice, ask_ai_fn):
        self._voice    = voice
        self._ask_ai   = ask_ai_fn
        self._city     = ""
        self._lat      = 0.0
        self._lon      = 0.0
        self._region   = ""
        self._country  = "India"
        self._detected = False
        self._tracking = False
        self._permitted= True

        # Load cache first for instant use
        self._load_cache()

        # Auto-detect in background — don't block startup
        threading.Thread(target=self._auto_detect, daemon=True).start()
        print("[STARK Location] Initialised — auto-detecting...")

    # ── Cache ─────────────────────────────────────────────────────────────────
    def _load_cache(self):
        if os.path.exists(LOCATION_CACHE):
            try:
                data = json.load(open(LOCATION_CACHE))
                self._city     = data.get("city","")
                self._lat      = data.get("lat", 0.0)
                self._lon      = data.get("lon", 0.0)
                self._region   = data.get("region","")
                self._country  = data.get("country","India")
                self._detected = bool(self._lat and self._lon)
                if self._detected:
                    print(f"[Location] Loaded: {self._city} ({self._lat:.4f},{self._lon:.4f})")
            except Exception:
                pass

    def _save_cache(self):
        try:
            json.dump({
                "city":    self._city,
                "lat":     self._lat,
                "lon":     self._lon,
                "region":  self._region,
                "country": self._country,
                "permitted": True,
            }, open(LOCATION_CACHE,"w"), indent=2)
        except Exception:
            pass

    # ── Auto detect on startup ────────────────────────────────────────────────
    def _auto_detect(self):
        """
        Runs on startup in background:
        1. Try Windows GPS
        2. Try IP location
        3. Start background GPS server for Chrome GPS
        """
        # Step 1: Windows GPS
        gps = self._get_windows_gps()
        if gps:
            self._update_from_gps(gps["lat"], gps["lon"], "Windows GPS")
            return

        # Step 2: IP location (fast, always works)
        self._detect_from_ip()

        # Step 3: Start GPS server in background for Chrome GPS
        # (more accurate — will update silently)
        threading.Thread(target=self._run_gps_server, daemon=True).start()

    # ── Windows GPS ───────────────────────────────────────────────────────────
    def _get_windows_gps(self) -> dict:
        try:
            ps = (
                "Add-Type -AssemblyName System.Device; "
                "$w = New-Object System.Device.Location.GeoCoordinateWatcher('High'); "
                "$w.Start($false); "
                "$t = [DateTime]::Now.AddSeconds(10); "
                "while($w.Status -ne 'Ready' -and [DateTime]::Now -lt $t)"
                "{Start-Sleep -Milliseconds 500}; "
                "Start-Sleep -Seconds 2; "
                "$c = $w.Position.Location; "
                "if(-not $c.IsUnknown){"
                "Write-Output ($c.Latitude.ToString() + ',' + $c.Longitude.ToString())"
                "}; $w.Stop()"
            )
            r = subprocess.run(["powershell","-Command",ps],
                capture_output=True, text=True, timeout=15)
            out = r.stdout.strip()
            if out and "," in out:
                lat = float(out.split(",")[0])
                lon = float(out.split(",")[1])
                if lat != 0.0 and lon != 0.0 and abs(lat) < 90:
                    return {"lat": lat, "lon": lon}
        except Exception as e:
            print(f"[Windows GPS] {e}")
        return {}

    # ── IP location ───────────────────────────────────────────────────────────
    def _detect_from_ip(self):
        try:
            # Use multiple IP services for better accuracy
            services = [
                "http://ip-api.com/json/",
                "https://ipapi.co/json/",
            ]
            for url in services:
                try:
                    resp = requests.get(url, timeout=5)
                    data = resp.json()
                    lat  = float(data.get("lat") or data.get("latitude") or 0)
                    lon  = float(data.get("lon") or data.get("longitude") or 0)
                    if lat and lon:
                        # Don't override city from IP — use USER_CITY from config
                        try:
                            import config as _cfg
                            city = getattr(_cfg, "USER_CITY", "") or data.get("city","")
                        except Exception:
                            city = data.get("city","Tirupati")
                        region  = data.get("regionName") or data.get("region","")
                        country = data.get("country","India")
                        self._lat     = lat
                        self._lon     = lon
                        self._city    = city
                        self._region  = region
                        self._country = country
                        self._detected = True
                        self._save_cache()
                        print(f"[Location IP] {self._city} ({lat:.4f},{lon:.4f})")
                        return
                except Exception:
                    continue
        except Exception as e:
            print(f"[IP location] {e}")

    # ── GPS server (Chrome GPS — most accurate) ───────────────────────────────
    def _run_gps_server(self):
        """Run background HTTP server to receive GPS from Chrome."""
        import http.server

        location_module = self   # reference for handler

        class GPSHandler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path == "/save_location":
                    try:
                        length = int(self.headers.get("Content-Length",0))
                        data   = json.loads(self.rfile.read(length))
                        lat    = float(data.get("lat",0))
                        lon    = float(data.get("lon",0))
                        if lat and lon:
                            location_module._update_from_gps(lat, lon, "Chrome GPS")
                        resp = json.dumps({"city": location_module._city,
                                          "status":"ok"}).encode()
                        self.send_response(200)
                        self.send_header("Content-Type","application/json")
                        self.send_header("Content-Length",len(resp))
                        self.send_header("Access-Control-Allow-Origin","*")
                        self.end_headers()
                        self.wfile.write(resp)
                    except Exception as e:
                        print(f"[GPS server] {e}")

            def do_OPTIONS(self):
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin","*")
                self.send_header("Access-Control-Allow-Methods","POST,OPTIONS")
                self.send_header("Access-Control-Allow-Headers","Content-Type")
                self.end_headers()

            def log_message(self, *args): pass

        try:
            server = http.server.HTTPServer(("localhost", GPS_PORT), GPSHandler)
            # Open GPS page silently in background
            threading.Thread(
                target=self._open_gps_page, daemon=True).start()
            server.serve_forever()
        except OSError:
            pass   # Port already in use — server already running

    def _open_gps_page(self):
        """Open GPS HTML page silently after 3 seconds."""
        time.sleep(3)
        html = os.path.abspath("stark_gps.html")
        if os.path.exists(html):
            webbrowser.open(f"file:///{html}")

    # ── Update from GPS coords ────────────────────────────────────────────────
    def _update_from_gps(self, lat: float, lon: float, source: str = "GPS"):
        """Update location from real GPS coordinates."""
        self._lat = lat
        self._lon = lon
        # Reverse geocode
        try:
            resp = requests.get(
                f"https://nominatim.openstreetmap.org/reverse"
                f"?lat={lat}&lon={lon}&format=json",
                headers={"User-Agent":"STARK-AI/1.0"}, timeout=5)
            addr = resp.json().get("address",{})
            city = (addr.get("city") or addr.get("town") or
                    addr.get("village") or addr.get("county",""))
            if city:
                self._city   = city
                self._region = addr.get("state","Andhra Pradesh")
        except Exception:
            pass

        # Update config.py automatically
        try:
            import config as _cfg
            cfg_path = "config.py"
            cfg = open(cfg_path).read()
            import re
            for key, val in [("GPS_LAT", str(lat)),
                             ("GPS_LON", str(lon)),
                             ("USER_CITY", f'"{self._city}"')]:
                if key in cfg:
                    cfg = re.sub(rf'{key}\s*=\s*[^\n]+', f'{key} = {val}', cfg)
                else:
                    cfg += f'\n{key} = {val}'
            open(cfg_path,"w").write(cfg)
        except Exception:
            pass

        self._detected = True
        self._save_cache()
        print(f"[{source}] {self._city} ({lat:.4f},{lon:.4f}) — config updated")

    # ── Live tracking ─────────────────────────────────────────────────────────
    def start_tracking(self):
        self._tracking = True
        threading.Thread(target=self._track_loop, daemon=True).start()
        self._voice.speak("Live location tracking started Sir.")

    def stop_tracking(self): self._tracking = False

    def _track_loop(self):
        while self._tracking:
            self._detect_from_ip()
            time.sleep(300)   # update every 5 minutes

    # ── Public methods ────────────────────────────────────────────────────────
    def detect_location(self) -> dict:
        return {
            "city":    self._city or "Tirupati",
            "region":  self._region or "Andhra Pradesh",
            "country": self._country,
            "lat":     self._lat,
            "lon":     self._lon,
        }

    def ask_permission(self) -> bool:
        return True   # Auto-permitted

    def speak_location(self):
        self.detect_location()
        if self._city:
            self._voice.speak(
                f"Sir, you are in {self._city}, {self._region}, {self._country}. "
                f"Coordinates: {self._lat:.4f}, {self._lon:.4f}.")
        else:
            self._voice.speak("Still detecting your location Sir. Please wait a moment.")

    def get_city(self) -> str:
        return self._city or "Tirupati"

    def get_coords(self) -> tuple:
        return (self._lat, self._lon)

    def show_on_map(self):
        if self._lat and self._lon:
            webbrowser.open(f"https://www.google.com/maps?q={self._lat},{self._lon}")
            self._voice.speak(
                f"Opened Google Maps on your current location in {self._city} Sir.")
        else:
            webbrowser.open("https://maps.google.com")
            self._voice.speak("Opened Google Maps Sir.")

    def find_nearby(self, place_type: str, city: str = "") -> None:
        self.detect_location()
        self._voice.speak(f"Searching for {place_type} near your location Sir.")
        if self._lat and self._lon:
            url = (f"https://www.google.com/maps/search/"
                   f"{urllib.parse.quote(place_type)}"
                   f"/@{self._lat},{self._lon},14z")
        else:
            q   = f"{place_type} near {self._city or 'Tirupati'}"
            url = f"https://www.google.com/maps/search/{urllib.parse.quote(q)}"
        webbrowser.open(url)
        self._voice.speak(
            f"Opened Google Maps showing {place_type} near your location Sir. "
            f"Say navigate to go to the nearest one.")

    def navigate_to(self, destination: str) -> None:
        self.detect_location()
        self._voice.speak(f"Opening navigation to {destination} Sir.")
        if self._lat and self._lon:
            url = (f"https://www.google.com/maps/dir/"
                   f"{self._lat},{self._lon}/"
                   f"{urllib.parse.quote(destination)}")
        else:
            url = (f"https://www.google.com/maps/dir/?api=1"
                   f"&destination={urllib.parse.quote(destination)}")
        webbrowser.open(url)

    def search_on_map(self, query: str) -> None:
        webbrowser.open(
            f"https://www.google.com/maps/search/{urllib.parse.quote(query)}")
        self._voice.speak(f"Opened Google Maps for {query} Sir.")

    def get_local_weather(self) -> None:
        city = self._city or "Tirupati"
        try:
            resp = requests.get(
                f"https://wttr.in/{urllib.parse.quote(city)}?format=3",
                timeout=5)
            if resp.status_code == 200:
                self._voice.speak(
                    f"Current weather in {city}: {resp.text.strip()}, Sir.")
        except Exception:
            self._voice.speak(f"Could not get weather Sir.")