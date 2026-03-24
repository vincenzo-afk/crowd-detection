"""
Zone Management Editor module.
Allows operators to configure and store polygonal zones.
"""

import json
import os

ZONE_FILE = "config/zones.json"

class ZoneManager:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.zones = {} # { "A": [[x1, y1], ...], ... }
        self.load()
        
    def load(self):
        if os.path.exists(ZONE_FILE):
            try:
                with open(ZONE_FILE, "r") as f:
                    data = json.load(f)
                    # Check relative bounds
                    if data.get("w") == self.w and data.get("h") == self.h:
                        self.zones = data.get("zones", {})
                    else:
                        print("[ZoneManager] Dimensions changed, discarding old zones.")
            except Exception as e:
                print(f"[ZoneManager] Load error: {e}")
                
    def save(self):
        try:
            os.makedirs(os.path.dirname(ZONE_FILE), exist_ok=True)
            with open(ZONE_FILE, "w") as f:
                json.dump({"w": self.w, "h": self.h, "zones": self.zones}, f)
        except Exception as e:
            print(f"[ZoneManager] Save error: {e}")
            
    def update_zone(self, zone_name: str, polygon: list):
        self.zones[zone_name] = polygon
        self.save()
        
    def delete_zone(self, zone_name: str):
        if zone_name in self.zones:
            del self.zones[zone_name]
            self.save()
            
    def get_all(self):
        return self.zones
