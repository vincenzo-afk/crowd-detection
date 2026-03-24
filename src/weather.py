"""
Weather-Aware Risk Adjustment.
Pulls local weather data (mocked) and boosts risk levels 
if conditions are unsafe (e.g. high heat + density = heat stress).
"""

import time
import random

class WeatherMonitor:
    def __init__(self, location="Venue Area"):
        self.location = location
        self.current_temp = 25.0
        self.humidity = 50.0
        self.precipitation = 0.0
        self._last_update = 0
        self.update_interval = 300 # seconds
        self._update_weather()
        
    def _update_weather(self):
        """Mock weather API call"""
        # In production this uses OpenWeatherAPI or similar.
        self.current_temp = 25.0 + random.uniform(-2, 10) # 23-35 C
        self.humidity = 50.0 + random.uniform(-10, 40)
        self.precipitation = random.choice([0.0, 0.0, 0.0, 2.5, 10.0]) # usually 0
        self._last_update = time.time()
        
    def get_risk_multiplier(self) -> float:
        if time.time() - self._last_update > self.update_interval:
            self._update_weather()
            
        mult = 1.0
        
        # Heat stress (Heat Index approximation)
        if self.current_temp > 32.0 and self.humidity > 60:
            mult += 0.25
        elif self.current_temp > 35.0:
            mult += 0.35
            
        # Rain causes slipping and crowding under shelters
        if self.precipitation > 5.0:
            mult += 0.15
            
        return round(mult, 2)
        
    def get_weather_data(self) -> dict:
        return {
            "temp": round(self.current_temp, 1),
            "humidity": round(self.humidity, 1),
            "precipitation": round(self.precipitation, 1),
            "risk_mult": self.get_risk_multiplier()
        }
