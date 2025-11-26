import requests
from datetime import datetime
from typing import Optional, Tuple, Dict
import logging

logger = logging.getLogger(__name__)

def get_weather_icon(condition_main: str, condition_id: int) -> str:
    if condition_id >= 200 and condition_id < 300:
        return "bi-cloud-lightning-rain"
    elif condition_id >= 300 and condition_id < 400:
        return "bi-cloud-drizzle"
    elif condition_id >= 500 and condition_id < 600:
        if condition_id == 500 or condition_id == 520:
            return "bi-cloud-rain"
        else:
            return "bi-cloud-rain-heavy"
    elif condition_id >= 600 and condition_id < 700:
        return "bi-cloud-snow"
    elif condition_id >= 700 and condition_id < 800:
        return "bi-cloud-fog"
    elif condition_id == 800:
        return "bi-brightness-high"
    elif condition_id in [801, 802]:
        return "bi-cloud-sun"
    elif condition_id in [803, 804]:
        return "bi-cloud"
    return "bi-cloud"

def fetch_current_weather(lat: float, lon: float, api_key: str) -> Dict:
    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    )
    r = requests.get(url, timeout=8)
    r.raise_for_status()
    data = r.json()

    main = data.get("main", {})
    weather = data.get("weather", [{}])[0]
    wind = data.get("wind", {})

    condition_main = weather.get("main", "Unknown")
    condition_desc = weather.get("description", "").title()
    condition_id = weather.get("id", 800)

    return {
        "temp": round(main.get("temp", 0)),
        "feels_like": round(main.get("feels_like", 0)),
        "humidity": main.get("humidity"),
        "wind": round(wind.get("speed", 0) * 3.6, 1),
        "condition": condition_desc,
        "icon": get_weather_icon(condition_main, condition_id),
        "fetched_at": datetime.utcnow().isoformat() + "Z"
    }

def fetch_forecast(lat: float, lon: float, api_key: str, days: int = 5) -> Dict:
    url = (
        f"https://api.openweathermap.org/data/2.5/forecast"
        f"?lat={lat}&lon={lon}&appid={api_key}&units=metric&cnt=40"
    )
    r = requests.get(url, timeout=8)
    r.raise_for_status()
    data = r.json()

    forecast_list = data.get("list", [])
    daily_data: Dict[str, Dict] = {}

    for item in forecast_list:
        dt_txt = item.get("dt_txt", "")
        date = dt_txt.split(" ")[0]

        temp = item.get("main", {}).get("temp")
        temp_min = item.get("main", {}).get("temp_min")
        temp_max = item.get("main", {}).get("temp_max")
        weather = item.get("weather", [{}])[0]
        condition_id = weather.get("id", 800)
        condition_main = weather.get("main", "")

        if date not in daily_data:
            daily_data[date] = {
                "temps": [],
                "mins": [],
                "maxs": [],
                "condition_id": condition_id,
                "condition_main": condition_main
            }

        if temp is not None:
            daily_data[date]["temps"].append(temp)
        if temp_min is not None:
            daily_data[date]["mins"].append(temp_min)
        if temp_max is not None:
            daily_data[date]["maxs"].append(temp_max)

    daily = []
    for date in sorted(daily_data.keys())[:days]:
        day = daily_data[date]
        avg_temp = round(sum(day["temps"]) / len(day["temps"])) if day["temps"] else None
        min_temp = round(min(day["mins"])) if day["mins"] else None
        max_temp = round(max(day["maxs"])) if day["maxs"] else None
        daily.append({
            "date": date,
            "temp": avg_temp,
            "min": min_temp,
            "max": max_temp,
            "condition": day["condition_main"],
            "icon": get_weather_icon(day["condition_main"], day["condition_id"])
        })
    return {"daily": daily}