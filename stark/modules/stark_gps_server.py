"""
STARK GPS Server
─────────────────
Run: python stark_gps_server.py
Then open: stark_gps.html in Chrome
Click "Get My Real Location" → allow location → STARK saves your real GPS

This uses Chrome's GPS (same as Google Maps) — most accurate method.
"""

import http.server
import json
import os
import requests
import webbrowser
import threading
import time

LOCATION_FILE = "stark_location.json"
CONFIG_FILE   = "config.py"
PORT          = 8765


class GPSHandler(http.server.BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path == "/save_location":
            length  = int(self.headers.get("Content-Length", 0))
            body    = self.rfile.read(length)
            data    = json.loads(body)
            lat     = data.get("lat", 0)
            lon     = data.get("lon", 0)

            # Get city from coordinates
            city   = "Tirupati"
            region = "Andhra Pradesh"
            try:
                resp = requests.get(
                    f"https://nominatim.openstreetmap.org/reverse"
                    f"?lat={lat}&lon={lon}&format=json",
                    headers={"User-Agent": "STARK-AI/1.0"}, timeout=5)
                addr = resp.json().get("address", {})
                city   = (addr.get("city") or addr.get("town") or
                          addr.get("village") or addr.get("county", city))
                region = addr.get("state", region)
            except Exception:
                pass

            # Save location cache
            location = {
                "city":      city,
                "region":    region,
                "country":   "India",
                "lat":       lat,
                "lon":       lon,
                "permitted": True,
                "source":    "Browser GPS"
            }
            with open(LOCATION_FILE, "w") as f:
                json.dump(location, f, indent=2)

            # Update config.py
            try:
                cfg = open(CONFIG_FILE).read()
                import re
                if "USER_CITY" in cfg:
                    cfg = re.sub(r'USER_CITY\s*=\s*"[^"]*"',
                                 f'USER_CITY = "{city}"', cfg)
                else:
                    cfg += f'\nUSER_CITY = "{city}"\n'
                if "GPS_LAT" in cfg:
                    cfg = re.sub(r'GPS_LAT\s*=\s*[\d.]+', f'GPS_LAT = {lat}', cfg)
                    cfg = re.sub(r'GPS_LON\s*=\s*[\d.]+', f'GPS_LON = {lon}', cfg)
                else:
                    cfg += f'\nGPS_LAT = {lat}\nGPS_LON = {lon}\n'
                open(CONFIG_FILE,"w").write(cfg)
            except Exception as e:
                print(f"[Config update] {e}")

            print(f"\n✅ Location saved: {city}, {region}")
            print(f"   GPS: {lat:.6f}, {lon:.6f}")

            # Send response
            response = json.dumps({
                "city":   city,
                "region": region,
                "lat":    lat,
                "lon":    lon,
            }).encode()

            self.send_response(200)
            self.send_header("Content-Type",   "application/json")
            self.send_header("Content-Length", len(response))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(response)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress server logs


def main():
    # Start HTTP server
    server = http.server.HTTPServer(("localhost", PORT), GPSHandler)

    print("=" * 50)
    print("  STARK GPS Setup")
    print("=" * 50)
    print(f"\n1. Server started on port {PORT}")
    print(f"2. Opening stark_gps.html in Chrome...")
    print(f"3. Click 'Get My Real Location'")
    print(f"4. Allow location when Chrome asks")
    print(f"5. STARK saves your real GPS automatically")
    print(f"\nPress Ctrl+C when done\n")

    # Open the HTML file in browser after 1 second
    def open_browser():
        time.sleep(1)
        html_path = os.path.abspath("stark_gps.html")
        webbrowser.open(f"file:///{html_path}")

    threading.Thread(target=open_browser, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n✅ GPS server stopped.")
        print(f"   Your location is saved in {LOCATION_FILE}")


if __name__ == "__main__":
    main()